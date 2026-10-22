"""Date-window regressions using only a temporary SQLite database."""

import json
import sqlite3
import datetime
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import URL

import models
from database import get_db
from dependencies import get_current_user
from services import db_pipeline_service as pipeline
from services import db_pool, db_utils
from routers.insights import _validated_dates, router as insights_router


@pytest.fixture
def orders_case(isolated_db, tmp_path, monkeypatch):
    sqlite_path = tmp_path / "generic_orders.sqlite"
    with sqlite3.connect(sqlite_path) as conn:
        conn.execute(
            "CREATE TABLE orders (id INTEGER, customer_ref TEXT, amount REAL, "
            "created_on TEXT, state TEXT)"
        )
        conn.executemany(
            "INSERT INTO orders VALUES (?, ?, ?, ?, ?)",
            [
                (1, "customer-a", 40.0, "2025-01-01", "paid"),
                (2, "customer-b", 10.0, "2026-01-01", "paid"),
                (3, "customer-b", 20.0, "2026-01-02", "unpaid"),
                (4, "customer-c", 35.0, "2026-01-03", "returned"),
                (5, "customer-d", 999.0, None, "paid"),
            ],
        )
    tenant = models.Tenant(name="Offline date fixture")
    isolated_db.add(tenant)
    isolated_db.flush()
    connection = models.DatabaseConnection(
        tenant_id=tenant.id,
        name="Offline date fixture",
        db_type="sqlite",
        database=str(sqlite_path),
        tables_metadata={
            "orders": {
                "columns": {
                    "id": "INTEGER", "customer_ref": "TEXT", "amount": "REAL",
                    "created_on": "TEXT", "state": "TEXT",
                },
                "row_count": 5,
            },
        },
    )
    isolated_db.add(connection)
    isolated_db.flush()
    engine = create_engine(URL.create("sqlite", database=str(sqlite_path)))
    monkeypatch.setattr(db_utils, "get_connection_url", lambda _connection: engine.url)
    monkeypatch.setattr(db_pool, "get_engine", lambda _url: engine)
    monkeypatch.setattr(
        "services.llm_generation_service.generate",
        lambda *_args, **_kwargs: json.dumps({
            "business_domain": "Test data", "executive_summary": "Synthetic summary",
            "strategic_insights": [], "tactical_recommendations": [],
        }),
    )
    cache = {}
    monkeypatch.setattr(pipeline, "cache_get", lambda key: cache.get(key))
    monkeypatch.setattr(pipeline, "cache_set", lambda key, value, **_kwargs: cache.__setitem__(key, value))
    yield isolated_db, connection, engine, cache
    engine.dispose()


def _run(case, *, date_from=None, date_to=None, selected_table=None):
    db, connection, _, _ = case
    return pipeline.DatabasePipelineService().run_db_pipeline(
        db=db, connection_id=connection.id, tenant_id=connection.tenant_id,
        selected_table=selected_table, date_from=date_from, date_to=date_to,
    )


@pytest.mark.parametrize("selected_table,metric_id", [
    (None, "total_revenue"), ("orders", "orders_amount_sum"),
])
def test_calendar_bounds_apply_to_federated_and_single_table(orders_case, selected_table, metric_id):
    first = _run(
        orders_case, selected_table=selected_table,
        date_from="2026-01-01", date_to="2026-01-02",
    )
    second = _run(
        orders_case, selected_table=selected_table,
        date_from="2026-01-03", date_to="2026-01-03",
    )
    first_metrics = {item["id"]: item for item in first["key_metrics"]}
    second_metrics = {item["id"]: item for item in second["key_metrics"]}
    first_charts = {item["id"]: item for item in first["auto_charts"]}
    second_charts = {item["id"]: item for item in second["auto_charts"]}
    assert first_metrics[metric_id]["raw_value"] == 30.0
    assert second_metrics[metric_id]["raw_value"] == 35.0
    if selected_table is None:
        assert first_metrics["total_orders"]["raw_value"] == 2
        assert second_metrics["total_orders"]["raw_value"] == 1
        assert first_metrics["net_revenue_delivered"]["raw_value"] == 10.0
        assert first_metrics["total_revenue"]["trend_text"] == "SPLY (-25.0%)"
        assert first_charts["monthly_revenue_velocity"]["data"] == [
            {"period": "2026-01", "value": 30.0},
        ]
        assert second_charts["monthly_revenue_velocity"]["data"] == [
            {"period": "2026-01", "value": 35.0},
        ]
    else:
        assert first_metrics["orders_total_rows"]["raw_value"] == 2
        assert second_metrics["orders_total_rows"]["raw_value"] == 1
        assert first_charts["orders_trend"]["data"] == [{"period": "2026-01", "value": 30.0}]
        assert second_charts["orders_trend"]["data"] == [{"period": "2026-01", "value": 35.0}]
    assert first["applied_date_from"] == "2026-01-01"
    assert first["applied_date_to"] == "2026-01-02"


@pytest.mark.parametrize("date_from,date_to", [
    ("2026-13-01", None),
    ("2026-1-01", None),
    ("2026-01-03", "2026-01-02"),
    (None, "2026-02-30"),
])
def test_invalid_dates_rejected_before_cache(orders_case, date_from, date_to):
    _, _, _, cache = orders_case
    with pytest.raises(ValueError, match="Invalid date filter"):
        _run(orders_case, date_from=date_from, date_to=date_to)
    assert not cache


def test_date_ranges_use_distinct_cache_entries(orders_case):
    _, _, _, cache = orders_case
    _run(orders_case, date_from="2026-01-01", date_to="2026-01-02")
    _run(orders_case, date_from="2026-01-03", date_to="2026-01-03")
    assert len(cache) == 2


