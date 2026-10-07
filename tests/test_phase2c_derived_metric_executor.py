import ast
import os
import sys
from typing import cast, Any
from unittest.mock import patch
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Setup path so imports work directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

import models
from database import Base
from services.db_utils import get_connection_url
from services import db_pool
from services.metric_executor import (
    MetricExecutor,
    MetricFilter,
    MetricResult,
)
from services.metric_recipes import (
    AtomicMetricOperand,
    AtomicMetricRecipe,
    DifferenceMetricRecipe,
    MetricRecipeValidationError,
    RatioMetricRecipe,
)
from services.derived_metric_executor import (
    DerivedMetricExecutionError,
    execute_metric_recipe,
)


@pytest.fixture(scope="module")
def execution_fixture():
    """
    Sets up a deterministic SQLite database with the exact prompt test dataset:
    orders:
      order_id | customer_id | total_amount | total_cost | status
      1        | 10          | 100          | 60         | completed
      2        | 10          | 200          | 100        | completed
      3        | 20          | 300          | 180        | shipped
      4        | 30          | 400          | 210        | cancelled

    customers:
      id       | name
      10       | Alice
      20       | Bob
      30       | Charlie
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSession()

    with engine.connect() as conn:
        conn.execute(
            text("""
            CREATE TABLE orders (
                order_id INTEGER PRIMARY KEY,
                customer_id INTEGER NOT NULL,
                total_amount REAL NOT NULL,
                total_cost REAL NOT NULL,
                status TEXT NOT NULL
            );
        """)
        )
        conn.execute(
            text("""
            CREATE TABLE customers (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );
        """)
        )
        conn.execute(
            text("""
            INSERT INTO orders (order_id, customer_id, total_amount, total_cost, status)
            VALUES 
                (1, 10, 100, 60, 'completed'),
                (2, 10, 200, 100, 'completed'),
                (3, 20, 300, 180, 'shipped'),
                (4, 30, 400, 210, 'cancelled');
        """)
        )
        conn.execute(
            text("""
            INSERT INTO customers (id, name)
            VALUES 
                (10, 'Alice'),
                (20, 'Bob'),
                (30, 'Charlie');
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
    conn_url = get_connection_url(db_conn)
    db_pool._engine_cache[conn_url] = engine

    # Seed SchemaRegistry for orders and customers
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
            column_name="total_cost",
            data_type="REAL",
            semantic_type="CURRENCY/AMOUNT",
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
        models.SchemaRegistry(
            connection_id=db_conn.id,
            table_name="customers",
            column_name="id",
            data_type="INTEGER",
            semantic_type="ID",
            is_primary_key=True,
            is_measure=False,
            is_dimension=False,
        ),
        models.SchemaRegistry(
            connection_id=db_conn.id,
            table_name="customers",
            column_name="name",
            data_type="TEXT",
            semantic_type="TEXT",
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


# ============================================================
# 1. ATOMIC RECIPE EXECUTION (SUM & COUNT_DISTINCT)
# ============================================================

def test_atomic_sum_executes_through_metric_executor(execution_fixture):
    db = execution_fixture["db"]
    tenant = execution_fixture["tenant"]
    db_conn = execution_fixture["db_conn"]

    recipe = AtomicMetricRecipe(
        metric_id="total_revenue",
        title="Total Revenue",
        format="currency",
        operand=AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="SUM",
        ),
    )

    result = execute_metric_recipe(
        recipe=recipe,
        connection_id=db_conn.id,
        tenant_id=tenant.id,
        db_conn=db_conn,
        db=db,
    )

    assert result.metric_id == "total_revenue"
    assert result.metric_type == "atomic"
    assert result.title == "Total Revenue"
    assert result.format == "currency"
    assert result.status == "ok"
    assert result.value == 1000.0
    assert len(result.components) == 1
    assert result.components[0].role == "operand"
    assert result.components[0].target_ref == "orders.total_amount"
    assert result.components[0].aggregation == "SUM"
    assert result.components[0].value == 1000.0


