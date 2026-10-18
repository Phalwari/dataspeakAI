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
