"""Offline Insights LLM payload tests; generation is always mocked."""

import json
import sqlite3

from sqlalchemy import create_engine
from sqlalchemy.engine import URL

import models
from services import db_pipeline_service as pipeline_module
from services import db_pool, db_utils


def test_llm_safe_points_removes_unvalidated_labels_and_chart_keys():
    safe = pipeline_module._llm_safe_points(
        [{"id": "Alice Example", "label": "Alice Example", "raw_value": 1234.5}],
        [{
            "id": "Alice Example",
            "title": "Alice Example",
            "type": "Alice Example",
            "xKey": "Alice Example",
            "yKey": "Alice Example",
            "data": [
                {"name": "Alice Example", "value": 20},
                {"name": "Alice Example", "val": 5},
            ],
        }, {
            "id": "Alice Example",
            "title": "Alice Example",
            "type": "bar",
            "xKey": "Alice Example",
            "yKey": "Alice Example",
            "data": [{"name": "Alice Example", "value": 42}],
        }],
    )

    assert safe == {
        "metrics": [1234.5],
        "chart_aggregates": [
            {"category": "aggregate", "values": [20, 5]},
            {"category": "category_aggregate", "values": [42]},
        ],
    }
    assert "Alice Example" not in json.dumps(safe)


def test_run_ai_synthesis_prompt_has_only_safe_aggregates(
    isolated_db, tmp_path, monkeypatch,
):
    """Offline integration: capture the actual prompt with a mocked generate call."""
    sqlite_path = tmp_path / "insights_llm_payload.sqlite"
    with sqlite3.connect(sqlite_path) as sqlite_db:
        sqlite_db.execute(
            "CREATE TABLE orders (order_id INTEGER, amount REAL, customer_name TEXT)"
        )
        sqlite_db.execute(
            "INSERT INTO orders VALUES (?, ?, ?)", (1, 1234.5, "Alice Example")
        )

    schema = {
        "orders": {
            "columns": {
                "order_id": "INTEGER",
                "amount": "REAL",
                "customer_name": "TEXT",
            },
            "row_count": 1,
        }
    }
    tenant = models.Tenant(name="Offline LLM payload test")
    isolated_db.add(tenant)
    isolated_db.flush()
    connection = models.DatabaseConnection(
        tenant_id=tenant.id,
        name="Offline LLM payload test",
        db_type="sqlite",
        database=str(sqlite_path),
        tables_metadata=schema,
    )
    isolated_db.add(connection)
    isolated_db.flush()

    captured_prompts = []

    def fake_generate(prompt, **_kwargs):
        captured_prompts.append(prompt)
        return json.dumps({
            "business_domain": "Test data",
            "executive_summary": "Synthetic summary",
            "strategic_insights": [],
            "tactical_recommendations": [],
        })

    engine = create_engine(URL.create("sqlite", database=str(sqlite_path)))
    monkeypatch.setattr(pipeline_module, "cache_get", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(pipeline_module, "cache_set", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(db_utils, "get_connection_url", lambda _connection: engine.url)
    monkeypatch.setattr(db_pool, "get_engine", lambda _url: engine)
    monkeypatch.setattr("services.llm_generation_service.generate", fake_generate)

    try:
        pipeline_module.DatabasePipelineService().run_db_pipeline(
            db=isolated_db,
            connection_id=connection.id,
            tenant_id=tenant.id,
            selected_table="orders",
            force_refresh=False,
        )
    finally:
        engine.dispose()

    assert captured_prompts
    prompt = "\n".join(captured_prompts)
    assert "Alice Example" not in prompt
    assert "1234.5" in prompt