def test_atomic_count_distinct_executes_correctly(execution_fixture):
    db = execution_fixture["db"]
    tenant = execution_fixture["tenant"]
    db_conn = execution_fixture["db_conn"]

    recipe = AtomicMetricRecipe(
        metric_id="total_orders",
        title="Total Orders",
        format="number",
        operand=AtomicMetricOperand(
            target_ref="orders.order_id",
            aggregation="COUNT_DISTINCT",
        ),
    )

    result = execute_metric_recipe(
        recipe=recipe,
        connection_id=db_conn.id,
        tenant_id=tenant.id,
        db_conn=db_conn,
        db=db,
    )

    assert result.metric_id == "total_orders"
    assert result.status == "ok"
    assert result.value == 4
    assert len(result.components) == 1
    assert result.components[0].role == "operand"
    assert result.components[0].value == 4


# ============================================================
# 2. RATIO & DIFFERENCE EXACT RESULTS
# ============================================================

def test_aov_ratio_equals_250(execution_fixture):
    db = execution_fixture["db"]
    tenant = execution_fixture["tenant"]
    db_conn = execution_fixture["db_conn"]

    recipe = RatioMetricRecipe(
        metric_id="aov",
        title="Average Order Value",
        format="currency",
        numerator=AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="SUM",
        ),
        denominator=AtomicMetricOperand(
            target_ref="orders.order_id",
            aggregation="COUNT_DISTINCT",
        ),
        zero_division="null",
    )

    result = execute_metric_recipe(
        recipe=recipe,
        connection_id=db_conn.id,
        tenant_id=tenant.id,
        db_conn=db_conn,
        db=db,
    )

    assert result.metric_id == "aov"
    assert result.metric_type == "ratio"
    assert result.title == "Average Order Value"
    assert result.format == "currency"
    assert result.status == "ok"
    assert result.value == 250.0  # 1000 / 4

    assert len(result.components) == 2
    num_comp = next(c for c in result.components if c.role == "numerator")
    den_comp = next(c for c in result.components if c.role == "denominator")
    assert num_comp.target_ref == "orders.total_amount"
    assert num_comp.aggregation == "SUM"
    assert num_comp.value == 1000.0
    assert den_comp.target_ref == "orders.order_id"
    assert den_comp.aggregation == "COUNT_DISTINCT"
    assert den_comp.value == 4


def test_gross_profit_difference_equals_450(execution_fixture):
    db = execution_fixture["db"]
    tenant = execution_fixture["tenant"]
    db_conn = execution_fixture["db_conn"]

    recipe = DifferenceMetricRecipe(
        metric_id="gross_profit",
        title="Gross Profit",
        format="currency",
        left=AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="SUM",
        ),
        right=AtomicMetricOperand(
            target_ref="orders.total_cost",
            aggregation="SUM",
        ),
    )

    result = execute_metric_recipe(
        recipe=recipe,
        connection_id=db_conn.id,
        tenant_id=tenant.id,
        db_conn=db_conn,
        db=db,
    )

    assert result.metric_id == "gross_profit"
    assert result.metric_type == "difference"
    assert result.title == "Gross Profit"
    assert result.status == "ok"
    assert result.value == 450.0  # 1000 - 550

    assert len(result.components) == 2
    left_comp = next(c for c in result.components if c.role == "left")
    right_comp = next(c for c in result.components if c.role == "right")
    assert left_comp.value == 1000.0
    assert right_comp.value == 550.0


# ============================================================
# 3. FILTERED EXECUTION
# ============================================================

def test_completed_only_aov_equals_150(execution_fixture):
    db = execution_fixture["db"]
    tenant = execution_fixture["tenant"]
    db_conn = execution_fixture["db_conn"]

    recipe = RatioMetricRecipe(
        metric_id="aov",
        title="Average Order Value",
        format="currency",
        numerator=AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="SUM",
        ),
        denominator=AtomicMetricOperand(
            target_ref="orders.order_id",
            aggregation="COUNT_DISTINCT",
        ),
        zero_division="null",
    )

    filters = [
        MetricFilter(
            column="orders.status",
            operator="=",
            value="completed",
        )
    ]

    result = execute_metric_recipe(
        recipe=recipe,
        connection_id=db_conn.id,
        tenant_id=tenant.id,
        db_conn=db_conn,
        db=db,
        filters=filters,
    )

    assert result.status == "ok"
    assert result.value == 150.0  # 300 / 2
    assert result.components[0].value == 300.0
    assert result.components[1].value == 2


