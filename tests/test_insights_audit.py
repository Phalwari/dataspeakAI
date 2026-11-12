"""Offline Insight action audit checks using the isolated SQLite application DB."""

import asyncio
import json

import pytest
from fastapi import HTTPException

import models
from routers import insights


@pytest.fixture
def actor(isolated_db):
    tenant = models.Tenant(name="Synthetic audit tenant")
    isolated_db.add(tenant)
    isolated_db.flush()
    user = models.User(
        email="audit-fixture@example.invalid", hashed_password="fixture-only",
        tenant_id=tenant.id,
    )
    connection = models.DatabaseConnection(
        tenant_id=tenant.id, name="Synthetic source", db_type="sqlite",
        database="synthetic-source",
    )
    isolated_db.add_all([user, connection])
    isolated_db.commit()
    return isolated_db, user, connection


def _audit_rows(db):
    return db.query(models.AuditLog).filter(
        models.AuditLog.action.like("insights.%")
    ).order_by(models.AuditLog.id).all()


def _fake_result(source="llm"):
    return {"executive_summary": {"source": source, "executive_summary": "Synthetic summary"}}


def test_generate_records_scoped_action_and_only_allowed_filters(actor, monkeypatch):
    db, user, connection = actor
    monkeypatch.setattr(insights.db_pipeline_service, "run_db_pipeline", lambda **_kwargs: _fake_result())
    insights.generate_database_insights(
        connection_id=connection.id, table="safe_table", refresh=False,
        date_from="2026-01-01", date_to="2026-01-02", current_user=user, db=db,
    )
    rows = _audit_rows(db)
    assert len(rows) == 1
    row = rows[0]
    assert (row.tenant_id, row.user_id, row.action) == (user.tenant_id, user.id, "insights.generate")
    assert row.details["connection_id"] == connection.id
    assert row.details["filters"] == {
        "table": "safe_table", "date_from": "2026-01-01", "date_to": "2026-01-02",
    }
    assert row.details["status"] == "success"
    assert isinstance(row.details["duration_ms"], int)
    assert set(row.details) == {"connection_id", "filters", "status", "duration_ms"}


def test_error_records_status_without_raw_exception(actor, monkeypatch):
    db, user, connection = actor
    monkeypatch.setattr(
        insights.db_pipeline_service, "run_db_pipeline",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("PRIVATE_MARKER")),
    )
    with pytest.raises(HTTPException) as exc:
        insights.generate_database_insights(
            connection_id=connection.id, table="unsafe/PRIVATE_MARKER", refresh=False,
            date_from=None, date_to=None, current_user=user, db=db,
        )
    assert exc.value.status_code == 500
    rows = _audit_rows(db)
    assert len(rows) == 1
    assert rows[0].details["status"] == "error"
    assert rows[0].details["filters"]["table"] is None
    assert "PRIVATE_MARKER" not in json.dumps(rows[0].details)


def test_post_records_fallback(actor, monkeypatch):
    db, user, connection = actor
    monkeypatch.setattr(
        insights.db_pipeline_service, "run_db_pipeline",
        lambda **_kwargs: _fake_result("deterministic_fallback"),
    )
    insights.run_database_pipeline_post(
        connection_id=connection.id, payload={"table": "safe_table"}, current_user=user, db=db,
    )
    assert _audit_rows(db)[0].details["status"] == "fallback"
    assert _audit_rows(db)[0].action == "insights.pipeline"


def test_refresh_and_export_record_actions(actor, monkeypatch):
    db, user, connection = actor
    monkeypatch.setattr(insights.db_pipeline_service, "invalidate_connection_cache", lambda **_kwargs: None)
    monkeypatch.setattr(insights.insights_engine, "refresh_tenant_insights", lambda **_kwargs: [])
    monkeypatch.setattr(insights.db_pipeline_service, "run_db_pipeline", lambda **_kwargs: _fake_result())
    insights.refresh_ai_insights(database_id=connection.id, current_user=user, db=db)
    insights.export_insights(connection_id=connection.id, current_user=user, db=db)
    assert [row.action for row in _audit_rows(db)] == ["insights.refresh", "insights.export"]
    assert all(row.tenant_id == user.tenant_id for row in _audit_rows(db))


def test_stream_updates_started_record_to_final_status(actor, monkeypatch):
    db, user, connection = actor
    monkeypatch.setattr(
        insights.db_pipeline_service, "run_db_pipeline_stream",
        lambda **_kwargs: iter([{"type": "result", "data": _fake_result("deterministic_fallback")}]),
    )
    response = insights.stream_database_pipeline(
        connection_id=connection.id, table=None, refresh=False,
        date_from=None, date_to=None, current_user=user, db=db,
    )
    assert _audit_rows(db)[0].details["status"] == "in_progress"

    async def consume():
        return "".join([chunk async for chunk in response.body_iterator])

    assert '"type": "result"' in asyncio.run(consume())
    rows = _audit_rows(db)
    assert len(rows) == 1
    assert rows[0].action == "insights.stream"
    assert rows[0].details["status"] == "fallback"
