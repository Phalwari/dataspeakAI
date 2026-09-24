"""
Phase 1.5D.2 - Atomic Regeneration Safety & Cross-Table Dimension Guard
Comprehensive regression test suite covering Tasks 1 through 4.
"""

import os
import sys
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

# Setup backend import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models
from database import Base
from routers.analytics import run_agent_pipeline_sync
from services.metric_executor import MetricExecutor, MetricRequest


@pytest.fixture
def atomic_db():
    """Sets up an isolated in-memory SQLite database with multi-table schema."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSession()

    # Seed Tenant 1 and Tenant 2
    t1 = models.Tenant(id=1, name="Tenant One")
    t2 = models.Tenant(id=2, name="Tenant Two")
    db.add_all([t1, t2])

    # Connection 1 belongs to Tenant 1
    conn1 = models.DatabaseConnection(
        id=1,
        tenant_id=1,
        name="Tenant 1 DB",
        db_type="sqlite",
        host="localhost",
        username="test",
        password="secret_password",
        database=":memory:",
    )
    # Connection 2 belongs to Tenant 2
    conn2 = models.DatabaseConnection(
        id=2,
        tenant_id=2,
        name="Tenant 2 DB",
        db_type="sqlite",
        host="localhost",
        username="test",
        password="secret_password",
        database=":memory:",
    )
    db.add_all([conn1, conn2])

    # Seed SchemaRegistry for Connection 1 (has orders and customers tables)
    schema_rows = [
        models.SchemaRegistry(connection_id=1, table_name="orders", column_name="order_id", data_type="INTEGER", is_primary_key=True, semantic_type="ID"),
        models.SchemaRegistry(connection_id=1, table_name="orders", column_name="total_amount", data_type="REAL", is_measure=True, semantic_type="NUMERIC_MEASURE"),
        models.SchemaRegistry(connection_id=1, table_name="orders", column_name="status", data_type="VARCHAR", is_dimension=True, semantic_type="CATEGORY"),
        models.SchemaRegistry(connection_id=1, table_name="customers", column_name="customer_id", data_type="INTEGER", is_primary_key=True, semantic_type="ID"),
        models.SchemaRegistry(connection_id=1, table_name="customers", column_name="region", data_type="VARCHAR", is_dimension=True, semantic_type="CATEGORY"),
    ]
    db.add_all(schema_rows)
    db.commit()

    try:
        yield db, conn1, conn2
    finally:
        db.close()


# ==============================================================================
# TESTS 1 & 2: ZERO VALID REGENERATION PRESERVES WORKING DASHBOARD
# ==============================================================================

def test_1_zero_valid_regeneration_preserves_old_kpi_records(atomic_db):
    """
    Proves that when regeneration receives 100% invalid agent specs,
    it does NOT delete the existing working KPI records.
    """
    db, conn1, _ = atomic_db

    # Pre-seed an existing valid dashboard
    old_kpi = models.KpiDefinition(
        tenant_id=1,
        connection_id=conn1.id,
        kpi_title="Existing Total Revenue",
        aggregation_function="SUM",
        target_column="orders.total_amount",
    )
    db.add(old_kpi)
    db.commit()

    # Incoming agent output with 100% invalid specs
    bad_specs = [
        SimpleNamespace(kpi_title="Bad 1", aggregation_function="", primary_column="orders.total_amount"),
        SimpleNamespace(kpi_title="Bad 2", aggregation_function="GROWTH", primary_column="orders.total_amount"),
        SimpleNamespace(kpi_title="Bad 3", aggregation_function="SUM", primary_column="unknown_tbl.col"),
    ]

    res = run_agent_pipeline_sync(
        tenant_id=1,
        connection_id=conn1.id,
        agent_kpis=bad_specs,
        db=db,
    )

    assert res == []

    # Old KPI records must be 100% intact!
    remaining = db.query(models.KpiDefinition).filter(models.KpiDefinition.connection_id == conn1.id).all()
    assert len(remaining) == 1
    assert remaining[0].kpi_title == "Existing Total Revenue"


def test_2_zero_valid_regeneration_preserves_old_layout(atomic_db):
    """
    Proves that when regeneration receives 100% invalid agent specs,
    the existing DashboardLayout is NOT modified or wiped.
    """
    db, conn1, _ = atomic_db

    old_layout = models.DashboardLayout(
        tenant_id=1,
        connection_id=conn1.id,
        business_domain="Proven Retail Domain",
        charts_config=[{"id": "c1", "title": "Old Chart"}],
        filters_config=[],
        validation_warnings=[],
        used_fallback=False,
    )
    db.add(old_layout)
    db.commit()

    bad_specs = [
        SimpleNamespace(kpi_title="Invalid", aggregation_function="", primary_column="orders.total_amount")
    ]
    candidate_layout = SimpleNamespace(
        business_domain="Hallucinated Overwrite Domain",
        charts=[],
        filters=[],
        validation_warnings=[],
        used_fallback=True,
    )

    res = run_agent_pipeline_sync(
        tenant_id=1,
        connection_id=conn1.id,
        agent_kpis=bad_specs,
        db=db,
        layout_config=candidate_layout,
    )

    assert res == []

    # Existing DashboardLayout must remain untouched
    layout_in_db = db.query(models.DashboardLayout).filter(models.DashboardLayout.connection_id == conn1.id).first()
    assert layout_in_db is not None
    assert layout_in_db.business_domain == "Proven Retail Domain"
    assert layout_in_db.charts_config == [{"id": "c1", "title": "Old Chart"}]


# ==============================================================================
# TESTS 3 & 4: SUCCESSFUL REGENERATION REPLACES KPIS AND UPDATES LAYOUT
# ==============================================================================

def test_3_successful_regeneration_replaces_kpis(atomic_db):
    """Proves that a valid replacement set replaces old KPIs."""
    db, conn1, _ = atomic_db

    old_kpi = models.KpiDefinition(
        tenant_id=1,
        connection_id=conn1.id,
        kpi_title="Old Stale KPI",
        aggregation_function="SUM",
        target_column="orders.total_amount",
    )
    db.add(old_kpi)
    db.commit()

    valid_spec = SimpleNamespace(
        kpi_title="Fresh New Revenue",
        aggregation_function="SUM",
        primary_column="orders.total_amount",
    )

    persisted = run_agent_pipeline_sync(
        tenant_id=1,
        connection_id=conn1.id,
        agent_kpis=[valid_spec],
        db=db,
    )

    assert len(persisted) == 1
    assert persisted[0].kpi_title == "Fresh New Revenue"

    kpis_in_db = db.query(models.KpiDefinition).filter(models.KpiDefinition.connection_id == conn1.id).all()
    assert len(kpis_in_db) == 1
    assert kpis_in_db[0].kpi_title == "Fresh New Revenue"


def test_4_successful_regeneration_updates_layout(atomic_db):
    """Proves that valid regeneration successfully updates the DashboardLayout."""
    db, conn1, _ = atomic_db

    old_layout = models.DashboardLayout(
        tenant_id=1,
        connection_id=conn1.id,
        business_domain="Old Domain",
        charts_config=[],
        filters_config=[],
    )
    db.add(old_layout)
    db.commit()

    valid_spec = SimpleNamespace(
        kpi_title="Revenue KPI",
        aggregation_function="SUM",
        primary_column="orders.total_amount",
    )
    new_layout_config = SimpleNamespace(
        business_domain="Updated E-Commerce Domain",
        charts=[{"id": "chart_1", "title": "Revenue Trend"}],
        filters=[{"column": "orders.status", "label": "Status"}],
        validation_warnings=["Warning: high volume"],
        used_fallback=False,
    )

    persisted = run_agent_pipeline_sync(
        tenant_id=1,
        connection_id=conn1.id,
        agent_kpis=[valid_spec],
        db=db,
        layout_config=new_layout_config,
    )

    assert len(persisted) == 1
    layout_in_db = db.query(models.DashboardLayout).filter(models.DashboardLayout.connection_id == conn1.id).first()
    assert layout_in_db is not None
    assert layout_in_db.business_domain == "Updated E-Commerce Domain"
    assert layout_in_db.charts_config == [{"id": "chart_1", "title": "Revenue Trend"}]


# ==============================================================================
# TESTS 5, 6, 7: TRANSACTION ATOMICITY AND CACHE INVALIDATION
# ==============================================================================

def test_5_layout_failure_rolls_back_kpi_replacement(atomic_db):
    """
    Proves that if an error occurs while persisting DashboardLayout,
    the entire transaction rolls back, preserving the old KPIs.
    """
    db, conn1, _ = atomic_db

    old_kpi = models.KpiDefinition(
        tenant_id=1,
        connection_id=conn1.id,
        kpi_title="Old Safe KPI",
        aggregation_function="SUM",
        target_column="orders.total_amount",
    )
    old_layout = models.DashboardLayout(
        tenant_id=1,
        connection_id=conn1.id,
        business_domain="Safe Old Domain",
    )
    db.add_all([old_kpi, old_layout])
    db.commit()

    valid_spec = SimpleNamespace(
        kpi_title="New Uncommitted KPI",
        aggregation_function="SUM",
        primary_column="orders.total_amount",
    )

    # Malicious layout config whose attribute access or serialization raises an exception during transaction
    bad_layout = MagicMock()
    bad_layout.charts = MagicMock()
    # Trigger an exception when inspecting layout
    type(bad_layout).business_domain = property(lambda self: (_ for _ in ()).throw(RuntimeError("DB Disk Write Failure!")))

    with pytest.raises(RuntimeError) as exc_info:
        run_agent_pipeline_sync(
            tenant_id=1,
            connection_id=conn1.id,
            agent_kpis=[valid_spec],
            db=db,
            layout_config=bad_layout,
        )

    assert "DB Disk Write Failure!" in str(exc_info.value)

    # Crucial Task 2: Transaction was rolled back! Old KPI and old layout remain intact!
    remaining_kpis = db.query(models.KpiDefinition).filter(models.KpiDefinition.connection_id == conn1.id).all()
    assert len(remaining_kpis) == 1
    assert remaining_kpis[0].kpi_title == "Old Safe KPI"

    layout_in_db = db.query(models.DashboardLayout).filter(models.DashboardLayout.connection_id == conn1.id).first()
    assert layout_in_db.business_domain == "Safe Old Domain"


def test_6_failed_transaction_does_not_invalidate_cache(atomic_db):
    """Proves that cache invalidation is NOT called when a transaction fails."""
    db, conn1, _ = atomic_db

    valid_spec = SimpleNamespace(
        kpi_title="New KPI",
        aggregation_function="SUM",
        primary_column="orders.total_amount",
    )

    bad_layout = MagicMock()
    type(bad_layout).business_domain = property(lambda self: (_ for _ in ()).throw(RuntimeError("Crash!")))

    with patch("routers.analytics.cache_service.invalidate") as mock_invalidate:
        with pytest.raises(RuntimeError):
            run_agent_pipeline_sync(
                tenant_id=1,
                connection_id=conn1.id,
                agent_kpis=[valid_spec],
                db=db,
                layout_config=bad_layout,
            )
        # Invalidate must NEVER have been called on failed transaction
        mock_invalidate.assert_not_called()


def test_7_successful_transaction_invalidates_cache_after_commit(atomic_db):
    """Proves that cache invalidation is executed after a successful commit."""
    db, conn1, _ = atomic_db

    valid_spec = SimpleNamespace(
        kpi_title="Valid Revenue",
        aggregation_function="SUM",
        primary_column="orders.total_amount",
    )

    with patch("routers.analytics.cache_service.invalidate") as mock_invalidate:
        persisted = run_agent_pipeline_sync(
            tenant_id=1,
            connection_id=conn1.id,
            agent_kpis=[valid_spec],
            db=db,
            commit=True,
        )
        assert len(persisted) == 1
        # Invalidation must be called for all 4 time-series ranges
        assert mock_invalidate.call_count == 4
        ranges_called = [call.args[1] for call in mock_invalidate.call_args_list]
        assert f"dash_view:{conn1.id}:7days" in ranges_called
        assert f"dash_view:{conn1.id}:30days" in ranges_called
        assert f"dash_view:{conn1.id}:90days" in ranges_called
        assert f"dash_view:{conn1.id}:1year" in ranges_called


# ==============================================================================
# TESTS 8, 9, 10: SAME-TABLE VS CROSS-TABLE DIMENSIONS
# ==============================================================================

def test_8_same_table_dimension_is_persisted(atomic_db):
    """
    Target: orders.total_amount, Dimension: orders.status
    Same table -> dimension preserved.
    """
    db, conn1, _ = atomic_db

    spec = SimpleNamespace(
        kpi_title="Revenue by Status",
        aggregation_function="SUM",
        primary_column="orders.total_amount",
        secondary_column="orders.status",
    )

    persisted = run_agent_pipeline_sync(
        tenant_id=1,
        connection_id=conn1.id,
        agent_kpis=[spec],
        db=db,
    )

    assert len(persisted) == 1
    k = persisted[0]
    assert k.target_column == "orders.total_amount"
    assert k.dimension_column == "orders.status"


def test_9_cross_table_dimension_is_omitted(atomic_db):
    """
    Target: orders.total_amount, Dimension: customers.region
    Both exist in SchemaRegistry, but belong to different tables.
    Cross-table dimension must be safely omitted (dimension_column=None)
    while preserving the primary metric.
    """
    db, conn1, _ = atomic_db

    spec = SimpleNamespace(
        kpi_title="Revenue by Customer Region",
        aggregation_function="SUM",
        primary_column="orders.total_amount",
        secondary_column="customers.region",
    )

    persisted = run_agent_pipeline_sync(
        tenant_id=1,
        connection_id=conn1.id,
        agent_kpis=[spec],
        db=db,
    )

    assert len(persisted) == 1
    k = persisted[0]
    assert k.target_column == "orders.total_amount"
    # Crucial Task 3 check: dimension is omitted to prevent invalid cross-table query
    assert k.dimension_column is None


def test_10_no_join_is_generated(atomic_db):
    """
    Proves that for the cross-table spec, no JOIN is generated,
    and MetricExecutor computes the primary metric safely on single table 'orders'.
    """
    db, conn1, _ = atomic_db

    # Create external customer database
    ext_engine = create_engine("sqlite:///:memory:")
    with ext_engine.begin() as conn:
        conn.execute(text("CREATE TABLE orders (order_id INTEGER PRIMARY KEY, total_amount REAL)"))
        conn.execute(text("INSERT INTO orders (order_id, total_amount) VALUES (1, 100.0), (2, 200.0)"))

    spec = SimpleNamespace(
        kpi_title="Revenue by Customer Region",
        aggregation_function="SUM",
        primary_column="orders.total_amount",
        secondary_column="customers.region",
    )

    persisted = run_agent_pipeline_sync(
        tenant_id=1,
        connection_id=conn1.id,
        agent_kpis=[spec],
        db=db,
    )

    kpi = persisted[0]
    req = MetricRequest(
        connection_id=conn1.id,
        target_ref=kpi.target_column,
        aggregation=kpi.aggregation_function,
        dimension_ref=kpi.dimension_column,
        tenant_id=1,
    )

    with patch("services.metric_executor.get_engine", return_value=ext_engine):
        result = MetricExecutor.execute(req, conn1, db)
        assert result.value == 300.0
        assert "JOIN" not in result.sql.upper()
        assert 'FROM "orders"' in result.sql


# ==============================================================================
# TEST 11: CONNECTION OWNERSHIP DEFENSE
# ==============================================================================

def test_11_cross_tenant_agent_persistence_is_rejected(atomic_db):
    """
    Proves that Tenant 2 cannot persist agent KPIs on Connection 1 (owned by Tenant 1).
    """
    db, conn1, conn2 = atomic_db

    spec = SimpleNamespace(
        kpi_title="Unauthorized Metric",
        aggregation_function="SUM",
        primary_column="orders.total_amount",
    )

    # Tenant 2 tries to persist on Connection 1
    with pytest.raises(ValueError) as exc_info:
        run_agent_pipeline_sync(
            tenant_id=2,  # Tenant 2!
            connection_id=conn1.id,  # Connection 1 belongs to Tenant 1!
            agent_kpis=[spec],
            db=db,
        )

    assert f"Database connection {conn1.id} not found or unauthorized for tenant 2" in str(exc_info.value)

    # Verify Connection 1 was NOT modified
    kpis_in_conn1 = db.query(models.KpiDefinition).filter(models.KpiDefinition.connection_id == conn1.id).all()
    assert len(kpis_in_conn1) == 0
