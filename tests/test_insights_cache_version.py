"""Offline E1 cache-generation tests using temporary SQLite databases."""

import datetime
import json
import sqlite3

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker

import models
from routers import insights as insights_router
from services import db_pipeline_service as pipeline
from services import db_pool, db_utils, redis_service
from services.db_migration import run_schema_migrations
from services.sql_dialect import UnsupportedDialectError


@pytest.fixture(autouse=True)
def isolated_memory_cache(monkeypatch):
    """Use and clear the real process-local cache implementation for every test."""
    redis_service._MEM_CACHE.clear()
    monkeypatch.setattr(pipeline, "cache_get", redis_service.cache_get)
    monkeypatch.setattr(pipeline, "cache_set", redis_service.cache_set)
    yield
    redis_service._MEM_CACHE.clear()


@pytest.fixture
def app_store(tmp_path):
    """Create an isolated file-backed application database and session."""
    db_path = tmp_path / "e1_app.sqlite"
    engine = create_engine(URL.create("sqlite", database=str(db_path)))
    models.Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db, SessionLocal
    finally:
        db.rollback()
        db.close()
        engine.dispose()


def _add_connection(db, tenant_name, connection_name, *, db_type="sqlite", database=None):
    tenant = models.Tenant(name=tenant_name)
    db.add(tenant)
    db.flush()
    connection = models.DatabaseConnection(
        tenant_id=tenant.id,
        name=connection_name,
        db_type=db_type,
        database=database,
        insights_cache_version=0,
    )
    db.add(connection)
    db.commit()
    return tenant, connection


def _stored_connection(db, connection_id):
    db.expire_all()
    return db.query(models.DatabaseConnection).filter(
        models.DatabaseConnection.id == connection_id,
    ).one()


def _install_analytics_fixture(tmp_path, monkeypatch, connection):
    analytics_path = tmp_path / "e1_analytics.sqlite"
    with sqlite3.connect(analytics_path) as analytics_db:
        analytics_db.execute(
            "CREATE TABLE transactions (id INTEGER, amount REAL, created_on TEXT)"
        )
        analytics_db.executemany(
            "INSERT INTO transactions VALUES (?, ?, ?)",
            [(1, 12.5, "2026-01-01"), (2, 7.5, "2026-01-02")],
        )

    connection.database = str(analytics_path)
    connection.tables_metadata = {
        "transactions": {
            "columns": {"id": "INTEGER", "amount": "REAL", "created_on": "TEXT"},
            "row_count": 2,
        }
    }
    analytics_engine = create_engine(URL.create("sqlite", database=str(analytics_path)))
    monkeypatch.setattr(db_utils, "get_connection_url", lambda _connection: analytics_engine.url)
    monkeypatch.setattr(db_pool, "get_engine", lambda _url: analytics_engine)
    monkeypatch.setattr(
        "services.llm_generation_service.generate",
        lambda *_args, **_kwargs: json.dumps({
            "business_domain": "Synthetic fixture",
            "executive_summary": "Synthetic summary",
            "strategic_insights": [],
            "tactical_recommendations": [],
        }),
    )
    return analytics_engine


def test_refresh_bumps_version_and_old_key_becomes_unreachable(app_store):
    db, _ = app_store
    tenant, connection = _add_connection(db, "Tenant A", "Connection A")
    old_key = pipeline._cache_key(tenant.id, connection.id, None, None, None, 0)
    redis_service.cache_set(
        old_key,
        {
            "insights_version": pipeline.INSIGHTS_CACHE_VERSION,
            "connection_cache_version": 0,
            "marker": "stale",
        },
    )

    new_version = pipeline.DatabasePipelineService().invalidate_connection_cache(
        db, tenant.id, connection.id,
    )
    new_key = pipeline._cache_key(
        tenant.id, connection.id, None, None, None, new_version,
    )

    assert new_version == 1
    assert new_key != old_key
    assert redis_service.cache_get(old_key)["marker"] == "stale"
    assert redis_service.cache_get(new_key) is None
    assert _stored_connection(db, connection.id).insights_cache_version == 1


def test_refresh_is_tenant_scoped(app_store):
    db, _ = app_store
    tenant_a, connection_a = _add_connection(db, "Tenant A", "Connection A")
    tenant_b, connection_b = _add_connection(db, "Tenant B", "Connection B")
    service = pipeline.DatabasePipelineService()

    with pytest.raises(ValueError, match="not found or unauthorized"):
        service.invalidate_connection_cache(db, tenant_b.id, connection_a.id)

    assert _stored_connection(db, connection_a.id).insights_cache_version == 0
    assert _stored_connection(db, connection_b.id).insights_cache_version == 0

    assert service.invalidate_connection_cache(db, tenant_a.id, connection_a.id) == 1
    assert _stored_connection(db, connection_a.id).insights_cache_version == 1
    assert _stored_connection(db, connection_b.id).insights_cache_version == 0


def test_refresh_clears_database_l2_fields(app_store):
    db, _ = app_store
    tenant, connection = _add_connection(db, "Tenant A", "Connection A")
    connection.insights_cache = {"marker": "stale"}
    connection.insights_cached_at = datetime.datetime.now(datetime.timezone.utc)
    db.commit()

    pipeline.DatabasePipelineService().invalidate_connection_cache(
        db, tenant.id, connection.id,
    )
    stored = _stored_connection(db, connection.id)

    assert stored.insights_cache_version == 1
    assert stored.insights_cache is None
    assert stored.insights_cached_at is None


