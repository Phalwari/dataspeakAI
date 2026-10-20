"""Generic temporary SQLite schemas; no committed database files or live services."""

import json
import sqlite3

from sqlalchemy import create_engine
from sqlalchemy.engine import URL

import models
from services import db_pipeline_service as pipeline
from services import db_pool, db_utils


def run_fixture(
    isolated_db, tmp_path, monkeypatch, *, schema_sql, rows, schema,
    selected_table=None, date_from=None, date_to=None, planner_mode="legacy",
):
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
    monkeypatch.setenv("INSIGHTS_PLANNER", planner_mode)
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


def run_legacy_and_v2(isolated_db, tmp_path, monkeypatch, **fixture):
    """Execute one synthetic SQLite fixture through both planner modes."""
    results = {}
    for mode in ("legacy", "v2"):
        mode_dir = tmp_path / mode
        mode_dir.mkdir(parents=True)
        results[mode] = run_fixture(
            isolated_db, mode_dir, monkeypatch, planner_mode=mode, **fixture,
        )
    return results


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


def test_phase_f_orders_fixture_legacy_v2_parity_classifies_net_revenue_addition(
    isolated_db, tmp_path, monkeypatch,
):
    inputs = {
        "schema_sql": [
            "CREATE TABLE activity (event_id INTEGER PRIMARY KEY, amount NUMERIC, "
            "created_on TEXT, state TEXT)",
        ],
        "rows": [
            ("INSERT INTO activity VALUES (?, ?, ?, ?)", (1, 25, "2026-01-01", "paid")),
            ("INSERT INTO activity VALUES (?, ?, ?, ?)", (2, 50, "2026-01-02", "unpaid")),
            ("INSERT INTO activity VALUES (?, ?, ?, ?)", (3, 10, "2026-01-03", "cancelled")),
            ("INSERT INTO activity VALUES (?, ?, ?, ?)", (4, 15, "2026-01-04", "returned")),
            ("INSERT INTO activity VALUES (?, ?, ?, ?)", (5, 40, "2026-01-05", "delivered")),
        ],
        "schema": {"activity": {"columns": {
            "event_id": "INTEGER", "amount": "NUMERIC",
            "created_on": "TEXT", "state": "TEXT",
        }, "row_count": 5}},
        "selected_table": "activity",
    }
    legacy_tmp = tmp_path / "legacy"
    v2_tmp = tmp_path / "v2"
    legacy_tmp.mkdir()
    v2_tmp.mkdir()
    monkeypatch.setenv("INSIGHTS_PLANNER", "legacy")
    legacy = run_fixture(isolated_db, legacy_tmp, monkeypatch, planner_mode="legacy", **inputs)
    monkeypatch.setenv("INSIGHTS_PLANNER", "v2")
    planner_v2 = run_fixture(isolated_db, v2_tmp, monkeypatch, planner_mode="v2", **inputs)

    legacy_metrics = {metric["id"]: metric for metric in legacy["key_metrics"]}
    v2_metrics = {metric["id"]: metric for metric in planner_v2["key_metrics"]}
    legacy_gross = legacy_metrics.get("activity_amount_sum")
    v2_gross = v2_metrics["revenue_total"]
    assert legacy_gross is not None and legacy_gross["raw_value"] == 140.0
    assert v2_gross["raw_value"] == 140.0
    assert v2_metrics["net_revenue"]["raw_value"] == 40.0
    assert planner_v2["planner_mode"] == "v2"


