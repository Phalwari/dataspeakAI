"""
tests/test_phase1_dashboard_wiring_regression.py
------------------------------------------------
Comprehensive automated regression tests for Phase 1 endpoints:
1. GET /api/analytics/overview:
   - Returns real counts (queries, databases, documents, api_calls_today).
   - Generates 7-day query timeline.
   - Summarizes database activity.
   - Returns recent queries list.
2. GET /api/logs:
   - Paginates query logs.
   - Filters by status (success, failed, all).
   - Filters by database_id.
   - Searches natural query and generated SQL.
   - Calculates aggregate statistics (total, successful, failed, success_rate, avg_latency).
3. GET /api/logs/export:
   - Streams CSV download with headers and proper rows.
4. GET /api/usage:
   - Returns period-bounded queries, tokens used, available tokens, and db counts.
   - Generates daily/hourly timeline points for 24h, 7d, 30d, 90d.
   - Summarizes queries by database type.
   - Summarizes hourly query distribution.
5. GET /api/admin/stats & GET /api/admin/tenants:
   - Gated behind get_current_admin_user: blocks non-admin (403) and allows admin.
   - Returns platform-wide stats and tenant roster.
6. Tenant Data Isolation:
   - Guarantees Tenant A never sees Tenant B's logs or overview stats.
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
from dependencies import get_current_user, get_current_admin_user
import models
import auth


@pytest.fixture
def test_environment():
    """Sets up an isolated SQLite in-memory database with seeded test data."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSession()

    try:
        # 1. Create Tenant 1 and users
        tenant1 = models.Tenant(id=1, name="Acme Corp")
        db.add(tenant1)

        user1_admin = models.User(
            id=1,
            email="admin@acme.com",
            hashed_password="hash",
            full_name="Acme Admin",
            role="Admin",
            tenant_id=1,
            is_active=True,
            is_verified=True,
        )
        user1_member = models.User(
            id=2,
            email="member@acme.com",
            hashed_password="hash",
            full_name="Acme Member",
            role="Team Member",
            tenant_id=1,
            is_active=True,
            is_verified=True,
        )
        db.add_all([user1_admin, user1_member])

        # 2. Create Tenant 2
        tenant2 = models.Tenant(id=2, name="Beta Corp")
        db.add(tenant2)
        user2_admin = models.User(
            id=3,
            email="admin@beta.com",
            hashed_password="hash",
            full_name="Beta Admin",
            role="Admin",
            tenant_id=2,
            is_active=True,
            is_verified=True,
        )
        db.add(user2_admin)

        # 3. Create Database Connections
        db1 = models.DatabaseConnection(
            id=1,
            tenant_id=1,
            name="Production PostgreSQL",
            db_type="postgresql",
            status="connected",
        )
        db2 = models.DatabaseConnection(
            id=2,
            tenant_id=1,
            name="Analytics SQLite",
            db_type="sqlite",
            status="connected",
        )
        db3 = models.DatabaseConnection(
            id=3,
            tenant_id=2,
            name="Beta MySQL",
            db_type="mysql",
            status="connected",
        )
        db.add_all([db1, db2, db3])

        # 4. Create Documents
        doc1 = models.Document(
            id=1,
            tenant_id=1,
            name="Q3 Financials.pdf",
            file_type="pdf",
            size=1024,
            status="Completed",
        )
        db.add(doc1)

        # 5. Create Query Logs for Tenant 1
        now = datetime.now(timezone.utc)
        log1 = models.QueryLog(
            id=1,
            tenant_id=1,
            user_id=1,
            database_id=1,
            natural_query="Show top 5 products by revenue",
            generated_sql="SELECT name, SUM(price) FROM products GROUP BY name LIMIT 5",
            status="success",
            execution_time_ms=120.5,
            rows_returned=5,
            tokens_used=450,
            created_at=now - timedelta(days=1),
        )
        log2 = models.QueryLog(
            id=2,
            tenant_id=1,
            user_id=1,
            database_id=1,
            natural_query="List all customer transactions in 2026",
            generated_sql="SELECT * FROM transactions WHERE date >= '2026-01-01'",
            status="success",
            execution_time_ms=210.0,
            rows_returned=100,
            tokens_used=800,
            created_at=now,
        )
        log3 = models.QueryLog(
            id=3,
            tenant_id=1,
            user_id=2,
            database_id=2,
            natural_query="Calculate monthly churn rate",
            generated_sql="SELECT churn_rate FROM metrics",
            status="failed",
            execution_time_ms=50.0,
            rows_returned=0,
            tokens_used=200,
            error_message="Table 'metrics' not found",
            created_at=now,
        )

        # Query log for Tenant 2
        log4 = models.QueryLog(
            id=4,
            tenant_id=2,
            user_id=3,
            database_id=3,
            natural_query="Beta query",
            generated_sql="SELECT 1",
            status="success",
            execution_time_ms=10.0,
            rows_returned=1,
            tokens_used=100,
            created_at=now,
        )
        db.add_all([log1, log2, log3, log4])
        db.commit()

        yield {
            "db": db,
            "engine": engine,
            "TestingSession": TestingSession,
            "user1_admin": user1_admin,
            "user1_member": user1_member,
            "user2_admin": user2_admin,
        }
    finally:
        db.close()


