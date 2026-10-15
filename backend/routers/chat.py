from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Tuple
import os
import asyncio
import requests
import json
import datetime
import numpy as np

import models
import schemas
from database import get_db
from dependencies import get_current_user
from services.query_router import classify_query_route, auto_select_database
from services.sql_engine import (
    get_connection_url, get_db_schema_context, generate_sql_from_nl,
    execute_safe_sql
)
from search.bm25_index import BM25IndexManager
from search.hybrid import reciprocal_rank_fusion, cross_encoder_rerank
from services.conversation_memory import ConversationMemoryManager
from services.conversation_title import (
    generate_heuristic_title,
    generate_and_set_conversation_title_in_background
)

router = APIRouter(prefix="/api", tags=["chat"])

# Cached HuggingFace embeddings model
embeddings_model = None

def get_embeddings():
    global embeddings_model
    if embeddings_model is None:
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
        except ImportError:
            from langchain_community.embeddings import HuggingFaceEmbeddings
        embeddings_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    return embeddings_model


def warmup_embeddings() -> bool:
    """Warms up the HuggingFace embeddings model at startup if enabled (default true in prod, false in tests)."""
    import sys
    is_testing = bool(
        os.getenv("PYTEST_CURRENT_TEST")
        or "pytest" in sys.modules
        or any("pytest" in arg.lower() for arg in sys.argv)
    )
    default_warmup = "false" if is_testing else "true"
    warmup_cfg = os.getenv("EMBEDDING_WARMUP", default_warmup).strip().lower()
    if warmup_cfg in ("1", "true", "yes", "on"):
        try:
            get_embeddings()
            return True
        except Exception as e:
            print(f"[EMBEDDING WARMUP] Note: {e}")
            return False
    return False


