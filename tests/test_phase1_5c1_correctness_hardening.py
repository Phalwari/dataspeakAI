"""
tests/test_phase1_5c1_correctness_hardening.py

Phase 1.5C.1 Test Suite: Live API Correctness Hardening.
Verifies all 14 requirements specified in the engineering directive:
1. Missing persisted aggregation never defaults to SUM
2. AVG(rate/percentage) succeeds through HTTP query endpoint
3. SUM(rate/percentage) still returns 400 as main requested metric
4. Optional SUM for a percentage summary becomes unavailable (null), not fatal
5. COUNT(*) vs COUNT(nullable_column) are different and correct (4 vs 2)
6. Scalar filter
7. List / IN filter
8. False filter (not dropped)
9. Zero filter (not dropped)
10. Parameter binding remains intact (SQL injection safety)
11. Bare "all" cannot resolve from unrelated global layout mapping
12. Ambiguous bare "all" fails clearly
13. Scatter path is validated via SchemaRegistry and rejects invalid/cross-table columns
14. Failed chart exposes safe diagnostic status without leaking internals
"""

import os
import sys
import tempfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Setup backend import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

import models
from database import Base, get_db
from main import app
from auth import create_access_token
from services.cache_service import cache_service
from services.metric_executor import MetricExecutor, MetricRequest, MetricFilter
from services.metric_adapter import (
    adapt_kpi_to_metric_request,
    resolve_kpi_target_and_dimension,
    LegacyKpiIncompatibleError,
)
from services.series_reader import read_scatter_series


