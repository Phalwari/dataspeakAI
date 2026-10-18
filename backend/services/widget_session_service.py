import os
import secrets
import jwt
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from urllib.parse import urlsplit
from fastapi import Request, HTTPException, status

_RUNTIME_FALLBACK_SECRET: Optional[str] = None

def get_widget_hmac_secret() -> str:
    global _RUNTIME_FALLBACK_SECRET
    env = os.getenv("ENVIRONMENT", "development").lower()
    secret = os.getenv("WIDGET_HMAC_SECRET")
    if env == "production":
        if not secret:
            raise RuntimeError(
                "CRITICAL SECURITY CONFIGURATION ERROR: WIDGET_HMAC_SECRET must be explicitly set when ENVIRONMENT=production. Application startup aborted."
            )
        return secret
    if secret:
        return secret
    secret_key = os.getenv("SECRET_KEY")
    if secret_key:
        return secret_key
    if not _RUNTIME_FALLBACK_SECRET:
        _RUNTIME_FALLBACK_SECRET = secrets.token_hex(32)
    return _RUNTIME_FALLBACK_SECRET

def normalize_origin(origin: Optional[str]) -> Optional[str]:
    if not origin:
        return None
    origin_str = origin.strip().rstrip("/").lower()
    return origin_str if origin_str else None

def extract_request_origin(request: Request) -> Optional[str]:
    # 1. Primary: Origin header
    origin = request.headers.get("origin")
    if origin:
        norm = normalize_origin(origin)
        if norm:
            return norm

    # 2. Fallback: Referer header
    referer = request.headers.get("referer")
    if referer:
        try:
            parsed = urlsplit(referer)
            if parsed.scheme and parsed.netloc:
                return normalize_origin(f"{parsed.scheme}://{parsed.netloc}")
        except Exception:
            pass

    return None

def is_origin_allowed(origin: Optional[str], allowed_origins: Optional[List[str]]) -> bool:
    if not origin or not allowed_origins:
        # Empty allowlist or missing origin = deny all
        return False

    norm_req = normalize_origin(origin)
    if not norm_req:
        return False

    for allowed in allowed_origins:
        norm_allowed = normalize_origin(allowed)
        if not norm_allowed or norm_allowed == "*":
            # Wildcard strictly disallowed/ignored
            continue
        if norm_req == norm_allowed:
            return True

    return False

def create_widget_session_token(
    tenant_id: int,
    public_key: str,
    origin: str,
    conversation_id: int,
    widget_key_id: Optional[int] = None,
    visitor_id: Optional[str] = None,
    allow_sql: bool = False,
    expires_minutes: int = 60
) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=expires_minutes)
    payload = {
        "sub": "widget_session",
        "tenant_id": tenant_id,
        "widget_key_id": widget_key_id,
        "visitor_id": visitor_id or secrets.token_hex(16),
        "public_key": public_key,
        "origin": normalize_origin(origin),
        "conversation_id": conversation_id,
        "allow_sql": allow_sql,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": secrets.token_hex(16)
    }
    return jwt.encode(payload, get_widget_hmac_secret(), algorithm="HS256")

def verify_widget_session_token(token: str, expected_origin: Optional[str] = None) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, get_widget_hmac_secret(), algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Widget session token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid widget session token"
        )

    if payload.get("sub") != "widget_session":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject"
        )

    required_claims = ["tenant_id", "conversation_id", "public_key"]
    for claim in required_claims:
        if claim not in payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Missing required session claim: {claim}"
            )

    if expected_origin:
        token_origin = normalize_origin(payload.get("origin"))
        expected_norm = normalize_origin(expected_origin)
        if token_origin != expected_norm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Origin mismatch for widget session token"
            )

    return payload

def create_widget_continuity_token(
    tenant_id: int,
    widget_key_id: int,
    public_key: str,
    visitor_id: str,
    conversation_id: int,
    expires_days: int = 30
) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(days=expires_days)
    payload = {
        "sub": "visitor_continuity",
        "tenant_id": tenant_id,
        "widget_key_id": widget_key_id,
        "visitor_id": visitor_id,
        "public_key": public_key,
        "conversation_id": conversation_id,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": secrets.token_hex(16)
    }
    return jwt.encode(payload, get_widget_hmac_secret(), algorithm="HS256")

def verify_widget_continuity_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, get_widget_hmac_secret(), algorithms=["HS256"])
        if payload.get("sub") != "visitor_continuity":
            return None
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
