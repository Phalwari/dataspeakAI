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
from services.db_pool import get_engine, invalidate_engine


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


def test_legacy_plaintext_credential_remains_decryptable():
    assert crypto_service.decrypt_secret("legacy-fake-password") == "legacy-fake-password"


def test_ssrf_guard_rejects_private_dns_resolution(monkeypatch):
    monkeypatch.setattr(DatabaseConnectionFactory, "allow_private_networks", classmethod(lambda _cls: False))
    monkeypatch.setattr(
        "services.connection_factory.socket.getaddrinfo",
        lambda *_args, **_kwargs: [(2, 1, 6, "", ("10.20.30.40", 5432))],
    )

    with pytest.raises(SSRFSecurityViolation):
        DatabaseConnectionFactory.validate_host_ssrf("private.example.test")


@pytest.mark.parametrize("private_ip", ["127.0.0.1", "10.20.30.40", "172.20.1.2", "192.168.1.5", "169.254.1.2"])
def test_ssrf_guard_rejects_private_ip_literals(monkeypatch, private_ip):
    monkeypatch.setattr(DatabaseConnectionFactory, "allow_private_networks", classmethod(lambda _cls: False))
    monkeypatch.setattr(
        "services.connection_factory.socket.getaddrinfo",
        lambda host, *_args, **_kwargs: [(2, 1, 6, "", (host, 5432))],
    )

    with pytest.raises(SSRFSecurityViolation):
        DatabaseConnectionFactory.validate_host_ssrf(private_ip)


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


def test_engine_pool_reuses_and_invalidates_sqlite_engine():
    url = "sqlite://"

    first = get_engine(url)
    second = get_engine(url, connect_args={"timeout": 5.0})
    assert get_engine(url) is first
    assert get_engine(url, connect_args={"timeout": 5.0}) is second
    assert invalidate_engine(url) is True
    assert get_engine(url) is not first
    assert invalidate_engine(url) is True
    assert invalidate_engine(url) is False


def test_connection_test_error_does_not_expose_driver_details(monkeypatch):
    monkeypatch.setattr(
        DatabaseConnectionFactory,
        "validate_connection_string",
        classmethod(lambda _cls, _value: "sqlite://"),
    )

    def fail_create_engine(*_args, **_kwargs):
        raise RuntimeError("driver diagnostic fake-password")

    monkeypatch.setattr("services.connection_factory.create_engine", fail_create_engine)

    success, message = DatabaseConnectionFactory.test_connection(
        "sqlite", connection_string="sqlite://"
    )

    assert success is False
    assert message == "Database connection failed"
    assert "fake-password" not in message


def test_cross_tenant_connection_lookup_returns_not_found():
    from fastapi import HTTPException
    from types import SimpleNamespace
    import models
    from routers.databases import get_accessible_connection

    class Query:
        def __init__(self):
            self.filters = []

        def filter(self, *criteria):
            self.filters.extend(criteria)
            return self

        def first(self):
            return None

    class Session:
        def __init__(self):
            self.query_obj = Query()

        def query(self, _model):
            return self.query_obj

    db = Session()
    tenant_b_user = SimpleNamespace(tenant_id=202, role="Admin", is_platform_admin=False)

    with pytest.raises(HTTPException) as exc:
        get_accessible_connection(101, tenant_b_user, db)

    assert exc.value.status_code == 404
    clauses = {clause.left.key: clause.right.value for clause in db.query_obj.filters}
    assert clauses["id"] == 101
    assert clauses["tenant_id"] == 202
