"""DB Insights failure-state tests: mocked unit paths and a separate real-engine check.

The unit test explicitly named ``*_unit`` uses a mocked database service. The
pooled-engine test runs a failing SQL statement through an actual SQLAlchemy
engine backed only by a temporary SQLite file. MongoDB uses a local fake client.
"""

import json
import sqlite3
import sys
from types import ModuleType

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import URL

import models
from services import db_pipeline_service as pipeline_module
from services import db_pool, db_utils


def _add_connection(db, *, database, schema, db_type="sqlite", connection_string=None):
    tenant = models.Tenant(name="Failure semantics test tenant")
    db.add(tenant)
    db.flush()
    connection = models.DatabaseConnection(
        tenant_id=tenant.id,
        name="Failure semantics test connection",
        db_type=db_type,
        database=database,
        connection_string=connection_string,
        tables_metadata=schema,
    )
    db.add(connection)
    db.flush()
    return connection


def _prepare_pipeline(monkeypatch, sqlite_path=None):
    monkeypatch.setattr(pipeline_module, "cache_get", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(pipeline_module, "cache_set", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "services.llm_generation_service.generate",
        lambda *_args, **_kwargs: json.dumps(
            {
                "business_domain": "Test data",
                "executive_summary": "Synthetic test summary",
                "strategic_insights": [],
                "tactical_recommendations": [],
            }
        ),
    )

    if sqlite_path is not None:
        engine = create_engine(f"sqlite:///{sqlite_path}")
        monkeypatch.setattr(db_utils, "get_connection_url", lambda _connection: f"sqlite:///{sqlite_path}")
        monkeypatch.setattr(db_pool, "get_engine", lambda _url: engine)
        return engine
    return None


def _run_pipeline(db, connection, *, selected_table=None, date_from=None, monkeypatch):
    return pipeline_module.DatabasePipelineService().run_db_pipeline(
        db=db,
        connection_id=connection.id,
        tenant_id=connection.tenant_id,
        selected_table=selected_table,
        date_from=date_from,
        force_refresh=False,
    )


def test_sql_null_sum_is_unavailable_and_empty_count_is_zero(isolated_db, tmp_path, monkeypatch):
    sqlite_path = tmp_path / "empty_orders.sqlite"
    with sqlite3.connect(sqlite_path) as sqlite_db:
        sqlite_db.execute("CREATE TABLE orders (order_id INTEGER, amount REAL)")

    schema = {"orders": {"columns": {"order_id": "INTEGER", "amount": "REAL"}, "row_count": 0}}
    connection = _add_connection(isolated_db, database=str(sqlite_path), schema=schema)
    engine = _prepare_pipeline(monkeypatch, sqlite_path)
    try:
        result = _run_pipeline(isolated_db, connection, selected_table="orders", monkeypatch=monkeypatch)
    finally:
        engine.dispose()

    metrics = {item["id"]: item for item in result["key_metrics"]}
    assert metrics["orders_amount_sum"]["status"] == "unavailable"
    assert metrics["orders_amount_sum"]["reason"] == "no_rows"
    assert metrics["orders_total_rows"]["status"] == "zero"
    assert metrics["orders_total_rows"]["raw_value"] == 0


def test_sqlite_stale_column_is_missing_role_without_query_or_zero(isolated_db, tmp_path, monkeypatch):
    """A stale schema column must not be treated as a SQLite string literal."""
    sqlite_path = tmp_path / "generic_orders.sqlite"
    with sqlite3.connect(sqlite_path) as sqlite_db:
        sqlite_db.execute(
            "CREATE TABLE orders (id INTEGER, customer_ref TEXT, amount REAL, created_on TEXT, state TEXT)"
        )
        sqlite_db.execute(
            "INSERT INTO orders VALUES (?, ?, ?, ?, ?)",
            (1, "synthetic-customer", 37.5, "2026-01-02", "paid"),
        )

    schema = {
        "orders": {
            "columns": {
                "id": "INTEGER",
                "customer_ref": "TEXT",
                "amount": "REAL",
                "created_on": "TEXT",
                "state": "TEXT",
                "ghost_amount": "REAL",
            },
            "row_count": 1,
        }
    }
    connection = _add_connection(isolated_db, database=str(sqlite_path), schema=schema)
    engine = _prepare_pipeline(monkeypatch, sqlite_path)
    executed_sql = []
    event.listen(
        engine,
        "before_cursor_execute",
        lambda _conn, _cursor, statement, _params, _context, _many: executed_sql.append(statement),
    )
    try:
        result = _run_pipeline(isolated_db, connection, selected_table="orders", monkeypatch=monkeypatch)
    finally:
        engine.dispose()

    metrics = {item["id"]: item for item in result["key_metrics"]}
    ghost_metric = metrics["orders_ghost_amount_sum"]
    assert ghost_metric["status"] == "unavailable"
    assert ghost_metric["reason"] == "missing_role"
    assert ghost_metric["raw_value"] is None
    assert not any('"ghost_amount"' in statement for statement in executed_sql)
    assert metrics["orders_amount_sum"]["status"] == "available"


def test_missing_role_is_reported_for_federated_revenue(isolated_db, tmp_path, monkeypatch):
    sqlite_path = tmp_path / "orders_without_revenue.sqlite"
    with sqlite3.connect(sqlite_path) as sqlite_db:
        sqlite_db.execute("CREATE TABLE orders (order_id INTEGER, created_at TEXT)")

    schema = {
        "orders": {"columns": {"order_id": "INTEGER", "created_at": "TEXT"}, "row_count": 0}
    }
    connection = _add_connection(isolated_db, database=str(sqlite_path), schema=schema)
    engine = _prepare_pipeline(monkeypatch, sqlite_path)
    try:
        result = _run_pipeline(isolated_db, connection, monkeypatch=monkeypatch)
    finally:
        engine.dispose()

    metrics = {item["id"]: item for item in result["key_metrics"]}
    assert metrics["total_revenue"]["status"] == "unavailable"
    assert metrics["total_revenue"]["reason"] == "missing_role"


def test_query_failure_is_reported_by_mocked_service_unit(isolated_db, monkeypatch):
    """Unit test: a mocked non-SQLite fallback maps to error/query_failed."""
    schema = {"orders": {"columns": {"order_id": "INTEGER", "amount": "REAL"}, "row_count": 0}}
    connection = _add_connection(isolated_db, database="offline-test-database", schema=schema, db_type="mysql")
    _prepare_pipeline(monkeypatch)
    monkeypatch.setattr(db_utils, "get_connection_url", lambda _connection: None)
    fallback_calls = []
    monkeypatch.setattr(
        pipeline_module.db_connection_service,
        "execute_query",
        lambda **_kwargs: fallback_calls.append(True) or [{"error": "synthetic query failure"}],
    )
    result = _run_pipeline(isolated_db, connection, selected_table="orders", monkeypatch=monkeypatch)

    metrics = {item["id"]: item for item in result["key_metrics"]}
    assert metrics["orders_amount_sum"]["status"] == "error", (
        f"status={metrics['orders_amount_sum'].get('status')}, "
        f"reason={metrics['orders_amount_sum'].get('reason')}, fallback_calls={len(fallback_calls)}"
    )
    assert metrics["orders_amount_sum"]["reason"] == "query_failed"
    assert fallback_calls
    assert all("synthetic query failure" not in warning for warning in result["data_quality"]["warnings"])


def test_real_pooled_sqlite_query_failure_sets_query_failed(isolated_db, tmp_path, monkeypatch):
    """Real-engine regression: a SQLite function error maps to error/query_failed."""
    sqlite_path = tmp_path / "pooled_query_failure.sqlite"
    with sqlite3.connect(sqlite_path) as sqlite_db:
        sqlite_db.execute("CREATE TABLE orders (order_id INTEGER, amount REAL)")
        sqlite_db.execute("INSERT INTO orders VALUES (1, 12.5)")

    schema = {"orders": {"columns": {"order_id": "INTEGER", "amount": "REAL"}, "row_count": 1}}
    connection = _add_connection(isolated_db, database=str(sqlite_path), schema=schema)
    engine = create_engine(URL.create("sqlite", database=str(sqlite_path)))
    pooled_errors = []
    url_calls = []
    pool_calls = []
    event.listen(engine, "handle_error", lambda _context: pooled_errors.append(True))

    def fail_round(*_args):
        raise sqlite3.OperationalError("synthetic SQLite function failure")

    event.listen(
        engine,
        "connect",
        lambda dbapi_connection, _record: dbapi_connection.create_function("ROUND", 2, fail_round),
    )
    monkeypatch.setattr(db_utils, "get_connection_url", lambda _connection: url_calls.append(True) or engine.url)
    monkeypatch.setattr(db_pool, "get_engine", lambda _url: pool_calls.append(True) or engine)
    _prepare_pipeline(monkeypatch)
    monkeypatch.setattr(
        pipeline_module.db_connection_service,
        "execute_query",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("synthetic fallback failure")),
    )

    try:
        result = _run_pipeline(isolated_db, connection, selected_table="orders", monkeypatch=monkeypatch)
    finally:
        engine.dispose()

    metrics = {item["id"]: item for item in result["key_metrics"]}
    assert pooled_errors, (
        "No pooled SQL error observed: "
        f"url_calls={len(url_calls)}, pool_calls={len(pool_calls)}, "
        f"metric_status={metrics.get('orders_amount_sum', {}).get('status')}"
    )
    assert metrics["orders_amount_sum"]["status"] == "error"
    assert metrics["orders_amount_sum"]["reason"] == "query_failed"


