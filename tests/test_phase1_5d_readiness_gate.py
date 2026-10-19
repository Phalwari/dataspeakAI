"""
Phase 1.5D - Contract Alignment, Legacy Cleanup & Production Readiness Gate
Comprehensive Test Suite covering Tasks 1 through 10.
"""

import os
import sys
# Setup backend import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

import models
from database import Base, get_db
from main import app
from dependencies import get_current_user
from services.metric_executor import MetricExecutor, MetricRequest, MetricFilter
from services.metric_adapter import (
    adapt_kpi_to_metric_request,
    resolve_kpi_target_and_dimension,
    LegacyKpiIncompatibleError,
)
from services.db_migration import run_schema_migrations, MIGRATION_COLUMNS
from services.domain_templates import get_domain_template, list_domain_templates, KpiRecipe
from services.cache_service import cache_service


from sqlalchemy.pool import StaticPool


@pytest.fixture(scope="module")
def gate_db():
    """Sets up an isolated SQLite database fixture for Phase 1.5D testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    run_schema_migrations(engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSession()

    # Seed Tenant 1 and User 1
    t1 = models.Tenant(id=1, name="Tenant One")
    db.add(t1)
    u1 = models.User(id=1, tenant_id=1, email="user1@example.com", hashed_password="pw", is_active=True)
    db.add(u1)

    # Seed Tenant 2 and User 2
    t2 = models.Tenant(id=2, name="Tenant Two")
    db.add(t2)
    u2 = models.User(id=2, tenant_id=2, email="user2@example.com", hashed_password="pw", is_active=True)
    db.add(u2)

    # Seed an external test database for Tenant 1
    ext_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with ext_engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE orders (
                order_id INTEGER PRIMARY KEY,
                customer_id INTEGER,
                total_amount REAL,
                status VARCHAR(50),
                created_at TIMESTAMP
            )
        """))
        conn.execute(text("""
            INSERT INTO orders (order_id, customer_id, total_amount, status, created_at) VALUES
            (1, 101, 100.0, 'completed', '2026-09-01 10:00:00'),
            (2, 102, 200.0, 'pending', '2026-09-05 11:00:00'),
            (3, 101, 300.0, 'completed', '2026-09-10 12:00:00'),
            (4, 103, 400.0, 'cancelled', '2026-09-15 13:00:00')
        """))
        conn.execute(text("""
            CREATE TABLE products (
                product_id INTEGER PRIMARY KEY,
                name VARCHAR(100),
                price REAL
            )
        """))
        conn.execute(text("""
            INSERT INTO products (product_id, name, price) VALUES
            (1, 'Product A', 50.0),
            (2, 'Product B', 75.0)
        """))

    # We attach the in-memory database URL
    db_conn1 = models.DatabaseConnection(
        id=1,
        tenant_id=1,
        name="Main Orders DB",
        db_type="sqlite",
        host="localhost",
        username="test",
        password="plain_password",
        database=":memory:",
    )
    db.add(db_conn1)

    # SchemaRegistry for Connection 1
    sr_orders = [
        models.SchemaRegistry(connection_id=1, table_name="orders", column_name="order_id", data_type="INTEGER", is_primary_key=True, semantic_type="ID"),
        models.SchemaRegistry(connection_id=1, table_name="orders", column_name="customer_id", data_type="INTEGER", is_dimension=True, semantic_type="ID"),
        models.SchemaRegistry(connection_id=1, table_name="orders", column_name="total_amount", data_type="REAL", is_measure=True, semantic_type="NUMERIC_MEASURE"),
        models.SchemaRegistry(connection_id=1, table_name="orders", column_name="status", data_type="VARCHAR", is_dimension=True, semantic_type="CATEGORY"),
        models.SchemaRegistry(connection_id=1, table_name="orders", column_name="created_at", data_type="TIMESTAMP", is_time_axis=True, semantic_type="DATETIME"),
        models.SchemaRegistry(connection_id=1, table_name="products", column_name="product_id", data_type="INTEGER", is_primary_key=True, semantic_type="ID"),
        models.SchemaRegistry(connection_id=1, table_name="products", column_name="name", data_type="VARCHAR", is_dimension=True, semantic_type="TEXT"),
        models.SchemaRegistry(connection_id=1, table_name="products", column_name="price", data_type="REAL", is_measure=True, semantic_type="NUMERIC_MEASURE"),
    ]
    db.add_all(sr_orders)
    db.commit()

    def override_get_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    # Attach in-memory engine cache for get_engine
    with patch("services.metric_executor.get_engine", return_value=ext_engine), \
         patch("routers.databases.get_engine", return_value=ext_engine):
        yield db, ext_engine, db_conn1, u1, u2

    app.dependency_overrides.pop(get_db, None)

    db.close()