def test_completed_only_gross_profit_equals_140(execution_fixture):
    db = execution_fixture["db"]
    tenant = execution_fixture["tenant"]
    db_conn = execution_fixture["db_conn"]

    recipe = DifferenceMetricRecipe(
        metric_id="gross_profit",
        title="Gross Profit",
        format="currency",
        left=AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="SUM",
        ),
        right=AtomicMetricOperand(
            target_ref="orders.total_cost",
            aggregation="SUM",
        ),
    )

    filters = [
        MetricFilter(
            column="orders.status",
            operator="=",
            value="completed",
        )
    ]

    result = execute_metric_recipe(
        recipe=recipe,
        connection_id=db_conn.id,
        tenant_id=tenant.id,
        db_conn=db_conn,
        db=db,
        filters=filters,
    )

    assert result.status == "ok"
    assert result.value == 140.0  # 300 - 160
    assert result.components[0].value == 300.0
    assert result.components[1].value == 160.0


def test_same_runtime_filters_reach_both_ratio_operands(execution_fixture):
    db = execution_fixture["db"]
    tenant = execution_fixture["tenant"]
    db_conn = execution_fixture["db_conn"]

    recipe = RatioMetricRecipe(
        metric_id="aov",
        title="Average Order Value",
        format="currency",
        numerator=AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="SUM",
        ),
        denominator=AtomicMetricOperand(
            target_ref="orders.order_id",
            aggregation="COUNT_DISTINCT",
        ),
        zero_division="null",
    )

    filters = [
        MetricFilter(column="orders.status", operator="=", value="shipped")
    ]

    with patch.object(MetricExecutor, "execute", wraps=MetricExecutor.execute) as spy_execute:
        result = execute_metric_recipe(
            recipe=recipe,
            connection_id=db_conn.id,
            tenant_id=tenant.id,
            db_conn=db_conn,
            db=db,
            filters=filters,
        )

        assert spy_execute.call_count == 2
        req_num = spy_execute.call_args_list[0][0][0]
        req_den = spy_execute.call_args_list[1][0][0]

        assert req_num.filters == filters
        assert req_den.filters == filters
        assert result.value == 300.0 / 1  # order 3 total_amount 300, 1 order


def test_same_runtime_filters_reach_both_difference_operands(execution_fixture):
    db = execution_fixture["db"]
    tenant = execution_fixture["tenant"]
    db_conn = execution_fixture["db_conn"]

    recipe = DifferenceMetricRecipe(
        metric_id="gross_profit",
        title="Gross Profit",
        format="currency",
        left=AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="SUM",
        ),
        right=AtomicMetricOperand(
            target_ref="orders.total_cost",
            aggregation="SUM",
        ),
    )

    filters = [
        MetricFilter(column="orders.status", operator="=", value="cancelled")
    ]

    with patch.object(MetricExecutor, "execute", wraps=MetricExecutor.execute) as spy_execute:
        result = execute_metric_recipe(
            recipe=recipe,
            connection_id=db_conn.id,
            tenant_id=tenant.id,
            db_conn=db_conn,
            db=db,
            filters=filters,
        )

        assert spy_execute.call_count == 2
        req_left = spy_execute.call_args_list[0][0][0]
        req_right = spy_execute.call_args_list[1][0][0]

        assert req_left.filters == filters
        assert req_right.filters == filters
        assert result.value == 400.0 - 210.0  # 190.0


# ============================================================
# 4. ZERO AND NULL DIVISION / NO DATA SEMANTICS
# ============================================================

def test_denominator_zero_produces_undefined_and_null(execution_fixture):
    db = execution_fixture["db"]
    tenant = execution_fixture["tenant"]
    db_conn = execution_fixture["db_conn"]

    recipe = RatioMetricRecipe(
        metric_id="aov",
        title="Average Order Value",
        format="currency",
        numerator=AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="SUM",
        ),
        denominator=AtomicMetricOperand(
            target_ref="orders.order_id",
            aggregation="COUNT_DISTINCT",
        ),
        zero_division="null",
    )

    # Mock denominator returning 0
    with patch.object(MetricExecutor, "execute") as mock_exec:
        mock_exec.side_effect = [
            MetricResult(target="orders.total_amount", aggregation="SUM", is_scalar=True, value=100.0),
            MetricResult(target="orders.order_id", aggregation="COUNT_DISTINCT", is_scalar=True, value=0),
        ]

        result = execute_metric_recipe(
            recipe=recipe,
            connection_id=db_conn.id,
            tenant_id=tenant.id,
            db_conn=db_conn,
            db=db,
        )

        assert result.status == "undefined"
        assert result.value is None