def test_old_unfiltered_db_cache_is_not_served(orders_case):
    db, connection, _, _ = orders_case
    connection.insights_cache = {"success": True, "key_metrics": [{"id": "stale"}]}
    connection.insights_cached_at = datetime.datetime.now(datetime.timezone.utc)
    db.flush()
    result = _run(orders_case)
    assert result["insights_version"] == pipeline.INSIGHTS_CACHE_VERSION
    assert "stale" not in {item["id"] for item in result["key_metrics"]}


def test_dates_are_bound_not_interpolated(orders_case):
    _, _, engine, _ = orders_case
    statements = []
    event.listen(
        engine, "before_cursor_execute",
        lambda _connection, _cursor, statement, parameters, _context, _many:
            statements.append((statement, parameters)),
    )
    _run(orders_case, date_from="2026-01-01", date_to="2026-01-02", selected_table="orders")
    scoped = [item for item in statements if "COUNT(*) as cnt" in item[0]]
    assert scoped
    assert any("2026-01-01" in item[1] and "2026-01-03" in item[1] for item in scoped)
    assert all("2026-01-01" not in item[0] for item in scoped)


def test_unrelated_table_is_not_reported_with_unfiltered_date_values():
    query = 'SELECT COUNT(*) FROM "customers"'
    assert pipeline._with_date_predicate(
        query, '"orders"', '"created_on"', {"date_from": "2026-01-01"},
    ) is None


def test_ambiguous_date_columns_are_not_chosen_by_order():
    assert pipeline._pick_date_column(["updated_at", "closed_at"]) is None
    assert pipeline._pick_date_column(["updated_at", "created_on"]) == "created_on"


def test_router_maps_invalid_calendar_input_to_400():
    with pytest.raises(HTTPException) as error:
        _validated_dates("2026-02-30", None)
    assert error.value.status_code == 400


def test_sply_leap_day_uses_previous_february_28(orders_case):
    _, _, engine, _ = orders_case
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO orders VALUES (:id, :customer_ref, :amount, :created_on, :state)"),
            [
                {"id": 10, "customer_ref": "sample-a", "amount": 40.0,
                 "created_on": "2023-02-28", "state": "paid"},
                {"id": 11, "customer_ref": "sample-b", "amount": 50.0,
                 "created_on": "2024-02-29", "state": "paid"},
            ],
        )
    statements = []
    event.listen(
        engine, "before_cursor_execute",
        lambda _connection, _cursor, statement, parameters, _context, _many:
            statements.append((statement, parameters)),
    )

    result = _run(orders_case, date_from="2024-02-29", date_to="2024-02-29")
    metrics = {item["id"]: item for item in result["key_metrics"]}

    assert metrics["total_revenue"]["trend_text"] == "SPLY (+25.0%)"
    assert any(
        "2024-02-29" in parameters and "2024-03-01" in parameters
        and "2023-02-28" in parameters and "2023-03-01" in parameters
        for statement, parameters in statements if "curr_val" in statement and "prev_val" in statement
    )


def test_sply_year_boundary_uses_matching_previous_window(orders_case):
    _, _, engine, _ = orders_case
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO orders VALUES (:id, :customer_ref, :amount, :created_on, :state)"),
            [
                {"id": 20, "customer_ref": "sample-a", "amount": 20.0,
                 "created_on": "2024-01-01", "state": "paid"},
                {"id": 21, "customer_ref": "sample-b", "amount": 20.0,
                 "created_on": "2024-01-02", "state": "paid"},
                {"id": 22, "customer_ref": "sample-c", "amount": 20.0,
                 "created_on": "2025-01-02", "state": "paid"},
            ],
        )
    statements = []
    event.listen(
        engine, "before_cursor_execute",
        lambda _connection, _cursor, statement, parameters, _context, _many:
            statements.append((statement, parameters)),
    )

    result = _run(orders_case, date_from="2025-01-01", date_to="2025-01-02")
    metrics = {item["id"]: item for item in result["key_metrics"]}

    assert metrics["total_revenue"]["trend_text"] == "SPLY (+50.0%)"
    assert any(
        "2025-01-01" in parameters and "2025-01-03" in parameters
        and "2024-01-01" in parameters and "2024-01-03" in parameters
        for statement, parameters in statements if "curr_val" in statement and "prev_val" in statement
    )


def test_filtered_request_rejects_existing_db_l2_payload(orders_case):
    db, connection, _, _ = orders_case
    connection.insights_cache = {
        "success": True,
        "insights_version": pipeline.INSIGHTS_CACHE_VERSION,
        "applied_date_from": "2026-01-03",
        "applied_date_to": "2026-01-03",
        "key_metrics": [{"id": "stale"}],
    }
    connection.insights_cached_at = datetime.datetime.now(datetime.timezone.utc)
    db.flush()

    result = _run(orders_case, date_from="2026-01-01", date_to="2026-01-02")
    metrics = {item["id"]: item for item in result["key_metrics"]}

    assert "stale" not in metrics
    assert metrics["total_revenue"]["raw_value"] == 30.0
    assert result["applied_date_from"] == "2026-01-01"
    assert result.get("cache_source") != "db_l2"


def test_invalid_date_returns_http_400_without_querying_database():
    app = FastAPI()
    app.include_router(insights_router)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(tenant_id=1)
    app.dependency_overrides[get_db] = lambda: object()

    with TestClient(app) as client:
        response = client.get("/api/insights/generate/1", params={"date_from": "2025-13-01"})

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid date filter"}
