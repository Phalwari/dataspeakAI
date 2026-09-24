import math
import os
import sys
from unittest.mock import MagicMock, patch
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
    RatioMetricRecipe,
)
from services.derived_metric_executor import (
    DerivedMetricExecutionError,
    _ensure_numeric,
    _get_recipe_table,
    _validate_runtime_filters,
    execute_metric_recipe,
)


@pytest.fixture(scope="module")
def boundary_fixture():
    """
    Sets up a deterministic SQLite database with the standard test dataset:
    orders:
      order_id | customer_id | total_amount | total_cost | status
      1        | 10          | 100          | 60         | completed
      2        | 10          | 200          | 100        | completed
      3        | 20          | 300          | 180        | shipped
      4        | 30          | 400          | 210        | cancelled

    customers:
      id       | name        | region
      10       | Alice       | Dubai
      20       | Bob         | London
      30       | Charlie     | New York
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
                name TEXT NOT NULL,
                region TEXT NOT NULL
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
            INSERT INTO customers (id, name, region)
            VALUES 
                (10, 'Alice', 'Dubai'),
                (20, 'Bob', 'London'),
                (30, 'Charlie', 'New York');
        """)
        )
        conn.commit()

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

    conn_url = get_connection_url(db_conn)
    db_pool._engine_cache[conn_url] = engine

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
        models.SchemaRegistry(
            connection_id=db_conn.id,
            table_name="customers",
            column_name="region",
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


# ============================================================
# 1. SAME-TABLE RUNTIME FILTER ACCEPTED
# ============================================================

def test_same_table_runtime_filter_accepted(boundary_fixture):
    """
    Test 1: same-table runtime filter accepted.
    orders.total_amount recipe + orders.status = "completed" filter
    executes cleanly and returns sum for completed orders (100 + 200 = 300).
    """
    db = boundary_fixture["db"]
    tenant = boundary_fixture["tenant"]
    db_conn = boundary_fixture["db_conn"]

    recipe = AtomicMetricRecipe(
        metric_id="revenue_completed",
        title="Completed Revenue",
        format="currency",
        operand=AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="SUM",
        ),
    )

    flt = MetricFilter(column="orders.status", operator="=", value="completed")

    result = execute_metric_recipe(
        recipe=recipe,
        connection_id=db_conn.id,
        tenant_id=tenant.id,
        db_conn=db_conn,
        db=db,
        filters=[flt],
    )

    assert result.status == "ok"
    assert result.value == 300.0
    assert len(result.components) == 1
    assert result.components[0].value == 300.0


# ============================================================
# 2. SAME-TABLE FILTER REACHES BOTH RATIO OPERANDS
# ============================================================

def test_same_table_filter_reaches_both_ratio_operands(boundary_fixture):
    """
    Test 2: same-table filter reaches both ratio operands.
    AOV = SUM(orders.total_amount) / COUNT(orders.order_id)
    with filter orders.status = "completed"
    Numerator: 100 + 200 = 300
    Denominator: 2
    AOV = 300 / 2 = 150.0
    """
    db = boundary_fixture["db"]
    tenant = boundary_fixture["tenant"]
    db_conn = boundary_fixture["db_conn"]

    recipe = RatioMetricRecipe(
        metric_id="aov",
        title="Average Order Value",
        format="currency",
        zero_division="null",
        numerator=AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="SUM",
        ),
        denominator=AtomicMetricOperand(
            target_ref="orders.order_id",
            aggregation="COUNT",
        ),
    )

    flt = MetricFilter(column="orders.status", operator="=", value="completed")

    result = execute_metric_recipe(
        recipe=recipe,
        connection_id=db_conn.id,
        tenant_id=tenant.id,
        db_conn=db_conn,
        db=db,
        filters=[flt],
    )

    assert result.status == "ok"
    assert result.value == 150.0
    assert len(result.components) == 2
    assert result.components[0].role == "numerator"
    assert result.components[0].value == 300.0
    assert result.components[1].role == "denominator"
    assert result.components[1].value == 2