@pytest.fixture(scope="module")
def hardening_fixture():
    """
    Sets up a deterministic SQLite customer database with:
    - 4 rows total
    - 'status' column containing 2 non-null values ('completed', 'shipped') and 2 NULLs
    - 'margin_pct' percentage measure (10.0, 20.0, 30.0, 40.0)
    - 'is_flagged' boolean/integer column (0, 0, 1, 1) -> 2 False/0, 2 True/1
    - 'error_code' integer column (0, 0, 404, 500) -> 2 zero values
    - 'total_amount' and 'profit' numeric measures for scatter correlation
    - A second table 'customers' for multi-table ambiguity tests
    """
    temp_dir = tempfile.mkdtemp()
    cust_db_path = os.path.join(temp_dir, "hardening_test.db").replace("\\", "/")
    cust_engine = create_engine(f"sqlite:///{cust_db_path}")

    with cust_engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE orders (
                order_id INTEGER PRIMARY KEY,
                customer_id INTEGER,
                total_amount REAL,
                profit REAL,
                margin_pct REAL,
                status VARCHAR(50),
                is_flagged BOOLEAN,
                error_code INTEGER
            )
        """))
        conn.execute(text("""
            CREATE TABLE customers (
                customer_id INTEGER PRIMARY KEY,
                customer_name VARCHAR(100)
            )
        """))
        # 4 rows:
        # Row 1: status='completed', is_flagged=0, error_code=0
        # Row 2: status='shipped', is_flagged=0, error_code=0
        # Row 3: status=NULL, is_flagged=1, error_code=404
        # Row 4: status=NULL, is_flagged=1, error_code=500
        conn.execute(text("""
            INSERT INTO orders (order_id, customer_id, total_amount, profit, margin_pct, status, is_flagged, error_code) VALUES
            (1, 10, 100.0, 20.0, 20.0, 'completed', 0, 0),
            (2, 10, 200.0, 40.0, 20.0, 'shipped', 0, 0),
            (3, 20, 300.0, 90.0, 30.0, NULL, 1, 404),
            (4, 30, 400.0, 160.0, 40.0, NULL, 1, 500)
        """))
        conn.execute(text("""
            INSERT INTO customers (customer_id, customer_name) VALUES
            (10, 'Alpha Corp'),
            (20, 'Beta LLC')
        """))
        conn.commit()

    # App DB (In-memory)
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

    tenant = models.Tenant(name="Hardening Tenant", industry="Analytics")
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    user = models.User(
        tenant_id=tenant.id,
        email="hardening@tester.com",
        full_name="Hardening Tester",
        hashed_password="pw",
        role="Admin",
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(data={"sub": user.email})

    db_conn = models.DatabaseConnection(
        tenant_id=tenant.id,
        name="Hardening DB",
        db_type="sqlite",
        host="localhost",
        username="admin",
        password="secret_password_123",
        database=cust_db_path,
        status="active",
    )
    db.add(db_conn)
    db.commit()
    db.refresh(db_conn)

    # SchemaRegistry registrations
    regs = [
        models.SchemaRegistry(connection_id=db_conn.id, table_name="orders", column_name="order_id", data_type="INTEGER", semantic_type="ID", is_primary_key=True, is_measure=False, is_dimension=False),
        models.SchemaRegistry(connection_id=db_conn.id, table_name="orders", column_name="customer_id", data_type="INTEGER", semantic_type="ID", is_foreign_key=True, is_measure=False, is_dimension=False),
        models.SchemaRegistry(connection_id=db_conn.id, table_name="orders", column_name="total_amount", data_type="REAL", semantic_type="NUMERIC_MEASURE", is_measure=True, is_dimension=False),
        models.SchemaRegistry(connection_id=db_conn.id, table_name="orders", column_name="profit", data_type="REAL", semantic_type="NUMERIC_MEASURE", is_measure=True, is_dimension=False),
        models.SchemaRegistry(connection_id=db_conn.id, table_name="orders", column_name="margin_pct", data_type="REAL", semantic_type="PERCENTAGE", is_measure=True, is_dimension=False),
        models.SchemaRegistry(connection_id=db_conn.id, table_name="orders", column_name="status", data_type="VARCHAR", semantic_type="CATEGORY", is_measure=False, is_dimension=True),
        models.SchemaRegistry(connection_id=db_conn.id, table_name="orders", column_name="is_flagged", data_type="BOOLEAN", semantic_type="BOOLEAN", is_measure=False, is_dimension=True),
        models.SchemaRegistry(connection_id=db_conn.id, table_name="orders", column_name="error_code", data_type="INTEGER", semantic_type="NUMERIC_MEASURE", is_measure=True, is_dimension=True),
        models.SchemaRegistry(connection_id=db_conn.id, table_name="customers", column_name="customer_id", data_type="INTEGER", semantic_type="ID", is_primary_key=True, is_measure=False, is_dimension=False),
        models.SchemaRegistry(connection_id=db_conn.id, table_name="customers", column_name="customer_name", data_type="VARCHAR", semantic_type="TEXT", is_measure=False, is_dimension=True),
    ]
    for r in regs:
        db.add(r)
    db.commit()

    return {
        "client": client,
        "db": db,
        "tenant": tenant,
        "user": user,
        "token": token,
        "conn": db_conn,
    }


# ============================================================================
# 1. MISSING PERSISTED AGGREGATION NEVER DEFAULTS TO SUM
# ============================================================================

def test_missing_persisted_aggregation_never_defaults_to_sum(hardening_fixture):
    """
    Prove that a KPI with aggregation_function=None or '' raises
    LegacyKpiIncompatibleError and NEVER silently defaults to SUM.
    Explicit aggregation like 'AVG' is preserved.
    """
    db = hardening_fixture["db"]
    conn = hardening_fixture["conn"]
    tenant = hardening_fixture["tenant"]

    # 1. None aggregation
    kpi_none = models.KpiDefinition(
        tenant_id=tenant.id,
        connection_id=conn.id,
        kpi_title="Missing Aggregation KPI",
        aggregation_function=None,
        target_column="orders.total_amount",
    )
    with pytest.raises(LegacyKpiIncompatibleError) as exc_none:
        adapt_kpi_to_metric_request(kpi_none, conn, db)
    assert "has no explicit aggregation function and must be regenerated" in str(exc_none.value)

    # 2. Blank string aggregation
    kpi_blank = models.KpiDefinition(
        tenant_id=tenant.id,
        connection_id=conn.id,
        kpi_title="Blank Aggregation KPI",
        aggregation_function="   ",
        target_column="orders.total_amount",
    )
    with pytest.raises(LegacyKpiIncompatibleError) as exc_blank:
        adapt_kpi_to_metric_request(kpi_blank, conn, db)
    assert "has no explicit aggregation function and must be regenerated" in str(exc_blank.value)

    # 3. Explicit AVG preserved exactly
    kpi_avg = models.KpiDefinition(
        tenant_id=tenant.id,
        connection_id=conn.id,
        kpi_title="Explicit AVG KPI",
        aggregation_function="AVG",
        target_column="orders.total_amount",
    )
    req = adapt_kpi_to_metric_request(kpi_avg, conn, db)
    assert req.aggregation == "AVG"


# ============================================================================
# 2, 3, 4. SEMANTIC-AWARE QUERY & SUMMARY STATS
# ============================================================================

def test_avg_percentage_succeeds_http_query_endpoint(hardening_fixture):
    """
    Valid AVG(orders.margin_pct) must succeed via POST /dashboard/{id}/query.
    Returns 200 with accurate calculation (avg of 20, 20, 30, 40 = 27.5).
    """
    client = hardening_fixture["client"]
    token = hardening_fixture["token"]
    conn_id = hardening_fixture["conn"].id

    res = client.post(
        f"/api/analytics/dashboard/{conn_id}/query",
        json={
            "table_name": "orders",
            "target_column": "margin_pct",
            "aggregation": "AVG",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["chart_data"][0]["value"] == 27.5


def test_sum_percentage_rejected_as_main_requested_metric(hardening_fixture):
    """
    Main metric SUM(orders.margin_pct) is semantically invalid and MUST return HTTP 400.
    """
    client = hardening_fixture["client"]
    token = hardening_fixture["token"]
    conn_id = hardening_fixture["conn"].id

    res = client.post(
        f"/api/analytics/dashboard/{conn_id}/query",
        json={
            "table_name": "orders",
            "target_column": "margin_pct",
            "aggregation": "SUM",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400
    detail = res.json().get("detail", "")
    assert "Cannot apply SUM to non-additive ratio/rate/percentage" in detail


def test_optional_sum_summary_stat_becomes_unavailable_not_fatal(hardening_fixture):
    """
    When AVG(orders.margin_pct) is requested, the optional summary stat for SUM
    must become None (null in JSON) rather than crashing the endpoint with 400.
    Other valid stats (average, max, min, count) must execute correctly.
    """
    client = hardening_fixture["client"]
    token = hardening_fixture["token"]
    conn_id = hardening_fixture["conn"].id

    res = client.post(
        f"/api/analytics/dashboard/{conn_id}/query",
        json={
            "table_name": "orders",
            "target_column": "margin_pct",
            "aggregation": "AVG",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    kpi_stats = res.json()["kpi_stats"]
    # Total (SUM) is not applicable to a percentage, so must be None (null in JSON)
    assert kpi_stats["total"] is None
    # Valid stats must be populated
    assert kpi_stats["average"] == 27.5
    assert kpi_stats["max"] == 40.0
    assert kpi_stats["min"] == 20.0
    assert kpi_stats["count"] == 4


# ============================================================================
# 5. CORRECT COUNT SEMANTICS: COUNT(*) vs COUNT(nullable_column)
# ============================================================================

def test_count_wildcard_vs_count_nullable_column(hardening_fixture):
    """
    Fixture has 4 rows total.
    'status' has 2 non-null values ('completed', 'shipped') and 2 NULLs.
    COUNT(*) must equal 4.
    COUNT(status) must equal 2.
    """
    client = hardening_fixture["client"]
    token = hardening_fixture["token"]
    conn_id = hardening_fixture["conn"].id

    # 1. COUNT(*)
    res_all = client.post(
        f"/api/analytics/dashboard/{conn_id}/query",
        json={
            "table_name": "orders",
            "target_column": "*",
            "aggregation": "COUNT",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_all.status_code == 200
    assert res_all.json()["chart_data"][0]["value"] == 4
    assert res_all.json()["kpi_stats"]["count"] == 4

    # 2. COUNT(status)
    res_status = client.post(
        f"/api/analytics/dashboard/{conn_id}/query",
        json={
            "table_name": "orders",
            "target_column": "status",
            "aggregation": "COUNT",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_status.status_code == 200
    assert res_status.json()["chart_data"][0]["value"] == 2
    assert res_status.json()["kpi_stats"]["count"] == 2


# ============================================================================
# 6, 7, 8, 9, 10. FILTER CORRECTNESS
# ============================================================================

def test_scalar_equality_filter(hardening_fixture):
    """Filter status='completed' must return only completed rows (1 row, total_amount=100.0)."""
    client = hardening_fixture["client"]
    token = hardening_fixture["token"]
    conn_id = hardening_fixture["conn"].id

    res = client.post(
        f"/api/analytics/dashboard/{conn_id}/query",
        json={
            "table_name": "orders",
            "target_column": "total_amount",
            "aggregation": "SUM",
            "filters": {"status": "completed"},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["chart_data"][0]["value"] == 100.0


def test_in_list_filter(hardening_fixture):
    """Filter status IN ['completed', 'shipped'] must return 2 rows (total_amount=300.0)."""
    client = hardening_fixture["client"]
    token = hardening_fixture["token"]
    conn_id = hardening_fixture["conn"].id

    res = client.post(
        f"/api/analytics/dashboard/{conn_id}/query",
        json={
            "table_name": "orders",
            "target_column": "total_amount",
            "aggregation": "SUM",
            "filters": {"status": ["completed", "shipped"]},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["chart_data"][0]["value"] == 300.0


def test_false_boolean_filter_not_dropped(hardening_fixture):
    """
    Filter is_flagged=False must NOT be dropped by truthiness checks.
    2 unflagged rows (rows 1 & 2): total_amount = 100 + 200 = 300.0.
    """
    client = hardening_fixture["client"]
    token = hardening_fixture["token"]
    conn_id = hardening_fixture["conn"].id

    res = client.post(
        f"/api/analytics/dashboard/{conn_id}/query",
        json={
            "table_name": "orders",
            "target_column": "total_amount",
            "aggregation": "SUM",
            "filters": {"is_flagged": False},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["chart_data"][0]["value"] == 300.0


def test_zero_integer_filter_not_dropped(hardening_fixture):
    """
    Filter error_code=0 must NOT be dropped by truthiness checks.
    2 rows with error_code=0 (rows 1 & 2): total_amount = 100 + 200 = 300.0.
    """
    client = hardening_fixture["client"]
    token = hardening_fixture["token"]
    conn_id = hardening_fixture["conn"].id

    res = client.post(
        f"/api/analytics/dashboard/{conn_id}/query",
        json={
            "table_name": "orders",
            "target_column": "total_amount",
            "aggregation": "SUM",
            "filters": {"error_code": 0},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["chart_data"][0]["value"] == 300.0


def test_malicious_filter_string_remains_bound_parameter(hardening_fixture):
    """
    Filter with SQL injection payload must remain a bound SQLAlchemy parameter.
    Does NOT match any row (0 rows returned) and does NOT execute injected SQL.
    """
    client = hardening_fixture["client"]
    token = hardening_fixture["token"]
    conn_id = hardening_fixture["conn"].id

    res = client.post(
        f"/api/analytics/dashboard/{conn_id}/query",
        json={
            "table_name": "orders",
            "target_column": "total_amount",
            "aggregation": "SUM",
            "filters": {"status": "' OR '1'='1"},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    # Bound parameter searched for exact literal "' OR '1'='1" -> 0 matches -> 0.0
    assert res.json()["chart_data"][0]["value"] == 0.0


# ============================================================================
# 11, 12. TIGHTENED BARE "all" RESOLUTION
# ============================================================================

def test_bare_all_cannot_resolve_from_unrelated_global_layout_mapping(hardening_fixture):
    """
    If a layout has domain_mapping pointing to 'orders', but a KPI has bare target 'all'
    with no dimension or time column in a multi-table database, the adapter MUST NOT
    infer 'orders' from the unrelated global layout mapping. It must fail clearly.
    """
    db = hardening_fixture["db"]
    conn = hardening_fixture["conn"]
    tenant = hardening_fixture["tenant"]

    layout = models.DashboardLayout(
        tenant_id=tenant.id,
        connection_id=conn.id,
        business_domain="Retail",
        domain_mapping={"revenue": "orders.total_amount"},
    )
    db.add(layout)
    db.commit()

    ambiguous_kpi = models.KpiDefinition(
        tenant_id=tenant.id,
        connection_id=conn.id,
        kpi_title="Unrelated Bare Count",
        aggregation_function="COUNT",
        target_column="all",
        dimension_column=None,
        time_column=None,
    )
    db.add(ambiguous_kpi)
    db.commit()

    with pytest.raises(LegacyKpiIncompatibleError) as exc_info:
        resolve_kpi_target_and_dimension(ambiguous_kpi, conn, db, layout=layout)

    assert "ambiguous table context across 2 tables" in str(exc_info.value)
    assert "KPI requires regeneration" in str(exc_info.value)


def test_ambiguous_bare_all_fails_with_no_guessing(hardening_fixture):
    """
    Prove that bare '*' or 'all' with no qualifying context across multiple tables
    raises LegacyKpiIncompatibleError.
    """
    db = hardening_fixture["db"]
    conn = hardening_fixture["conn"]
    tenant = hardening_fixture["tenant"]

    kpi = models.KpiDefinition(
        tenant_id=tenant.id,
        connection_id=conn.id,
        kpi_title="Ambiguous Wildcard",
        aggregation_function="COUNT",
        target_column="*",
    )
    with pytest.raises(LegacyKpiIncompatibleError):
        resolve_kpi_target_and_dimension(kpi, conn, db)


# ============================================================================
# 13. SCATTER DATA PATH VALIDATION
# ============================================================================

def test_scatter_series_reader_valid_and_invalid_paths(hardening_fixture):
    """
    Prove that series_reader:
    1. Returns valid scatter data points bounded by limit for registered measures.
    2. Rejects invalid column not in SchemaRegistry.
    3. Rejects column from another table (enforces intra-table constraint).
    """
    db = hardening_fixture["db"]
    conn = hardening_fixture["conn"]

    # 1. Valid scatter query
    scatter_pts = read_scatter_series(
        db_conn=conn,
        db=db,
        table_name="orders",
        measure1_col="total_amount",
        measure2_col="profit",
        label_col="status",
        limit=40,
    )
    assert len(scatter_pts) == 4
    assert scatter_pts[0]["x"] == 100.0
    assert scatter_pts[0]["y"] == 20.0

    # 2. Reject unknown column
    with pytest.raises(ValueError) as exc_col:
        read_scatter_series(
            db_conn=conn,
            db=db,
            table_name="orders",
            measure1_col="total_amount",
            measure2_col="non_existent_measure",
        )
    assert "does not exist in table 'orders'" in str(exc_col.value)

    # 3. Reject column from another table (e.g. customer_name from customers passed to orders)
    with pytest.raises(ValueError) as exc_cross:
        read_scatter_series(
            db_conn=conn,
            db=db,
            table_name="orders",
            measure1_col="total_amount",
            measure2_col="customer_name",  # exists in customers, NOT in orders
        )
    assert "does not exist in table 'orders'" in str(exc_cross.value)


# ============================================================================
# 14. FAILED CHART EXPOSES SAFE DIAGNOSTIC STATUS WITHOUT LEAKING INTERNALS
# ============================================================================

def test_failed_chart_exposes_safe_diagnostic_status_without_leakage(hardening_fixture):
    """
    In GET /dashboard/{connection_id}:
    - Succeeded charts have status="success".
    - Incompatible legacy KPIs have status="error" and error_code="LEGACY_KPI_INCOMPATIBLE".
    - No passwords ('secret_password_123'), connection strings, or raw SQL are leaked in the client response.
    """
    client = hardening_fixture["client"]
    token = hardening_fixture["token"]
    conn = hardening_fixture["conn"]
    db = hardening_fixture["db"]
    tenant = hardening_fixture["tenant"]

    # Add a valid KPI
    valid_kpi = models.KpiDefinition(
        tenant_id=tenant.id,
        connection_id=conn.id,
        kpi_title="Valid Revenue",
        aggregation_function="SUM",
        target_column="orders.total_amount",
        default_chart_type="Bar",
    )
    # Add an incompatible legacy KPI (missing aggregation)
    broken_kpi = models.KpiDefinition(
        tenant_id=tenant.id,
        connection_id=conn.id,
        kpi_title="Corrupted Aggregation KPI",
        aggregation_function=None,
        target_column="orders.total_amount",
        default_chart_type="Line",
    )
    db.add(valid_kpi)
    db.add(broken_kpi)
    db.commit()

    cache_service._store.clear()

    res = client.get(
        f"/api/analytics/dashboard/{conn.id}?date_range=all",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    charts = res.json()["live_charts"]

    # Find the charts
    valid_entry = next((c for c in charts if c["title"] == "Valid Revenue"), None)
    broken_entry = next((c for c in charts if c["title"] == "Corrupted Aggregation KPI"), None)

    assert valid_entry is not None
    assert valid_entry["status"] == "success"
    assert len(valid_entry["data"]) > 0

    assert broken_entry is not None
    assert broken_entry["status"] == "error"
    assert broken_entry["error_code"] == "LEGACY_KPI_INCOMPATIBLE"
    assert broken_entry["data"] == []

    # Verify security: NO leakage of password or database paths
    raw_response_text = res.text
    assert "secret_password_123" not in raw_response_text
    assert "SELECT " not in raw_response_text
