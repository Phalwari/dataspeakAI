"""
tests/test_phase1_5b_metric_engine.py

Comprehensive Test Suite for Phase 1.5B: Canonical Metric Engine.
Validates:
1. Exact numeric correctness against deterministic SQLite dataset.
2. Semantic policy enforcement (preventing SUM/AVG on IDs, percentages, rates, categories).
3. Whitelist enforcement and explicit failure for unsupported aggregations (e.g. MEDIAN).
4. Table safety: Cross-table metric rejection without valid relationship path.
5. Canonical wildcard and legacy "all" handling (strictly COUNT only).
6. SQL bound parameter safety on filters.
7. Tenant isolation at the executor level.
"""

import os
import sys
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Setup path so imports work directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

import models
from database import Base
from services.metric_semantics import validate_metric_aggregation, ALLOWED_AGGREGATIONS
from services.metric_executor import (
    MetricExecutor,
    MetricRequest,
    MetricFilter,
    MetricResult,
)


@pytest.fixture(scope="module")
def metric_fixture():
    """
    Sets up a deterministic SQLite database with the exact prompt test dataset:
    orders:
      order_id     | customer_id | total_amount | unit_price | margin_pct | error_rate | status
      1            | 10          | 100.0        | 10.0       | 0.15       | 0.01       | completed
      2            | 10          | 200.0        | 20.0       | 0.20       | 0.02       | completed
      3            | 20          | 300.0        | 30.0       | 0.18       | 0.01       | shipped
      4            | 30          | 400.0        | 40.0       | 0.22       | 0.05       | cancelled
    """
    # Shared in-memory engine for test DB
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSession()

    # Create real orders table in SQLite
    with engine.connect() as conn:
        conn.execute(
            text("""
            CREATE TABLE orders (
                order_id INTEGER PRIMARY KEY,
                customer_id INTEGER NOT NULL,
                total_amount REAL NOT NULL,
                unit_price REAL NOT NULL,
                margin_pct REAL NOT NULL,
                error_rate REAL NOT NULL,
                status TEXT NOT NULL
            );
        """)
        )
        conn.execute(
            text("""
            INSERT INTO orders (order_id, customer_id, total_amount, unit_price, margin_pct, error_rate, status)
            VALUES 
                (1, 10, 100.0, 10.0, 0.15, 0.01, 'completed'),
                (2, 10, 200.0, 20.0, 0.20, 0.02, 'completed'),
                (3, 20, 300.0, 30.0, 0.18, 0.01, 'shipped'),
                (4, 30, 400.0, 40.0, 0.22, 0.05, 'cancelled');
        """)
        )
        conn.commit()

    # Seed Tenant and DatabaseConnection
    tenant = models.Tenant(name="Acme Corp", industry="E-commerce")
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    db_conn = models.DatabaseConnection(
        tenant_id=tenant.id,
        name="Orders Warehouse",
        db_type="sqlite",
        host=":memory:",
        username="user",
        password="pwd",
        database=":memory:",
        status="connected",
    )
    db.add(db_conn)
    db.commit()
    db.refresh(db_conn)

    # Monkeypatch db_pool to use our in-memory engine
    from services.db_utils import get_connection_url
    from services import db_pool
    conn_url = get_connection_url(db_conn)
    db_pool._engine_cache[conn_url] = engine

    # Seed SchemaRegistry for orders table
    registry_entries = [
        models.SchemaRegistry(
            connection_id=db_conn.id,
            table_name="orders",
            column_name="order_id",
            data_type="INTEGER",
            semantic_type="ID",
            is_primary_key=True,
            is_measure=False,
            is_dimension=False,
        ),
        models.SchemaRegistry(
            connection_id=db_conn.id,
            table_name="orders",
            column_name="customer_id",
            data_type="INTEGER",
            semantic_type="ID",
            is_foreign_key=True,
            is_measure=False,
            is_dimension=False,
        ),
        models.SchemaRegistry(
            connection_id=db_conn.id,
            table_name="orders",
            column_name="total_amount",
            data_type="REAL",
            semantic_type="CURRENCY/AMOUNT",
            is_measure=True,
            is_dimension=False,
        ),
        models.SchemaRegistry(
            connection_id=db_conn.id,
            table_name="orders",
            column_name="unit_price",
            data_type="REAL",
            semantic_type="NUMERIC_MEASURE",
            is_measure=True,
            is_dimension=False,
        ),
        models.SchemaRegistry(
            connection_id=db_conn.id,
            table_name="orders",
            column_name="margin_pct",
            data_type="REAL",
            semantic_type="PERCENTAGE",
            is_measure=True,
            is_dimension=False,
        ),
        models.SchemaRegistry(
            connection_id=db_conn.id,
            table_name="orders",
            column_name="error_rate",
            data_type="REAL",
            semantic_type="RATE",
            is_measure=True,
            is_dimension=False,
        ),
        models.SchemaRegistry(
            connection_id=db_conn.id,
            table_name="orders",
            column_name="status",
            data_type="TEXT",
            semantic_type="CATEGORY",
            is_measure=False,
            is_dimension=True,
        ),
    ]
    db.add_all(registry_entries)
    db.commit()

    yield {
        "db": db,
        "engine": engine,
        "tenant": tenant,
        "db_conn": db_conn,
    }

    db.close()