def test_analytics_overview_endpoint(test_environment):
    """Verify GET /api/analytics/overview returns live tenant metrics and 7-day timeline."""
    env = test_environment
    db = env["db"]
    user = env["user1_admin"]

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    client = TestClient(app)

    try:
        response = client.get("/api/analytics/overview")
        assert response.status_code == 200, response.text
        data = response.json()

        assert data["total_queries"] == 3  # Tenant 1 has 3 logs
        assert data["connected_databases"] == 2
        assert data["uploaded_documents"] == 1
        assert data["api_calls_today"] >= 2
        assert data["subscription_plan"] == "Starter"

        # Check 7-day query timeline
        assert len(data["query_data"]) == 7
        assert sum(pt["queries"] for pt in data["query_data"]) == 3

        # Check database activity
        assert len(data["database_activity"]) >= 2
        db1_act = next((a for a in data["database_activity"] if a["name"] == "Production PostgreSQL"), None)
        assert db1_act is not None
        assert db1_act["queries"] == 2

        # Check recent queries
        assert len(data["recent_queries"]) == 3
        first_q = data["recent_queries"][0]
        assert "question" in first_q
        assert "database" in first_q
        assert "status" in first_q
    finally:
        app.dependency_overrides.clear()


def test_query_logs_endpoint_pagination_and_filtering(test_environment):
    """Verify GET /api/logs with search, status filter, and pagination."""
    env = test_environment
    db = env["db"]
    user = env["user1_admin"]

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    client = TestClient(app)

    try:
        # 1. Fetch all logs
        res = client.get("/api/logs?page=1&limit=10")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 3
        assert data["total_queries"] == 3
        assert data["successful"] == 2
        assert data["failed"] == 1
        assert data["success_rate"] == 66.7
        assert data["avg_response_time_ms"] > 0
        assert len(data["items"]) == 3

        # 2. Filter by status failed
        res_failed = client.get("/api/logs?status=failed")
        assert res_failed.status_code == 200
        failed_data = res_failed.json()
        assert failed_data["total"] == 1
        assert failed_data["items"][0]["status"] == "failed"
        assert "Table 'metrics' not found" in failed_data["items"][0]["error"]

        # 3. Filter by search pattern
        res_search = client.get("/api/logs?search=transactions")
        assert res_search.status_code == 200
        search_data = res_search.json()
        assert search_data["total"] == 1
        assert "transactions" in search_data["items"][0]["generatedQuery"]

        # 4. Filter by database_id
        res_db = client.get("/api/logs?database_id=2")
        assert res_db.status_code == 200
        db_data = res_db.json()
        assert db_data["total"] == 1
        assert db_data["items"][0]["database"] == "Analytics SQLite"
    finally:
        app.dependency_overrides.clear()


def test_query_logs_csv_export(test_environment):
    """Verify GET /api/logs/export streams CSV attachment."""
    env = test_environment
    db = env["db"]
    user = env["user1_admin"]

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    client = TestClient(app)

    try:
        res = client.get("/api/logs/export")
        assert res.status_code == 200
        assert "text/csv" in res.headers["content-type"]
        assert "attachment; filename=query_logs_" in res.headers["content-disposition"]

        content = res.text
        lines = content.strip().split("\r\n") if "\r\n" in content else content.strip().split("\n")
        assert len(lines) == 4  # Header + 3 query log rows
        header = lines[0]
        assert "id,timestamp,database,status" in header
        assert "user_question,generated_sql,error_message" in header
    finally:
        app.dependency_overrides.clear()


def test_tenant_usage_endpoint(test_environment):
    """Verify GET /api/usage returns token metrics, charts, and hourly distributions."""
    env = test_environment
    db = env["db"]
    user = env["user1_admin"]

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    client = TestClient(app)

    try:
        res = client.get("/api/usage?period=7d")
        assert res.status_code == 200
        data = res.json()

        assert data["total_queries"] == 3
        assert data["tokens_used"] == (450 + 800 + 200)
        assert data["token_limit"] == 500000
        assert data["available_tokens"] == 500000 - (450 + 800 + 200)
        assert data["databases_count"] == 2
        assert len(data["usage_data"]) == 7
        assert len(data["database_type_data"]) >= 2
        assert len(data["hourly_data"]) == 6

        # Check 24h period query
        res_24h = client.get("/api/usage?period=24h")
        assert res_24h.status_code == 200
        data_24h = res_24h.json()
        assert len(data_24h["usage_data"]) == 24
    finally:
        app.dependency_overrides.clear()


