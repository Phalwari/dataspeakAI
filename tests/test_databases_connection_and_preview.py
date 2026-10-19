"""Offline connection checks; external database targets are never contacted here."""

import sys
from types import ModuleType, SimpleNamespace

from services.connection_factory import DatabaseConnectionFactory
from routers import databases


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
    fake_db = SimpleNamespace(
        list_collection_names=lambda: ["orders"],
    )

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
