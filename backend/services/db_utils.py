import os, base64, hashlib
from cryptography.fernet import Fernet
import models

ENCRYPTION_SECRET = os.getenv("SECRET_KEY", "dataspeakai-default-encryption-secret-key-32b")
_FERNET_KEY = base64.urlsafe_b64encode(hashlib.sha256(ENCRYPTION_SECRET.encode()).digest())
_fernet = Fernet(_FERNET_KEY)

def encrypt_password(plain_pwd: str) -> str:
    if not plain_pwd:
        return plain_pwd
    return _fernet.encrypt(plain_pwd.encode()).decode()

def decrypt_password(enc_pwd: str) -> str:
    if not enc_pwd:
        return enc_pwd
    try:
        return _fernet.decrypt(enc_pwd.encode()).decode()
    except Exception:
        # Fallback if stored in plain text prior to encryption
        return enc_pwd

def get_connection_url(db_conn: models.DatabaseConnection) -> str:
    pwd = decrypt_password(db_conn.password)
    if db_conn.db_type == "postgresql":
        return f"postgresql://{db_conn.username}:{pwd}@{db_conn.host}/{db_conn.database}"
    elif db_conn.db_type in ("mysql", "mariadb"):
        return f"mysql+pymysql://{db_conn.username}:{pwd}@{db_conn.host}/{db_conn.database}"
    elif db_conn.db_type == "sqlite":
        path = (db_conn.database if db_conn.database else db_conn.host) or ""
        path = path.strip('"\'').replace("\\", "/")
        return f"sqlite:///{path}"
    return None
