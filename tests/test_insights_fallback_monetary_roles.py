"""Offline fallback wording checks on synthetic SQLite schemas."""

import sqlite3

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

import models
from services import db_pipeline_service as pipeline
from services import db_pool, db_utils, llm_generation_service as llm


@pytest.mark.parametrize(
    ("column", "expected"),
    [
        ("gross_revenue", True),
        ("salesAmount", True),
        ("order_amount", True),
        ("grand_total", True),
        ("unit_price", True),
        ("salary", False),
        ("total_salary", False),
        ("salary_amount", False),
        ("unit_cost", False),
        ("service_fee", False),
        ("account_balance", False),
        ("payroll_amount", False),
        ("expense_total", False),
        ("sales_tax", False),
        ("discount_total", False),
        (None, False),
    ],
)
def test_fallback_column_name_requires_revenue_marker_without_cost_marker(column, expected):
    assert pipeline._is_revenue_like_fallback_column(column) is expected


@pytest.mark.parametrize(
    ("table_name", "money_column", "expected_text"),
    [
        ("employees", "salary", "Insufficient data to generate a reliable business summary."),
        ("sales_records", "sales_amount", "Computed monetary sum is $150.00 across 1 record."),
    ],
)
def test_fallback_uses_only_revenue_like_money(
    isolated_db, tmp_path, monkeypatch, table_name, money_column, expected_text,
):
    source_path = tmp_path / "fallback_roles.sqlite"
    with sqlite3.connect(source_path) as source:
        source.execute(f"CREATE TABLE {table_name} (id INTEGER, {money_column} REAL)")
        source.execute(f"INSERT INTO {table_name} VALUES (?, ?)", (1, 150.0))
        if table_name == "employees":
            source.execute("CREATE TABLE inventory (id INTEGER, units_in_stock INTEGER)")
            source.execute("INSERT INTO inventory VALUES (?, ?)", (1, 7))

    tenant = models.Tenant(name="Synthetic fallback tenant")
    isolated_db.add(tenant)
    isolated_db.flush()
    schema = {table_name: {
        "columns": {"id": "INTEGER", money_column: "REAL"}, "row_count": 1,
    }}
    if table_name == "employees":
        schema["inventory"] = {
            "columns": {"id": "INTEGER", "units_in_stock": "INTEGER"},
            "row_count": 1,
        }
    connection = models.DatabaseConnection(
        tenant_id=tenant.id,
        name="Synthetic fallback source",
        db_type="sqlite",
        database=str(source_path),
        tables_metadata=schema,
    )
    isolated_db.add(connection)
    isolated_db.flush()

    engine = create_engine(URL.create("sqlite", database=str(source_path)))
    monkeypatch.setattr(db_utils, "get_connection_url", lambda _connection: engine.url)
    monkeypatch.setattr(db_pool, "get_engine", lambda _url: engine)
    monkeypatch.setattr(pipeline, "cache_get", lambda _key: None)
    monkeypatch.setattr(pipeline, "cache_set", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        llm, "generate",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(TimeoutError("synthetic timeout")),
    )
    try:
        result = pipeline.DatabasePipelineService().run_db_pipeline(
            db=isolated_db,
            tenant_id=tenant.id,
            connection_id=connection.id,
            selected_table=table_name,
        )
    finally:
        engine.dispose()

    summary = result["executive_summary"]
    assert summary["source"] == "deterministic_fallback"
    assert summary["llm_error"] == "Timeout"
    assert summary["executive_summary"] == expected_text
    metrics = {item["id"]: item for item in result["key_metrics"]}
    assert metrics[f"{table_name}_{money_column}_sum"]["raw_value"] == 150.0
    assert metrics[f"{table_name}_{money_column}_sum"]["status"] == "available"