def test_startup_migration_adds_version_zero_to_legacy_row(tmp_path):
    db_path = tmp_path / "legacy_app.sqlite"
    engine = create_engine(URL.create("sqlite", database=str(db_path)))
    try:
        with engine.begin() as connection:
            connection.execute(text(
                "CREATE TABLE database_connections ("
                "id INTEGER PRIMARY KEY, tenant_id INTEGER NOT NULL, name VARCHAR NOT NULL, "
                "db_type VARCHAR NOT NULL)"
            ))
            connection.execute(text(
                "INSERT INTO database_connections (id, tenant_id, name, db_type) "
                "VALUES (1, 7, 'Legacy fixture', 'sqlite')"
            ))

        run_schema_migrations(engine)
        run_schema_migrations(engine)

        columns = {column["name"]: column for column in inspect(engine).get_columns("database_connections")}
        with engine.connect() as connection:
            version = connection.execute(text(
                "SELECT insights_cache_version FROM database_connections WHERE id = 1"
            )).scalar_one()

        assert "insights_cache_version" in columns
        assert columns["insights_cache_version"]["nullable"] is False
        assert version == 0
    finally:
        engine.dispose()


def test_pipeline_rejects_stale_generation_key(app_store):
    db, _ = app_store
    tenant, connection = _add_connection(
        db, "Tenant A", "Unsupported fixture", db_type="unsupported",
    )
    connection.insights_cache_version = 1
    db.commit()
    stale_key = pipeline._cache_key(tenant.id, connection.id, None, None, None, 0)
    current_key = pipeline._cache_key(tenant.id, connection.id, None, None, None, 1)
    redis_service.cache_set(
        stale_key,
        {
            "insights_version": pipeline.INSIGHTS_CACHE_VERSION,
            "connection_cache_version": 0,
            "success": True,
        },
    )

    with pytest.raises(UnsupportedDialectError):
        pipeline.DatabasePipelineService().run_db_pipeline(
            db=db,
            tenant_id=tenant.id,
            connection_id=connection.id,
        )

    assert redis_service.cache_get(stale_key) is not None
    assert redis_service.cache_get(current_key) is None


def test_l2_write_requires_unchanged_cache_version(app_store, tmp_path, monkeypatch):
    db, _ = app_store
    tenant, connection = _add_connection(db, "Tenant A", "Connection A")
    analytics_engine = _install_analytics_fixture(tmp_path, monkeypatch, connection)
    db.commit()
    original_cache_set = redis_service.cache_set
    refresh_triggered = False

    def cache_set_then_refresh(key, value, **kwargs):
        nonlocal refresh_triggered
        stored = original_cache_set(key, value, **kwargs)
        if not refresh_triggered:
            refresh_triggered = True
            assert pipeline.DatabasePipelineService().invalidate_connection_cache(
                db, tenant.id, connection.id,
            ) == 1
        return stored

    monkeypatch.setattr(pipeline, "cache_set", cache_set_then_refresh)
    try:
        result = pipeline.DatabasePipelineService().run_db_pipeline(
            db=db,
            tenant_id=tenant.id,
            connection_id=connection.id,
        )
    finally:
        analytics_engine.dispose()

    stored = _stored_connection(db, connection.id)
    assert refresh_triggered is True
    assert result["connection_cache_version"] == 0
    assert stored.insights_cache_version == 1
    assert stored.insights_cache is None
    assert stored.insights_cached_at is None


def test_calculation_failure_after_refresh_keeps_new_generation(app_store):
    db, _ = app_store
    tenant, connection = _add_connection(
        db, "Tenant A", "Unsupported fixture", db_type="unsupported",
    )
    connection.insights_cache = {"marker": "stale"}
    connection.insights_cached_at = datetime.datetime.now(datetime.timezone.utc)
    db.commit()

    with pytest.raises(UnsupportedDialectError):
        pipeline.DatabasePipelineService().run_db_pipeline(
            db=db,
            tenant_id=tenant.id,
            connection_id=connection.id,
            force_refresh=True,
        )

    stored = _stored_connection(db, connection.id)
    assert stored.insights_cache_version == 1
    assert stored.insights_cache is None
    assert stored.insights_cached_at is None


def test_scoped_legacy_refresh_also_invalidates_pipeline_cache(app_store, monkeypatch):
    db, _ = app_store
    tenant, connection = _add_connection(db, "Tenant A", "Connection A")
    connection.insights_cache = {"marker": "stale"}
    connection.insights_cached_at = datetime.datetime.now(datetime.timezone.utc)
    db.commit()
    monkeypatch.setattr(
        insights_router.insights_engine,
        "refresh_tenant_insights",
        lambda **_kwargs: [],
    )

    response = insights_router.refresh_ai_insights(
        database_id=connection.id,
        current_user=type("User", (), {"tenant_id": tenant.id})(),
        db=db,
    )
    stored = _stored_connection(db, connection.id)

    assert response.refreshed_count == 0
    assert stored.insights_cache_version == 1
    assert stored.insights_cache is None
    assert stored.insights_cached_at is None