# ============================================================
# 3. CROSS-TABLE RUNTIME FILTER REJECTED
# ============================================================

def test_cross_table_runtime_filter_rejected(boundary_fixture):
    """
    Test 3: cross-table runtime filter rejected.
    target = orders.total_amount
    filter = customers.region = "Dubai"
    Must raise DerivedMetricExecutionError:
    "Cross-table runtime filters require a validated relationship path."
    """
    db = boundary_fixture["db"]
    tenant = boundary_fixture["tenant"]
    db_conn = boundary_fixture["db_conn"]

    recipe = AtomicMetricRecipe(
        metric_id="revenue",
        title="Total Revenue",
        format="currency",
        operand=AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="SUM",
        ),
    )

    flt = MetricFilter(column="customers.region", operator="=", value="Dubai")

    with pytest.raises(DerivedMetricExecutionError) as exc_info:
        execute_metric_recipe(
            recipe=recipe,
            connection_id=db_conn.id,
            tenant_id=tenant.id,
            db_conn=db_conn,
            db=db,
            filters=[flt],
        )

    assert "Cross-table runtime filters require a validated relationship path." in str(exc_info.value)


# ============================================================
# 4. CROSS-TABLE FILTER REJECTED BEFORE METRICEXECUTOR EXECUTION
# ============================================================

def test_cross_table_filter_rejected_before_metric_executor_customer_db_execution(boundary_fixture):
    """
    Test 4: cross-table filter rejected before MetricExecutor customer DB execution.
    Verifies that MetricExecutor.execute is never invoked when a cross-table filter is supplied.
    """
    db = boundary_fixture["db"]
    tenant = boundary_fixture["tenant"]
    db_conn = boundary_fixture["db_conn"]

    recipe = RatioMetricRecipe(
        metric_id="aov",
        title="Average Order Value",
        format="currency",
        zero_division="null",
        numerator=AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="SUM",
        ),
        denominator=AtomicMetricOperand(
            target_ref="orders.order_id",
            aggregation="COUNT",
        ),
    )

    flt = MetricFilter(column="customers.region", operator="=", value="Dubai")

    with patch.object(MetricExecutor, "execute") as mock_executor:
        with pytest.raises(DerivedMetricExecutionError) as exc_info:
            execute_metric_recipe(
                recipe=recipe,
                connection_id=db_conn.id,
                tenant_id=tenant.id,
                db_conn=db_conn,
                db=db,
                filters=[flt],
            )

        assert "Cross-table runtime filters require a validated relationship path." in str(exc_info.value)
        # Assert MetricExecutor was NEVER called - rejected at the boundary!
        assert mock_executor.call_count == 0


# ============================================================
# 5. UNQUALIFIED RUNTIME FILTER REJECTED
# ============================================================

def test_unqualified_runtime_filter_rejected(boundary_fixture):
    """
    Test 5: unqualified runtime filter rejected.
    filter = status = "completed" (missing 'orders.' prefix)
    Must raise DerivedMetricExecutionError:
    "Runtime metric filters must use qualified table.column references."
    """
    db = boundary_fixture["db"]
    tenant = boundary_fixture["tenant"]
    db_conn = boundary_fixture["db_conn"]

    recipe = AtomicMetricRecipe(
        metric_id="revenue",
        title="Total Revenue",
        format="currency",
        operand=AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="SUM",
        ),
    )

    flt = MetricFilter(column="status", operator="=", value="completed")

    with patch.object(MetricExecutor, "execute") as mock_executor:
        with pytest.raises(DerivedMetricExecutionError) as exc_info:
            execute_metric_recipe(
                recipe=recipe,
                connection_id=db_conn.id,
                tenant_id=tenant.id,
                db_conn=db_conn,
                db=db,
                filters=[flt],
            )

        assert "Runtime metric filters must use qualified table.column references." in str(exc_info.value)
        assert mock_executor.call_count == 0


# ============================================================
# 6. NO FILTER STILL WORKS
# ============================================================

