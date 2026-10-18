from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import jwt
from jwt.exceptions import InvalidTokenError
from database import get_db
import models
import auth

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception

    # Check whether user account is active (Task NR-1.1-A-T05)
    if not getattr(user, "is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive or disabled"
        )

    # Check token version for revocable sessions (Task NR-1.1-A-T05)
    token_version = payload.get("tv")
    user_token_version = getattr(user, "token_version", 1)
    if token_version is not None and token_version != user_token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been revoked. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user

def get_current_admin_user(current_user: models.User = Depends(get_current_user)):
    if not getattr(current_user, "is_platform_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform administrator access required"
        )
    return current_user


# ===========================================================================
# Reusable RBAC Permission Dependencies (Task NR-1.1-A-T02)
# ===========================================================================

def require_tenant_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    """
    Dependency that enforces tenant-level administrative write privileges.
    Allows: Platform Superadmin, Tenant Admin.
    """
    if not auth.can_manage_tenant(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant administrator privileges required"
        )
    return current_user

def require_source_manager(current_user: models.User = Depends(get_current_user)) -> models.User:
    """
    Dependency that enforces data source management privileges (databases, documents).
    Allows: Platform Superadmin, Tenant Admin, Developer.
    """
    if not auth.can_manage_sources(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to manage data sources"
        )
    return current_user

def require_query_executor(current_user: models.User = Depends(get_current_user)) -> models.User:
    """
    Dependency that enforces query execution privileges.
    Allows: Platform Superadmin, Tenant Admin, Developer, Business Owner.
    """
    if not auth.can_execute_queries(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to execute queries"
        )
    return current_user

def require_key_manager(current_user: models.User = Depends(get_current_user)) -> models.User:
    """
    Dependency that enforces API key and widget key management privileges.
    Allows: Platform Superadmin, Tenant Admin, Developer.
    """
    if not auth.can_manage_keys(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to manage API keys"
        )
    return current_user


from fastapi.security import APIKeyHeader
from sqlalchemy import or_

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def get_authenticated_api_key(
    raw_api_key: str = Depends(api_key_header),
    db: Session = Depends(get_db)
) -> models.ApiKey:
    """Authenticates external API requests using hashed API keys with plaintext fallback."""
    import hashlib
    if not raw_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header"
        )
    key_hash = hashlib.sha256(raw_api_key.encode("utf-8")).hexdigest()
    api_key = db.query(models.ApiKey).filter(
        or_(models.ApiKey.hashed_key == key_hash, models.ApiKey.key == raw_api_key),
        models.ApiKey.status == "active"
    ).first()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key"
        )
    api_key.total_requests = (api_key.total_requests or 0) + 1
    api_key.last_used_at = models.utc_now()
    db.commit()
    return api_key