# ==============================================================================
# SECTION 1: EXACT NUMERIC CORRECTNESS TESTS
# ==============================================================================

def test_exact_numeric_aggregations(metric_fixture):
    """
    Proves exact mathematical outputs for standard aggregate metrics:
    - SUM(total_amount) = 1000
    - AVG(total_amount) = 250
    - MIN(total_amount) = 100
    - MAX(total_amount) = 400
    - COUNT(order_id) = 4
    - COUNT_DISTINCT(customer_id) = 3
    """
    db = metric_fixture["db"]
    conn = metric_fixture["db_conn"]

    # 1. SUM(total_amount) = 100 + 200 + 300 + 400 = 1000
    res_sum = MetricExecutor.execute(
        MetricRequest(connection_id=conn.id, target_ref="orders.total_amount", aggregation="SUM"),
        conn,
        db,
    )
    assert res_sum.is_scalar is True
    assert res_sum.value == 1000.0

    # 2. AVG(total_amount) = 1000 / 4 = 250
    res_avg = MetricExecutor.execute(
        MetricRequest(connection_id=conn.id, target_ref="orders.total_amount", aggregation="AVG"),
        conn,
        db,
    )
    assert res_avg.value == 250.0

    # 3. MIN(total_amount) = 100
    res_min = MetricExecutor.execute(
        MetricRequest(connection_id=conn.id, target_ref="orders.total_amount", aggregation="MIN"),
        conn,
        db,
    )
    assert res_min.value == 100.0

    # 4. MAX(total_amount) = 400
    res_max = MetricExecutor.execute(
        MetricRequest(connection_id=conn.id, target_ref="orders.total_amount", aggregation="MAX"),
        conn,
        db,
    )
    assert res_max.value == 400.0

    # 5. COUNT(order_id) = 4
    res_cnt = MetricExecutor.execute(
        MetricRequest(connection_id=conn.id, target_ref="orders.order_id", aggregation="COUNT"),
        conn,
        db,
    )
    assert res_cnt.value == 4

    # 6. COUNT_DISTINCT(customer_id) = 3 (customers: 10, 20, 30)
    res_cnt_dist = MetricExecutor.execute(
        MetricRequest(connection_id=conn.id, target_ref="orders.customer_id", aggregation="COUNT_DISTINCT"),
        conn,
        db,
    )
    assert res_cnt_dist.value == 3