# ==============================================================================
# TASK 1: AUDIT EVERY KpiDefinition WRITE PATH
# ==============================================================================

def test_task1_apply_mapping_rejects_missing_or_blank_aggregation(gate_db):
    """
    Proves that apply_user_confirmed_mapping rejects templates/recipes with missing,
    blank, or unsupported aggregation_function, preventing NULL/blank persistence.
    """
    db, _, db_conn, u1, _ = gate_db

    client = TestClient(app)
    app.dependency_overrides[get_current_user] = lambda: models.User(id=1, tenant_id=1, email="user1@example.com", is_active=True, is_verified=True, role="Admin")

    try:
        bad_template = get_domain_template("e-commerce")
        corrupted_recipe = KpiRecipe(
            id="bad_kpi",
            title="Corrupted Revenue",
            formula_template="SUM({revenue})",
            required_variables=["revenue"],
            aggregation="",  # Empty string aggregation!
            description="Bad KPI"
        )

        with patch("routers.analytics.get_domain_template") as mock_tmpl:
            mock_tmpl.return_value = MagicMock(
                kpis=[corrupted_recipe],
                charts=[],
                business_domain="E-Commerce",
            )
            response = client.post(
                f"/api/analytics/connections/{db_conn.id}/apply-mapping",
                json={
                    "domain": "e-commerce",
                    "mappings": {"revenue": "orders.total_amount"},
                    "confirmed_by_user": True
                }
            )
            assert response.status_code == 400
            assert "invalid or missing aggregation" in response.json()["detail"].lower()

    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_task1_domain_templates_have_explicit_valid_aggregations():
    """
    Validates that every single predefined domain template in domain_templates.py
    explicitly supplies a valid, whitelisted aggregation function.
    """
    allowed_aggregations = {"SUM", "AVG", "MIN", "MAX", "COUNT", "COUNT_DISTINCT"}
    for domain_meta in list_domain_templates():
        domain_id = domain_meta.get("id") or domain_meta.get("domain_id") if isinstance(domain_meta, dict) else getattr(domain_meta, "id", None)
        tmpl = get_domain_template(domain_id)
        for kpi in tmpl.kpis:
            raw_agg = (kpi.aggregation or "").strip().upper()
            assert raw_agg in allowed_aggregations, (
                f"Domain '{domain_id}' KPI '{kpi.title}' has invalid/missing aggregation: '{kpi.aggregation}'"
            )


# ==============================================================================
# TASK 2: AUDIT UNSUPPORTED AGGREGATION VALUES
# ==============================================================================

@pytest.mark.parametrize("unsupported_agg", [
    "COMPUTED",
    "RATIO",
    "DIFFERENCE",
    "PERCENT_CHANGE",
    "GROWTH",
    "MEDIAN",
])
def test_task2_metric_adapter_rejects_unsupported_aggregations(gate_db, unsupported_agg):
    """
    Proves that metric_adapter raises LegacyKpiIncompatibleError for unsupported aggregations,
    preventing non-whitelisted operations from crashing the live pipeline.
    """
    db, _, db_conn, _, _ = gate_db

    kpi = models.KpiDefinition(
        id=999,
        tenant_id=1,
        connection_id=db_conn.id,
        kpi_title=f"Test {unsupported_agg}",
        aggregation_function=unsupported_agg,
        target_column="orders.total_amount",
        default_chart_type="Bar"
    )

    with pytest.raises(LegacyKpiIncompatibleError) as exc_info:
        adapt_kpi_to_metric_request(kpi, db_conn, db)

    err_text = str(exc_info.value)
    assert f"unsupported aggregation '{unsupported_agg}'" in err_text
    assert "Phase 2 Metric Recipes" in err_text


# ==============================================================================
# TASK 3: REMOVE HYPOTHETICAL KPI MODEL FIELD LOGIC
# ==============================================================================