def test_no_filter_still_works(boundary_fixture):
    """
    Test 6: no filter still works.
    filters=None and filters=[] execute normally.
    """
    db = boundary_fixture["db"]
    tenant = boundary_fixture["tenant"]
    db_conn = boundary_fixture["db_conn"]

    recipe = AtomicMetricRecipe(
        metric_id="revenue",
        title="Total Revenue",
        format="currency",
        operand=AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="SUM",
        ),
    )

    # Test with filters=None
    result_none = execute_metric_recipe(
        recipe=recipe,
        connection_id=db_conn.id,
        tenant_id=tenant.id,
        db_conn=db_conn,
        db=db,
        filters=None,
    )
    assert result_none.status == "ok"
    assert result_none.value == 1000.0

    # Test with filters=[]
    result_empty = execute_metric_recipe(
        recipe=recipe,
        connection_id=db_conn.id,
        tenant_id=tenant.id,
        db_conn=db_conn,
        db=db,
        filters=[],
    )
    assert result_empty.status == "ok"
    assert result_empty.value == 1000.0


# ============================================================
# 7. NAN NUMERATOR REJECTED
# ============================================================

def test_nan_numerator_rejected(boundary_fixture):
    """
    Test 7: NaN numerator rejected.
    Numerator returning float("nan") must raise DerivedMetricExecutionError:
    "Derived metric component 'numerator' returned a non-finite numeric value."
    """
    db = boundary_fixture["db"]
    tenant = boundary_fixture["tenant"]
    db_conn = boundary_fixture["db_conn"]

    recipe = RatioMetricRecipe(
        metric_id="aov",
        title="Average Order Value",
        format="currency",
        zero_division="null",
        numerator=AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="SUM",
        ),
        denominator=AtomicMetricOperand(
            target_ref="orders.order_id",
            aggregation="COUNT",
        ),
    )

    with patch(
        "services.derived_metric_executor._execute_atomic_operand",
        side_effect=[float("nan"), 4],
    ):
        with pytest.raises(DerivedMetricExecutionError) as exc_info:
            execute_metric_recipe(
                recipe=recipe,
                connection_id=db_conn.id,
                tenant_id=tenant.id,
                db_conn=db_conn,
                db=db,
            )

        assert "Derived metric component 'numerator' returned a non-finite numeric value." in str(exc_info.value)


# ============================================================
# 8. INFINITE NUMERATOR REJECTED
# ============================================================

def test_infinite_numerator_rejected(boundary_fixture):
    """
    Test 8: infinite numerator rejected.
    Numerator returning float("inf") must raise DerivedMetricExecutionError:
    "Derived metric component 'numerator' returned a non-finite numeric value."
    """
    db = boundary_fixture["db"]
    tenant = boundary_fixture["tenant"]
    db_conn = boundary_fixture["db_conn"]

    recipe = RatioMetricRecipe(
        metric_id="aov",
        title="Average Order Value",
        format="currency",
        zero_division="null",
        numerator=AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="SUM",
        ),
        denominator=AtomicMetricOperand(
            target_ref="orders.order_id",
            aggregation="COUNT",
        ),
    )

    with patch(
        "services.derived_metric_executor._execute_atomic_operand",
        side_effect=[float("inf"), 4],
    ):
        with pytest.raises(DerivedMetricExecutionError) as exc_info:
            execute_metric_recipe(
                recipe=recipe,
                connection_id=db_conn.id,
                tenant_id=tenant.id,
                db_conn=db_conn,
                db=db,
            )

        assert "Derived metric component 'numerator' returned a non-finite numeric value." in str(exc_info.value)


# ============================================================
# 9. NEGATIVE INFINITE DIFFERENCE OPERAND REJECTED
# ============================================================