def test_ratio_does_not_replace_zero_denominator_with_one(execution_fixture):
    db = execution_fixture["db"]
    tenant = execution_fixture["tenant"]
    db_conn = execution_fixture["db_conn"]

    recipe = RatioMetricRecipe(
        metric_id="ratio_metric",
        title="Ratio Metric",
        format="ratio",
        numerator=AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="SUM",
        ),
        denominator=AtomicMetricOperand(
            target_ref="orders.order_id",
            aggregation="COUNT_DISTINCT",
        ),
        zero_division="null",
    )

    with patch.object(MetricExecutor, "execute") as mock_exec:
        mock_exec.side_effect = [
            MetricResult(target="orders.total_amount", aggregation="SUM", is_scalar=True, value=500.0),
            MetricResult(target="orders.order_id", aggregation="COUNT_DISTINCT", is_scalar=True, value=0),
        ]

        result = execute_metric_recipe(
            recipe=recipe,
            connection_id=db_conn.id,
            tenant_id=tenant.id,
            db_conn=db_conn,
            db=db,
        )

        # Must NOT evaluate to 500.0 / 1
        assert result.status == "undefined"
        assert result.value is None


def test_numerator_none_produces_no_data_and_null(execution_fixture):
    db = execution_fixture["db"]
    tenant = execution_fixture["tenant"]
    db_conn = execution_fixture["db_conn"]

    recipe = RatioMetricRecipe(
        metric_id="aov",
        title="Average Order Value",
        format="currency",
        numerator=AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="SUM",
        ),
        denominator=AtomicMetricOperand(
            target_ref="orders.order_id",
            aggregation="COUNT_DISTINCT",
        ),
        zero_division="null",
    )

    with patch.object(MetricExecutor, "execute") as mock_exec:
        mock_exec.side_effect = [
            MetricResult(target="orders.total_amount", aggregation="SUM", is_scalar=True, value=None),
            MetricResult(target="orders.order_id", aggregation="COUNT_DISTINCT", is_scalar=True, value=4),
        ]

        result = execute_metric_recipe(
            recipe=recipe,
            connection_id=db_conn.id,
            tenant_id=tenant.id,
            db_conn=db_conn,
            db=db,
        )

        assert result.status == "no_data"
        assert result.value is None


def test_denominator_none_produces_no_data_and_null(execution_fixture):
    db = execution_fixture["db"]
    tenant = execution_fixture["tenant"]
    db_conn = execution_fixture["db_conn"]

    recipe = RatioMetricRecipe(
        metric_id="aov",
        title="Average Order Value",
        format="currency",
        numerator=AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="SUM",
        ),
        denominator=AtomicMetricOperand(
            target_ref="orders.order_id",
            aggregation="COUNT_DISTINCT",
        ),
        zero_division="null",
    )

    with patch.object(MetricExecutor, "execute") as mock_exec:
        mock_exec.side_effect = [
            MetricResult(target="orders.total_amount", aggregation="SUM", is_scalar=True, value=100.0),
            MetricResult(target="orders.order_id", aggregation="COUNT_DISTINCT", is_scalar=True, value=None),
        ]

        result = execute_metric_recipe(
            recipe=recipe,
            connection_id=db_conn.id,
            tenant_id=tenant.id,
            db_conn=db_conn,
            db=db,
        )

        assert result.status == "no_data"
        assert result.value is None


