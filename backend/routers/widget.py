import os
import time
import json
import requests
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse, HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import ipaddress
import models, schemas
from database import get_db
from services.widget_session_service import (
    extract_request_origin,
    is_origin_allowed,
    create_widget_session_token,
    verify_widget_session_token
)
from services.widget_rate_limiter import widget_limiter
from services.sql_engine import validate_widget_sql, generate_sql_from_nl, execute_safe_sql

router = APIRouter(prefix="/api/widget", tags=["widget"])

def _is_ip_in_trusted_proxies(ip_str: str, trusted_proxies_cfg: Optional[str] = None) -> bool:
    cfg = trusted_proxies_cfg if trusted_proxies_cfg is not None else os.getenv("TRUSTED_PROXIES", "")
    if not cfg or not cfg.strip():
        return False
    try:
        target_ip = ipaddress.ip_address(ip_str.strip())
    except ValueError:
        return False

    for item in cfg.split(","):
        token = item.strip()
        if not token:
            continue
        try:
            if "/" in token:
                net = ipaddress.ip_network(token, strict=False)
                if target_ip in net:
                    return True
            else:
                trusted_ip = ipaddress.ip_address(token)
                if target_ip == trusted_ip:
                    return True
        except ValueError:
            continue
    return False


def extract_client_ip(request: Request, trusted_proxies_cfg: Optional[str] = None) -> str:
    """
    Extracts the authenticated client IP safely against X-Forwarded-For spoofing (SEC-03).
    - If request.client is None, defaults to '127.0.0.1'.
    - If request.client.host is NOT in TRUSTED_PROXIES (or TRUSTED_PROXIES is unset),
      request.client.host is returned directly. X-Forwarded-For headers from untrusted clients
      are strictly ignored to prevent rate limiter bypass.
    - If request.client.host IS in TRUSTED_PROXIES, walks X-Forwarded-For backwards from right
      to left, returning the right-most untrusted IP in the proxy chain.
    """
    direct_host = request.client.host if request.client else "127.0.0.1"
    
    if not _is_ip_in_trusted_proxies(direct_host, trusted_proxies_cfg):
        return direct_host

    forwarded = request.headers.get("x-forwarded-for")
    if not forwarded:
        return direct_host

    entries = [x.strip() for x in forwarded.split(",") if x.strip()]
    if not entries:
        return direct_host

    # Walk from right to left (closest to trusted proxy) to find the right-most untrusted entry
    for entry in reversed(entries):
        if not _is_ip_in_trusted_proxies(entry, trusted_proxies_cfg):
            try:
                ipaddress.ip_address(entry)
                return entry
            except ValueError:
                continue

    return entries[0]


# -------------------------------------------------------------
# PII Column Masking Helper
# -------------------------------------------------------------
def mask_pii_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    sensitive_keys = {"password", "hashed_password", "secret", "token", "api_key", "ssn", "salt"}
    sanitized = []
    for row in rows:
        masked_row = {}
        for k, v in row.items():
            if any(s in str(k).lower() for s in sensitive_keys):
                masked_row[k] = "[REDACTED]"
            else:
                masked_row[k] = v
        sanitized.append(masked_row)
    return sanitized


def get_client_ip(request: Request) -> str:
    """
    Extracts the client IP address. Only trusts the X-Forwarded-For header if
    request.client.host matches a configured trusted proxy list (SEC-03).
    """
    remote_host = request.client.host if request.client else "127.0.0.1"
    raw_trusted = os.getenv("TRUSTED_PROXIES", "127.0.0.1,::1")
    trusted_proxies = {p.strip() for p in raw_trusted.split(",") if p.strip()}

    if remote_host in trusted_proxies:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            candidate = forwarded.split(",")[0].strip()
            if candidate:
                return candidate
    return remote_host