def test_row_count_wildcards_and_legacy_all(metric_fixture):
    """
    Proves that COUNT(*) and legacy COUNT(orders.all) return row counts (4).
    """
    db = metric_fixture["db"]
    conn = metric_fixture["db_conn"]

    res_star = MetricExecutor.execute(
        MetricRequest(
            connection_id=conn.id,
            target_ref="orders.*",
            aggregation="COUNT",
        ),
        conn,
        db,
    )
    assert res_star.value == 4

    res_all = MetricExecutor.execute(
        MetricRequest(
            connection_id=conn.id,
            target_ref="orders.all",
            aggregation="COUNT",
        ),
        conn,
        db,
    )
    assert res_all.value == 4


def test_parameterized_filter_execution(metric_fixture):
    """
    Proves that filters with bound parameters execute safely and accurately:
    SUM(total_amount) WHERE status = 'completed' -> 100 + 200 = 300
    """
    db = metric_fixture["db"]
    conn = metric_fixture["db_conn"]

    req = MetricRequest(
        connection_id=conn.id,
        target_ref="orders.total_amount",
        aggregation="SUM",
        filters=[MetricFilter(column="orders.status", operator="=", value="completed")],
    )
    res = MetricExecutor.execute(req, conn, db)
    assert res.value == 300.0
    assert ":flt_0" in res.sql
    assert "'completed'" not in res.sql  # Proves bound parameter was used, no string injection!


def test_dimension_breakdown_execution(metric_fixture):
    """
    Proves dimensional breakdown:
    SUM(total_amount) GROUP BY orders.status
    """
    db = metric_fixture["db"]
    conn = metric_fixture["db_conn"]

    req = MetricRequest(
        connection_id=conn.id,
        target_ref="orders.total_amount",
        aggregation="SUM",
        dimension_ref="orders.status",
    )
    res = MetricExecutor.execute(req, conn, db)
    assert res.is_scalar is False
    assert res.data is not None

    status_map = {item["dimension"]: item["value"] for item in res.data}
    assert status_map["completed"] == 300.0
    assert status_map["shipped"] == 300.0
    assert status_map["cancelled"] == 400.0


# ==============================================================================
# SECTION 2: NEGATIVE SAFETY TESTS
# ==============================================================================

def test_reject_sum_and_avg_on_identifiers(metric_fixture):
    """
    Identifiers (PK, FK, ID, UUID) must reject SUM and AVG.
    """
    db = metric_fixture["db"]
    conn = metric_fixture["db_conn"]

    # SUM(order_id)
    with pytest.raises(ValueError) as ex1:
        MetricExecutor.execute(
            MetricRequest(connection_id=conn.id, target_ref="orders.order_id", aggregation="SUM"),
            conn,
            db,
        )
    assert "Cannot apply 'SUM' to identifier column" in str(ex1.value)

    # AVG(order_id)
    with pytest.raises(ValueError) as ex2:
        MetricExecutor.execute(
            MetricRequest(connection_id=conn.id, target_ref="orders.order_id", aggregation="AVG"),
            conn,
            db,
        )
    assert "Cannot apply 'AVG' to identifier column" in str(ex2.value)

    # SUM(customer_id)
    with pytest.raises(ValueError) as ex3:
        MetricExecutor.execute(
            MetricRequest(connection_id=conn.id, target_ref="orders.customer_id", aggregation="SUM"),
            conn,
            db,
        )
    assert "Cannot apply 'SUM' to identifier column" in str(ex3.value)


def test_reject_sum_on_percentages_and_rates(metric_fixture):
    """
    Non-additive measures (percentages, rates, ratios) must reject SUM.
    """
    db = metric_fixture["db"]
    conn = metric_fixture["db_conn"]

    with pytest.raises(ValueError) as ex1:
        MetricExecutor.execute(
            MetricRequest(connection_id=conn.id, target_ref="orders.margin_pct", aggregation="SUM"),
            conn,
            db,
        )
    assert "Cannot apply SUM to non-additive ratio/rate/percentage" in str(ex1.value)

    with pytest.raises(ValueError) as ex2:
        MetricExecutor.execute(
            MetricRequest(connection_id=conn.id, target_ref="orders.error_rate", aggregation="SUM"),
            conn,
            db,
        )
    assert "Cannot apply SUM to non-additive ratio/rate/percentage" in str(ex2.value)