def retrieve_rag_chunks(query: str, tenant_id: int, db: Session, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Executes hybrid dense-sparse search with RRF fusion across tenant documents.
    Uses versioned index path with fallback, and protects against vector dimension mismatches.
    """
    from routers.documents import resolve_tenant_vector_index_path
    index_path, exists = resolve_tenant_vector_index_path(tenant_id, "all-MiniLM-L6-v2")
    if not exists or not os.path.exists(index_path):
        return []

    emb_model = get_embeddings()
    from langchain_community.vectorstores import FAISS

    try:
        vectorstore = FAISS.load_local(index_path, emb_model, allow_dangerous_deserialization=True)
    except Exception as e:
        print(f"Error loading FAISS index: {e}")
        return []

    # 1. Dense search
    embedding = emb_model.embed_query(query)
    query_vec = np.array([embedding], dtype=np.float32)

    # Dimension mismatch guard (Task 7.2.4)
    if hasattr(vectorstore, "index") and hasattr(vectorstore.index, "d"):
        if vectorstore.index.d != query_vec.shape[1]:
            print(f"[RAG] Dimension mismatch in tenant {tenant_id} index: expected {vectorstore.index.d}, got {query_vec.shape[1]}")
            return []

    scores, indices = vectorstore.index.search(query_vec, 40)

    dense_results = []
    for score, i in zip(scores[0], indices[0]):
        if i == -1:
            continue
        try:
            _id = vectorstore.index_to_docstore_id[int(i)]
            doc = vectorstore.docstore.search(_id)
            if hasattr(doc, "page_content"):
                meta = getattr(doc, "metadata", {}) or {}
                content_str = str(doc.page_content)
            elif isinstance(doc, str):
                meta = {}
                content_str = doc
            else:
                continue
            dense_results.append({
                "content": content_str,
                "metadata": meta,
                "score": float(score)
            })
        except KeyError:
            continue

    # 2. Sparse BM25 search
    sparse_results = []
    try:
        bm25_manager = BM25IndexManager(tenant_id=tenant_id)
        bm25_hits = bm25_manager.search(query, top_k=40)
        for hit in bm25_hits:
            chunk_obj = db.query(models.DocumentChunk).filter(models.DocumentChunk.id == hit["chunk_id"]).first()
            if chunk_obj:
                meta = dict(hit.get("metadata") or {})
                meta["chunk_id"] = chunk_obj.id
                meta["parent_chunk_id"] = chunk_obj.parent_chunk_id
                meta["hierarchy_level"] = chunk_obj.hierarchy_level
                sparse_results.append({
                    "content": chunk_obj.content,
                    "metadata": meta,
                    "score": hit["score"]
                })
    except Exception as e:
        print(f"BM25 search note: {e}")

    # 3. Reciprocal Rank Fusion
    top_results = reciprocal_rank_fusion(dense_results, sparse_results, k=60, top_k=top_k * 2)

    # 4. Optional Cross-Encoder Re-ranking
    if top_results:
        try:
            top_results = cross_encoder_rerank(query, top_results, top_k=top_k)
        except Exception:
            top_results = top_results[:top_k]

    return top_results


def build_grounded_rag_context(
    retrieved_chunks: List[Dict[str, Any]],
    db: Session
) -> Tuple[str, List[schemas.SourceCitation]]:
    """
    Resolves parent chunk context for retrieved child chunks (Task 7.2.2).
    Deduplicates parent sections so surrounding context is provided to the LLM
    without repeating tokens. Retains precise child chunk citations for UI pills.
    """
    context_sections = []
    seen_parent_ids = set()
    citations: List[schemas.SourceCitation] = []

    for idx, r in enumerate(retrieved_chunks, 1):
        meta = r.get("metadata", {}) or {}
        source_name = meta.get("source", f"Document_{idx}")
        page_num = meta.get("page_number")
        c_type = meta.get("content_type", "text")
        ref_id = meta.get("reference_id")
        content = r.get("content", "").strip()
        parent_chunk_id = meta.get("parent_chunk_id")

        citation_obj = schemas.SourceCitation(
            document_name=source_name,
            page_number=page_num,
            content_type=c_type,
            reference_id=ref_id,
            snippet=(content[:220] + "...") if len(content) > 220 else content,
            score=round(float(r.get("score", 0.0)), 3)
        )
        citations.append(citation_obj)

        parent_chunk = None
        if parent_chunk_id and parent_chunk_id not in seen_parent_ids:
            parent_chunk = db.query(models.DocumentChunk).filter(models.DocumentChunk.id == parent_chunk_id).first()
            if parent_chunk:
                seen_parent_ids.add(parent_chunk_id)

        page_tag = f", Page {page_num}" if page_num else ""
        type_tag = f" [{c_type.upper()}]" if c_type != "text" else ""

        if parent_chunk and parent_chunk.content:
            sec_heading = f" - Section: {parent_chunk.section_heading}" if parent_chunk.section_heading else ""
            context_sections.append(
                f"[Document Section #{idx} - Source: {source_name}{page_tag}{sec_heading} (Parent Context)]\n"
                f"{parent_chunk.content.strip()}\n\n"
                f"Specific Matching Passage:\n{content}"
            )
        else:
            context_sections.append(f"[Document Chunk #{idx} - Source: {source_name}{page_tag}{type_tag}]\n{content}")

    context_text = "\n\n".join(context_sections)
    return context_text, citations


def build_conversation_history_text(messages: List[models.Message], max_messages: int = 10, conversation: Optional[models.Conversation] = None) -> str:
    """
    Formats the conversation history for LLM multi-turn context.
    Delegates to ConversationMemoryManager to maintain a single memory mechanism across the platform.
    """
    return ConversationMemoryManager.build_context(conversation, messages, max_recent_turns=max_messages)


@router.get("/conversations", response_model=List[schemas.ConversationListItem])
def list_conversations(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")

    convs = db.query(models.Conversation).filter(
        models.Conversation.tenant_id == current_user.tenant_id
    ).order_by(models.Conversation.updated_at.desc()).all()

    results = []
    for c in convs:
        last_msg = db.query(models.Message).filter(
            models.Message.conversation_id == c.id
        ).order_by(models.Message.created_at.desc()).first()

        count = db.query(models.Message).filter(
            models.Message.conversation_id == c.id
        ).count()

        snippet = None
        if last_msg:
            snippet = (last_msg.content[:75] + "...") if len(last_msg.content) > 75 else last_msg.content

        results.append(schemas.ConversationListItem(
            id=c.id,
            title=c.title,
            platform=c.platform,
            created_at=c.created_at,
            updated_at=c.updated_at,
            last_message=snippet,
            message_count=count
        ))

    return results


@router.get("/conversations/{conversation_id}", response_model=schemas.ConversationResponse)
def get_conversation(
    conversation_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conv = db.query(models.Conversation).filter(
        models.Conversation.id == conversation_id,
        models.Conversation.tenant_id == current_user.tenant_id
    ).first()

    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = db.query(models.Message).filter(
        models.Message.conversation_id == conversation_id
    ).order_by(models.Message.created_at.asc()).all()

    return schemas.ConversationResponse(
        id=conv.id,
        tenant_id=conv.tenant_id,
        user_id=conv.user_id,
        title=conv.title,
        platform=conv.platform,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[schemas.MessageResponse.model_validate(m) for m in messages]
    )


@router.patch("/conversations/{conversation_id}", response_model=schemas.ConversationResponse)
def update_conversation(
    conversation_id: int,
    payload: schemas.ConversationUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conv = db.query(models.Conversation).filter(
        models.Conversation.id == conversation_id,
        models.Conversation.tenant_id == current_user.tenant_id
    ).first()

    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conv.title = payload.title.strip()
    db.commit()
    db.refresh(conv)

    messages = db.query(models.Message).filter(
        models.Message.conversation_id == conversation_id
    ).order_by(models.Message.created_at.asc()).all()

    return schemas.ConversationResponse(
        id=conv.id,
        tenant_id=conv.tenant_id,
        user_id=conv.user_id,
        title=conv.title,
        platform=conv.platform,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[schemas.MessageResponse.model_validate(m) for m in messages]
    )


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conv = db.query(models.Conversation).filter(
        models.Conversation.id == conversation_id,
        models.Conversation.tenant_id == current_user.tenant_id
    ).first()

    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    db.delete(conv)
    db.commit()
    return {"message": "Conversation deleted successfully", "id": conversation_id}


@router.post("/chat", response_model=schemas.ChatResponse)
def chat_endpoint(
    req: schemas.ChatRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Main unified conversational endpoint for DataSpeakAI:
    Handles multi-turn conversation memory, intelligent RAG / SQL / Hybrid routing,
    source citations, and synthesized responses.
    """
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")

    tenant_id: int = int(current_user.tenant_id)
    user_query = req.query.strip()
    if not user_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    is_stream = bool(req.stream) or bool(request and request.headers.get("accept") == "text/event-stream")

    # 1. Manage Conversation Session
    conv = None
    is_new_conversation = False
    initial_title = None
    if req.conversation_id:
        conv = db.query(models.Conversation).filter(
            models.Conversation.id == req.conversation_id,
            models.Conversation.tenant_id == tenant_id
        ).first()

    if not conv:
        is_new_conversation = True
        auto_title = generate_heuristic_title(user_query)
        initial_title = auto_title
        conv = models.Conversation(
            tenant_id=tenant_id,
            user_id=current_user.id,
            title=auto_title,
            platform="web"
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
    else:
        initial_title = conv.title

    conv_id: int = int(conv.id)

    # 2. Record User Message in DB
    user_msg = models.Message(
        conversation_id=conv_id,
        sender_role="user",
        content=user_query,
        sanitized_content=user_query,
        query_type="user"
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # 3. Load Recent Conversation History (ConversationMemoryManager: Task 7.1.4)
    past_messages = db.query(models.Message).filter(
        models.Message.conversation_id == conv_id,
        models.Message.id != user_msg.id
    ).order_by(models.Message.created_at.asc()).all()

    history_text = ConversationMemoryManager.build_context(conv, past_messages)

    # Asynchronously trigger background summarization when threshold is crossed (> 15 turns)
    current_summary_turns = int(conv.summary_turn_count or 0)
    if ConversationMemoryManager.should_trigger_summary(len(past_messages), current_summary_turns):
        if background_tasks is not None:
            background_tasks.add_task(
                ConversationMemoryManager.summarize_in_background,
                conversation_id=conv_id,
                tenant_id=tenant_id
            )
        else:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    ConversationMemoryManager.summarize_in_background(
                        conversation_id=conv_id,
                        tenant_id=tenant_id
                    )
                )
            except RuntimeError:
                pass

    # 4. Route Query (RAG vs SQL vs Hybrid)
    route_decision = classify_query_route(
        query=user_query,
        tenant_id=tenant_id,
        db=db,
        source_preference=req.source_preference,
        explicit_database_id=req.database_id
    )

    route_type = route_decision.route_type
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    citations: List[schemas.SourceCitation] = []
    retrieved_chunks: List[Dict[str, Any]] = []
    sql_response_obj = None
    assistant_answer = ""
    synthesis_prompt = ""
    msg_metadata: Dict[str, Any] = {
        "route_decision": route_decision.to_dict(),
        "sources": []
    }

    # ==========================================
    # BRANCH A: SQL Database Query Execution
    # ==========================================
    if route_type == "sql":
        db_conn = None
        if route_decision.database_id:
            db_conn = db.query(models.DatabaseConnection).filter(
                models.DatabaseConnection.id == route_decision.database_id,
                models.DatabaseConnection.tenant_id == tenant_id
            ).first()

        if not db_conn:
            db_conn = auto_select_database(user_query, tenant_id, db)

        if not db_conn:
            assistant_answer = "No database connection is available for your organization. Please connect a database in the Databases tab or switch source to Knowledge Base."
        else:
            # Generate and execute SQL via Self-Correcting SQLAgent
            nl_res = generate_sql_from_nl(db_conn, user_query, db_session=db)
            msg_metadata["sql_agent"] = {
                "attempts": nl_res.get("attempts", 1),
                "corrections_made": nl_res.get("corrections_made", False)
            }
            if nl_res.get("error"):
                assistant_answer = f"I encountered an issue generating the query: {nl_res['error']}"
                sql_response_obj = schemas.NLQueryResponse(
                    query=user_query,
                    generated_sql="",
                    explanation=nl_res.get("explanation", ""),
                    status="failed",
                    error_detail=nl_res.get("error")
                )
            else:
                gen_sql = nl_res["sql"]
                try:
                    exec_res = execute_safe_sql(db_conn, gen_sql, max_rows=100)
                    sql_response_obj = schemas.NLQueryResponse(
                        query=user_query,
                        generated_sql=gen_sql,
                        explanation=nl_res["explanation"],
                        columns=exec_res["columns"],
                        rows=exec_res["rows"],
                        row_count=exec_res["row_count"],
                        execution_time_ms=exec_res["execution_time_ms"],
                        status="success"
                    )

                    # Synthesize natural response from table results
                    rows_preview = json.dumps(exec_res["rows"][:15], indent=2)
                    synthesis_prompt = (
                        "You are DataSpeakAI, an intelligent conversational Business Intelligence assistant.\n"
                        f"{history_text}\n"
                        f"User Question: {user_query}\n"
                        f"Executed SQL: {gen_sql}\n"
                        f"Execution Result Summary: {exec_res['row_count']} row(s) returned.\n"
                        f"Data Rows (JSON sample):\n{rows_preview}\n\n"
                        "Provide a clear, natural language answer summarizing the key findings directly answering the user's question. Highlight key figures, averages, top entities, or trends concisely."
                    )
                    if not is_stream and gemini_api_key:
                        try:
                            gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
                            gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={gemini_api_key}"
                            payload = {"contents": [{"parts": [{"text": synthesis_prompt}]}]}
                            headers = {"Content-Type": "application/json"}
                            res = requests.post(gemini_url, json=payload, headers=headers, timeout=25)
                            if res.status_code == 200:
                                assistant_answer = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                        except Exception as err:
                            print(f"Gemini SQL synthesis error: {err}")

                    if not assistant_answer:
                        assistant_answer = f"{nl_res['explanation']}\n\nReturned **{exec_res['row_count']}** matching record(s) from database `{db_conn.name}`."

                except Exception as ex:
                    import logging
                    logging.getLogger("dataspeak.chat").error(f"[SQL Execution Error] Database `{db_conn.name}`: {ex}")
                    assistant_answer = "Unable to execute query on the database. An internal database error occurred."
                    sql_response_obj = schemas.NLQueryResponse(
                        query=user_query,
                        generated_sql=gen_sql,
                        explanation=nl_res.get("explanation", ""),
                        status="failed",
                        error_detail="Internal query execution error"
                    )

            # Record in QueryLog
            if sql_response_obj:
                log_entry = models.QueryLog(
                    tenant_id=tenant_id,
                    user_id=current_user.id,
                    database_id=db_conn.id if db_conn else None,
                    natural_query=user_query,
                    generated_sql=sql_response_obj.generated_sql,
                    status=sql_response_obj.status,
                    execution_time_ms=sql_response_obj.execution_time_ms,
                    rows_returned=sql_response_obj.row_count,
                    error_message=sql_response_obj.error_detail
                )
                db.add(log_entry)

    # ==========================================
    # BRANCH B: RAG Document Knowledge Base Search
    # ==========================================
    elif route_type == "rag":
        retrieved_chunks = retrieve_rag_chunks(user_query, tenant_id=tenant_id, db=db, top_k=5)
        
        if not retrieved_chunks:
            assistant_answer = "I searched your Knowledge Base, but found no relevant document chunks matching your question. Please ensure documents have been uploaded and indexed."
        else:
            context_text, citations = build_grounded_rag_context(retrieved_chunks, db)
            synthesis_prompt = (
                "You are DataSpeakAI, an expert Conversational AI Assistant grounded in enterprise knowledge base documents.\n"
                f"{history_text}\n"
                "Based strictly on the document context provided below, synthesize a concise, comprehensive, and clear natural language answer.\n"
                "IMPORTANT CITATION RULES:\n"
                "1. When stating facts, numbers, dates, or concepts, include inline citations in the format [Source: filename, p. X] or [Source: filename].\n"
                "2. If the answer cannot be found in the context, clearly say so rather than hallucinating.\n\n"
                f"User Question: {user_query}\n\n"
                f"Retrieved Document Context:\n{context_text}"
            )

            if not is_stream and gemini_api_key:
                try:
                    gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
                    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={gemini_api_key}"
                    payload = {"contents": [{"parts": [{"text": synthesis_prompt}]}]}
                    headers = {"Content-Type": "application/json"}
                    res = requests.post(gemini_url, json=payload, headers=headers, timeout=30)
                    if res.status_code == 200:
                        assistant_answer = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                except Exception as err:
                    print(f"Gemini RAG synthesis error: {err}")

            if not assistant_answer:
                summary_items = [f"- {c.snippet} [Source: {c.document_name}]" for c in citations[:3]]
                assistant_answer = f"Found relevant information across {len(citations)} document chunk(s):\n\n" + "\n".join(summary_items)

            # Grounding Verification (Task 7.2.3)
            if not is_stream:
                from services.citation_service import citation_service
                grounding_res = citation_service.verify_grounding(
                    response_text=assistant_answer,
                    retrieved_chunks=retrieved_chunks,
                    embedding_model=get_embeddings()
                )
                if grounding_res.get("citations"):
                    citations = grounding_res["citations"]
                msg_metadata["grounding"] = {
                    "confidence": grounding_res.get("grounding_confidence", 0.0),
                    "has_low_confidence": grounding_res.get("has_low_confidence", False),
                    "disclaimer": grounding_res.get("disclaimer"),
                    "verified_claims": grounding_res.get("claims", [])
                }

    # ==========================================
    # BRANCH C: Hybrid Multi-Source Retrieval
    # ==========================================
    elif route_type == "hybrid":
        # 1. RAG Chunks with Parent Context Expansion
        retrieved_chunks = retrieve_rag_chunks(user_query, tenant_id=tenant_id, db=db, top_k=3)
        context_text, citations = build_grounded_rag_context(retrieved_chunks, db)

        # 2. SQL Execution
        db_conn = auto_select_database(user_query, tenant_id, db)
        sql_rows_text = "None"
        if db_conn:
            nl_res = generate_sql_from_nl(db_conn, user_query, db_session=db)
            if not nl_res.get("error"):
                try:
                    exec_res = execute_safe_sql(db_conn, nl_res["sql"], max_rows=50)
                    sql_response_obj = schemas.NLQueryResponse(
                        query=user_query,
                        generated_sql=nl_res["sql"],
                        explanation=nl_res["explanation"],
                        columns=exec_res["columns"],
                        rows=exec_res["rows"],
                        row_count=exec_res["row_count"],
                        execution_time_ms=exec_res["execution_time_ms"],
                        status="success"
                    )
                    sql_rows_text = json.dumps(exec_res["rows"][:10], indent=2)
                except Exception as ex:
                    print(f"Hybrid SQL execution note: {ex}")

        # 3. Unified Synthesis
        if gemini_api_key:
            try:
                synthesis_prompt = (
                    "You are DataSpeakAI, synthesizing an answer using BOTH structured database tables AND document knowledge base files.\n"
                    f"{history_text}\n"
                    f"User Question: {user_query}\n\n"
                    f"Document Context:\n{context_text}\n\n"
                    f"Database Table Results:\n{sql_rows_text}\n\n"
                    "Synthesize a unified, comprehensive answer combining both the numerical database findings and the qualitative document context. Cite document sources using [Source: filename]."
                )
                if not is_stream:
                    gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
                    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={gemini_api_key}"
                    payload = {"contents": [{"parts": [{"text": synthesis_prompt}]}]}
                    headers = {"Content-Type": "application/json"}
                    res = requests.post(gemini_url, json=payload, headers=headers, timeout=30)
                    if res.status_code == 200:
                        assistant_answer = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            except Exception as err:
                print(f"Hybrid synthesis error: {err}")

        if not assistant_answer:
            assistant_answer = f"Synthesized hybrid insights from knowledge base documents and database tables."

        # Grounding Verification (Task 7.2.3)
        if not is_stream and retrieved_chunks:
            from services.citation_service import citation_service
            grounding_res = citation_service.verify_grounding(
                response_text=assistant_answer,
                retrieved_chunks=retrieved_chunks,
                embedding_model=get_embeddings()
            )
            if grounding_res.get("citations"):
                citations = grounding_res["citations"]
            msg_metadata["grounding"] = {
                "confidence": grounding_res.get("grounding_confidence", 0.0),
                "has_low_confidence": grounding_res.get("has_low_confidence", False),
                "disclaimer": grounding_res.get("disclaimer"),
                "verified_claims": grounding_res.get("claims", [])
            }

    # 5. Record Assistant Message in DB
    msg_metadata["sources"] = [c.model_dump() for c in citations]
    if sql_response_obj:
        msg_metadata["sql_data"] = sql_response_obj.model_dump()

    if is_stream:
        from services.chat_stream import stream_chat_response

        def on_stream_complete(full_answer: str) -> int:
            if route_type in ("rag", "hybrid") and retrieved_chunks:
                try:
                    from services.citation_service import citation_service
                    grounding_res = citation_service.verify_grounding(
                        response_text=full_answer,
                        retrieved_chunks=retrieved_chunks,
                        embedding_model=get_embeddings()
                    )
                    if grounding_res.get("citations"):
                        msg_metadata["sources"] = [c.model_dump() for c in grounding_res["citations"]]
                    msg_metadata["grounding"] = {
                        "confidence": grounding_res.get("grounding_confidence", 0.0),
                        "has_low_confidence": grounding_res.get("has_low_confidence", False),
                        "disclaimer": grounding_res.get("disclaimer"),
                        "verified_claims": grounding_res.get("claims", [])
                    }
                except Exception as g_err:
                    print(f"Streaming grounding verification note: {g_err}")

            assistant_msg = models.Message(
                conversation_id=conv_id,
                sender_role="assistant",
                content=full_answer,
                sanitized_content=full_answer,
                query_type=route_type,
                metadata_json=msg_metadata
            )
            db.add(assistant_msg)
            conv.updated_at = datetime.datetime.now(datetime.timezone.utc)
            db.commit()
            db.refresh(assistant_msg)

            # Task 7.1.5: Trigger dynamic background title generation on initial turn
            if is_new_conversation:
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(
                        generate_and_set_conversation_title_in_background(
                            conversation_id=conv_id,
                            tenant_id=tenant_id,
                            user_query=user_query,
                            assistant_answer=full_answer,
                            initial_heuristic_title=initial_title
                        )
                    )
                except RuntimeError:
                    pass

            return int(assistant_msg.id)

        return StreamingResponse(
            stream_chat_response(
                request=request,
                conversation_id=conv_id,
                user_query=user_query,
                prompt=synthesis_prompt,
                tenant_id=tenant_id,
                citations=citations,
                sql_data=sql_response_obj,
                query_type=route_type,
                on_complete=on_stream_complete,
                static_fallback=assistant_answer
            ),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"}
        )

    assistant_msg = models.Message(
        conversation_id=conv_id,
        sender_role="assistant",
        content=assistant_answer,
        sanitized_content=assistant_answer,
        query_type=route_type,
        metadata_json=msg_metadata
    )
    db.add(assistant_msg)
    conv.updated_at = datetime.datetime.now(datetime.timezone.utc)
    db.commit()
    db.refresh(assistant_msg)

    # Task 7.1.5: Trigger dynamic background title generation on initial turn
    if is_new_conversation:
        if background_tasks is not None:
            background_tasks.add_task(
                generate_and_set_conversation_title_in_background,
                conversation_id=conv_id,
                tenant_id=tenant_id,
                user_query=user_query,
                assistant_answer=assistant_answer,
                initial_heuristic_title=initial_title
            )
        else:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    generate_and_set_conversation_title_in_background(
                        conversation_id=conv_id,
                        tenant_id=tenant_id,
                        user_query=user_query,
                        assistant_answer=assistant_answer,
                        initial_heuristic_title=initial_title
                    )
                )
            except RuntimeError:
                pass

    return schemas.ChatResponse(
        conversation_id=conv_id,
        message_id=int(assistant_msg.id),
        user_message_id=int(user_msg.id),
        query=user_query,
        answer=assistant_answer,
        query_type=route_type,
        sources=citations,
        sql_data=sql_response_obj.model_dump() if sql_response_obj else None,
        grounding=msg_metadata.get("grounding"),
        created_at=assistant_msg.created_at
    )


@router.post("/chat/widget", response_model=schemas.WidgetChatResponse)
def widget_chat_endpoint(
    req: schemas.WidgetChatRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    from routers.widget import process_widget_chat
    return process_widget_chat(req, request, db)