# -------------------------------------------------------------
# Handshake Endpoint (Stage A)
# -------------------------------------------------------------
@router.post("/session", response_model=schemas.WidgetSessionResponse)
def create_widget_session(
    session_req: schemas.WidgetSessionRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Validates public widget key + origin, returns HMAC-signed short-lived session token.
    """
    origin = extract_request_origin(request)
    if not origin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing or invalid Origin / Referer header"
        )

    now = datetime.now(timezone.utc)
    widget_key = db.query(models.WidgetKey).filter(
        (models.WidgetKey.public_key == session_req.public_key) |
        (
            (models.WidgetKey.previous_key == session_req.public_key) &
            (models.WidgetKey.previous_key_expires_at > now)
        )
    ).first()

    if not widget_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired widget key"
        )

    if not widget_key.enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Widget key is disabled or revoked"
        )

    if not is_origin_allowed(origin, widget_key.allowed_origins):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Origin not permitted for this widget key"
        )

    conv = None
    if session_req.conversation_id:
        conv = db.query(models.Conversation).filter(
            models.Conversation.id == session_req.conversation_id,
            models.Conversation.tenant_id == widget_key.tenant_id
        ).first()

    if not conv:
        conv = models.Conversation(
            tenant_id=widget_key.tenant_id,
            title="Widget Chat",
            platform="widget"
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

    expires_minutes = 60
    session_token = create_widget_session_token(
        tenant_id=widget_key.tenant_id,
        public_key=widget_key.public_key,
        origin=origin,
        conversation_id=conv.id,
        allow_sql=bool(widget_key.allow_sql),
        expires_minutes=expires_minutes
    )

    response.headers["Vary"] = "Origin"

    return schemas.WidgetSessionResponse(
        session_token=session_token,
        expires_in=expires_minutes * 60,
        tenant_id=widget_key.tenant_id,
        conversation_id=conv.id
    )


# -------------------------------------------------------------
# Public-Safe Configuration Endpoint (Stage B)
# -------------------------------------------------------------
@router.get("/config", response_model=schemas.WidgetConfigResponse)
def get_widget_config(
    key: Optional[str] = None,
    request: Request = None,
    response: Response = None,
    db: Session = Depends(get_db)
):
    """
    Returns public-safe branding configuration for the widget.
    Guaranteed to never expose internal IDs, secrets, or database connection strings.
    """
    public_key = key
    if not public_key and request:
        auth_hdr = request.headers.get("authorization")
        if auth_hdr and auth_hdr.startswith("Bearer "):
            token = auth_hdr.split(" ", 1)[1]
            try:
                claims = verify_widget_session_token(token)
                public_key = claims.get("public_key")
            except Exception:
                pass

    if not public_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Public widget key parameter 'key' or session token is required"
        )

    now = datetime.now(timezone.utc)
    widget_key = db.query(models.WidgetKey).filter(
        (models.WidgetKey.public_key == public_key) |
        (
            (models.WidgetKey.previous_key == public_key) &
            (models.WidgetKey.previous_key_expires_at > now)
        )
    ).first()

    if not widget_key or not widget_key.enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Widget key not found or disabled"
        )

    if request:
        origin = extract_request_origin(request)
        if origin and not is_origin_allowed(origin, widget_key.allowed_origins):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Origin not permitted for this widget key"
            )

    cfg = db.query(models.ChatbotConfig).filter(
        models.ChatbotConfig.tenant_id == widget_key.tenant_id
    ).first()

    if response:
        response.headers["Vary"] = "Origin"

    if cfg:
        return schemas.WidgetConfigResponse(
            theme_color=cfg.theme_color or "#3b82f6",
            widget_title=cfg.widget_title or "AI Assistant",
            greeting_message=cfg.greeting_message or "Hello! How can I help you today?",
            position=cfg.position or "bottom-right",
            welcome_delay=cfg.welcome_delay or 1,
            sound_enabled=bool(cfg.sound_enabled)
        )

    return schemas.WidgetConfigResponse()


# -------------------------------------------------------------
# Chat Processing Implementation (Shared between /api/widget/chat & /api/chat/widget)
# -------------------------------------------------------------
def process_widget_chat(
    req: schemas.WidgetChatRequest,
    request: Request,
    db: Session
):
    # 1. Extract session token
    token = req.session_token
    auth_hdr = request.headers.get("authorization")
    if not token and auth_hdr and auth_hdr.startswith("Bearer "):
        token = auth_hdr.split(" ", 1)[1]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Widget session token is required"
        )

    # 2. Extract and verify origin
    origin = extract_request_origin(request)
    if not origin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing or invalid Origin header for widget chat"
        )
    claims = verify_widget_session_token(token, expected_origin=origin)

    tenant_id = claims["tenant_id"]
    public_key = claims["public_key"]
    session_conv_id = claims["conversation_id"]

    # 3. Rate limiting checks (Key, IP, Session)
    client_ip = extract_client_ip(request)

    allowed, retry_after = widget_limiter.check_rate_limits(
        public_key=public_key,
        client_ip=client_ip,
        session_id=str(session_conv_id)
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)}
        )

    # 4. Key status & active origin re-validation (so revoking a key or removing an origin kills live sessions)
    widget_key = db.query(models.WidgetKey).filter(models.WidgetKey.public_key == public_key).first()
    if not widget_key or not widget_key.enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Widget key is disabled or revoked"
        )

    if not is_origin_allowed(origin, widget_key.allowed_origins):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Origin is not in allowed origins for this widget key"
        )

    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    current_month_usage = db.query(models.QueryLog).filter(
        models.QueryLog.widget_key_id == widget_key.id,
        models.QueryLog.source == "widget",
        models.QueryLog.created_at >= month_start
    ).count()

    cap = widget_key.monthly_message_cap or 1000
    if current_month_usage >= cap:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Monthly message quota exceeded for this widget",
            headers={"Retry-After": "86400"}
        )

    # 5. Conversation resolution
    conv = None
    target_conv_id = req.conversation_id or session_conv_id
    if target_conv_id:
        conv = db.query(models.Conversation).filter(
            models.Conversation.id == target_conv_id,
            models.Conversation.tenant_id == tenant_id
        ).first()

    if not conv:
        conv = models.Conversation(
            tenant_id=tenant_id,
            title="Widget Chat",
            platform="widget"
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

    user_query = req.query.strip()
    if not user_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    # Record user message
    user_msg = models.Message(
        conversation_id=conv.id,
        sender_role="user",
        content=user_query,
        sanitized_content=user_query,
        query_type="user"
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # Load conversation history for multi-turn context
    from routers.chat import retrieve_rag_chunks, build_conversation_history_text
    past_messages = db.query(models.Message).filter(
        models.Message.conversation_id == conv.id,
        models.Message.id != user_msg.id
    ).order_by(models.Message.created_at.asc()).all()
    history_text = build_conversation_history_text(past_messages, max_messages=8)

    citations: List[schemas.SourceCitation] = []
    assistant_answer = ""
    route_type = "rag"
    start_time = time.time()
    gemini_api_key = os.getenv("GEMINI_API_KEY")

    # 6. SQL Security Policy Evaluation
    allow_sql = bool(widget_key.allow_sql)
    sql_executed = False

    # Detect if query explicitly requests database operations
    db_keywords = ["sql", "database", "table", "records", "query", "select", "rows"]
    is_asking_db = any(kw in user_query.lower() for kw in db_keywords)

    if allow_sql and is_asking_db and widget_key.allowed_database_ids:
        # Check if database is in allowed_database_ids
        allowed_db_ids = widget_key.allowed_database_ids
        db_conn = db.query(models.DatabaseConnection).filter(
            models.DatabaseConnection.id.in_(allowed_db_ids),
            models.DatabaseConnection.tenant_id == tenant_id
        ).first()

        if db_conn:
            nl_res = generate_sql_from_nl(db_conn, user_query, db_session=db)
            gen_sql = nl_res.get("sql", "")
            is_valid, validation_err = validate_widget_sql(gen_sql, allowed_tables=widget_key.allowed_tables)

            if is_valid and gen_sql:
                try:
                    exec_res = execute_safe_sql(db_conn, gen_sql, max_rows=50)
                    sql_executed = True
                    route_type = "sql"

                    # Mask PII from rows before LLM synthesis
                    masked_rows = mask_pii_rows(exec_res.get("rows", []))
                    rows_summary = json.dumps(masked_rows[:10], indent=2)

                    if gemini_api_key:
                        try:
                            prompt = (
                                "You are DataSpeakAI, a secure conversational assistant.\n"
                                f"{history_text}\n"
                                f"User Question: {user_query}\n"
                                f"Query Result ({exec_res.get('row_count', 0)} matching records):\n{rows_summary}\n\n"
                                "Summarize the key findings directly and clearly for the user. Do not expose internal database table names or raw queries."
                            )
                            gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
                            res = requests.post(
                                f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={gemini_api_key}",
                                json={"contents": [{"parts": [{"text": prompt}]}]},
                                headers={"Content-Type": "application/json"},
                                timeout=25
                            )
                            if res.status_code == 200:
                                assistant_answer = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                        except Exception as e:
                            print(f"Widget Gemini synthesis error: {e}")

                    if not assistant_answer:
                        assistant_answer = f"Found {exec_res.get('row_count', 0)} matching records for your question."

                except Exception as ex:
                    print(f"Widget SQL execution error: {ex}")

    # Fallback to RAG if SQL was not executed
    if not sql_executed:
        route_type = "rag"
        rag_hits = retrieve_rag_chunks(user_query, tenant_id=tenant_id, db=db, top_k=4)

        if rag_hits:
            context_parts = []
            for idx, r in enumerate(rag_hits, 1):
                meta = r.get("metadata", {})
                source_name = meta.get("source", f"Document_{idx}")
                page_num = meta.get("page_number")
                c_type = meta.get("content_type", "text")
                ref_id = meta.get("reference_id")
                content = r.get("content", "").strip()

                citation_obj = schemas.SourceCitation(
                    document_name=source_name,
                    page_number=page_num,
                    content_type=c_type,
                    reference_id=ref_id,
                    snippet=(content[:200] + "...") if len(content) > 200 else content,
                    score=round(r.get("score", 0.0), 3)
                )
                citations.append(citation_obj)
                page_tag = f", p. {page_num}" if page_num else ""
                context_parts.append(f"[{source_name}{page_tag}]\n{content}")

            context_text = "\n\n".join(context_parts)

            if gemini_api_key:
                try:
                    prompt = (
                        "You are DataSpeakAI, a helpful AI assistant for website visitors.\n"
                        f"{history_text}\n"
                        "Answer the visitor's question based strictly on the following knowledge base context.\n"
                        "Rules:\n"
                        "- Provide a clear, natural language explanation.\n"
                        "- Include inline citations like [Source: filename] where relevant.\n"
                        "- If the context does not contain the answer, politely say you don't have that information.\n\n"
                        f"Visitor Question: {user_query}\n\n"
                        f"Context:\n{context_text}"
                    )
                    gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
                    res = requests.post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={gemini_api_key}",
                        json={"contents": [{"parts": [{"text": prompt}]}]},
                        headers={"Content-Type": "application/json"},
                        timeout=25
                    )
                    if res.status_code == 200:
                        assistant_answer = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                except Exception as err:
                    print(f"Widget RAG synthesis note: {err}")

            if not assistant_answer:
                assistant_answer = f"Found relevant information across {len(citations)} document citation(s):\n\n" + "\n".join([f"- {c.snippet} [{c.document_name}]" for c in citations[:2]])
        else:
            assistant_answer = "I'm sorry, I couldn't find relevant information in our knowledge base. Please feel free to ask another question or contact support."

    exec_duration_ms = round((time.time() - start_time) * 1000, 2)

    # 7. Record assistant message and query log
    assistant_msg = models.Message(
        conversation_id=conv.id,
        sender_role="assistant",
        content=assistant_answer,
        sanitized_content=assistant_answer,
        query_type=route_type,
        metadata_json={
            "source": "widget",
            "citations": [c.model_dump() for c in citations]
        }
    )
    db.add(assistant_msg)

    log_entry = models.QueryLog(
        tenant_id=tenant_id,
        widget_key_id=widget_key.id,
        source="widget",
        natural_query=user_query,
        status="success",
        execution_time_ms=exec_duration_ms,
        rows_returned=len(citations) if route_type == "rag" else 1
    )
    db.add(log_entry)
    conv.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(assistant_msg)

    # 8. Return SSE Streaming or JSON
    is_stream = req.stream or (request.headers.get("accept") == "text/event-stream")
    if is_stream:
        # Check concurrent streams cap
        if not widget_limiter.acquire_stream(public_key):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Maximum concurrent streams reached for this widget key",
                headers={"Retry-After": "5"}
            )

        def event_stream_generator():
            try:
                words = assistant_answer.split(" ")
                for i, w in enumerate(words):
                    chunk_text = w + (" " if i < len(words) - 1 else "")
                    payload = json.dumps({"chunk": chunk_text, "done": False})
                    yield f"data: {payload}\n\n"
                    time.sleep(0.015)

                final_payload = json.dumps({
                    "chunk": "",
                    "done": True,
                    "conversation_id": conv.id,
                    "message_id": assistant_msg.id,
                    "sources": [c.model_dump() for c in citations]
                })
                yield f"data: {final_payload}\n\n"
            finally:
                widget_limiter.release_stream(public_key)

        return StreamingResponse(
            event_stream_generator(),
            media_type="text/event-stream",
            headers={"Vary": "Origin", "Cache-Control": "no-cache"}
        )

    return schemas.WidgetChatResponse(
        conversation_id=conv.id,
        message_id=assistant_msg.id,
        query=user_query,
        answer=assistant_answer,
        query_type=route_type,
        sources=citations,
        created_at=assistant_msg.created_at
    )


@router.post("/chat", response_model=schemas.WidgetChatResponse)
def widget_chat_endpoint(
    req: schemas.WidgetChatRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    return process_widget_chat(req, request, db)


@router.get("/embed/{public_key}", response_class=HTMLResponse)
def get_widget_embed_page(public_key: str, request: Request, db: Session = Depends(get_db)):
    """
    Fallback iframe embed page with strictly bound frame-ancestors CSP.
    Restricts embedding exclusively to the origins listed in the widget key's allowlist.
    """
    now = datetime.now(timezone.utc)
    widget_key = db.query(models.WidgetKey).filter(
        (models.WidgetKey.public_key == public_key) |
        (
            (models.WidgetKey.previous_key == public_key) &
            (models.WidgetKey.previous_key_expires_at > now)
        )
    ).first()

    if not widget_key or not widget_key.enabled:
        err_res = HTMLResponse(
            status_code=404,
            content="<html><body><h3 style='font-family:sans-serif;padding:20px;'>Widget key not found or disabled</h3></body></html>"
        )
        err_res.headers["Content-Security-Policy"] = "frame-ancestors 'none';"
        return err_res

    # Check key allowed_origins strictly
    raw_origins = widget_key.allowed_origins or []
    has_invalid = False
    valid_origins = []
    for o in raw_origins:
        try:
            valid_origins.append(schemas.validate_origin_item(o))
        except Exception:
            has_invalid = True
            break

    if has_invalid or not valid_origins:
        denied_res = HTMLResponse(
            status_code=403,
            content="<html><body><h3 style='font-family:sans-serif;padding:20px;'>Widget allowlist contains invalid origins or is empty. Embedding disallowed.</h3></body></html>"
        )
        denied_res.headers["Content-Security-Policy"] = "frame-ancestors 'none';"
        return denied_res

    api_origin = str(request.base_url).rstrip("/")
    ancestors_str = f"'self' {' '.join(valid_origins)}"
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DataSpeakAI Chatbot</title>
  <style>
    body, html {{ margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; background: transparent; }}
  </style>
</head>
<body>
  <script src="{api_origin}/widget.js" data-key="{widget_key.public_key}" data-api="{api_origin}" async></script>
</body>
</html>"""

    res = HTMLResponse(content=html_content)
    res.headers["Content-Security-Policy"] = (
        f"frame-ancestors {ancestors_str}; "
        f"default-src 'self' 'unsafe-inline' {api_origin} http: https: data:; "
        f"script-src 'self' 'unsafe-inline' {api_origin} http: https:; "
        f"connect-src 'self' {api_origin} http: https:; "
        "style-src 'self' 'unsafe-inline';"
    )
    return res

