import models
from services.crypto_service import encrypt_secret, decrypt_secret
from services.connection_factory import DatabaseConnectionFactory


def encrypt_password(plain_pwd: str) -> str:
    if not plain_pwd:
        return plain_pwd
    return encrypt_secret(plain_pwd) or plain_pwd


def decrypt_password(enc_pwd: str) -> str:
    if not enc_pwd:
        return enc_pwd
    return decrypt_secret(enc_pwd) or enc_pwd


def get_connection_url(db_conn: models.DatabaseConnection) -> str | None:
    if not db_conn:
        return None
    try:
        url = DatabaseConnectionFactory.build_connection_url(
            db_type=db_conn.db_type,
            host=db_conn.host,
            port=db_conn.port,
            database=db_conn.database,
            username=db_conn.username,
            password=db_conn.password,
        )
        return url.render_as_string(hide_password=False)
    except Exception:
        # Fallback for unconfigured or custom endpoints
        return None