def test_difference_operand_none_produces_no_data_and_null(execution_fixture):
    db = execution_fixture["db"]
    tenant = execution_fixture["tenant"]
    db_conn = execution_fixture["db_conn"]

    recipe = DifferenceMetricRecipe(
        metric_id="gross_profit",
        title="Gross Profit",
        format="currency",
        left=AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="SUM",
        ),
        right=AtomicMetricOperand(
            target_ref="orders.total_cost",
            aggregation="SUM",
        ),
    )

    # Left is None
    with patch.object(MetricExecutor, "execute") as mock_exec:
        mock_exec.side_effect = [
            MetricResult(target="orders.total_amount", aggregation="SUM", is_scalar=True, value=None),
            MetricResult(target="orders.total_cost", aggregation="SUM", is_scalar=True, value=200.0),
        ]

        res_left = execute_metric_recipe(
            recipe=recipe,
            connection_id=db_conn.id,
            tenant_id=tenant.id,
            db_conn=db_conn,
            db=db,
        )
        assert res_left.status == "no_data"
        assert res_left.value is None

    # Right is None
    with patch.object(MetricExecutor, "execute") as mock_exec:
        mock_exec.side_effect = [
            MetricResult(target="orders.total_amount", aggregation="SUM", is_scalar=True, value=500.0),
            MetricResult(target="orders.total_cost", aggregation="SUM", is_scalar=True, value=None),
        ]

        res_right = execute_metric_recipe(
            recipe=recipe,
            connection_id=db_conn.id,
            tenant_id=tenant.id,
            db_conn=db_conn,
            db=db,
        )
        assert res_right.status == "no_data"
        assert res_right.value is None


def test_legitimate_atomic_count_zero_remains_0(execution_fixture):
    db = execution_fixture["db"]
    tenant = execution_fixture["tenant"]
    db_conn = execution_fixture["db_conn"]

    recipe = AtomicMetricRecipe(
        metric_id="empty_count",
        title="Empty Count",
        format="number",
        operand=AtomicMetricOperand(
            target_ref="orders.order_id",
            aggregation="COUNT",
        ),
    )

    filters = [
        MetricFilter(column="orders.status", operator="=", value="nonexistent_status_xyz")
    ]

    result = execute_metric_recipe(
        recipe=recipe,
        connection_id=db_conn.id,
        tenant_id=tenant.id,
        db_conn=db_conn,
        db=db,
        filters=filters,
    )

    assert result.status == "ok"
    assert result.value == 0
    assert result.components[0].value == 0


def test_legitimate_difference_result_zero_remains_0(execution_fixture):
    db = execution_fixture["db"]
    tenant = execution_fixture["tenant"]
    db_conn = execution_fixture["db_conn"]

    recipe = DifferenceMetricRecipe(
        metric_id="zero_diff",
        title="Zero Difference",
        format="currency",
        left=AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="SUM",
        ),
        right=AtomicMetricOperand(
            target_ref="orders.total_cost",
            aggregation="SUM",
        ),
    )

    with patch.object(MetricExecutor, "execute") as mock_exec:
        mock_exec.side_effect = [
            MetricResult(target="orders.total_amount", aggregation="SUM", is_scalar=True, value=250.0),
            MetricResult(target="orders.total_cost", aggregation="SUM", is_scalar=True, value=250.0),
        ]

        result = execute_metric_recipe(
            recipe=recipe,
            connection_id=db_conn.id,
            tenant_id=tenant.id,
            db_conn=db_conn,
            db=db,
        )

        assert result.status == "ok"
        assert result.value == 0.0


def test_none_is_not_fabricated_as_zero(execution_fixture):
    db = execution_fixture["db"]
    tenant = execution_fixture["tenant"]
    db_conn = execution_fixture["db_conn"]

    recipe = AtomicMetricRecipe(
        metric_id="empty_sum",
        title="Empty Sum",
        format="currency",
        operand=AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="SUM",
        ),
    )

    # When MetricExecutor returns None (no data), derived executor must NEVER fabricate 0
    with patch.object(MetricExecutor, "execute") as mock_exec:
        mock_exec.return_value = MetricResult(
            target="orders.total_amount",
            aggregation="SUM",
            is_scalar=True,
            value=None,
        )

        result = execute_metric_recipe(
            recipe=recipe,
            connection_id=db_conn.id,
            tenant_id=tenant.id,
            db_conn=db_conn,
            db=db,
        )

        assert result.status == "no_data"
        assert result.value is None


# ============================================================
# 5. DEFENSE CHECKS: NON-NUMERIC, NON-SCALAR, SECURITY
# ============================================================