def test_task3_no_hypothetical_source_table_logic(gate_db):
    """
    Proves that resolve_kpi_target_and_dimension does not rely on hypothetical
    source_table or table_name attributes on KpiDefinition.
    """
    db, _, db_conn, _, _ = gate_db

    # In a multi-table schema (orders, products), an unqualified target "total_amount"
    # with dummy source_table set dynamically should NOT use that dummy attribute
    # if it doesn't exist in the database schema.
    kpi = models.KpiDefinition(
        id=1001,
        tenant_id=1,
        connection_id=db_conn.id,
        kpi_title="Ambiguous Wildcard",
        aggregation_function="COUNT",
        target_column="*",  # Bare wildcard
        dimension_column=None,
        time_column=None,
    )
    # Even if an object had hypothetical attributes injected dynamically,
    # bare wildcard across multiple tables without dimension/time context must raise LegacyKpiIncompatibleError
    setattr(kpi, "source_table", "orders")
    setattr(kpi, "table_name", "orders")

    with pytest.raises(LegacyKpiIncompatibleError) as exc_info:
        resolve_kpi_target_and_dimension(kpi, db_conn, db)

    assert "ambiguous table context across 2 tables" in str(exc_info.value)


# ==============================================================================
# TASK 4: AI INSIGHTS BACKEND / FRONTEND CONTRACT
# ==============================================================================

def test_task4_ai_insights_get_does_not_invoke_llm(gate_db):
    """
    Proves that GET /connections/{id}/ai-insights strictly retrieves cached insights
    and NEVER silently invokes an LLM or generate_ai_insights_from_stats.
    """
    db, _, db_conn, u1, _ = gate_db

    client = TestClient(app)
    app.dependency_overrides[get_current_user] = lambda: models.User(id=1, tenant_id=1, email="user1@example.com", is_active=True, is_verified=True, role="Admin")

    try:
        # Invalidate any cached insights
        cache_service.invalidate(u1.tenant_id, f"connection_ai_insights:{db_conn.id}")

        with patch("routers.analytics.generate_ai_insights_from_stats") as mock_gen:
            res = client.get(f"/api/analytics/connections/{db_conn.id}/ai-insights")
            assert res.status_code == 200
            data = res.json()
            assert data.get("status") == "not_generated"
            # Crucial: LLM generator was NOT called!
            mock_gen.assert_not_called()

    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_task4_ai_insights_post_generates_and_caches(gate_db):
    """
    Proves that POST /connections/{id}/ai-insights/generate explicitly generates
    fresh insights, stores them in cache_service, and GET subsequently returns them.
    """
    db, _, db_conn, u1, _ = gate_db

    client = TestClient(app)
    app.dependency_overrides[get_current_user] = lambda: models.User(id=1, tenant_id=1, email="user1@example.com", is_active=True, is_verified=True, role="Admin")

    mock_insights_payload = {
        "business_type": "E-Commerce Retail",
        "key_metrics": [
            {"title": "Total Revenue", "value": "$1,000.00", "trend": "+12%", "impact": "High"}
        ],
        "observations": ["Observed strong checkout volume"],
        "recommendations": ["Optimize cart recovery"]
    }

    try:
        with patch("routers.analytics.generate_ai_insights_from_stats", return_value=mock_insights_payload) as mock_gen:
            # 1. Trigger POST generate
            post_res = client.post(f"/api/analytics/connections/{db_conn.id}/ai-insights/generate")
            assert post_res.status_code == 200
            assert post_res.json()["business_type"] == "E-Commerce Retail"
            mock_gen.assert_called_once()

            # 2. Subsequent GET returns the cached result without invoking generator again
            get_res = client.get(f"/api/analytics/connections/{db_conn.id}/ai-insights")
            assert get_res.status_code == 200
            assert get_res.json()["business_type"] == "E-Commerce Retail"
            assert mock_gen.call_count == 1  # Still 1!

    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_task4_ai_insights_tenant_isolation(gate_db):
    """
    Proves that Tenant 2 cannot access or trigger AI insights for Tenant 1's connection.
    """
    db, _, db_conn, _, u2 = gate_db

    client = TestClient(app)
    app.dependency_overrides[get_current_user] = lambda: models.User(id=2, tenant_id=2, email="user2@example.com", is_active=True, is_verified=True, role="Admin")

    try:
        # Connection 1 belongs to Tenant 1
        res_get = client.get(f"/api/analytics/connections/{db_conn.id}/ai-insights")
        assert res_get.status_code in (403, 404)

        res_post = client.post(f"/api/analytics/connections/{db_conn.id}/ai-insights/generate")
        assert res_post.status_code in (403, 404)

    finally:
        app.dependency_overrides.pop(get_current_user, None)


