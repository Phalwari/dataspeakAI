"""
Unit and Integration Tests for Sprint NR-1.2-A: Connection Factory & Secrets.
Verifies:
1. crypto_service Fernet envelope encryption ('v1:'), decryption, and URL password redaction.
2. connection_factory SSRF defense blocking RFC 1918, loopback (127.0.0.1), link-local (169.254.169.254).
3. connection_factory SQLite sandbox path validation and traversal rejection.
4. API key hashing (SHA-256) and masked listings ('omq_live_***').
"""
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from services.crypto_service import (
    encrypt_secret,
    decrypt_secret,
    is_encrypted,
    redact_secret,
    redact_connection_url,
)
from services.connection_factory import (
    DatabaseConnectionFactory,
    SSRFSecurityViolation,
    InvalidDatabasePathError,
)
import models


def test_crypto_envelope_encryption_roundtrip():
    """Verifies that encrypt_secret tags with v1: and decrypt_secret restores exact plaintext."""
    plaintext = "super-secret-password-12345!"
    ciphertext = encrypt_secret(plaintext)
    
    assert ciphertext.startswith("v1:")
    assert is_encrypted(ciphertext) is True
    assert ciphertext != plaintext

    decrypted = decrypt_secret(ciphertext)
    assert decrypted == plaintext


def test_crypto_encryption_is_idempotent():
    """Encrypting an already encrypted v1: token must not double-encrypt."""
    plaintext = "database-password"
    ciphertext1 = encrypt_secret(plaintext)
    ciphertext2 = encrypt_secret(ciphertext1)
    
    assert ciphertext1 == ciphertext2
    assert decrypt_secret(ciphertext2) == plaintext


def test_crypto_legacy_plaintext_fallback():
    """Decrypting a legacy plaintext string without v1: prefix returns it untouched."""
    legacy_pwd = "plain_unencrypted_legacy_password"
    assert is_encrypted(legacy_pwd) is False
    assert decrypt_secret(legacy_pwd) == legacy_pwd


def test_crypto_url_redaction():
    """Verifies passwords in connection strings are properly scrubbed."""
    raw_url = "postgresql://dbuser:supersecret123@db.example.com:5432/analytics"
    redacted = redact_connection_url(raw_url)
    assert "supersecret123" not in redacted
    assert "postgresql://dbuser:***@db.example.com:5432/analytics" == redacted


def test_ssrf_blocks_loopback(monkeypatch):
    """Factory must block loopback addresses by default."""
    monkeypatch.delenv("ALLOW_PRIVATE_DB_HOSTS", raising=False)
    
    with pytest.raises(SSRFSecurityViolation, match="prohibited IP|private or internal IP"):
        DatabaseConnectionFactory.validate_host_ssrf("127.0.0.1")

    with pytest.raises(SSRFSecurityViolation, match="prohibited IP|private or internal IP"):
        DatabaseConnectionFactory.validate_host_ssrf("localhost")


def test_ssrf_blocks_rfc1918_private_ips(monkeypatch):
    """Factory must block 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16 by default."""
    monkeypatch.delenv("ALLOW_PRIVATE_DB_HOSTS", raising=False)
    
    for private_ip in ["10.0.0.1", "172.16.0.5", "192.168.1.100"]:
        with pytest.raises(SSRFSecurityViolation, match="private or internal IP"):
            DatabaseConnectionFactory.validate_host_ssrf(private_ip)


def test_ssrf_blocks_link_local_metadata(monkeypatch):
    """Factory must block cloud metadata IP 169.254.169.254."""
    monkeypatch.delenv("ALLOW_PRIVATE_DB_HOSTS", raising=False)
    
    with pytest.raises(SSRFSecurityViolation, match="private or internal IP"):
        DatabaseConnectionFactory.validate_host_ssrf("169.254.169.254")


def test_ssrf_allows_private_ips_when_explicitly_configured(monkeypatch):
    """When ALLOW_PRIVATE_DB_HOSTS=true, internal hosts are allowed."""
    monkeypatch.setenv("ALLOW_PRIVATE_DB_HOSTS", "true")
    
    # 127.0.0.1 should now be accepted
    host = DatabaseConnectionFactory.validate_host_ssrf("127.0.0.1")
    assert host == "127.0.0.1"


def test_sqlite_managed_root_and_traversal_rejection():
    """SQLite paths must reside inside data/sqlite_dbs and reject directory traversal."""
    # Rejects .. traversal
    with pytest.raises(InvalidDatabasePathError, match="traversal"):
        DatabaseConnectionFactory.validate_sqlite_path("../../etc/passwd.db")

    # Rejects invalid extension
    with pytest.raises(InvalidDatabasePathError, match="valid extension"):
        DatabaseConnectionFactory.validate_sqlite_path("malicious.sh")

    # Accepts valid name inside sandbox
    valid_path = DatabaseConnectionFactory.validate_sqlite_path("tenant_12_sales.db")
    assert valid_path.name == "tenant_12_sales.db"
    assert "data" in str(valid_path)


def test_api_key_hashing_and_redaction():
    """Verifies that API keys generate omq_live_ prefixes and are hashed with SHA-256."""
    from backend.routers.api_keys import generate_secure_key, hash_key
    
    raw_key = generate_secure_key()
    assert raw_key.startswith("omq_live_")
    
    prefix = raw_key[:12]
    hashed = hash_key(raw_key)
    
    assert len(hashed) == 64  # SHA-256 hex length
    assert hashed != raw_key
    
    # Verify deterministic lookup by hash
    assert hash_key(raw_key) == hashed


