"""Offline security regression tests for the database connection layer."""

import pytest

from services import crypto_service
from services import connection_factory
from services.connection_factory import (
    DatabaseConnectionFactory,
    InvalidDatabasePathError,
    SSRFSecurityViolation,
)
from services.database_connection_service import DatabaseConnectionService


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


def test_ssrf_guard_rejects_private_dns_resolution(monkeypatch):
    monkeypatch.setattr(DatabaseConnectionFactory, "allow_private_networks", classmethod(lambda _cls: False))
    monkeypatch.setattr(
        "services.connection_factory.socket.getaddrinfo",
        lambda *_args, **_kwargs: [(2, 1, 6, "", ("10.20.30.40", 5432))],
    )

    with pytest.raises(SSRFSecurityViolation):
        DatabaseConnectionFactory.validate_host_ssrf("private.example.test")


def test_connection_uri_validates_query_parameter_host(monkeypatch):
    monkeypatch.setattr(DatabaseConnectionFactory, "allow_private_networks", classmethod(lambda _cls: False))

    def fake_getaddrinfo(host, *_args, **_kwargs):
        ip = "8.8.8.8" if host == "public.example.test" else "10.20.30.40"
        return [(2, 1, 6, "", (ip, 5432))]

    monkeypatch.setattr("services.connection_factory.socket.getaddrinfo", fake_getaddrinfo)

    with pytest.raises(SSRFSecurityViolation):
        DatabaseConnectionFactory.validate_connection_string(
            "postgresql://test-user@public.example.test/catalog?host=private.example.test"
        )


@pytest.mark.parametrize(
    "connection_uri",
    [
        "postgresql://test-user@/catalog?host=%2Fvar%2Frun%2Fpostgresql",
        "mysql://test-user@public.example.test/catalog?unix_socket=%2Ftmp%2Fmysql.sock",
    ],
)
def test_connection_uri_rejects_unix_sockets(connection_uri):
    with pytest.raises(SSRFSecurityViolation, match="Unix socket"):
        DatabaseConnectionFactory.validate_connection_string(connection_uri)


def test_sqlite_path_sandbox_rejects_traversal(monkeypatch, tmp_path):
    monkeypatch.setattr(connection_factory, "DEFAULT_SQLITE_ROOT", tmp_path / "managed")
    monkeypatch.setenv("ENVIRONMENT", "production")

    with pytest.raises(InvalidDatabasePathError):
        DatabaseConnectionFactory.validate_sqlite_path("../outside.db")


def test_direct_sqlite_service_paths_enforce_sandbox(monkeypatch, tmp_path):
    import sqlite3

    monkeypatch.setattr(connection_factory, "DEFAULT_SQLITE_ROOT", tmp_path / "managed")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setattr(sqlite3, "connect", lambda *_args, **_kwargs: pytest.fail("sandboxed path reached SQLite"))

    assert DatabaseConnectionService.test_sqlite("../outside.db")[0] is False
    assert "error" in DatabaseConnectionService.get_sqlite_schema("../outside.db")
    assert "error" in DatabaseConnectionService.get_tables("sqlite", database="../outside.db")[0]
    assert "error" in DatabaseConnectionService.preview_table(
        "sqlite", database="../outside.db", table_name="orders"
    )


def test_sqlite_connection_lists_tables_and_rejects_writes(monkeypatch, tmp_path):
    import sqlite3

    monkeypatch.setattr(connection_factory, "DEFAULT_SQLITE_ROOT", tmp_path / "managed")
    monkeypatch.setenv("ENVIRONMENT", "test")
    db_path = tmp_path / "sample.sqlite"
    with sqlite3.connect(db_path) as local_db:
        local_db.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, amount INTEGER)")
        local_db.execute("INSERT INTO orders (amount) VALUES (125)")

    tables = DatabaseConnectionService.get_tables("sqlite", database=str(db_path))
    rows = DatabaseConnectionService.execute_query(
        "sqlite", database=str(db_path), query="SELECT id, amount FROM orders"
    )

    assert tables == [{"name": "orders", "rows": 1}]
    assert rows == [{"id": 1, "amount": 125}]
    with pytest.raises(ValueError, match="Only read-only SELECT"):
        DatabaseConnectionService.execute_query(
            "sqlite", database=str(db_path), query="INSERT INTO orders (amount) VALUES (999)"
        )
