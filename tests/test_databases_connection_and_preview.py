import os
import sys
import pytest
from unittest.mock import MagicMock, patch

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import models
from services.connection_factory import DatabaseConnectionFactory
from services.sql_engine import execute_safe_sql
from routers.databases import _get_mongo_client_and_db
from routers import connections as connections_router
from routers import databases


@pytest.mark.skipif(os.getenv("RUN_LIVE_DATABASE_TESTS") != "1", reason="External database integration: set RUN_LIVE_DATABASE_TESTS=1 in an authorized network environment")
def test_postgresql_live_connection_and_preview():
    """Verify live public PostgreSQL connects, introspects tables, and returns preview data."""
    ok, err = DatabaseConnectionFactory.test_connection(
        db_type="postgresql",
        host="hh-pgsql-public.ebi.ac.uk",
        port=5432,
        database="pfmegrnargs",
        username="reader",
        password="NWDMCE5xdipIjRrp",
        statement_timeout_ms=5000
    )
    assert ok is True
    assert err is None

    fake_conn = models.DatabaseConnection(
        id=1,
        tenant_id=1,
        name="RNAcentral Live PG",
        db_type="postgresql",
        host="hh-pgsql-public.ebi.ac.uk",
        port=5432,
        database="pfmegrnargs",
        username="reader",
        password="NWDMCE5xdipIjRrp",
        status="connected"
    )
    result = execute_safe_sql(fake_conn, 'SELECT * FROM "rna" LIMIT 5', max_rows=5)
    assert result["row_count"] > 0
    assert "upi" in [c.lower() for c in result["columns"]] or len(result["columns"]) > 0


@pytest.mark.skipif(os.getenv("RUN_LIVE_DATABASE_TESTS") != "1", reason="External database integration: set RUN_LIVE_DATABASE_TESTS=1 in an authorized network environment")
def test_mysql_live_connection_and_preview_with_ansi_quotes():
    """Verify live public MySQL connects, and executes data preview with double quotes without OperationalError 1193."""
    ok, err = DatabaseConnectionFactory.test_connection(
        db_type="mysql",
        host="ensembldb.ensembl.org",
        port=3306,
        database="homo_sapiens_core_110_38",
        username="anonymous",
        password="",
        statement_timeout_ms=5000
    )
    assert ok is True
    assert err is None

    fake_conn = models.DatabaseConnection(
        id=2,
        tenant_id=1,
        name="Ensembl Live MySQL",
        db_type="mysql",
        host="ensembldb.ensembl.org",
        port=3306,
        database="homo_sapiens_core_110_38",
        username="anonymous",
        password="",
        status="connected"
    )
    result = execute_safe_sql(fake_conn, 'SELECT * FROM "analysis" LIMIT 3', max_rows=3)
    assert result["row_count"] > 0
    assert len(result["columns"]) > 0
    assert "analysis_id" in [c.lower() for c in result["columns"]]


def test_mongodb_connection_factory_string_support():
    """Verify DatabaseConnectionFactory recognizes mongodb+srv and mongodb connection strings without calling SQLAlchemy."""
    with patch("socket.getaddrinfo", return_value=[(2, 1, 6, '', ('93.184.216.34', 27017))]), \
         patch("pymongo.MongoClient") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        mock_instance.admin.command.return_value = {"ok": 1}

        ok, err = DatabaseConnectionFactory.test_connection(
            db_type="mongodb",
            connection_string="mongodb+srv://testuser:testpass@cluster0.mongodb.net/sample_mflix?retryWrites=true&w=majority"
        )
        assert ok is True
        assert err is None
        mock_client.assert_called_once()
        mock_instance.admin.command.assert_called_with("ping")


def test_mongodb_router_client_and_db_helper():
    """Verify _get_mongo_client_and_db properly initializes client for mongodb connections."""
    fake_conn = models.DatabaseConnection(
        id=3,
        tenant_id=1,
        name="Atlas Mongo",
        db_type="mongodb",
        connection_string="mongodb+srv://testuser:testpass@cluster0.mongodb.net/testdb",
        status="connected"
    )

    with patch("socket.getaddrinfo", return_value=[(2, 1, 6, '', ('93.184.216.34', 27017))]), \
         patch("pymongo.MongoClient") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        mock_db = MagicMock()
        mock_instance.get_default_database.return_value = mock_db

        client, db = _get_mongo_client_and_db(fake_conn)
        assert client == mock_instance
        assert db == mock_db


def test_mongodb_connection_factory_uses_mongo_client_without_network(monkeypatch):
    calls = []

    class FakeClient:
        admin = SimpleNamespace(command=lambda command: calls.append(command))

        def close(self):
            calls.append("closed")

    mongo_module = ModuleType("pymongo")
    mongo_module.MongoClient = lambda *args, **kwargs: FakeClient()
    monkeypatch.setitem(sys.modules, "pymongo", mongo_module)
    monkeypatch.setattr(
        DatabaseConnectionFactory,
        "validate_connection_string",
        staticmethod(lambda _uri: "mongodb://placeholder.invalid/catalog"),
    )

    success, error = DatabaseConnectionFactory.test_connection(
        db_type="mongodb",
        connection_string="mongodb://placeholder.invalid/catalog",
    )

    assert success is True
    assert error is None
    assert calls == ["ping", "closed"]


def test_mongodb_orders_collection_uses_mongo_router_branch(monkeypatch):
    calls = []
    fake_db = SimpleNamespace(list_collection_names=lambda: ["orders"])

    class FakeClient:
        def get_default_database(self):
            return fake_db

        def close(self):
            calls.append("closed")

    mongo_module = ModuleType("pymongo")
    mongo_module.MongoClient = lambda *args, **kwargs: FakeClient()
    monkeypatch.setitem(sys.modules, "pymongo", mongo_module)
    monkeypatch.setattr(
        databases.DatabaseConnectionFactory,
        "validate_connection_string",
        staticmethod(lambda _uri: "mongodb://placeholder.invalid/catalog"),
    )
    connection = SimpleNamespace(
        connection_string="mongodb://placeholder.invalid/catalog",
        host=None,
        database="catalog",
        db_type="mongodb",
    )
    monkeypatch.setattr(databases, "get_accessible_connection", lambda *_args: connection)

    result = databases.get_database_tables(
        db_id=1,
        current_user=SimpleNamespace(tenant_id=1),
        db=object(),
    )

    assert result == ["orders"]
    assert calls == ["closed"]


def test_connections_tables_route_uses_mongo_collection_branch(monkeypatch):
    calls = []
    connection = SimpleNamespace(db_type="mongodb", tables_metadata={}, tenant_id=1)
    fake_db = SimpleNamespace(list_collection_names=lambda: ["orders"])

    class FakeClient:
        def close(self):
            calls.append("closed")

    class Query:
        def filter(self, *_criteria):
            return self

        def first(self):
            return connection

    class Session:
        def query(self, *_models):
            return Query()

    monkeypatch.setattr(
        databases,
        "_get_mongo_client_and_db",
        lambda _connection: (FakeClient(), fake_db),
    )

    result = connections_router.get_connection_tables(
        connection_id=1,
        current_user=SimpleNamespace(tenant_id=1),
        db=Session(),
    )

    assert result == ["orders"]
    assert calls == ["closed"]