def test_phase_f_parity_matrix_covers_misleading_quantity_hr_and_empty_sqlite_families(
    isolated_db, tmp_path, monkeypatch,
):
    """Direct offline parity: intentional legacy semantic gaps are explicit per fixture."""
    fixtures = {
        "misleading_names": {
            "schema_sql": [
                "CREATE TABLE measurements (id INTEGER, total_orders INTEGER, "
                "discount_rate REAL, network_id INTEGER, void TEXT, created_on TEXT)",
            ],
            "rows": [("INSERT INTO measurements VALUES (?, ?, ?, ?, ?, ?)",
                      (1, 4, 0.25, 90, "active", "2026-01-02"))],
            "schema": {"measurements": {"columns": {
                "id": "INTEGER", "total_orders": "INTEGER", "discount_rate": "REAL",
                "network_id": "INTEGER", "void": "TEXT", "created_on": "TEXT",
            }, "row_count": 1}},
            "selected_table": "measurements",
        },
        "quantity_without_price": {
            "schema_sql": [
                "CREATE TABLE transactions (id INTEGER, quantity INTEGER, created_on TEXT, status TEXT)",
            ],
            "rows": [
                ("INSERT INTO transactions VALUES (?, ?, ?, ?)", (1, 2, "2026-01-01", "paid")),
                ("INSERT INTO transactions VALUES (?, ?, ?, ?)", (2, 1, "2026-01-02", "unpaid")),
                ("INSERT INTO transactions VALUES (?, ?, ?, ?)", (3, 99, None, "paid")),
            ],
            "schema": {"transactions": {"columns": {
                "id": "INTEGER", "quantity": "INTEGER", "created_on": "TEXT", "status": "TEXT",
            }, "row_count": 3}},
            "date_from": "2026-01-01", "date_to": "2026-01-02",
        },
        "hr_salary": {
            "schema_sql": [
                "CREATE TABLE workforce (id INTEGER PRIMARY KEY, salary NUMERIC, department TEXT, hired_on TEXT)",
            ],
            "rows": [("INSERT INTO workforce VALUES (?, ?, ?, ?)",
                      (1, 150, "Operations", "2026-01-01"))],
            "schema": {"workforce": {"columns": {
                "id": "INTEGER", "salary": "NUMERIC", "department": "TEXT", "hired_on": "TEXT",
            }, "row_count": 1}},
            "selected_table": "workforce",
        },
        "empty_table": {
            "schema_sql": ["CREATE TABLE observations (id INTEGER PRIMARY KEY, state TEXT)"],
            "rows": [],
            "schema": {"observations": {"columns": {
                "id": "INTEGER", "state": "TEXT",
            }, "row_count": 0}},
            "selected_table": "observations",
        },
    }

    outputs = {
        name: run_legacy_and_v2(isolated_db, tmp_path / name, monkeypatch, **fixture)
        for name, fixture in fixtures.items()
    }

    misleading_legacy = {item["id"]: item for item in outputs["misleading_names"]["legacy"]["key_metrics"]}
    misleading_v2 = {item["id"]: item for item in outputs["misleading_names"]["v2"]["key_metrics"]}
    # Intentional: legacy sums a count-like name as a number; V2 declines revenue.
    assert misleading_legacy["measurements_total_orders_sum"]["raw_value"] == 4
    assert misleading_v2["revenue_total"]["status"] == "unavailable"
    assert misleading_v2["revenue_total"]["reason"] == "missing_role"

    quantity_legacy = {item["id"]: item for item in outputs["quantity_without_price"]["legacy"]["key_metrics"]}
    quantity_v2 = {item["id"]: item for item in outputs["quantity_without_price"]["v2"]["key_metrics"]}
    assert quantity_legacy["total_revenue"]["status"] == "unavailable"
    assert quantity_v2["revenue_total"]["status"] == "unavailable"
    assert quantity_legacy["total_orders"]["raw_value"] == 2
    assert quantity_v2["row_count_transactions"]["raw_value"] == 2

    hr_legacy = {item["id"]: item for item in outputs["hr_salary"]["legacy"]["key_metrics"]}
    hr_v2 = {item["id"]: item for item in outputs["hr_salary"]["v2"]["key_metrics"]}
    assert hr_legacy["workforce_salary_sum"]["raw_value"] == 150
    assert hr_v2["revenue_total"]["status"] == "unavailable"
    assert next(item["raw_value"] for item in hr_v2.values() if "salary" in item["id"]) == 150

    empty_legacy = {item["id"]: item for item in outputs["empty_table"]["legacy"]["key_metrics"]}
    empty_v2 = {item["id"]: item for item in outputs["empty_table"]["v2"]["key_metrics"]}
    # Intentional: legacy omits an empty selected table; V2 reports typed zero.
    assert "observations_row_count" not in empty_legacy
    assert empty_v2["row_count_observations"]["status"] == "zero"
    assert empty_v2["row_count_observations"]["raw_value"] == 0