def test_reject_unsupported_aggregation(metric_fixture):
    """
    Unsupported aggregations (like MEDIAN, MODE, STDDEV) must be rejected with an error.
    Never silently converted to SUM.
    """
    db = metric_fixture["db"]
    conn = metric_fixture["db_conn"]

    with pytest.raises(ValueError) as ex:
        MetricExecutor.execute(
            MetricRequest(connection_id=conn.id, target_ref="orders.total_amount", aggregation="MEDIAN"),
            conn,
            db,
        )
    assert "Unsupported aggregation 'MEDIAN'" in str(ex.value)


def test_reject_wildcards_on_arithmetic_aggregations(metric_fixture):
    """
    Wildcards (*, all) are only valid with COUNT. SUM(*), AVG(*), MIN(*), etc. must be rejected.
    """
    db = metric_fixture["db"]
    conn = metric_fixture["db_conn"]

    for forbidden_agg in ["SUM", "AVG", "MIN", "MAX", "COUNT_DISTINCT"]:
        with pytest.raises(ValueError) as ex:
            MetricExecutor.execute(
                MetricRequest(connection_id=conn.id, target_ref="orders.*", aggregation=forbidden_agg),
                conn,
                db,
            )
        assert "is only valid for COUNT aggregation" in str(ex.value)


def test_reject_unqualified_target(metric_fixture):
    """
    Bare unqualified target references must be rejected.
    """
    db = metric_fixture["db"]
    conn = metric_fixture["db_conn"]

    with pytest.raises(ValueError) as ex:
        MetricExecutor.execute(
            MetricRequest(connection_id=conn.id, target_ref="total_amount", aggregation="SUM"),
            conn,
            db,
        )
    assert "Qualified column reference required" in str(ex.value)


def test_reject_unknown_table_or_column(metric_fixture):
    """
    Tables or columns not registered in SchemaRegistry must be rejected.
    """
    db = metric_fixture["db"]
    conn = metric_fixture["db_conn"]

    # Unknown table
    with pytest.raises(ValueError) as ex1:
        MetricExecutor.execute(
            MetricRequest(connection_id=conn.id, target_ref="customers.total_amount", aggregation="SUM"),
            conn,
            db,
        )
    assert "Table 'customers' does not exist in verified SchemaRegistry" in str(ex1.value)

    # Unknown column
    with pytest.raises(ValueError) as ex2:
        MetricExecutor.execute(
            MetricRequest(connection_id=conn.id, target_ref="orders.fake_column", aggregation="SUM"),
            conn,
            db,
        )
    assert "Column 'fake_column' does not exist in table 'orders'" in str(ex2.value)


def test_reject_cross_table_metrics_without_relationship_path(metric_fixture):
    """
    Phase 1.5B rejects cross-table dimensions without automatic unvalidated joins.
    """
    db = metric_fixture["db"]
    conn = metric_fixture["db_conn"]

    with pytest.raises(ValueError) as ex:
        MetricExecutor.execute(
            MetricRequest(
                connection_id=conn.id,
                target_ref="orders.total_amount",
                aggregation="SUM",
                dimension_ref="customers.region",
            ),
            conn,
            db,
        )
    assert "Cross-table metric requires a validated relationship path" in str(ex.value)


def test_reject_unauthorized_cross_tenant_execution(metric_fixture):
    """
    Executor must enforce tenant scoping when tenant_id is provided.
    """
    db = metric_fixture["db"]
    conn = metric_fixture["db_conn"]

    with pytest.raises(ValueError) as ex:
        MetricExecutor.execute(
            MetricRequest(
                connection_id=conn.id,
                target_ref="orders.total_amount",
                aggregation="SUM",
                tenant_id=999999,  # Intruder tenant
            ),
            conn,
            db,
        )
    assert "Unauthorized" in str(ex.value)


# ==============================================================================
# SECTION 3: DIRECT SEMANTIC POLICY UNIT TESTS
# ==============================================================================