def test_non_numeric_ratio_operand_rejected(execution_fixture):
    db = execution_fixture["db"]
    tenant = execution_fixture["tenant"]
    db_conn = execution_fixture["db_conn"]

    recipe = RatioMetricRecipe(
        metric_id="bad_ratio",
        title="Bad Ratio",
        format="ratio",
        numerator=AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="SUM",
        ),
        denominator=AtomicMetricOperand(
            target_ref="orders.order_id",
            aggregation="COUNT_DISTINCT",
        ),
        zero_division="null",
    )

    # Case A: boolean returned
    with patch.object(MetricExecutor, "execute") as mock_exec:
        mock_exec.side_effect = [
            MetricResult(target="orders.total_amount", aggregation="SUM", is_scalar=True, value=True),
            MetricResult(target="orders.order_id", aggregation="COUNT_DISTINCT", is_scalar=True, value=4),
        ]
        with pytest.raises(DerivedMetricExecutionError, match="returned a boolean value"):
            execute_metric_recipe(
                recipe=recipe,
                connection_id=db_conn.id,
                tenant_id=tenant.id,
                db_conn=db_conn,
                db=db,
            )

    # Case B: string returned
    with patch.object(MetricExecutor, "execute") as mock_exec:
        mock_exec.side_effect = [
            MetricResult(target="orders.total_amount", aggregation="SUM", is_scalar=True, value=cast(Any, "non_numeric_string")),
            MetricResult(target="orders.order_id", aggregation="COUNT_DISTINCT", is_scalar=True, value=4),
        ]
        with pytest.raises(DerivedMetricExecutionError, match="did not return a numeric value"):
            execute_metric_recipe(
                recipe=recipe,
                connection_id=db_conn.id,
                tenant_id=tenant.id,
                db_conn=db_conn,
                db=db,
            )


def test_non_numeric_difference_operand_rejected(execution_fixture):
    db = execution_fixture["db"]
    tenant = execution_fixture["tenant"]
    db_conn = execution_fixture["db_conn"]

    recipe = DifferenceMetricRecipe(
        metric_id="bad_diff",
        title="Bad Difference",
        format="currency",
        left=AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="SUM",
        ),
        right=AtomicMetricOperand(
            target_ref="orders.total_cost",
            aggregation="SUM",
        ),
    )

    with patch.object(MetricExecutor, "execute") as mock_exec:
        mock_exec.side_effect = [
            MetricResult(target="orders.total_amount", aggregation="SUM", is_scalar=True, value=100.0),
            MetricResult(target="orders.total_cost", aggregation="SUM", is_scalar=True, value=False),  # boolean!
        ]
        with pytest.raises(DerivedMetricExecutionError, match="returned a boolean value"):
            execute_metric_recipe(
                recipe=recipe,
                connection_id=db_conn.id,
                tenant_id=tenant.id,
                db_conn=db_conn,
                db=db,
            )


def test_non_scalar_operand_result_rejected(execution_fixture):
    db = execution_fixture["db"]
    tenant = execution_fixture["tenant"]
    db_conn = execution_fixture["db_conn"]

    recipe = AtomicMetricRecipe(
        metric_id="bad_scalar",
        title="Bad Scalar",
        format="currency",
        operand=AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="SUM",
        ),
    )

    with patch.object(MetricExecutor, "execute") as mock_exec:
        mock_exec.return_value = MetricResult(
            target="orders.total_amount",
            aggregation="SUM",
            is_scalar=False,  # Non-scalar!
            data=[{"val": 100}],
        )

        with pytest.raises(DerivedMetricExecutionError, match="must return scalar results"):
            execute_metric_recipe(
                recipe=recipe,
                connection_id=db_conn.id,
                tenant_id=tenant.id,
                db_conn=db_conn,
                db=db,
            )


def test_wrong_tenant_rejected_before_customer_db_execution(execution_fixture):
    db = execution_fixture["db"]
    tenant = execution_fixture["tenant"]
    db_conn = execution_fixture["db_conn"]

    recipe = AtomicMetricRecipe(
        metric_id="total_rev",
        title="Total Rev",
        format="currency",
        operand=AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="SUM",
        ),
    )

    # Requested tenant_id does not match db_conn.tenant_id
    with pytest.raises(DerivedMetricExecutionError, match="does not belong to the requested tenant"):
        execute_metric_recipe(
            recipe=recipe,
            connection_id=db_conn.id,
            tenant_id=tenant.id + 9999,
            db_conn=db_conn,
            db=db,
        )


