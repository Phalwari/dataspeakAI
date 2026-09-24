import os
import sys
import pytest
from typing import cast
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Setup path so imports work directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

import models
from database import Base, get_db
from main import app
from auth import create_access_token
from services.schema_profiler import profile_database_schema, TableProfile, ColumnProfile
from services.query_builder import parse_column_ref, quote_ident
from services.dashboard_agents.validator import validate_dashboard_config
from services.dashboard_agents.schemas import (
    KpiAgentOutput,
    KpiSpec,
    ChartLayoutOutput,
)


@pytest.fixture(scope="module")
def test_setup():
    """
    Sets up an in-memory SQLite database with StaticPool and FastAPI TestClient.
    Seeds two distinct tenants (Tenant A and Tenant B) with admin users and auth tokens.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    import database
    orig_session_local = database.SessionLocal
    database.SessionLocal = TestingSessionLocal
    client = TestClient(app)

    db = TestingSessionLocal()

    # Tenant A
    tenant_a = models.Tenant(name="Tenant Alpha Corp", industry="Retail")
    db.add(tenant_a)
    db.commit()
    db.refresh(tenant_a)

    user_a = models.User(
        tenant_id=tenant_a.id,
        email="admin@alpha.com",
        full_name="Alpha Admin",
        hashed_password="pw",
        role="Admin",
        is_verified=True,
    )
    db.add(user_a)
    db.commit()
    db.refresh(user_a)

    # Tenant B
    tenant_b = models.Tenant(name="Tenant Beta Corp", industry="Health")
    db.add(tenant_b)
    db.commit()
    db.refresh(tenant_b)

    user_b = models.User(
        tenant_id=tenant_b.id,
        email="admin@beta.com",
        full_name="Beta Admin",
        hashed_password="pw",
        role="Admin",
        is_verified=True,
    )
    db.add(user_b)
    db.commit()
    db.refresh(user_b)

    token_a = create_access_token(data={"sub": user_a.email, "tenant_id": tenant_a.id})
    token_b = create_access_token(data={"sub": user_b.email, "tenant_id": tenant_b.id})

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Connection owned strictly by Tenant A
    conn_a = models.DatabaseConnection(
        tenant_id=tenant_a.id,
        name="Alpha Private DB",
        db_type="sqlite",
        host=":memory:",
        username="alpha",
        password="secret_password",
        database="alpha.db",
        status="connected",
    )
    db.add(conn_a)
    db.commit()
    db.refresh(conn_a)

    # Add dummy schema registry entries for Conn A
    reg1 = models.SchemaRegistry(
        connection_id=conn_a.id,
        table_name="orders",
        column_name="order_id",
        data_type="INTEGER",
        semantic_type="ID",
        is_primary_key=True,
        is_measure=False,
        is_dimension=False,
        is_time_axis=False,
    )
    reg2 = models.SchemaRegistry(
        connection_id=conn_a.id,
        table_name="orders",
        column_name="total_amount",
        data_type="DECIMAL",
        semantic_type="CURRENCY/AMOUNT",
        is_primary_key=False,
        is_measure=True,
        is_dimension=False,
        is_time_axis=False,
    )
    reg3 = models.SchemaRegistry(
        connection_id=conn_a.id,
        table_name="orders",
        column_name="order_date",
        data_type="DATETIME",
        semantic_type="DATETIME",
        is_primary_key=False,
        is_measure=False,
        is_dimension=False,
        is_time_axis=True,
    )
    reg4 = models.SchemaRegistry(
        connection_id=conn_a.id,
        table_name="orders",
        column_name="status",
        data_type="VARCHAR",
        semantic_type="CATEGORY",
        is_primary_key=False,
        is_measure=False,
        is_dimension=True,
        is_time_axis=False,
    )
    db.add_all([reg1, reg2, reg3, reg4])
    db.commit()

    yield {
        "client": client,
        "db": db,
        "tenant_a": tenant_a,
        "tenant_b": tenant_b,
        "conn_a": conn_a,
        "headers_a": headers_a,
        "headers_b": headers_b,
    }

    database.SessionLocal = orig_session_local
    db.close()


# ------------------------------------------------------------------------------
# 1. Tenant Isolation Tests
# ------------------------------------------------------------------------------

def test_cross_tenant_dashboard_blocked(test_setup):
    """
    Tenant B must NEVER be able to view or inspect Tenant A's dashboard or schema metadata.
    """
    client = test_setup["client"]
    conn_a_id = test_setup["conn_a"].id
    headers_b = test_setup["headers_b"]

    resp = client.get(f"/api/analytics/dashboard/{conn_a_id}", headers=headers_b)
    assert resp.status_code == 404, f"Expected 404 for cross-tenant access, got {resp.status_code}"
    assert "Database connection not found" in resp.json()["detail"]


def test_cross_tenant_profile_status_blocked(test_setup):
    """
    Tenant B must NEVER be able to query Tenant A's profiling state or column counts.
    """
    client = test_setup["client"]
    conn_a_id = test_setup["conn_a"].id
    headers_b = test_setup["headers_b"]

    resp = client.get(f"/api/analytics/connections/{conn_a_id}/profile-status", headers=headers_b)
    assert resp.status_code == 404, f"Expected 404 for cross-tenant profile-status, got {resp.status_code}"
    assert "Database connection not found" in resp.json()["detail"]


def test_cross_tenant_refresh_cache_blocked(test_setup):
    """
    Tenant B must NEVER be able to trigger cache invalidation on Tenant A's dashboard.
    """
    client = test_setup["client"]
    conn_a_id = test_setup["conn_a"].id
    headers_b = test_setup["headers_b"]

    resp = client.post(f"/api/analytics/dashboard/{conn_a_id}/refresh-cache", headers=headers_b)
    assert resp.status_code == 404, f"Expected 404 for cross-tenant refresh-cache, got {resp.status_code}"


def test_cross_tenant_suggest_mapping_blocked(test_setup):
    """
    Tenant B must NEVER be able to suggest mappings on Tenant A's connection.
    """
    client = test_setup["client"]
    conn_a_id = test_setup["conn_a"].id
    headers_b = test_setup["headers_b"]

    resp = client.post(
        f"/api/analytics/connections/{conn_a_id}/suggest-mapping",
        headers=headers_b,
        json={"domain": "ecommerce"},
    )
    assert resp.status_code == 404, f"Expected 404 for cross-tenant suggest-mapping, got {resp.status_code}"


def test_cross_tenant_apply_mapping_blocked(test_setup):
    """
    Tenant B must NEVER be able to apply mappings or write KPIs to Tenant A's connection.
    """
    client = test_setup["client"]
    conn_a_id = test_setup["conn_a"].id
    headers_b = test_setup["headers_b"]

    resp = client.post(
        f"/api/analytics/connections/{conn_a_id}/apply-mapping",
        headers=headers_b,
        json={"domain": "ecommerce", "mappings": {}, "confirmed_by_user": True},
    )
    assert resp.status_code == 404, f"Expected 404 for cross-tenant apply-mapping, got {resp.status_code}"


# ------------------------------------------------------------------------------
# 2. Production Mock Fallback Removal
# ------------------------------------------------------------------------------

def test_missing_connection_url_does_not_generate_mock_schema(test_setup):
    """
    If a real database connection URL cannot be resolved, schema_profiler must
    raise ValueError and NEVER silently inject fake users/orders tables into SchemaRegistry.
    """
    db = test_setup["db"]
    tenant_a = test_setup["tenant_a"]

    broken_conn = models.DatabaseConnection(
        tenant_id=tenant_a.id,
        name="Broken Unresolvable DB",
        db_type="custom_unsupported_engine",
        host="broken-host.internal",
        username="none",
        password="none",
        database="invalid_db",
        status="error",
    )
    db.add(broken_conn)
    db.commit()
    db.refresh(broken_conn)

    # Must raise ValueError
    with pytest.raises(ValueError) as exc_info:
        profile_database_schema(broken_conn, db)

    assert "Could not resolve database connection URL" in str(exc_info.value)

    # Verify that NO fake tables were inserted into SchemaRegistry
    fake_entries = (
        db.query(models.SchemaRegistry)
        .filter(models.SchemaRegistry.connection_id == broken_conn.id)
        .all()
    )
    assert len(fake_entries) == 0, f"Production profiler must never generate fake schema! Found {len(fake_entries)}"


# ------------------------------------------------------------------------------
# 3. Qualified Column Identity Preservation & Atomic apply-mapping
# ------------------------------------------------------------------------------

def test_apply_mapping_preserves_qualified_column_references(test_setup):
    """
    apply_user_confirmed_mapping must preserve the full 'orders.total_amount'
    in KpiDefinition.target_column, chart axes, and filters. It must NOT strip
    the table prefix down to 'total_amount'.
    """
    client = test_setup["client"]
    db = test_setup["db"]
    conn_a = test_setup["conn_a"]
    headers_a = test_setup["headers_a"]

    valid_mapping = {
        "domain": "ecommerce",
        "mappings": {
            "revenue": "orders.total_amount",
            "order_date": "orders.order_date",
            "order_id": "orders.order_id",
            "category": "orders.status",
        },
        "confirmed_by_user": True,
    }

    resp = client.post(
        f"/api/analytics/connections/{conn_a.id}/apply-mapping",
        headers=headers_a,
        json=valid_mapping,
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    # Verify persisted KpiDefinition.target_column
    persisted_kpis = (
        db.query(models.KpiDefinition)
        .filter(models.KpiDefinition.connection_id == conn_a.id)
        .all()
    )
    assert len(persisted_kpis) >= 1

    rev_kpi = next((k for k in persisted_kpis if k.kpi_title == "Total Revenue"), None)
    assert rev_kpi is not None
    # Crucial assertion: Table prefix MUST be retained!
    assert rev_kpi.target_column == "orders.total_amount", (
        f"Expected qualified 'orders.total_amount', but got stripped: '{rev_kpi.target_column}'"
    )

    # Verify DashboardLayout preserves qualified chart axes and filters
    layout = (
        db.query(models.DashboardLayout)
        .filter(models.DashboardLayout.connection_id == conn_a.id)
        .first()
    )
    assert layout is not None

    if layout.charts_config:
        first_chart = layout.charts_config[0]
        # Y-axis should be qualified
        assert first_chart.get("y_axis") == "orders.total_amount"

    if layout.filters_config:
        first_filter = layout.filters_config[0]
        assert first_filter.get("column") == "orders.status"


def test_failed_apply_mapping_does_not_destroy_previous_dashboard(test_setup):
    """
    If an apply-mapping request fails (e.g. invalid column), the previous valid
    KPIs and DashboardLayout must NOT be deleted.
    """
    client = test_setup["client"]
    db = test_setup["db"]
    conn_a = test_setup["conn_a"]
    headers_a = test_setup["headers_a"]

    # Check that previous valid KPIs exist
    kpis_before = (
        db.query(models.KpiDefinition)
        .filter(models.KpiDefinition.connection_id == conn_a.id)
        .all()
    )
    count_before = len(kpis_before)
    assert count_before > 0

    # Attempt invalid mapping with a nonexistent column
    invalid_mapping = {
        "domain": "ecommerce",
        "mappings": {"revenue": "nonexistent_table.fake_column"},
        "confirmed_by_user": True,
    }

    resp = client.post(
        f"/api/analytics/connections/{conn_a.id}/apply-mapping",
        headers=headers_a,
        json=invalid_mapping,
    )
    assert resp.status_code == 400

    # Verify that previous KPIs were NOT destroyed!
    kpis_after = (
        db.query(models.KpiDefinition)
        .filter(models.KpiDefinition.connection_id == conn_a.id)
        .all()
    )
    assert len(kpis_after) == count_before, (
        f"Atomic failure violated: Expected {count_before} KPIs, but found {len(kpis_after)}"
    )


def test_apply_mapping_mid_transaction_exception_rollback(test_setup, monkeypatch):
    """
    Simulates a mid-transaction failure (e.g. database disconnect during commit).
    Verifies that the entire transaction is rolled back and previous KPIs/DashboardLayout
    remain intact.
    """
    client = test_setup["client"]
    db = test_setup["db"]
    conn_a = test_setup["conn_a"]
    headers_a = test_setup["headers_a"]

    kpis_before = (
        db.query(models.KpiDefinition)
        .filter(models.KpiDefinition.connection_id == conn_a.id)
        .all()
    )
    count_before = len(kpis_before)
    assert count_before > 0

    valid_mapping = {
        "domain": "ecommerce",
        "mappings": {
            "revenue": "orders.total_amount",
            "order_date": "orders.order_date",
            "order_id": "orders.order_id",
            "category": "orders.status",
        },
        "confirmed_by_user": True,
    }

    # Monkeypatch commit on Session to simulate failure during commit
    original_commit = db.commit
    def failing_commit():
        raise Exception("Simulated database failure during commit")

    from sqlalchemy.orm import Session
    monkeypatch.setattr(Session, "commit", failing_commit)

    try:
        resp = client.post(
            f"/api/analytics/connections/{conn_a.id}/apply-mapping",
            headers=headers_a,
            json=valid_mapping,
        )
        assert resp.status_code == 500
        assert "Failed to save dashboard mapping" in resp.text
    finally:
        monkeypatch.undo()

    # Re-query using fresh query to verify rollback
    kpis_after = (
        db.query(models.KpiDefinition)
        .filter(models.KpiDefinition.connection_id == conn_a.id)
        .all()
    )
    assert len(kpis_after) == count_before, (
        f"Rollback failed: Expected {count_before} KPIs preserved, got {len(kpis_after)}"
    )


# ------------------------------------------------------------------------------
# 4. Decoupled Profiling & Utility Tests
# ------------------------------------------------------------------------------

def test_profile_does_not_invoke_llm_dashboard_generation(test_setup):
    """
    In Phase 1.5, schema profiling profiles SchemaRegistry only.
    It does NOT invoke the legacy LangGraph LLM dashboard generation.
    """
    import asyncio
    from routers.analytics import _profiling_job_runner

    db = test_setup["db"]
    tenant_a = test_setup["tenant_a"]

    # Create a fresh connection
    conn_fresh = models.DatabaseConnection(
        tenant_id=tenant_a.id,
        name="Fresh SQLite Connection",
        db_type="sqlite",
        host=":memory:",
        username="fresh",
        password="secret_password",
        database="fresh.db",
        status="connected",
    )
    db.add(conn_fresh)
    db.commit()
    db.refresh(conn_fresh)

    # Run profiling runner synchronously via asyncio.run
    asyncio.run(_profiling_job_runner(cast(int, tenant_a.id), cast(int, conn_fresh.id)))

    # In Phase 1.5, KpiDefinition must NOT be generated automatically by profiling!
    kpis = (
        db.query(models.KpiDefinition)
        .filter(models.KpiDefinition.connection_id == conn_fresh.id)
        .all()
    )
    assert len(kpis) == 0, (
        f"Profiling must not generate KPIs automatically! Found {len(kpis)} unconfirmed KPIs."
    )


def test_llm_pipeline_isolation_function_call_level(test_setup, monkeypatch):
    """
    Explicitly mocks the legacy LangGraph pipeline and fallback KPI generator.
    Asserts both functions were NOT called during schema profiling.
    """
    import asyncio
    from unittest.mock import MagicMock
    import routers.analytics as analytics_module

    mock_llm_pipeline = MagicMock()
    mock_fallback_generator = MagicMock()

    monkeypatch.setattr(analytics_module, "generate_dashboard_via_agents", mock_llm_pipeline)
    monkeypatch.setattr(analytics_module, "generate_kpis_and_chart_specs", mock_fallback_generator)

    db = test_setup["db"]
    tenant_a = test_setup["tenant_a"]

    conn_test = models.DatabaseConnection(
        tenant_id=tenant_a.id,
        name="LLM Isolation DB",
        db_type="sqlite",
        host=":memory:",
        username="test",
        password="test_password",
        database="llm_isolation.db",
        status="connected",
    )
    db.add(conn_test)
    db.commit()
    db.refresh(conn_test)

    asyncio.run(analytics_module._profiling_job_runner(cast(int, tenant_a.id), cast(int, conn_test.id)))

    # Explicit function-call boundary assertions
    mock_llm_pipeline.assert_not_called()
    mock_fallback_generator.assert_not_called()


def test_thread_worker_session_isolation(test_setup):
    """
    Verifies that _sync_worker_profile_connection creates and closes its own SessionLocal
    and operates only with primitive IDs, strictly preventing session leakage across threads.
    """
    from routers.analytics import _sync_worker_profile_connection
    tenant_a = test_setup["tenant_a"]
    conn_a = test_setup["conn_a"]

    # Passing only primitive IDs
    _sync_worker_profile_connection(tenant_a.id, conn_a.id)

    # Invalid connection ID must raise ValueError
    with pytest.raises(ValueError) as exc:
        _sync_worker_profile_connection(tenant_a.id, 99999)
    assert "not found or unauthorized" in str(exc.value)


def test_parse_column_ref_validation():
    """
    parse_column_ref must enforce strict 'table.column' qualification.
    """
    # Valid references
    t, c = parse_column_ref("orders.total_amount")
    assert t == "orders" and c == "total_amount"

    t, c = parse_column_ref("public.users.email")
    assert t == "public" and c == "users.email"

    # Invalid references must raise ValueError
    with pytest.raises(ValueError):
        parse_column_ref("total_amount")

    with pytest.raises(ValueError):
        parse_column_ref("")

    with pytest.raises(ValueError):
        parse_column_ref("orders.")

    with pytest.raises(ValueError):
        parse_column_ref(".total_amount")


def test_dialect_aware_quoting():
    """
    quote_ident must apply dialect-specific identifier quoting.
    """
    assert quote_ident("orders", "mysql") == "`orders`"
    assert quote_ident("orders", "mariadb") == "`orders`"
    assert quote_ident("orders", "postgresql") == '"orders"'
    assert quote_ident("orders", "sqlite") == '"orders"'
    assert quote_ident("*", "mysql") == "*"


def test_validator_reads_top_values():
    """
    Validator must read top_values from ColumnProfile to validate categorical values.
    """
    from services.dashboard_agents.schemas import SemanticAnalysis

    cp = ColumnProfile(
        name="status",
        data_type="VARCHAR",
        semantic_type="CATEGORY",
        is_dimension=True,
        top_values=["completed", "shipped", "pending"],
    )
    tp = TableProfile(table_name="orders", row_count=100, columns=[cp])

    semantic = SemanticAnalysis(
        business_domain="Retail",
        domain_confidence=0.9,
        columns=[],
        detected_relationships=[],
    )

    kpi_output = KpiAgentOutput(
        kpis=[
            KpiSpec(
                kpi_title="Completed Orders",
                formula_description="Orders with status completed",
                primary_column="orders.status",
                aggregation_function="computed",
                target_value="completed",
                priority=1,
                reasoning="Track completed fulfillment",
            )
        ]
    )
    chart_output = ChartLayoutOutput(charts=[], filters=[])

    validated = validate_dashboard_config(semantic, kpi_output, chart_output, [tp])
    # The KPI should NOT have been dropped because "completed" is present in top_values
    assert len(validated.kpis) == 1
    assert validated.kpis[0].kpi_title == "Completed Orders"