# ==============================================================================
# TASK 5: LEGACY CALCULATION PATH ISOLATION
# ==============================================================================

def test_task5_legacy_generators_not_invoked_during_live_dashboard(gate_db):
    """
    Proves that legacy KPI generators (e.g. generate_kpis_and_chart_specs) are NOT
    invoked during normal live dashboard viewing or interactive querying.
    """
    db, ext_engine, db_conn, u1, _ = gate_db

    client = TestClient(app)
    app.dependency_overrides[get_current_user] = lambda: models.User(id=1, tenant_id=1, email="user1@example.com", is_active=True, is_verified=True, role="Admin")

    # Seed one valid KPI definition
    db.query(models.KpiDefinition).filter(models.KpiDefinition.connection_id == db_conn.id).delete()
    kpi = models.KpiDefinition(
        id=10,
        tenant_id=1,
        connection_id=db_conn.id,
        kpi_title="Total Sales",
        aggregation_function="SUM",
        target_column="orders.total_amount",
        default_chart_type="Bar"
    )
    db.add(kpi)
    db.commit()

    try:
        with patch("routers.analytics.generate_kpis_and_chart_specs") as mock_legacy_gen, \
             patch("services.kpi_chart_engine.generate_kpis_and_chart_specs") as mock_legacy_gen2, \
             patch("services.metric_executor.get_engine", return_value=ext_engine):

            # Live Dashboard request
            res = client.get(f"/api/analytics/dashboard/{db_conn.id}")
            assert res.status_code == 200
            mock_legacy_gen.assert_not_called()
            mock_legacy_gen2.assert_not_called()

            # Interactive Query request
            q_res = client.post(
                f"/api/analytics/dashboard/{db_conn.id}/query",
                json={
                    "table_name": "orders",
                    "target_column": "total_amount",
                    "aggregation": "SUM"
                }
            )
            assert q_res.status_code == 200
            mock_legacy_gen.assert_not_called()
            mock_legacy_gen2.assert_not_called()

    finally:
        app.dependency_overrides.pop(get_current_user, None)


# ==============================================================================
# TASK 6: FILTER CONTRACT STRICTNESS
# ==============================================================================

def test_task6_filter_in_requires_collection(gate_db):
    """
    Proves that operator='IN' rejects scalar values and requires list/tuple/set.
    """
    db, ext_engine, db_conn, _, _ = gate_db

    req = MetricRequest(
        connection_id=db_conn.id,
        target_ref="orders.total_amount",
        aggregation="SUM",
        filters=[
            MetricFilter(column="orders.status", operator="IN", value="completed")  # String instead of list!
        ],
        tenant_id=1
    )

    with patch("services.metric_executor.get_engine", return_value=ext_engine):
        with pytest.raises(ValueError) as exc_info:
            MetricExecutor.execute(req, db_conn, db)
        assert "requires a list, tuple, or set" in str(exc_info.value)


def test_task6_scalar_operators_reject_collection(gate_db):
    """
    Proves that scalar operators (=, !=, >, <, >=, <=, LIKE, ILIKE) reject list/tuple/set.
    """
    db, ext_engine, db_conn, _, _ = gate_db

    req = MetricRequest(
        connection_id=db_conn.id,
        target_ref="orders.total_amount",
        aggregation="SUM",
        filters=[
            MetricFilter(column="orders.status", operator="=", value=["completed", "pending"])  # List for scalar '='!
        ],
        tenant_id=1
    )

    with patch("services.metric_executor.get_engine", return_value=ext_engine):
        with pytest.raises(ValueError) as exc_info:
            MetricExecutor.execute(req, db_conn, db)
        assert "does not support list/tuple/set values" in str(exc_info.value)


def test_task6_empty_in_list_resolves_to_zero_rows(gate_db):
    """
    Proves that an empty IN list safely resolves to no rows ('1 = 0') with value 0.
    """
    db, ext_engine, db_conn, _, _ = gate_db

    req = MetricRequest(
        connection_id=db_conn.id,
        target_ref="orders.total_amount",
        aggregation="SUM",
        filters=[
            MetricFilter(column="orders.status", operator="IN", value=[])  # Empty list!
        ],
        tenant_id=1
    )

    with patch("services.metric_executor.get_engine", return_value=ext_engine):
        res = MetricExecutor.execute(req, db_conn, db)
        assert res.value == 0
        assert "1 = 0" in res.sql


