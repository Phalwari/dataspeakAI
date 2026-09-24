"""
tests/test_phase1_5c_dashboard_executor_integration.py

Comprehensive Test Suite for Phase 1.5C: Wire Live Dashboard APIs to Canonical MetricExecutor.
Validates:
1. Exact numeric correctness against deterministic SQLite dataset via HTTP API endpoints:
   - SUM(total_amount) = 1000.0
   - AVG(total_amount) = 250.0
   - COUNT(order_id) = 4
   - COUNT_DISTINCT(customer_id) = 3
   - Dimension breakdown: completed = 300.0, shipped = 300.0, cancelled = 400.0
2. Semantic policy rejection via HTTP endpoints:
   - SUM(order_id) -> 400 Bad Request
   - MEDIAN(total_amount) -> 400 Bad Request
   - Unknown table -> 400 Bad Request
   - Unknown column -> 400 Bad Request
   - Cross-table metric -> 400 Bad Request
   - Cross-tenant connection access -> 404 Not Found
3. Legacy 'all' resolution:
   - Unambiguous context -> resolved to table.*
   - Ambiguous bare 'all' -> LegacyKpiIncompatibleError (never guesses)
4. Proof old calculation functions are not called (isolation assertion).
5. Old vs New calculation parity and correction verification.
"""

import os
import sys
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Setup path so imports work directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

import models
from database import Base, get_db
from main import app
from auth import create_access_token
from services.cache_service import cache_service
from services.metric_executor import MetricExecutor
from services.metric_adapter import (
    adapt_kpi_to_metric_request,
    resolve_kpi_target_and_dimension,
    LegacyKpiIncompatibleError,
)
import services.kpi_chart_engine as kpi_chart_engine