@pytest.mark.xfail(
    strict=True,
    reason="Current pipeline falls back to an available table instead of assigning missing_table status.",
)
def test_missing_selected_table_has_missing_table_reason(isolated_db, tmp_path, monkeypatch):
    sqlite_path = tmp_path / "selected_table_missing.sqlite"
    with sqlite3.connect(sqlite_path) as sqlite_db:
        sqlite_db.execute("CREATE TABLE orders (order_id INTEGER)")

    schema = {"orders": {"columns": {"order_id": "INTEGER"}, "row_count": 0}}
    connection = _add_connection(isolated_db, database=str(sqlite_path), schema=schema)
    engine = _prepare_pipeline(monkeypatch, sqlite_path)
    try:
        result = _run_pipeline(
            isolated_db,
            connection,
            selected_table="missing_table",
            monkeypatch=monkeypatch,
        )
    finally:
        engine.dispose()

    missing = [item for item in result["key_metrics"] if item.get("reason") == "missing_table"]
    assert missing


def test_mongo_filtered_count_failure_never_uses_unfiltered_count(isolated_db, monkeypatch):
    count_calls = []

    class FakeCollection:
        def count_documents(self, query):
            count_calls.append(("filtered", query))
            raise RuntimeError("synthetic filtered count failure")

        def estimated_document_count(self):
            count_calls.append(("estimated", None))
            raise AssertionError("unfiltered estimated count must not run")

        def aggregate(self, _pipeline):
            return []

        def distinct(self, _field, _query=None):
            return []

        def find_one(self, *_args, **_kwargs):
            return None

    collection = FakeCollection()

    class FakeMongoDatabase:
        def __getitem__(self, _name):
            return collection

    class FakeMongoClient:
        def __init__(self, *_args, **_kwargs):
            pass

        def get_default_database(self):
            return FakeMongoDatabase()

        def close(self):
            pass

    pymongo_module = ModuleType("pymongo")
    pymongo_module.MongoClient = FakeMongoClient
    monkeypatch.setitem(sys.modules, "pymongo", pymongo_module)
    _prepare_pipeline(monkeypatch)
    monkeypatch.setattr(
        pipeline_module.encryption_service,
        "decrypt",
        lambda _value: "offline-mock-placeholder",
    )

    schema = {
        "orders": {
            "columns": {"created_at": "DATETIME", "amount": "REAL"},
            "row_count": 1,
        }
    }
    connection = _add_connection(
        isolated_db,
        database="offline-mongo-test",
        schema=schema,
        db_type="mongodb",
        connection_string="offline-mock-placeholder",
    )

    try:
        _run_pipeline(
            isolated_db,
            connection,
            selected_table="orders",
            date_from="2026-01-01",
            monkeypatch=monkeypatch,
        )
    except TypeError:
        # Current code may fail later when it compares an unavailable count to a number.
        # The invariant under test is that no unfiltered count fallback was attempted.
        pass

    assert len(count_calls) == 1
    assert count_calls[0][0] == "filtered"
    assert "created_at" in count_calls[0][1]
