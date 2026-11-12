"""Generic, offline Insights structure/status snapshots; no persisted data files."""

import json
from pathlib import Path

from scripts.insights_diff import compare, main, project
from test_insights_date_filters import _run as run_orders, orders_case
from test_insights_generic_fixtures import run_fixture
from test_insights_mongo_filters import FakeCollection, run_mongo_case


GOLDEN = Path(__file__).parent / "golden" / "insights"


def assert_snapshot(name, result):
    snapshot = project(result)
    path = GOLDEN / f"{name}.json"
    assert path.exists(), f"Missing golden snapshot: {name}"
    assert snapshot == json.loads(path.read_text(encoding="utf-8"))


def test_orders_status_snapshot(orders_case):
    result = run_orders(orders_case, date_from="2026-01-01", date_to="2026-01-03")
    assert_snapshot("orders_status", result)


def test_misleading_names_snapshot(isolated_db, tmp_path, monkeypatch):
    result = run_fixture(
        isolated_db, tmp_path, monkeypatch,
        schema_sql=["CREATE TABLE measurements (id INTEGER, total_orders INTEGER, discount_rate REAL, network_id INTEGER, void TEXT, created_on TEXT)"],
        rows=[("INSERT INTO measurements VALUES (?, ?, ?, ?, ?, ?)", (1, 4, 0.25, 90, "active", "2026-01-02"))],
        schema={"measurements": {"columns": {
            "id": "INTEGER", "total_orders": "INTEGER", "discount_rate": "REAL",
            "network_id": "INTEGER", "void": "TEXT", "created_on": "TEXT",
        }, "row_count": 1}},
        selected_table="measurements",
    )
    assert_snapshot("misleading_names", result)


def test_quantity_without_price_snapshot(isolated_db, tmp_path, monkeypatch):
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
    assert_snapshot("quantity_without_price", result)


def test_hr_inventory_snapshot(isolated_db, tmp_path, monkeypatch):
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
        schema={
            "employees": {"columns": {"id": "INTEGER", "salary": "REAL", "department": "TEXT", "hire_date": "TEXT"}, "row_count": 1},
            "inventory": {"columns": {"id": "INTEGER", "units_in_stock": "INTEGER", "unit_cost": "REAL", "updated_on": "TEXT"}, "row_count": 1},
        },
        selected_table="employees",
    )
    assert_snapshot("hr_inventory", result)


def test_mongo_nested_metadata_snapshot(isolated_db, monkeypatch):
    class NestedCollection(FakeCollection):
        def find_one(self, *_args, **_kwargs):
            return {"customer": {"segment": "synthetic"}, "amount": 4, "created_on": "2026-01-01"}

    result = run_mongo_case(
        isolated_db, monkeypatch, NestedCollection(),
        columns_override={"amount": "number", "customer.segment": "string", "created_on": "date"},
    )
    assert_snapshot("mongo_nested_mock", result)


def test_projection_excludes_numeric_values_and_detects_status_changes(tmp_path, capsys):
    payload = {"success": True, "db_type": "sqlite", "key_metrics": [
        {"id": "fixture_total", "status": "available", "reason": None, "format": "number", "raw_value": 25},
    ], "charts": []}
    first = project(payload)
    payload["key_metrics"][0]["raw_value"] = 900
    assert project(payload) == first
    payload["key_metrics"][0]["status"] = "error"
    second = project(payload)
    assert any("status" in change for change in compare(first, second))
    baseline_path = tmp_path / "baseline.json"
    current_path = tmp_path / "current.json"
    baseline_path.write_text(json.dumps(first), encoding="utf-8")
    current_path.write_text(json.dumps(second), encoding="utf-8")
    assert main(["insights_diff.py", str(baseline_path), str(current_path)]) == 1
    assert "raw_value" not in capsys.readouterr().out
    raw_baseline = tmp_path / "raw_baseline.json"
    raw_current = tmp_path / "raw_current.json"
    payload["key_metrics"][0]["status"] = "available"
    payload["key_metrics"][0]["raw_value"] = 25
    raw_baseline.write_text(json.dumps(payload), encoding="utf-8")
    payload["key_metrics"][0]["raw_value"] = 900
    raw_current.write_text(json.dumps(payload), encoding="utf-8")
    assert main(["insights_diff.py", str(raw_baseline), str(raw_current)]) == 0
    assert "raw_value" not in capsys.readouterr().out