def test_wrong_db_conn_rejected(execution_fixture):
    db = execution_fixture["db"]
    tenant = execution_fixture["tenant"]
    db_conn = execution_fixture["db_conn"]

    recipe = AtomicMetricRecipe(
        metric_id="total_rev",
        title="Total Rev",
        format="currency",
        operand=AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="SUM",
        ),
    )

    # Requested connection_id does not match db_conn.id
    with pytest.raises(DerivedMetricExecutionError, match="does not match requested connection"):
        execute_metric_recipe(
            recipe=recipe,
            connection_id=db_conn.id + 9999,
            tenant_id=tenant.id,
            db_conn=db_conn,
            db=db,
        )


def test_recipe_revalidated_before_execution(execution_fixture):
    db = execution_fixture["db"]
    tenant = execution_fixture["tenant"]
    db_conn = execution_fixture["db_conn"]

    # Attempt to execute an invalid recipe: SUM on an identifier column (order_id)
    invalid_recipe = AtomicMetricRecipe(
        metric_id="invalid_sum",
        title="Invalid Sum",
        format="currency",
        operand=AtomicMetricOperand(
            target_ref="orders.order_id",
            aggregation="SUM",
        ),
    )

    with pytest.raises(MetricRecipeValidationError, match="Cannot apply 'SUM' to identifier column"):
        execute_metric_recipe(
            recipe=invalid_recipe,
            connection_id=db_conn.id,
            tenant_id=tenant.id,
            db_conn=db_conn,
            db=db,
        )


def test_cross_table_derived_recipe_remains_impossible():
    from pydantic import ValidationError

    # Cross-table ratio: numerator orders, denominator customers
    # Must fail immediately at schema validation boundary
    with pytest.raises(ValidationError, match="Cross-table derived metrics require a validated relationship path"):
        RatioMetricRecipe(
            metric_id="cross_table_ratio",
            title="Cross Table Ratio",
            format="ratio",
            numerator=AtomicMetricOperand(
                target_ref="orders.total_amount",
                aggregation="SUM",
            ),
            denominator=AtomicMetricOperand(
                target_ref="customers.id",
                aggregation="COUNT_DISTINCT",
            ),
            zero_division="null",
        )


# ============================================================
# 6. ARCHITECTURAL PURITY & SECURITY AUDIT
# ============================================================

def test_no_raw_sql_in_derived_metric_executor():
    import services.derived_metric_executor as dme
    with open(dme.__file__, "r", encoding="utf-8") as f:
        content = f.read()

    forbidden_tokens = ["text(", "SELECT", "FROM", "WHERE", "JOIN", "GROUP BY", "ORDER BY"]
    for token in forbidden_tokens:
        assert token not in content, f"Forbidden SQL token '{token}' found in derived_metric_executor.py"


def test_no_eval_or_exec_in_derived_metric_executor():
    import services.derived_metric_executor as dme
    with open(dme.__file__, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec"):
                pytest.fail(f"Dangerous call '{node.func.id}' found in derived_metric_executor.py")


def test_no_join_generated(execution_fixture):
    db = execution_fixture["db"]
    tenant = execution_fixture["tenant"]
    db_conn = execution_fixture["db_conn"]

    recipe = RatioMetricRecipe(
        metric_id="aov",
        title="Average Order Value",
        format="currency",
        numerator=AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="SUM",
        ),
        denominator=AtomicMetricOperand(
            target_ref="orders.order_id",
            aggregation="COUNT_DISTINCT",
        ),
        zero_division="null",
    )

    with patch.object(MetricExecutor, "execute", wraps=MetricExecutor.execute) as spy_execute:
        execute_metric_recipe(
            recipe=recipe,
            connection_id=db_conn.id,
            tenant_id=tenant.id,
            db_conn=db_conn,
            db=db,
        )

        for call in spy_execute.call_args_list:
            result = spy_execute.spy_return if hasattr(spy_execute, "spy_return") else None
            # Every atomic query must be single table without joins
            req = call[0][0]
            assert "." in req.target_ref
            table = req.target_ref.split(".")[0]
            assert table == "orders"