def test_negative_infinite_difference_operand_rejected(boundary_fixture):
    """
    Test 9: negative infinite difference operand rejected.
    Right operand returning -float("inf") must raise DerivedMetricExecutionError:
    "Derived metric component 'right' returned a non-finite numeric value."
    """
    db = boundary_fixture["db"]
    tenant = boundary_fixture["tenant"]
    db_conn = boundary_fixture["db_conn"]

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

    with patch(
        "services.derived_metric_executor._execute_atomic_operand",
        side_effect=[1000.0, -float("inf")],
    ):
        with pytest.raises(DerivedMetricExecutionError) as exc_info:
            execute_metric_recipe(
                recipe=recipe,
                connection_id=db_conn.id,
                tenant_id=tenant.id,
                db_conn=db_conn,
                db=db,
            )

        assert "Derived metric component 'right' returned a non-finite numeric value." in str(exc_info.value)


# ============================================================
# 10. LEGITIMATE ZERO REMAINS VALID
# ============================================================

def test_legitimate_zero_remains_valid(boundary_fixture):
    """
    Test 10: legitimate zero remains valid.
    Zero numerator in ratio -> value=0.0, status='ok'
    Zero difference (left == right) -> value=0.0, status='ok'
    """
    db = boundary_fixture["db"]
    tenant = boundary_fixture["tenant"]
    db_conn = boundary_fixture["db_conn"]

    # Ratio with 0 numerator
    ratio_recipe = RatioMetricRecipe(
        metric_id="zero_ratio",
        title="Zero Ratio",
        format="number",
        zero_division="null",
        numerator=AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="SUM",
        ),
        denominator=AtomicMetricOperand(
            target_ref="orders.order_id",
            aggregation="COUNT",
        ),
    )

    with patch(
        "services.derived_metric_executor._execute_atomic_operand",
        side_effect=[0, 4],
    ):
        ratio_res = execute_metric_recipe(
            recipe=ratio_recipe,
            connection_id=db_conn.id,
            tenant_id=tenant.id,
            db_conn=db_conn,
            db=db,
        )
        assert ratio_res.status == "ok"
        assert ratio_res.value == 0.0

    # Difference resulting in exact 0
    diff_recipe = DifferenceMetricRecipe(
        metric_id="zero_profit",
        title="Zero Profit",
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

    with patch(
        "services.derived_metric_executor._execute_atomic_operand",
        side_effect=[500.0, 500.0],
    ):
        diff_res = execute_metric_recipe(
            recipe=diff_recipe,
            connection_id=db_conn.id,
            tenant_id=tenant.id,
            db_conn=db_conn,
            db=db,
        )
        assert diff_res.status == "ok"
        assert diff_res.value == 0.0


# ============================================================
# 11. NORMAL FINITE AOV REMAINS 250
# ============================================================

def test_normal_finite_aov_remains_250(boundary_fixture):
    """
    Test 11: normal finite AOV remains 250.
    Orders total amount = 100 + 200 + 300 + 400 = 1000
    Orders count = 4
    AOV = 1000 / 4 = 250.0
    """
    db = boundary_fixture["db"]
    tenant = boundary_fixture["tenant"]
    db_conn = boundary_fixture["db_conn"]

    recipe = RatioMetricRecipe(
        metric_id="aov",
        title="Average Order Value",
        format="currency",
        zero_division="null",
        numerator=AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="SUM",
        ),
        denominator=AtomicMetricOperand(
            target_ref="orders.order_id",
            aggregation="COUNT",
        ),
    )

    result = execute_metric_recipe(
        recipe=recipe,
        connection_id=db_conn.id,
        tenant_id=tenant.id,
        db_conn=db_conn,
        db=db,
    )

    assert result.status == "ok"
    assert result.value == 250.0
    assert len(result.components) == 2
    assert result.components[0].role == "numerator"
    assert result.components[0].value == 1000.0
    assert result.components[1].role == "denominator"
    assert result.components[1].value == 4


# ============================================================
# 12. ALL EXISTING PHASE 2C TESTS REMAIN GREEN / HELPER TESTS
# ============================================================