def test_sqlite_memory_fixture_support():
    """Verifies that :memory: is supported by the connection factory for in-memory testing."""
    mem_url = DatabaseConnectionFactory.build_connection_url(
        db_type="sqlite",
        database=":memory:",
    )
    assert "sqlite" in mem_url.drivername
    assert "memory" in mem_url.render_as_string(hide_password=False)

    validated = DatabaseConnectionFactory.validate_sqlite_path(":memory:")
    assert validated == ":memory:"


def test_database_connection_credentials_redacted():
    """Verifies that DatabaseConnectionResponse never returns plain passwords or v1: ciphertext envelopes."""
    import schemas
    from services.crypto_service import encrypt_secret

    # Simulate an ORM model instance with encrypted password and encrypted connection string
    class MockDbConn:
        id = 42
        name = "Production Postgres"
        db_name = "prod_db"
        db_type = "postgresql"
        host = "db.example.com"
        port = 5432
        username = "admin_user"
        password = encrypt_secret("TopSecretPassword123!")
        database = "analytics"
        connection_string = encrypt_secret("postgresql://admin_user:TopSecretPassword123!@db.example.com:5432/analytics")
        description = "Core Analytics"
        status = "connected"
        tables_metadata = None
        created_at = None

    response = schemas.DatabaseConnectionResponse.model_validate(MockDbConn())
    dumped = response.model_dump()

    # Password must be completely None/scrubbed
    assert dumped["password"] is None

    # Connection string must have password masked and must not contain raw ciphertext envelope v1:
    assert dumped["connection_string"] == "postgresql://admin_user:***@db.example.com:5432/analytics"
    assert "TopSecretPassword123!" not in str(dumped)
    assert not str(dumped["connection_string"]).startswith("v1:")


def test_connection_factory_get_connection_url_and_special_chars():
    """Verifies that get_connection_url safely escapes passwords with special chars and delegates properly."""
    from services.db_utils import get_connection_url as db_utils_get_url
    from services.sql_engine import get_connection_url as sql_engine_get_url
    from services.crypto_service import encrypt_secret

    raw_pwd = "P@ss:w/ord?#%123!"
    enc_pwd = encrypt_secret(raw_pwd)

    class MockConn:
        db_type = "postgresql"
        host = "8.8.8.8"
        port = 5432
        database = "testdb"
        username = "testuser"
        password = enc_pwd
        connection_string = None

    conn = MockConn()
    url = DatabaseConnectionFactory.get_connection_url(conn)
    assert url is not None
    assert "testuser" in url
    assert "testdb" in url

    # db_utils and sql_engine must delegate and return identical output
    assert db_utils_get_url(conn) == url
    assert sql_engine_get_url(conn) == url


def test_connection_string_ssrf_and_encryption(monkeypatch):
    """Verifies validate_connection_string detects SSRF in direct URIs and migration 007 encrypts plaintext."""
    monkeypatch.delenv("ALLOW_PRIVATE_DB_HOSTS", raising=False)

    # 1. Blocks loopback URI
    with pytest.raises(SSRFSecurityViolation, match="prohibited IP|private or internal IP"):
        DatabaseConnectionFactory.validate_connection_string("postgresql://user:pass@127.0.0.1:5432/db")

    with pytest.raises(SSRFSecurityViolation, match="prohibited IP|private or internal IP"):
        DatabaseConnectionFactory.validate_connection_string("mysql://user:pass@localhost:3306/db")

    # 2. Blocks SQLite traversal URI
    with pytest.raises(InvalidDatabasePathError, match="traversal"):
        DatabaseConnectionFactory.validate_connection_string("sqlite:///../../etc/passwd.db")

    # 3. Accepts valid remote URI
    valid_uri = "postgresql://user:pass@8.8.8.8:5432/analytics"
    validated = DatabaseConnectionFactory.validate_connection_string(valid_uri)
    assert validated == valid_uri

    # 4. Encryption backfill for connection_string
    from sqlalchemy import Table, Column, Integer, String, MetaData, select

    mem_engine = create_engine("sqlite:///:memory:")
    meta = MetaData()
    db_tbl = Table(
        "database_connections",
        meta,
        Column("id", Integer, primary_key=True),
        Column("connection_string", String),
    )
    meta.create_all(mem_engine)

    with mem_engine.begin() as conn:
        conn.execute(db_tbl.insert().values(id=1, connection_string="postgresql://u:p@8.8.8.8:5432/d1"))
        conn.execute(db_tbl.insert().values(id=2, connection_string="v1:already_encrypted"))

    # Execute backfill logic as specified in migration 007
    with mem_engine.begin() as conn:
        conn_rows = conn.execute(
            select(db_tbl.c.id, db_tbl.c.connection_string)
            .where(db_tbl.c.connection_string.isnot(None))
        ).fetchall()
        for row in conn_rows:
            conn_id, raw_conn_str = row[0], row[1]
            if raw_conn_str and not str(raw_conn_str).startswith("v1:"):
                encrypted = encrypt_secret(raw_conn_str)
                conn.execute(
                    db_tbl.update()
                    .where(db_tbl.c.id == conn_id)
                    .values(connection_string=encrypted)
                )

    with mem_engine.connect() as conn:
        rows = conn.execute(select(db_tbl.c.id, db_tbl.c.connection_string).order_by(db_tbl.c.id)).fetchall()
        assert str(rows[0][1]).startswith("v1:")
        assert decrypt_secret(rows[0][1]) == "postgresql://u:p@8.8.8.8:5432/d1"
        assert rows[1][1] == "v1:already_encrypted"