def test_metric_executor_call_counts(execution_fixture):
    db = execution_fixture["db"]
    tenant = execution_fixture["tenant"]
    db_conn = execution_fixture["db_conn"]

    atomic = AtomicMetricRecipe(
        metric_id="rev",
        title="Rev",
        format="currency",
        operand=AtomicMetricOperand(target_ref="orders.total_amount", aggregation="SUM"),
    )
    ratio = RatioMetricRecipe(
        metric_id="aov",
        title="AOV",
        format="currency",
        numerator=AtomicMetricOperand(target_ref="orders.total_amount", aggregation="SUM"),
        denominator=AtomicMetricOperand(target_ref="orders.order_id", aggregation="COUNT_DISTINCT"),
        zero_division="null",
    )
    diff = DifferenceMetricRecipe(
        metric_id="profit",
        title="Profit",
        format="currency",
        left=AtomicMetricOperand(target_ref="orders.total_amount", aggregation="SUM"),
        right=AtomicMetricOperand(target_ref="orders.total_cost", aggregation="SUM"),
    )

    with patch.object(MetricExecutor, "execute", wraps=MetricExecutor.execute) as spy_exec:
        execute_metric_recipe(recipe=atomic, connection_id=db_conn.id, tenant_id=tenant.id, db_conn=db_conn, db=db)
        assert spy_exec.call_count == 1

    with patch.object(MetricExecutor, "execute", wraps=MetricExecutor.execute) as spy_exec:
        execute_metric_recipe(recipe=ratio, connection_id=db_conn.id, tenant_id=tenant.id, db_conn=db_conn, db=db)
        assert spy_exec.call_count == 2

    with patch.object(MetricExecutor, "execute", wraps=MetricExecutor.execute) as spy_exec:
        execute_metric_recipe(recipe=diff, connection_id=db_conn.id, tenant_id=tenant.id, db_conn=db_conn, db=db)
        assert spy_exec.call_count == 2


def test_calculation_layer_does_not_round(execution_fixture):
    db = execution_fixture["db"]
    tenant = execution_fixture["tenant"]
    db_conn = execution_fixture["db_conn"]

    recipe = RatioMetricRecipe(
        metric_id="unrounded_ratio",
        title="Unrounded Ratio",
        format="currency",
        numerator=AtomicMetricOperand(target_ref="orders.total_amount", aggregation="SUM"),
        denominator=AtomicMetricOperand(target_ref="orders.order_id", aggregation="COUNT_DISTINCT"),
        zero_division="null",
    )

    with patch.object(MetricExecutor, "execute") as mock_exec:
        # Simulate 1000 / 3
        mock_exec.side_effect = [
            MetricResult(target="orders.total_amount", aggregation="SUM", is_scalar=True, value=1000.0),
            MetricResult(target="orders.order_id", aggregation="COUNT_DISTINCT", is_scalar=True, value=3),
        ]

        result = execute_metric_recipe(
            recipe=recipe,
            connection_id=db_conn.id,
            tenant_id=tenant.id,
            db_conn=db_conn,
            db=db,
        )

        assert result.status == "ok"
        # Must retain full float precision (not rounded to 333.33)
        assert result.value == 1000.0 / 3
        assert result.value == 333.3333333333333


def test_unsupported_recipe_type_raises_error(execution_fixture):
    db = execution_fixture["db"]
    tenant = execution_fixture["tenant"]
    db_conn = execution_fixture["db_conn"]

    class MockUnsupportedRecipe:
        metric_id = "unsupported"
        metric_type = "unsupported"
        title = "Unsupported"
        format = "number"

    with patch("services.derived_metric_executor.validate_recipe_for_connection", return_value=MockUnsupportedRecipe()):
        with pytest.raises(DerivedMetricExecutionError, match="Unsupported MetricRecipe type: MockUnsupportedRecipe"):
            execute_metric_recipe(
                recipe=MockUnsupportedRecipe(),  # type: ignore[arg-type]
                connection_id=db_conn.id,
                tenant_id=tenant.id,
                db_conn=db_conn,
                db=db,
            )

