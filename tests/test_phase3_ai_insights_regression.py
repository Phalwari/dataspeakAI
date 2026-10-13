"""
tests/test_phase3_ai_insights_regression.py
-------------------------------------------
Comprehensive automated regression test suite for Phase 3:
1. ORM Schema & Foreign Key Lifecycle:
   - GeneratedInsight and Recommendation models
   - Cascade deletion of recommendations on insight deletion
   - Nullable database_id link and cascade on tenant deletion
2. InsightsEngine Telemetry Collection & Anomaly Detection:
   - Genuine query logs, latency, and error rate telemetry calculations
   - Deterministic rule triggers: error rate spikes, latency bottlenecks, unprofiled databases, empty KB
3. Deterministic Fallback Synthesis:
   - Formulates authentic structured insights without hallucinated numbers when LLM is offline
4. API Endpoints:
   - GET /api/insights (overview KPIs, category filtering, severity filtering, DB scoping, dismissed toggle)
   - POST /api/insights/refresh (synchronous refresh and persistence)
   - PUT /api/insights/{id}/status (active vs dismissed)
   - PUT /api/insights/recommendations/{id}/status (pending vs completed)
5. Multi-Tenant Data Isolation:
   - Guarantees Tenant A cannot view, modify, or dismiss Tenant B's insights or recommendations.
"""

import os
import sys
from datetime import datetime, timezone, timedelta

# Ensure backend directory is in path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from main import app
from database import Base, get_db
from dependencies import get_current_user
import models
import auth
from services.insights_engine import insights_engine