def test_direct_semantic_policy_unit_tests():
    """
    Tests validate_metric_aggregation directly across all semantic categories.
    """
    # 1. Primary Key / Identifier
    pk_reg = models.SchemaRegistry(
        table_name="orders",
        column_name="order_id",
        data_type="INTEGER",
        semantic_type="ID",
        is_primary_key=True,
    )
    with pytest.raises(ValueError, match="Cannot apply 'SUM' to identifier column"):
        validate_metric_aggregation("orders.order_id", "SUM", pk_reg)

    with pytest.raises(ValueError, match="Cannot apply 'AVG' to identifier column"):
        validate_metric_aggregation("orders.order_id", "AVG", pk_reg)

    # COUNT and COUNT_DISTINCT are allowed on PK
    validate_metric_aggregation("orders.order_id", "COUNT", pk_reg)
    validate_metric_aggregation("orders.order_id", "COUNT_DISTINCT", pk_reg)

    # 2. Percentage / Rate / Ratio
    pct_reg = models.SchemaRegistry(
        table_name="orders",
        column_name="margin_pct",
        data_type="FLOAT",
        semantic_type="PERCENTAGE",
        is_measure=True,
    )
    with pytest.raises(ValueError, match="Cannot apply SUM to non-additive ratio/rate/percentage"):
        validate_metric_aggregation("orders.margin_pct", "SUM", pct_reg)

    # AVG, MIN, MAX are allowed on percentages
    validate_metric_aggregation("orders.margin_pct", "AVG", pct_reg)
    validate_metric_aggregation("orders.margin_pct", "MAX", pct_reg)

    # Column name regex signal detection without explicit semantic type
    rate_col_reg = models.SchemaRegistry(
        table_name="system",
        column_name="failure_rate",
        data_type="FLOAT",
        semantic_type="NUMERIC_MEASURE",
        is_measure=True,
    )
    with pytest.raises(ValueError, match="Cannot apply SUM to non-additive ratio/rate/percentage"):
        validate_metric_aggregation("system.failure_rate", "SUM", rate_col_reg)

    # 3. Text / Category
    cat_reg = models.SchemaRegistry(
        table_name="orders",
        column_name="customer_category",
        data_type="VARCHAR",
        semantic_type="CATEGORY",
        is_dimension=True,
    )
    with pytest.raises(ValueError, match="Cannot apply arithmetic aggregation 'SUM' to text/categorical column"):
        validate_metric_aggregation("orders.customer_category", "SUM", cat_reg)

    validate_metric_aggregation("orders.customer_category", "COUNT", cat_reg)
    validate_metric_aggregation("orders.customer_category", "COUNT_DISTINCT", cat_reg)

    # 4. Date / Temporal
    date_reg = models.SchemaRegistry(
        table_name="orders",
        column_name="created_at",
        data_type="DATETIME",
        semantic_type="DATETIME",
        is_time_axis=True,
    )
    with pytest.raises(ValueError, match="Cannot apply arithmetic aggregation 'SUM' to temporal column"):
        validate_metric_aggregation("orders.created_at", "SUM", date_reg)

    validate_metric_aggregation("orders.created_at", "MIN", date_reg)
    validate_metric_aggregation("orders.created_at", "MAX", date_reg)

    # 5. Currency / Valid Numeric Measure
    curr_reg = models.SchemaRegistry(
        table_name="orders",
        column_name="total_amount",
        data_type="DECIMAL",
        semantic_type="CURRENCY/AMOUNT",
        is_measure=True,
    )
    validate_metric_aggregation("orders.total_amount", "SUM", curr_reg)
    validate_metric_aggregation("orders.total_amount", "AVG", curr_reg)
    validate_metric_aggregation("orders.total_amount", "MIN", curr_reg)
    validate_metric_aggregation("orders.total_amount", "MAX", curr_reg)

    # 6. Unsupported aggregation
    with pytest.raises(ValueError, match="Unsupported aggregation 'GEOMETRIC_MEAN'"):
        validate_metric_aggregation("orders.total_amount", "GEOMETRIC_MEAN", curr_reg)