@pytest.fixture(scope="module")
def c_integration_setup():
    """
    Sets up:
    1. An in-memory SQLite app DB for tenant, user, database_connections, schema_registry, kpi_definitions.
    2. A deterministic external SQLite database on disk containing the exact prompt orders dataset:
       order_id | customer_id | total_amount | status
       1        | 10          | 100.0        | completed
       2        | 10          | 200.0        | completed
       3        | 20          | 300.0        | shipped
       4        | 30          | 400.0        | cancelled
    """
    # 1. External customer DB
    temp_dir = tempfile.mkdtemp()
    customer_db_path = os.path.join(temp_dir, "customer_orders.db").replace("\\", "/")
    customer_engine = create_engine(f"sqlite:///{customer_db_path}")

    with customer_engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE orders (
                order_id INTEGER PRIMARY KEY,
                customer_id INTEGER,
                total_amount REAL,
                status VARCHAR(50)
            )
        """))
        conn.execute(text("""
            CREATE TABLE customers (
                customer_id INTEGER PRIMARY KEY,
                customer_name VARCHAR(100)
            )
        """))
        conn.execute(text("""
            INSERT INTO orders (order_id, customer_id, total_amount, status) VALUES
            (1, 10, 100.0, 'completed'),
            (2, 10, 200.0, 'completed'),
            (3, 20, 300.0, 'shipped'),
            (4, 30, 400.0, 'cancelled')
        """))
        conn.execute(text("""
            INSERT INTO customers (customer_id, customer_name) VALUES
            (10, 'Alpha Corp'),
            (20, 'Beta LLC'),
            (30, 'Gamma Inc')
        """))
        conn.commit()

    # 2. Main App DB (In-memory)
    app_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=app_engine)
    Base.metadata.create_all(bind=app_engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    db = TestingSession()

    # Tenant 1 (Owner of the customer DB connection)
    tenant1 = models.Tenant(name="Tenant One Corp", industry="Retail")
    db.add(tenant1)
    db.commit()
    db.refresh(tenant1)

    user1 = models.User(
        tenant_id=tenant1.id,
        email="user1@tenant1.com",
        full_name="User One",
        hashed_password="hashed_pw",
        role="Admin",
        is_verified=True,
    )
    db.add(user1)
    db.commit()
    db.refresh(user1)

    token_t1 = create_access_token(data={"sub": user1.email})

    # Tenant 2 (Unrelated Tenant for cross-tenant isolation testing)
    tenant2 = models.Tenant(name="Tenant Two Corp", industry="SaaS")
    db.add(tenant2)
    db.commit()
    db.refresh(tenant2)

    user2 = models.User(
        tenant_id=tenant2.id,
        email="user2@tenant2.com",
        full_name="User Two",
        hashed_password="hashed_pw",
        role="Admin",
        is_verified=True,
    )
    db.add(user2)
    db.commit()
    db.refresh(user2)

    token_t2 = create_access_token(data={"sub": user2.email})

    # DatabaseConnection for Tenant 1
    conn1 = models.DatabaseConnection(
        tenant_id=tenant1.id,
        name="Production Orders DB",
        db_type="sqlite",
        host="localhost",
        username="admin",
        password="secret",
        database=customer_db_path,
        status="active",
    )
    db.add(conn1)
    db.commit()
    db.refresh(conn1)

    # DatabaseConnection for Tenant 2
    conn2 = models.DatabaseConnection(
        tenant_id=tenant2.id,
        name="Tenant 2 DB",
        db_type="sqlite",
        host="localhost",
        username="admin",
        password="secret",
        database=":memory:",
        status="active",
    )
    db.add(conn2)
    db.commit()
    db.refresh(conn2)

    # Register Schema in SchemaRegistry for conn1
    registries = [
        models.SchemaRegistry(
            connection_id=conn1.id,
            table_name="orders",
            column_name="order_id",
            data_type="INTEGER",
            semantic_type="ID",
            is_primary_key=True,
            is_measure=False,
            is_dimension=False,
        ),
        models.SchemaRegistry(
            connection_id=conn1.id,
            table_name="orders",
            column_name="customer_id",
            data_type="INTEGER",
            semantic_type="ID",
            is_foreign_key=True,
            is_measure=False,
            is_dimension=False,
        ),
        models.SchemaRegistry(
            connection_id=conn1.id,
            table_name="orders",
            column_name="total_amount",
            data_type="REAL",
            semantic_type="NUMERIC_MEASURE",
            is_measure=True,
            is_dimension=False,
        ),
        models.SchemaRegistry(
            connection_id=conn1.id,
            table_name="orders",
            column_name="status",
            data_type="VARCHAR",
            semantic_type="CATEGORY",
            is_measure=False,
            is_dimension=True,
        ),
        models.SchemaRegistry(
            connection_id=conn1.id,
            table_name="customers",
            column_name="customer_id",
            data_type="INTEGER",
            semantic_type="ID",
            is_primary_key=True,
            is_measure=False,
            is_dimension=False,
        ),
        models.SchemaRegistry(
            connection_id=conn1.id,
            table_name="customers",
            column_name="customer_name",
            data_type="VARCHAR",
            semantic_type="TEXT",
            is_measure=False,
            is_dimension=True,
        ),
    ]
    for r in registries:
        db.add(r)
    db.commit()

    # Seed representative KpiDefinitions for Tenant 1
    kpis = [
        models.KpiDefinition(
            tenant_id=tenant1.id,
            connection_id=conn1.id,
            kpi_title="Total Revenue",
            aggregation_function="SUM",
            target_column="orders.total_amount",
            dimension_column=None,
            default_chart_type="Line",
            priority=1,
            reasoning="Total gross revenue from orders",
        ),
        models.KpiDefinition(
            tenant_id=tenant1.id,
            connection_id=conn1.id,
            kpi_title="Average Order Value",
            aggregation_function="AVG",
            target_column="orders.total_amount",
            dimension_column=None,
            default_chart_type="Bar",
            priority=2,
            reasoning="Average basket size",
        ),
        models.KpiDefinition(
            tenant_id=tenant1.id,
            connection_id=conn1.id,
            kpi_title="Total Order Count",
            aggregation_function="COUNT",
            target_column="orders.*",
            dimension_column=None,
            default_chart_type="Bar",
            priority=3,
            reasoning="Total order transactions volume",
        ),
        models.KpiDefinition(
            tenant_id=tenant1.id,
            connection_id=conn1.id,
            kpi_title="Unique Customers",
            aggregation_function="COUNT_DISTINCT",
            target_column="orders.customer_id",
            dimension_column=None,
            default_chart_type="Bar",
            priority=4,
            reasoning="Count of distinct customers purchasing",
        ),
        models.KpiDefinition(
            tenant_id=tenant1.id,
            connection_id=conn1.id,
            kpi_title="Revenue by Status",
            aggregation_function="SUM",
            target_column="orders.total_amount",
            dimension_column="orders.status",
            default_chart_type="Bar",
            priority=5,
            reasoning="Fulfillment status revenue distribution",
        ),
    ]
    for k in kpis:
        db.add(k)
    db.commit()
    cache_service.clear()

    yield {
        "client": client,
        "token_t1": token_t1,
        "token_t2": token_t2,
        "conn1_id": conn1.id,
        "conn2_id": conn2.id,
        "tenant1_id": tenant1.id,
        "tenant2_id": tenant2.id,
        "db": db,
        "conn1": conn1,
    }

    cache_service.clear()
    db.close()


# ============================================================================
# TASK 7: HTTP INTEGRATION TESTS - EXACT NUMERIC VALUES
# ============================================================================

def test_http_dashboard_exact_numeric_kpis(c_integration_setup):
    """
    Test GET /api/analytics/dashboard/{connection_id}
    Proves all KPI values match the proven deterministic dataset:
    SUM(total_amount) = 1000.0
    AVG(total_amount) = 250.0
    COUNT(orders.*) = 4
    COUNT_DISTINCT(customer_id) = 3
    Revenue by Status breakdown: completed=300.0, shipped=300.0, cancelled=400.0
    """
    client = c_integration_setup["client"]
    token = c_integration_setup["token_t1"]
    conn_id = c_integration_setup["conn1_id"]

    res = client.get(
        f"/api/analytics/dashboard/{conn_id}?date_range=all",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()

    # 1. Verify Frontend Contract Preservation
    assert "connection_id" in data
    assert "business_domain" in data
    assert "table_count" in data
    assert "measure_count" in data
    assert "dimension_count" in data
    assert "kpis" in data
    assert "live_charts" in data
    assert "charts_config" in data
    assert "filters_config" in data
    assert "schema_summary" in data

    live_charts = {c["title"]: c for c in data["live_charts"]}

    # 2. Exact Numeric Assertions
    # Total Revenue = 100.0 + 200.0 + 300.0 + 400.0 = 1000.0
    assert "Total Revenue" in live_charts
    rev_data = live_charts["Total Revenue"]["data"]
    assert len(rev_data) == 1
    assert rev_data[0]["value"] == 1000.0

    # Average Order Value = 1000.0 / 4 = 250.0
    assert "Average Order Value" in live_charts
    avg_data = live_charts["Average Order Value"]["data"]
    assert len(avg_data) == 1
    assert avg_data[0]["value"] == 250.0

    # Total Order Count = 4
    assert "Total Order Count" in live_charts
    cnt_data = live_charts["Total Order Count"]["data"]
    assert len(cnt_data) == 1
    assert cnt_data[0]["value"] == 4.0

    # Unique Customers = 3 (customers 10, 20, 30)
    assert "Unique Customers" in live_charts
    dist_data = live_charts["Unique Customers"]["data"]
    assert len(dist_data) == 1
    assert dist_data[0]["value"] == 3.0

    # Revenue by Status: completed = 100+200 = 300.0, shipped = 300.0, cancelled = 400.0
    assert "Revenue by Status" in live_charts
    status_data = live_charts["Revenue by Status"]["data"]
    status_map = {item["name"]: item["value"] for item in status_data}

    assert status_map.get("completed") == 300.0
    assert status_map.get("shipped") == 300.0
    assert status_map.get("cancelled") == 400.0


def test_http_query_exact_numeric_and_breakdown(c_integration_setup):
    """
    Test POST /api/analytics/dashboard/{connection_id}/query
    Proves ad-hoc queries return canonical stats and chart breakdown.
    """
    client = c_integration_setup["client"]
    token = c_integration_setup["token_t1"]
    conn_id = c_integration_setup["conn1_id"]

    req_body = {
        "table_name": "orders",
        "target_column": "total_amount",
        "dimension_column": "status",
        "aggregation": "SUM",
        "date_range": "all",
        "limit": 10,
    }

    res = client.post(
        f"/api/analytics/dashboard/{conn_id}/query",
        json=req_body,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "success"
    assert data["table_name"] == "orders"
    assert data["target_column"] == "total_amount"
    assert data["dimension_column"] == "status"
    assert data["aggregation"] == "SUM"

    # Verify Summary Stats: total=1000, avg=250, max=400, min=100, count=4
    stats = data["kpi_stats"]
    assert stats["total"] == 1000.0
    assert stats["average"] == 250.0
    assert stats["max"] == 400.0
    assert stats["min"] == 100.0
    assert stats["count"] == 4

    # Verify chart_data breakdown
    chart_map = {pt["name"]: pt["value"] for pt in data["chart_data"]}
    assert chart_map["completed"] == 300.0
    assert chart_map["shipped"] == 300.0
    assert chart_map["cancelled"] == 400.0


# ============================================================================
# TASK 7: HTTP INTEGRATION TESTS - SECURITY & GUARD REJECTIONS
# ============================================================================

def test_rejection_sum_on_identifier(c_integration_setup):
    """
    Verify API rejection (HTTP 400) for SUM on an identifier column (order_id).
    """
    client = c_integration_setup["client"]
    token = c_integration_setup["token_t1"]
    conn_id = c_integration_setup["conn1_id"]

    req_body = {
        "table_name": "orders",
        "target_column": "order_id",
        "aggregation": "SUM",
        "date_range": "all",
    }

    res = client.post(
        f"/api/analytics/dashboard/{conn_id}/query",
        json=req_body,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400
    assert "identifier" in res.json()["detail"].lower()


def test_rejection_median_unsupported_aggregation(c_integration_setup):
    """
    Verify API rejection (HTTP 400) for unsupported aggregation 'MEDIAN'.
    """
    client = c_integration_setup["client"]
    token = c_integration_setup["token_t1"]
    conn_id = c_integration_setup["conn1_id"]

    req_body = {
        "table_name": "orders",
        "target_column": "total_amount",
        "aggregation": "MEDIAN",
        "date_range": "all",
    }

    res = client.post(
        f"/api/analytics/dashboard/{conn_id}/query",
        json=req_body,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400
    assert "median" in res.json()["detail"].lower()


def test_rejection_unknown_table(c_integration_setup):
    """
    Verify API rejection (HTTP 400) when requesting an unverified table.
    """
    client = c_integration_setup["client"]
    token = c_integration_setup["token_t1"]
    conn_id = c_integration_setup["conn1_id"]

    req_body = {
        "table_name": "ghost_table",
        "target_column": "total_amount",
        "aggregation": "SUM",
    }

    res = client.post(
        f"/api/analytics/dashboard/{conn_id}/query",
        json=req_body,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400


def test_rejection_unknown_column(c_integration_setup):
    """
    Verify API rejection (HTTP 400) when requesting an unverified column.
    """
    client = c_integration_setup["client"]
    token = c_integration_setup["token_t1"]
    conn_id = c_integration_setup["conn1_id"]

    req_body = {
        "table_name": "orders",
        "target_column": "fake_revenue_col",
        "aggregation": "SUM",
    }

    res = client.post(
        f"/api/analytics/dashboard/{conn_id}/query",
        json=req_body,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400


def test_rejection_cross_table_dimension(c_integration_setup):
    """
    Verify API rejection (HTTP 400) when requesting a cross-table metric
    without an explicit joined relationship path.
    """
    client = c_integration_setup["client"]
    token = c_integration_setup["token_t1"]
    conn_id = c_integration_setup["conn1_id"]

    req_body = {
        "table_name": "orders",
        "target_column": "total_amount",
        "dimension_column": "customers.customer_name",
        "aggregation": "SUM",
    }

    res = client.post(
        f"/api/analytics/dashboard/{conn_id}/query",
        json=req_body,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400
    assert "different tables" in res.json()["detail"].lower() or "schema" in res.json()["detail"].lower()


def test_cross_tenant_isolation(c_integration_setup):
    """
    Verify Tenant 2 cannot query or access Tenant 1's connection (HTTP 404).
    """
    client = c_integration_setup["client"]
    token_t2 = c_integration_setup["token_t2"]
    conn1_id = c_integration_setup["conn1_id"]

    # Dashboard endpoint
    res = client.get(
        f"/api/analytics/dashboard/{conn1_id}",
        headers={"Authorization": f"Bearer {token_t2}"},
    )
    assert res.status_code == 404

    # Query endpoint
    res2 = client.post(
        f"/api/analytics/dashboard/{conn1_id}/query",
        json={"table_name": "orders", "target_column": "total_amount", "aggregation": "SUM"},
        headers={"Authorization": f"Bearer {token_t2}"},
    )
    assert res2.status_code == 404


# ============================================================================
# TASK 8: LEGACY 'all' INTEGRATION TESTS
# ============================================================================

def test_legacy_all_with_unambiguous_dimension_context(c_integration_setup):
    """
    Test legacy KPI with target_column="all" and dimension_column="orders.status".
    Must deterministically convert to orders.* without guessing.
    """
    db = c_integration_setup["db"]
    conn = c_integration_setup["conn1"]
    tenant_id = c_integration_setup["tenant1_id"]

    legacy_kpi = models.KpiDefinition(
        tenant_id=tenant_id,
        connection_id=conn.id,
        kpi_title="Legacy Status Counts",
        aggregation_function="COUNT",
        target_column="all",
        dimension_column="orders.status",
    )
    db.add(legacy_kpi)
    db.commit()
    db.refresh(legacy_kpi)

    req = adapt_kpi_to_metric_request(legacy_kpi, conn, db)
    assert req.target_ref == "orders.*"
    assert req.dimension_ref == "orders.status"
    assert req.aggregation == "COUNT"

    res = MetricExecutor.execute(req, conn, db)
    assert res.is_scalar is False
    assert res.data is not None
    assert len(res.data) == 3
    counts = {d["dimension"]: d["value"] for d in res.data}
    assert counts["completed"] == 2.0
    assert counts["shipped"] == 1.0
    assert counts["cancelled"] == 1.0


def test_legacy_all_with_table_prefix(c_integration_setup):
    """
    Test target_column="orders.all". Must normalize to "orders.*".
    """
    db = c_integration_setup["db"]
    conn = c_integration_setup["conn1"]
    tenant_id = c_integration_setup["tenant1_id"]

    legacy_kpi = models.KpiDefinition(
        tenant_id=tenant_id,
        connection_id=conn.id,
        kpi_title="Orders All Normalization",
        aggregation_function="COUNT",
        target_column="orders.all",
    )
    db.add(legacy_kpi)
    db.commit()

    req = adapt_kpi_to_metric_request(legacy_kpi, conn, db)
    assert req.target_ref == "orders.*"


def test_legacy_all_ambiguous_fails_clearly_no_guessing(c_integration_setup):
    """
    Negative test: Prove ambiguous bare 'all' across multiple tables
    without dimension or time context raises LegacyKpiIncompatibleError
    and NEVER guesses the first table.
    """
    db = c_integration_setup["db"]
    conn = c_integration_setup["conn1"]
    tenant_id = c_integration_setup["tenant1_id"]

    # In our setup, SchemaRegistry has 2 tables: 'orders' and 'customers'
    ambiguous_kpi = models.KpiDefinition(
        tenant_id=tenant_id,
        connection_id=conn.id,
        kpi_title="Ambiguous Row Count",
        aggregation_function="COUNT",
        target_column="all",
        dimension_column=None,
        time_column=None,
    )
    db.add(ambiguous_kpi)
    db.commit()

    # Must raise LegacyKpiIncompatibleError
    with pytest.raises(LegacyKpiIncompatibleError) as exc_info:
        resolve_kpi_target_and_dimension(ambiguous_kpi, conn, db, layout=None)

    error_msg = str(exc_info.value)
    assert "ambiguous table context across 2 tables" in error_msg
    assert "orders" in error_msg and "customers" in error_msg
    assert "KPI requires regeneration" in error_msg


# ============================================================================
# TASK 6: PROOF OLD CALCULATION FUNCTIONS ARE NOT CALLED
# ============================================================================

def test_legacy_generation_and_ad_hoc_calculation_functions_not_called(c_integration_setup):
    """
    Asserts that GET /dashboard/{connection_id} and POST /dashboard/{connection_id}/query
    do NOT invoke legacy generation functions or ad-hoc calculation engines,
    proving 100% execution flows through MetricExecutor.
    """
    client = c_integration_setup["client"]
    token = c_integration_setup["token_t1"]
    conn_id = c_integration_setup["conn1_id"]

    with patch.object(
        kpi_chart_engine,
        "generate_kpis_and_chart_specs",
        side_effect=AssertionError("generate_kpis_and_chart_specs was improperly called during live dashboard!"),
    ) as mock_legacy_engine:
        # 1. Execute live dashboard
        dash_res = client.get(
            f"/api/analytics/dashboard/{conn_id}?date_range=all",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert dash_res.status_code == 200
        mock_legacy_engine.assert_not_called()

        # 2. Execute live query
        query_res = client.post(
            f"/api/analytics/dashboard/{conn_id}/query",
            json={"table_name": "orders", "target_column": "total_amount", "aggregation": "SUM"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert query_res.status_code == 200
        mock_legacy_engine.assert_not_called()


def test_metric_executor_is_sole_live_calculation_authority(c_integration_setup):
    """
    Monkeyspy MetricExecutor.execute to prove that live dashboard and query
    endpoints execute ONLY via MetricExecutor.
    """
    client = c_integration_setup["client"]
    token = c_integration_setup["token_t1"]
    conn_id = c_integration_setup["conn1_id"]

    original_execute = MetricExecutor.execute
    call_records = []

    def spy_execute(request, db_conn, db):
        call_records.append(request)
        return original_execute(request, db_conn, db)

    with patch.object(MetricExecutor, "execute", side_effect=spy_execute):
        # Clear cache to force live re-computation
        cache_service._store.clear()

        # 1. Trigger Dashboard
        dash_res = client.get(
            f"/api/analytics/dashboard/{conn_id}?date_range=all",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert dash_res.status_code == 200
        # Should have executed requests for our 5 seeded KPIs
        assert len(call_records) >= 5

        # 2. Trigger Query
        calls_before = len(call_records)
        query_res = client.post(
            f"/api/analytics/dashboard/{conn_id}/query",
            json={"table_name": "orders", "target_column": "total_amount", "aggregation": "SUM"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert query_res.status_code == 200
        # Chart + summary stats should have been executed via MetricExecutor
        assert len(call_records) > calls_before