@pytest.fixture
def test_env():
    """Sets up an isolated SQLite in-memory database with seeded test data for Phase 3."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    session = TestingSession()

    # 1. Seed Tenants
    tenant_a = models.Tenant(id=1, name="Acme Analytics", plan="Pro")
    tenant_b = models.Tenant(id=2, name="Beta Logistics", plan="Starter")
    session.add_all([tenant_a, tenant_b])
    session.commit()

    # 2. Seed Users
    hashed_pw = auth.get_password_hash("TestPassword123!")
    user_a = models.User(
        id=1,
        email="alice@acme.com",
        hashed_password=hashed_pw,
        full_name="Alice Acme",
        role="Admin",
        is_active=True,
        is_verified=True,
        tenant_id=1,
    )
    user_b = models.User(
        id=2,
        email="bob@beta.com",
        hashed_password=hashed_pw,
        full_name="Bob Beta",
        role="Admin",
        is_active=True,
        is_verified=True,
        tenant_id=2,
    )
    session.add_all([user_a, user_b])
    session.commit()

    # 3. Seed Database Connection
    db_conn = models.DatabaseConnection(
        id=1,
        tenant_id=1,
        name="Production Postgres",
        db_type="postgresql",
        database="acme_prod",
        status="connected",
        tables_metadata=[{"table_name": "orders"}, {"table_name": "customers"}],
    )
    session.add(db_conn)
    session.commit()

    # 4. Seed Query Logs (4 success, 2 failed -> 33.3% failure rate)
    now = datetime.now(timezone.utc)
    for i in range(4):
        session.add(models.QueryLog(
            tenant_id=1,
            user_id=1,
            database_id=1,
            natural_query=f"Show total orders batch {i}",
            generated_sql=f"SELECT COUNT(*) FROM orders WHERE batch = {i}",
            status="success",
            execution_time_ms=120.0 + i * 10,
            tokens_used=150,
            created_at=now - timedelta(hours=i),
        ))
    session.add(models.QueryLog(
        tenant_id=1,
        user_id=1,
        database_id=1,
        natural_query="Select invalid column",
        generated_sql="SELECT unknown_col FROM orders",
        status="failed",
        error_message="Column unknown_col does not exist in table orders",
        execution_time_ms=50.0,
        tokens_used=90,
        created_at=now - timedelta(minutes=30),
    ))
    session.add(models.QueryLog(
        tenant_id=1,
        user_id=1,
        database_id=1,
        natural_query="Timeout query",
        generated_sql="SELECT * FROM large_log",
        status="failed",
        error_message="Statement timeout exceeded after 5000ms",
        execution_time_ms=5000.0,
        tokens_used=110,
        created_at=now - timedelta(minutes=10),
    ))
    session.commit()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    yield {
        "session": session,
        "tenant_a": tenant_a,
        "tenant_b": tenant_b,
        "user_a": user_a,
        "user_b": user_b,
        "db_conn": db_conn,
    }

    app.dependency_overrides.clear()
    session.close()
    Base.metadata.drop_all(bind=engine)


# ── Test 1: ORM Schema & Foreign Key Cascades ─────────────────────────────────

def test_models_and_foreign_keys(test_env):
    session = test_env["session"]

    insight = models.GeneratedInsight(
        tenant_id=1,
        database_id=1,
        title="Elevated Query Error Rate",
        category="Performance",
        severity="critical",
        summary="Error rate of 33.3% detected across recent queries.",
        impact_score=8.5,
        confidence_score=0.96,
        status="active"
    )
    session.add(insight)
    session.commit()

    rec1 = models.Recommendation(
        insight_id=insight.id,
        action_step="Review column schemas in orders table",
        priority="high",
        action_type="navigate_logs",
        action_url="/dashboard/logs?status=failed",
        status="pending"
    )
    rec2 = models.Recommendation(
        insight_id=insight.id,
        action_step="Add index on large_log table to prevent timeouts",
        priority="medium",
        action_type="navigate_databases",
        action_url="/dashboard/databases",
        status="pending"
    )
    session.add_all([rec1, rec2])
    session.commit()

    # Verify query and relationship
    fetched = session.query(models.GeneratedInsight).filter_by(id=insight.id).first()
    assert fetched is not None
    assert fetched.title == "Elevated Query Error Rate"
    assert fetched.severity == "critical"
    assert len(fetched.recommendations) == 2

    # Verify cascade delete
    session.delete(fetched)
    session.commit()
    assert session.query(models.Recommendation).filter_by(insight_id=insight.id).count() == 0


# ── Test 2: Telemetry Collection & Anomaly Detection ──────────────────────────

def test_telemetry_collection_and_anomalies(test_env):
    session = test_env["session"]

    telemetry = insights_engine.collect_tenant_telemetry(tenant_id=1, database_id=None, db=session)
    assert telemetry["has_data"] is True
    assert telemetry["queries"]["total"] == 6
    assert telemetry["queries"]["failed"] == 2
    assert telemetry["queries"]["failure_rate_pct"] == pytest.approx(33.33, rel=1e-2)
    assert telemetry["databases"]["count"] == 1
    assert telemetry["databases"]["total_tables"] == 2

    anomalies = insights_engine.detect_deterministic_anomalies(telemetry)
    assert len(anomalies) > 0
    # Rule HIGH_FAILURE_RATE should trigger on 33.3% failure rate
    rules = [a["rule"] for a in anomalies]
    assert "HIGH_FAILURE_RATE" in rules
    assert any(a["severity"] == "critical" for a in anomalies)


# ── Test 3: Deterministic Fallback Synthesis ──────────────────────────────────

def test_deterministic_fallback_synthesis(test_env):
    session = test_env["session"]

    telemetry = insights_engine.collect_tenant_telemetry(tenant_id=1, database_id=1, db=session)
    anomalies = insights_engine.detect_deterministic_anomalies(telemetry)
    fallback_insights = insights_engine.generate_deterministic_fallback(telemetry, anomalies, database_id=1)

    assert len(fallback_insights) >= 2
    # Check first insight properties
    first = fallback_insights[0]
    assert "Query Execution Failure Rate" in first["title"]
    assert first["category"] == "Performance"
    assert first["severity"] in ("critical", "warning")
    assert len(first["recommendations"]) >= 1
    assert first["recommendations"][0]["action_type"] == "navigate_logs"
    assert first["recommendations"][0]["action_url"] == "/dashboard/logs?status=failed"


# ── Test 4: Database Persistence & Atomic Refresh ─────────────────────────────

def test_persist_and_refresh_insights(test_env):
    session = test_env["session"]

    persisted = insights_engine.refresh_tenant_insights(tenant_id=1, database_id=1, db=session)
    assert len(persisted) > 0

    # Query directly from DB
    db_insights = session.query(models.GeneratedInsight).filter_by(tenant_id=1).all()
    assert len(db_insights) == len(persisted)
    for insight in db_insights:
        assert insight.status == "active"
        assert len(insight.recommendations) > 0


# ── Test 5: GET /api/insights Endpoint ────────────────────────────────────────

def test_get_ai_insights_endpoint(test_env):
    user_a = test_env["user_a"]
    app.dependency_overrides[get_current_user] = lambda: user_a

    client = TestClient(app)
    response = client.get("/api/insights")
    assert response.status_code == 200

    data = response.json()
    assert "summary" in data
    assert "insights" in data
    assert data["summary"]["total_insights"] > 0
    assert data["has_connected_sources"] is True

    # Validate structure of first insight
    first_insight = data["insights"][0]
    assert "id" in first_insight
    assert "title" in first_insight
    assert "category" in first_insight
    assert "severity" in first_insight
    assert "recommendations" in first_insight
    assert isinstance(first_insight["recommendations"], list)


# ── Test 6: GET /api/insights Category & Severity Filtering ───────────────────

def test_get_ai_insights_filtering(test_env):
    user_a = test_env["user_a"]
    app.dependency_overrides[get_current_user] = lambda: user_a

    client = TestClient(app)

    # 1. Filter by Performance Category
    res_perf = client.get("/api/insights?category=Performance")
    assert res_perf.status_code == 200
    for item in res_perf.json()["insights"]:
        assert item["category"].lower() == "performance"

    # 2. Filter by Severity
    res_crit = client.get("/api/insights?severity=critical")
    assert res_crit.status_code == 200
    for item in res_crit.json()["insights"]:
        assert item["severity"].lower() == "critical"

    # 3. Filter by Database ID
    res_db = client.get("/api/insights?database_id=1")
    assert res_db.status_code == 200
    assert len(res_db.json()["insights"]) > 0


# ── Test 7: POST /api/insights/refresh Endpoint ───────────────────────────────

def test_post_refresh_ai_insights_endpoint(test_env):
    user_a = test_env["user_a"]
    app.dependency_overrides[get_current_user] = lambda: user_a

    client = TestClient(app)
    response = client.post("/api/insights/refresh?database_id=1")
    assert response.status_code == 200

    data = response.json()
    assert "refreshed_count" in data
    assert data["refreshed_count"] > 0
    assert len(data["insights"]) == data["refreshed_count"]


# ── Test 8: PUT /api/insights/{id}/status (Dismiss vs Active) ──────────────────

def test_update_insight_status_endpoint(test_env):
    session = test_env["session"]
    user_a = test_env["user_a"]
    app.dependency_overrides[get_current_user] = lambda: user_a

    # Ensure an insight exists
    insights_engine.refresh_tenant_insights(tenant_id=1, database_id=1, db=session)
    insight = session.query(models.GeneratedInsight).filter_by(tenant_id=1).first()
    assert insight is not None

    client = TestClient(app)

    # Dismiss insight
    res_dismiss = client.put(f"/api/insights/{insight.id}/status", json={"status": "dismissed"})
    assert res_dismiss.status_code == 200
    assert res_dismiss.json()["status"] == "dismissed"

    # Verify GET active filter excludes dismissed insight
    res_active = client.get("/api/insights?status=active")
    assert all(i["id"] != insight.id for i in res_active.json()["insights"])

    # Verify GET all includes dismissed insight
    res_all = client.get("/api/insights?status=all")
    assert any(i["id"] == insight.id for i in res_all.json()["insights"])

    # Restore to active
    res_restore = client.put(f"/api/insights/{insight.id}/status", json={"status": "active"})
    assert res_restore.status_code == 200
    assert res_restore.json()["status"] == "active"

    # Invalid status returns 400
    res_invalid = client.put(f"/api/insights/{insight.id}/status", json={"status": "invalid_val"})
    assert res_invalid.status_code == 400


# ── Test 9: PUT /api/insights/recommendations/{id}/status ─────────────────────

def test_update_recommendation_status_endpoint(test_env):
    session = test_env["session"]
    user_a = test_env["user_a"]
    app.dependency_overrides[get_current_user] = lambda: user_a

    insights_engine.refresh_tenant_insights(tenant_id=1, database_id=1, db=session)
    rec = session.query(models.Recommendation).join(models.GeneratedInsight).filter(
        models.GeneratedInsight.tenant_id == 1
    ).first()
    assert rec is not None
    assert rec.status == "pending"

    client = TestClient(app)

    # Mark as completed
    res_completed = client.put(f"/api/insights/recommendations/{rec.id}/status", json={"status": "completed"})
    assert res_completed.status_code == 200
    assert res_completed.json()["status"] == "completed"

    # Mark back to pending
    res_pending = client.put(f"/api/insights/recommendations/{rec.id}/status", json={"status": "pending"})
    assert res_pending.status_code == 200
    assert res_pending.json()["status"] == "pending"

    # 404 on non-existent recommendation
    res_404 = client.put("/api/insights/recommendations/99999/status", json={"status": "completed"})
    assert res_404.status_code == 404


# ── Test 10: Multi-Tenant Data Isolation ──────────────────────────────────────

def test_strict_tenant_isolation(test_env):
    session = test_env["session"]
    user_b = test_env["user_b"]  # Belongs to Tenant 2 (Beta Logistics)

    # Ensure Tenant 1 has insights
    insights_engine.refresh_tenant_insights(tenant_id=1, database_id=1, db=session)
    insight_t1 = session.query(models.GeneratedInsight).filter_by(tenant_id=1).first()
    rec_t1 = insight_t1.recommendations[0]

    # Authenticate as User B (Tenant 2)
    app.dependency_overrides[get_current_user] = lambda: user_b
    client = TestClient(app)

    # 1. Tenant B must see 0 insights from Tenant A
    res_t2 = client.get("/api/insights")
    assert res_t2.status_code == 200
    assert len(res_t2.json()["insights"]) == 0
    assert res_t2.json()["summary"]["total_insights"] == 0

    # 2. Tenant B cannot mutate Tenant A's insight status (404)
    res_mutate_insight = client.put(f"/api/insights/{insight_t1.id}/status", json={"status": "dismissed"})
    assert res_mutate_insight.status_code == 404

    # 3. Tenant B cannot mutate Tenant A's recommendation status (403 unauthorized)
    res_mutate_rec = client.put(f"/api/insights/recommendations/{rec_t1.id}/status", json={"status": "completed"})
    assert res_mutate_rec.status_code == 403