def test_unit_ensure_numeric_behavior():
    """
    Direct unit tests for _ensure_numeric boundary behavior:
    - None -> None
    - bool -> DerivedMetricExecutionError
    - non-numeric -> DerivedMetricExecutionError
    - NaN / +inf / -inf -> DerivedMetricExecutionError
    - int / float -> returned as is
    """
    assert _ensure_numeric(None, role="test") is None
    assert _ensure_numeric(42, role="test") == 42
    assert _ensure_numeric(3.14, role="test") == 3.14
    assert _ensure_numeric(0, role="test") == 0
    assert _ensure_numeric(0.0, role="test") == 0.0

    with pytest.raises(DerivedMetricExecutionError, match="boolean value"):
        _ensure_numeric(True, role="test")

    with pytest.raises(DerivedMetricExecutionError, match="boolean value"):
        _ensure_numeric(False, role="test")

    with pytest.raises(DerivedMetricExecutionError, match="numeric value"):
        _ensure_numeric("42", role="test")

    with pytest.raises(DerivedMetricExecutionError, match="non-finite numeric value"):
        _ensure_numeric(float("nan"), role="test")

    with pytest.raises(DerivedMetricExecutionError, match="non-finite numeric value"):
        _ensure_numeric(float("inf"), role="test")

    with pytest.raises(DerivedMetricExecutionError, match="non-finite numeric value"):
        _ensure_numeric(float("-inf"), role="test")


def test_get_recipe_table_boundary():
    """
    _get_recipe_table returns single source table or raises DerivedMetricExecutionError.
    """
    atomic = AtomicMetricRecipe(
        metric_id="rev",
        title="Rev",
        format="currency",
        operand=AtomicMetricOperand(target_ref="orders.total_amount", aggregation="SUM"),
    )
    assert _get_recipe_table(atomic) == "orders"


# ============================================================
# 13. ARITHMETIC OVERFLOW RESULT GUARDS (FINITE INPUTS -> NON-FINITE OUTPUT)
# ============================================================

def test_finite_operands_division_overflow_produces_non_finite_rejected(boundary_fixture):
    """
    Finite operands whose division produces non-finite output:
    e.g. 1e308 / 1e-308 -> inf
    Must raise DerivedMetricExecutionError:
    "Derived metric ratio calculation resulted in a non-finite value."
    """
    db = boundary_fixture["db"]
    tenant = boundary_fixture["tenant"]
    db_conn = boundary_fixture["db_conn"]

    recipe = RatioMetricRecipe(
        metric_id="aov_overflow",
        title="Overflow AOV",
        format="currency",
        zero_division="null",
        numerator=AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="SUM",
        ),
        denominator=AtomicMetricOperand(
            target_ref="orders.order_id",
            aggregation="COUNT",
        ),
    )

    with patch(
        "services.derived_metric_executor._execute_atomic_operand",
        side_effect=[1e308, 1e-308],
    ):
        with pytest.raises(DerivedMetricExecutionError) as exc_info:
            execute_metric_recipe(
                recipe=recipe,
                connection_id=db_conn.id,
                tenant_id=tenant.id,
                db_conn=db_conn,
                db=db,
            )

        assert "Derived metric ratio calculation resulted in a non-finite value." in str(exc_info.value)


def test_finite_operands_subtraction_overflow_produces_non_finite_rejected(boundary_fixture):
    """
    Finite operands whose subtraction produces non-finite output:
    e.g. 1e308 - (-1e308) -> inf
    Must raise DerivedMetricExecutionError:
    "Derived metric difference calculation resulted in a non-finite value."
    """
    db = boundary_fixture["db"]
    tenant = boundary_fixture["tenant"]
    db_conn = boundary_fixture["db_conn"]

    recipe = DifferenceMetricRecipe(
        metric_id="profit_overflow",
        title="Overflow Profit",
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

    with patch(
        "services.derived_metric_executor._execute_atomic_operand",
        side_effect=[1e308, -1e308],
    ):
        with pytest.raises(DerivedMetricExecutionError) as exc_info:
            execute_metric_recipe(
                recipe=recipe,
                connection_id=db_conn.id,
                tenant_id=tenant.id,
                db_conn=db_conn,
                db=db,
            )

        assert "Derived metric difference calculation resulted in a non-finite value." in str(exc_info.value)
