import bcrypt
import jwt
from datetime import datetime, timedelta
import os
import secrets

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    SECRET_KEY = secrets.token_hex(32)
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24))

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# ===========================================================================
# Centralized Tenant Role & Permission Matrix (Task NR-1.1-A-T02)
# ===========================================================================

# Capability Constants
CAP_ADMIN_WRITES = "admin:writes"        # Tenant settings, invite/remove members, update roles
CAP_SOURCE_GRANTS = "source:grants"      # Add/edit/delete DB connections, upload/delete docs
CAP_QUERY_EXECUTE = "query:execute"      # Run SQL queries, execute KPI recipes, preview data
CAP_KEY_MANAGEMENT = "key:management"    # Create/revoke/delete API keys and widget keys
CAP_CONV_SHARE = "conv:share"            # Grant/revoke chat conversation read access

# Role Capabilities Mapping
ROLE_CAPABILITIES = {
    "Admin": {
        CAP_ADMIN_WRITES,
        CAP_SOURCE_GRANTS,
        CAP_QUERY_EXECUTE,
        CAP_KEY_MANAGEMENT,
        CAP_CONV_SHARE,
    },
    "Developer": {
        CAP_SOURCE_GRANTS,
        CAP_QUERY_EXECUTE,
        CAP_KEY_MANAGEMENT,
    },
    "Business Owner": {
        CAP_QUERY_EXECUTE,
        CAP_CONV_SHARE,
    },
    "Viewer": set(),
}

def is_user_active(user) -> bool:
    """Check whether user account is active."""
    if user is None:
        return False
    return bool(getattr(user, "is_active", True))

def can_manage_tenant(user) -> bool:
    """
    Check if user has tenant-level administrative write authority.
    Granted to: Platform Superadmin, Tenant Admin, or Tenant Owner.
    """
    if not is_user_active(user):
        return False
    if getattr(user, "is_platform_admin", False):
        return True
    return getattr(user, "role", None) == "Admin"

def can_manage_sources(user) -> bool:
    """
    Check if user can add, edit, or delete database connections and documents.
    Granted to: Platform Superadmin, Tenant Admin, Developer.
    """
    if not is_user_active(user):
        return False
    if getattr(user, "is_platform_admin", False):
        return True
    return getattr(user, "role", None) in ("Admin", "Developer")

def can_execute_queries(user) -> bool:
    """
    Check if user can execute queries, inspect schema, and run KPI recipes.
    Granted to: Platform Superadmin, Tenant Admin, Developer, Business Owner.
    """
    if not is_user_active(user):
        return False
    if getattr(user, "is_platform_admin", False):
        return True
    return getattr(user, "role", None) in ("Admin", "Developer", "Business Owner")

def can_manage_keys(user) -> bool:
    """
    Check if user can create, list, revoke, and delete API/widget keys.
    Granted to: Platform Superadmin, Tenant Admin, Developer.
    """
    if not is_user_active(user):
        return False
    if getattr(user, "is_platform_admin", False):
        return True
    return getattr(user, "role", None) in ("Admin", "Developer")

def can_share_conversations(user) -> bool:
    """
    Check if user has capability to share conversations.
    Granted to: Platform Superadmin, Tenant Admin, Developer, Business Owner.
    """
    if not is_user_active(user):
        return False
    if getattr(user, "is_platform_admin", False):
        return True
    return getattr(user, "role", None) in ("Admin", "Developer", "Business Owner")

def has_capability(user, capability: str) -> bool:
    """
    Generic capability verification function.
    """
    if not is_user_active(user):
        return False
    if getattr(user, "is_platform_admin", False):
        return True
    role = getattr(user, "role", None)
    return capability in ROLE_CAPABILITIES.get(role, set())