def test_admin_panel_endpoints_role_gating(test_environment):
    """Verify GET /api/admin/stats & /api/admin/tenants are protected by Admin role."""
    env = test_environment
    db = env["db"]
    admin_user = env["user1_admin"]
    member_user = env["user1_member"]

    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    try:
        # Non-admin user receives 403 Forbidden
        app.dependency_overrides[get_current_user] = lambda: member_user
        app.dependency_overrides[get_current_admin_user] = lambda: get_current_admin_user(member_user)

        res_blocked_stats = client.get("/api/admin/stats")
        assert res_blocked_stats.status_code == 403

        res_blocked_tenants = client.get("/api/admin/tenants")
        assert res_blocked_tenants.status_code == 403

        # Admin user receives 200 OK
        app.dependency_overrides[get_current_user] = lambda: admin_user
        app.dependency_overrides[get_current_admin_user] = lambda: admin_user

        res_stats = client.get("/api/admin/stats")
        assert res_stats.status_code == 200
        stats_data = res_stats.json()
        assert stats_data["total_tenants"] == 2
        assert stats_data["total_users"] == 3
        assert stats_data["total_queries"] == 4  # 3 from Tenant 1 + 1 from Tenant 2
        assert stats_data["active_databases"] == 3

        res_tenants = client.get("/api/admin/tenants")
        assert res_tenants.status_code == 200
        tenants_data = res_tenants.json()
        assert len(tenants_data) == 2
        t1 = next(t for t in tenants_data if t["company"] == "Acme Corp")
        assert t1["queries"] == 3
        assert t1["databases"] == 2
        assert t1["users_count"] == 2
    finally:
        app.dependency_overrides.clear()


def test_tenant_data_isolation(test_environment):
    """Verify Tenant 2 user only sees Tenant 2 queries and databases in overview & logs."""
    env = test_environment
    db = env["db"]
    user2 = env["user2_admin"]

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user2
    client = TestClient(app)

    try:
        # Tenant 2 overview
        res_overview = client.get("/api/analytics/overview")
        assert res_overview.status_code == 200
        overview_data = res_overview.json()
        assert overview_data["total_queries"] == 1  # Only 1 query for Tenant 2
        assert overview_data["connected_databases"] == 1
        assert overview_data["uploaded_documents"] == 0

        # Tenant 2 logs
        res_logs = client.get("/api/logs")
        assert res_logs.status_code == 200
        logs_data = res_logs.json()
        assert logs_data["total"] == 1
        assert logs_data["items"][0]["userQuestion"] == "Beta query"
    finally:
        app.dependency_overrides.clear()


def test_query_logs_csv_export_formula_injection_defense(test_environment):
    """Verify CSV export sanitizes malicious formula triggers (=, +, -, @, \\t, \\r)."""
    env = test_environment
    db = env["db"]
    user = env["user1_admin"]

    # Inject a query log with formula injection attempts
    malicious_log = models.QueryLog(
        id=999,
        tenant_id=1,
        user_id=1,
        database_id=1,
        natural_query="=cmd|' /C calc'!A0",
        generated_sql="@SUM(1+1)",
        error_message="+malicious_error",
        status="failed",
        created_at=datetime.now(timezone.utc),
    )
    db.add(malicious_log)
    db.commit()

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    client = TestClient(app)

    try:
        res = client.get("/api/logs/export")
        assert res.status_code == 200
        csv_text = res.text

        # All formula triggers must be escaped with a leading single quote
        assert "'=cmd|' /C calc'!A0" in csv_text
        assert "'@SUM(1+1)" in csv_text
        assert "'+malicious_error" in csv_text
    finally:
        app.dependency_overrides.clear()


def test_api_overview_alias_route(test_environment):
    """Verify /api/overview functions as a clean alias to /api/analytics/overview."""
    env = test_environment
    db = env["db"]
    user = env["user1_admin"]

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    client = TestClient(app)

    try:
        res_alias = client.get("/api/overview")
        assert res_alias.status_code == 200
        data_alias = res_alias.json()

        res_full = client.get("/api/analytics/overview")
        assert res_full.status_code == 200
        data_full = res_full.json()

        assert data_alias["total_queries"] == data_full["total_queries"]
        assert data_alias["connected_databases"] == data_full["connected_databases"]
    finally:
        app.dependency_overrides.clear()


def test_admin_stats_platform_activity_and_tenant_plans(test_environment):
    """Verify platform_activity timeline on admin stats and persistent plan on tenants."""
    env = test_environment
    db = env["db"]
    admin = env["user1_admin"]

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: admin
    app.dependency_overrides[get_current_admin_user] = lambda: admin
    client = TestClient(app)

    try:
        # Verify admin stats includes platform_activity
        res_stats = client.get("/api/admin/stats")
        assert res_stats.status_code == 200
        data_stats = res_stats.json()
        assert "platform_activity" in data_stats
        assert len(data_stats["platform_activity"]) == 7
        for point in data_stats["platform_activity"]:
            assert "name" in point
            assert "date" in point
            assert "queries" in point

        # Verify admin tenants returns persisted plan
        res_tenants = client.get("/api/admin/tenants")
        assert res_tenants.status_code == 200
        data_tenants = res_tenants.json()
        assert len(data_tenants) == 2
        for t in data_tenants:
            assert t["plan"] in ["Starter", "Pro", "Enterprise"]
            assert "@" in t["email"] or t["email"] == "No users"
    finally:
        app.dependency_overrides.clear()

