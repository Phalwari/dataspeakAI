"""Offline security regression tests for the database connection layer."""

import pytest

from services import crypto_service


def test_credential_encryption_round_trip_with_configured_key(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DATA_ENCRYPTION_KEY", "test-only-encryption-material")
    monkeypatch.delenv("SECRET_KEY", raising=False)

    encrypted = crypto_service.encrypt_secret("fake-database-password")

    assert encrypted.startswith("v1:")
    assert encrypted != "fake-database-password"
    assert crypto_service.decrypt_secret(encrypted) == "fake-database-password"


def test_credential_encryption_requires_key_in_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("DATA_ENCRYPTION_KEY", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError, match="configured production key"):
        crypto_service.encrypt_secret("fake-database-password")