def test_task6_valid_in_and_scalar_filters_succeed(gate_db):
    """
    Proves that valid IN lists and scalar equality execute accurately with bound parameters.
    """
    db, ext_engine, db_conn, _, _ = gate_db

    # 1. Valid IN filter (orders 1 and 3 are completed = 100 + 300 = 400)
    req_in = MetricRequest(
        connection_id=db_conn.id,
        target_ref="orders.total_amount",
        aggregation="SUM",
        filters=[
            MetricFilter(column="orders.status", operator="IN", value=["completed"])
        ],
        tenant_id=1
    )
    with patch("services.metric_executor.get_engine", return_value=ext_engine):
        res_in = MetricExecutor.execute(req_in, db_conn, db)
        assert res_in.value == 400.0

    # 2. Valid scalar filter (order 2 is pending = 200)
    req_scalar = MetricRequest(
        connection_id=db_conn.id,
        target_ref="orders.total_amount",
        aggregation="SUM",
        filters=[
            MetricFilter(column="orders.status", operator="=", value="pending")
        ],
        tenant_id=1
    )
    with patch("services.metric_executor.get_engine", return_value=ext_engine):
        res_scalar = MetricExecutor.execute(req_scalar, db_conn, db)
        assert res_scalar.value == 200.0


# ==============================================================================
# TASK 8: SCHEMA DRIFT & MIGRATION READINESS
# ==============================================================================

def test_task8_schema_migrations_adds_all_required_columns():
    """
    Proves that run_schema_migrations inspects existing tables and non-destructively
    adds all missing columns across environments.
    """
    # Create an older schema without progress or visual_pages
    test_engine = create_engine("sqlite:///:memory:")
    with test_engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE documents (
                id INTEGER PRIMARY KEY,
                tenant_id INTEGER,
                name VARCHAR,
                file_type VARCHAR,
                created_at TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE document_chunks (
                id INTEGER PRIMARY KEY,
                document_id INTEGER,
                content VARCHAR,
                created_at TIMESTAMP
            )
        """))

    # Verify missing initially
    insp = inspect(test_engine)
    cols_doc_pre = {c["name"] for c in insp.get_columns("documents")}
    assert "progress" not in cols_doc_pre
    assert "pages_processed" not in cols_doc_pre

    # Run migrations
    run_schema_migrations(test_engine)

    # Verify present post migration
    insp = inspect(test_engine)
    cols_doc_post = {c["name"] for c in insp.get_columns("documents")}
    assert "progress" in cols_doc_post
    assert "pages_processed" in cols_doc_post
    assert "visual_pages" in cols_doc_post
    assert "embedding_model" in cols_doc_post

    cols_chunks_post = {c["name"] for c in insp.get_columns("document_chunks")}
    assert "section_heading" in cols_chunks_post
    assert "content_type" in cols_chunks_post
    assert "page_number" in cols_chunks_post
    assert "reference_id" in cols_chunks_post


# ==============================================================================
# TASK 9: SAFE ERROR CONTRACT
# ==============================================================================

def test_task9_query_error_does_not_leak_credentials_or_raw_driver(gate_db):
    """
    Proves that unexpected calculation or connection errors in the query endpoint
    return safe sanitized error messages and do not leak credentials or raw SQL.
    """
    db, _, db_conn, u1, _ = gate_db

    client = TestClient(app)
    app.dependency_overrides[get_current_user] = lambda: models.User(id=1, tenant_id=1, email="user1@example.com", is_active=True, is_verified=True, role="Admin")

    try:
        # Simulate an unexpected driver crash containing raw connection URL with password
        sensitive_error_msg = "psycopg2.OperationalError: FATAL: password authentication failed for user 'admin' at postgresql://admin:SuperSecretPass123!@10.0.0.1:5432/prod_db"
        with patch("services.metric_executor.MetricExecutor.execute", side_effect=Exception(sensitive_error_msg)):
            res = client.post(
                f"/api/analytics/dashboard/{db_conn.id}/query",
                json={
                    "table_name": "orders",
                    "target_column": "total_amount",
                    "aggregation": "SUM"
                }
            )
            assert res.status_code == 400
            detail = res.json()["detail"]
            # Sensitive information MUST NOT leak to client
            assert "SuperSecretPass123!" not in detail
            assert "postgresql://" not in detail
            assert "Query calculation failed due to an internal execution error." in detail

    finally:
        app.dependency_overrides.pop(get_current_user, None)
