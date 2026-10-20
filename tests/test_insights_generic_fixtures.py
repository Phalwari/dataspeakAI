"""Generic temporary SQLite schemas; no committed database files or live services."""

import json
import sqlite3

from sqlalchemy import create_engine
from sqlalchemy.engine import URL

import models
from services import db_pipeline_service as pipeline
from services import db_pool, db_utils


def run_fixture(isolated_db, tmp_path, monkeypatch, *, schema_sql, rows, schema, selected_table=None, date_from=None, date_to=None):
    sqlite_path = tmp_path / "generic_fixture.sqlite"
    with sqlite3.connect(sqlite_path) as conn:
        for statement in schema_sql:
            conn.execute(statement)
        for statement, values in rows:
            conn.execute(statement, values)
    tenant = models.Tenant(name="Offline generic fixture")
    isolated_db.add(tenant)
    isolated_db.flush()
    connection = models.DatabaseConnection(
        tenant_id=tenant.id, name="Offline generic fixture", db_type="sqlite",
        database=str(sqlite_path), tables_metadata=schema,
    )
    isolated_db.add(connection)
    isolated_db.flush()
    engine = create_engine(URL.create("sqlite", database=str(sqlite_path)))
    monkeypatch.setattr(db_utils, "get_connection_url", lambda _connection: engine.url)
    monkeypatch.setattr(db_pool, "get_engine", lambda _url: engine)
    monkeypatch.setattr(pipeline, "cache_get", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(pipeline, "cache_set", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "services.llm_generation_service.generate",
        lambda *_args, **_kwargs: json.dumps({
            "business_domain": "Test data", "executive_summary": "Synthetic summary",
            "strategic_insights": [], "tactical_recommendations": [],
        }),
    )
    try:
        return pipeline.DatabasePipelineService().run_db_pipeline(
            db=isolated_db, connection_id=connection.id, tenant_id=tenant.id,
            selected_table=selected_table, date_from=date_from, date_to=date_to,
        )
    finally:
        engine.dispose()


def test_misleading_names_are_not_currency_or_identifiers(isolated_db, tmp_path, monkeypatch):
    result = run_fixture(
        isolated_db, tmp_path, monkeypatch,
        schema_sql=[
            "CREATE TABLE measurements (id INTEGER, total_orders INTEGER, discount_rate REAL, "
            "network_id INTEGER, void TEXT, created_on TEXT)",
        ],
        rows=[
            ("INSERT INTO measurements VALUES (?, ?, ?, ?, ?, ?)", (1, 4, 0.25, 90, "active", "2026-01-02")),
        ],
        schema={"measurements": {"columns": {
            "id": "INTEGER", "total_orders": "INTEGER", "discount_rate": "REAL",
            "network_id": "INTEGER", "void": "TEXT", "created_on": "TEXT",
        }, "row_count": 1}},
        selected_table="measurements",
    )
    metrics = {item["id"]: item for item in result["key_metrics"]}
    assert metrics["measurements_total_orders_sum"]["format"] == "number"
    assert metrics["measurements_discount_rate_sum"]["format"] == "number"
    assert metrics["measurements_void_distinct"]["raw_value"] == 1
    assert not any("network_id" in item["id"] for item in result["key_metrics"])


def test_quantity_without_price_has_no_revenue_and_excludes_null_dates(isolated_db, tmp_path, monkeypatch):
    result = run_fixture(
        isolated_db, tmp_path, monkeypatch,
        schema_sql=["CREATE TABLE transactions (id INTEGER, quantity INTEGER, created_on TEXT, status TEXT)"],
        rows=[
            ("INSERT INTO transactions VALUES (?, ?, ?, ?)", (1, 2, "2026-01-01", "paid")),
            ("INSERT INTO transactions VALUES (?, ?, ?, ?)", (2, 1, "2026-01-02", "unpaid")),
            ("INSERT INTO transactions VALUES (?, ?, ?, ?)", (3, 99, None, "paid")),
        ],
        schema={"transactions": {"columns": {
            "id": "INTEGER", "quantity": "INTEGER", "created_on": "TEXT", "status": "TEXT",
        }, "row_count": 3}},
        date_from="2026-01-01", date_to="2026-01-02",
    )
    metrics = {item["id"]: item for item in result["key_metrics"]}
    assert metrics["total_revenue"]["status"] == "unavailable"
    assert metrics["total_revenue"]["reason"] == "missing_role"
    assert metrics["total_orders"]["raw_value"] == 2
    assert metrics["units_sold"]["raw_value"] == 3


def test_hr_and_inventory_have_no_fabricated_revenue(isolated_db, tmp_path, monkeypatch):
    schema = {
        "employees": {"columns": {
            "id": "INTEGER", "salary": "REAL", "department": "TEXT", "hire_date": "TEXT",
        }, "row_count": 1},
        "inventory": {"columns": {
            "id": "INTEGER", "units_in_stock": "INTEGER", "unit_cost": "REAL", "updated_on": "TEXT",
        }, "row_count": 1},
    }
    result = run_fixture(
        isolated_db, tmp_path, monkeypatch,
        schema_sql=[
            "CREATE TABLE employees (id INTEGER, salary REAL, department TEXT, hire_date TEXT)",
            "CREATE TABLE inventory (id INTEGER, units_in_stock INTEGER, unit_cost REAL, updated_on TEXT)",
        ],
        rows=[
            ("INSERT INTO employees VALUES (?, ?, ?, ?)", (1, 150.0, "Operations", "2026-01-01")),
            ("INSERT INTO inventory VALUES (?, ?, ?, ?)", (1, 7, 12.0, "2026-01-01")),
        ],
        schema=schema,
        selected_table="employees",
    )
    metrics = {item["id"]: item for item in result["key_metrics"]}
    assert "total_revenue" not in metrics
    assert metrics["employees_salary_sum"]["raw_value"] == 150.0
