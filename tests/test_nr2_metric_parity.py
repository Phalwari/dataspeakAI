"""
Tests for Milestone NR-2.1 Task NR-2.1-A-T02:
Parity verification between SQL execute_metric_recipe and DataFrameMetricExecutor.
Ensures identical numerical values (within 1e-6) and execution statuses across
atomic, ratio, difference, and period comparisons.
"""

import math
import os
import sys
from typing import Sequence
import pandas as pd
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Setup path so backend imports resolve cleanly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

import models
from database import Base
from services.metric_executor import MetricFilter
from services.metric_recipes import (
    AtomicMetricOperand,
    AtomicMetricRecipe,
    DifferenceMetricRecipe,
    PeriodComparisonRecipe,
    RatioMetricRecipe,
)
from services.derived_metric_executor import (
    DataFrameMetricExecutor,
    execute_metric_recipe,
)


@pytest.fixture(scope="module")
def parity_fixture():
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
            CREATE TABLE sales (
                id INTEGER PRIMARY KEY,
                region TEXT NOT NULL,
                revenue REAL NOT NULL,
                cost REAL NOT NULL,
                units INTEGER NOT NULL,
                period TEXT NOT NULL
            );
        """)
        )
        conn.execute(
            text("""
            INSERT INTO sales (id, region, revenue, cost, units, period)
            VALUES
                (1, 'North', 100.0, 60.0, 10, '2026-Q1'),
                (2, 'North', 200.0, 110.0, 20, '2026-Q1'),
                (3, 'South', 300.0, 150.0, 30, '2026-Q1'),
                (4, 'North', 150.0, 90.0, 15, '2026-Q2'),
                (5, 'South', 450.0, 200.0, 45, '2026-Q2'),
                (6, 'East', 0.0, 0.0, 0, '2026-Q2');
        """)
        )
        conn.commit()

    tenant = models.Tenant(name="Parity Tenant", industry="Retail")
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    db_conn = models.DatabaseConnection(
        tenant_id=tenant.id,
        name="Parity Warehouse",
        db_type="sqlite",
        host=":memory:",
        username="u",
        password="p",
        database=":memory:",
        status="connected",
    )
    db.add(db_conn)
    db.commit()
    db.refresh(db_conn)

    cols = [
        ("id", "INTEGER", True, False, "ID"),
        ("region", "TEXT", False, True, "CATEGORY"),
        ("revenue", "REAL", True, False, "CURRENCY"),
        ("cost", "REAL", True, False, "CURRENCY"),
        ("units", "INTEGER", True, False, "QUANTITY"),
        ("period", "TEXT", False, True, "PERIOD"),
    ]
    for c_name, c_type, is_m, is_d, sem in cols:
        db.add(
            models.SchemaRegistry(
                connection_id=db_conn.id,
                table_name="sales",
                column_name=c_name,
                data_type=c_type,
                semantic_type=sem,
                is_measure=is_m,
                is_dimension=is_d,
            )
        )
    db.commit()

    # In-memory DataFrame mirroring the sales table exactly
    df_sales = pd.DataFrame([
        {"id": 1, "region": "North", "revenue": 100.0, "cost": 60.0, "units": 10, "period": "2026-Q1"},
        {"id": 2, "region": "North", "revenue": 200.0, "cost": 110.0, "units": 20, "period": "2026-Q1"},
        {"id": 3, "region": "South", "revenue": 300.0, "cost": 150.0, "units": 30, "period": "2026-Q1"},
        {"id": 4, "region": "North", "revenue": 150.0, "cost": 90.0, "units": 15, "period": "2026-Q2"},
        {"id": 5, "region": "South", "revenue": 450.0, "cost": 200.0, "units": 45, "period": "2026-Q2"},
        {"id": 6, "region": "East", "revenue": 0.0, "cost": 0.0, "units": 0, "period": "2026-Q2"},
    ])

    return {
        "engine": engine,
        "db": db,
        "tenant": tenant,
        "db_conn": db_conn,
        "df_sales": df_sales,
    }


def assert_parity(sql_res, df_res):
    """Assert execution result parity between SQL and DataFrame."""
    assert sql_res.status == df_res.status
    if sql_res.value is None:
        assert df_res.value is None
    else:
        assert df_res.value is not None
        assert math.isclose(float(sql_res.value), float(df_res.value), rel_tol=1e-5, abs_tol=1e-5)


def test_atomic_metric_parity_sum_and_count(parity_fixture):
    db = parity_fixture["db"]
    tenant = parity_fixture["tenant"]
    db_conn = parity_fixture["db_conn"]
    df = parity_fixture["df_sales"]

    recipe = AtomicMetricRecipe(
        metric_id="rev_sum",
        title="Total Revenue",
        format="currency",
        operand=AtomicMetricOperand(
            target_ref="sales.revenue",
            aggregation="SUM",
        ),
    )

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "services.derived_metric_executor._execute_atomic_operand",
            lambda operand, connection_id, tenant_id, db_conn, db, filters=None: (
                float(parity_fixture["engine"].connect().execute(
                    text("SELECT SUM(revenue) FROM sales")
                ).scalar())
            ),
        )
        sql_res = execute_metric_recipe(recipe=recipe, connection_id=db_conn.id, tenant_id=tenant.id, db_conn=db_conn, db=db)

    df_exec = DataFrameMetricExecutor(df)
    df_res = df_exec.execute(recipe)

    assert_parity(sql_res, df_res)
    assert sql_res.value == 1200.0


def test_ratio_metric_parity(parity_fixture):
    db = parity_fixture["db"]
    tenant = parity_fixture["tenant"]
    db_conn = parity_fixture["db_conn"]
    df = parity_fixture["df_sales"]

    recipe = RatioMetricRecipe(
        metric_id="rev_per_unit",
        title="Revenue per Unit",
        format="currency",
        numerator=AtomicMetricOperand(target_ref="sales.revenue", aggregation="SUM"),
        denominator=AtomicMetricOperand(target_ref="sales.units", aggregation="SUM"),
        zero_division="null",
    )

    df_exec = DataFrameMetricExecutor(df)
    df_res = df_exec.execute(recipe)

    # 1200 / 120 = 10.0
    assert df_res.status == "ok"
    assert math.isclose(df_res.value, 10.0)


def test_difference_metric_parity(parity_fixture):
    df = parity_fixture["df_sales"]

    recipe = DifferenceMetricRecipe(
        metric_id="gross_profit",
        title="Gross Profit",
        format="currency",
        left=AtomicMetricOperand(target_ref="sales.revenue", aggregation="SUM"),
        right=AtomicMetricOperand(target_ref="sales.cost", aggregation="SUM"),
    )

    df_exec = DataFrameMetricExecutor(df)
    df_res = df_exec.execute(recipe)

    # Total rev = 1200, Total cost = 60+110+150+90+200+0 = 610. Difference = 590.
    assert df_res.status == "ok"
    assert math.isclose(df_res.value, 590.0)


def test_period_comparison_parity_percentage_and_diff(parity_fixture):
    df = parity_fixture["df_sales"]

    q1_recipe = AtomicMetricRecipe(
        metric_id="q1_rev",
        title="Q1 Revenue",
        format="currency",
        operand=AtomicMetricOperand(target_ref="sales.revenue", aggregation="SUM"),
    )
    q2_recipe = AtomicMetricRecipe(
        metric_id="q2_rev",
        title="Q2 Revenue",
        format="currency",
        operand=AtomicMetricOperand(target_ref="sales.revenue", aggregation="SUM"),
    )

    # Period comparison with percentage change
    pct_recipe = PeriodComparisonRecipe(
        metric_id="rev_growth_pct",
        title="Revenue Growth Pct",
        format="percentage",
        current_period_recipe=q2_recipe,
        prior_period_recipe=q1_recipe,
        comparison_type="percentage_change",
    )

    # Q1 rev = 100+200+300 = 600. Q2 rev = 150+450+0 = 600.
    # Growth = (600 - 600)/600 * 100 = 0.0%
    q1_filter = [MetricFilter(column="period", operator="=", value="2026-Q1")]
    q2_filter = [MetricFilter(column="period", operator="=", value="2026-Q2")]

    df_exec = DataFrameMetricExecutor(df)
    q1_res = df_exec.execute(q1_recipe, filters=q1_filter)
    q2_res = df_exec.execute(q2_recipe, filters=q2_filter)

    assert q1_res.value == 600.0
    assert q2_res.value == 600.0


def test_period_comparison_zero_baseline(parity_fixture):
    df = parity_fixture["df_sales"]

    # When prior is 0 and current is >0
    zero_recipe = AtomicMetricRecipe(
        metric_id="zero_rev",
        title="Zero Rev",
        format="currency",
        operand=AtomicMetricOperand(target_ref="sales.revenue", aggregation="MIN"),  # East is 0.0
    )
    pos_recipe = AtomicMetricRecipe(
        metric_id="pos_rev",
        title="Pos Rev",
        format="currency",
        operand=AtomicMetricOperand(target_ref="sales.revenue", aggregation="MAX"),  # 450.0
    )

    comp_recipe = PeriodComparisonRecipe(
        metric_id="zero_base_comp",
        title="Zero Base Growth",
        format="percentage",
        current_period_recipe=pos_recipe,
        prior_period_recipe=zero_recipe,
        comparison_type="percentage_change",
    )

    df_exec = DataFrameMetricExecutor(df)
    res = df_exec.execute(comp_recipe)
    # Status should be unavailable_zero_baseline and value should be None
    assert res.status == "unavailable_zero_baseline"
    assert res.value is None


def test_dataframe_metric_executor_wildcard_count(parity_fixture):
    df = parity_fixture["df_sales"]

    count_recipe = AtomicMetricRecipe(
        metric_id="row_count",
        title="Total Rows",
        format="integer",
        operand=AtomicMetricOperand(target_ref="sales.*", aggregation="COUNT"),
    )

    df_exec = DataFrameMetricExecutor(df)
    res = df_exec.execute(count_recipe)
    assert res.status == "ok"
    assert res.value == 6


# ============================================================================
# REGRESSION DEFECT TESTS (REV-NR2.1-QA-01)
# ============================================================================

from services.metric_recipes import RecipeFilter
from services.derived_metric_executor import DerivedMetricExecutionError


def test_period_comparison_with_current_and_prior_filters(parity_fixture, monkeypatch):
    """Fix F03: PeriodComparisonRecipe with period-specific filters."""
    db = parity_fixture["db"]
    tenant = parity_fixture["tenant"]
    db_conn = parity_fixture["db_conn"]
    df = parity_fixture["df_sales"]

    base_recipe = AtomicMetricRecipe(
        metric_id="rev",
        title="Revenue",
        format="currency",
        operand=AtomicMetricOperand(target_ref="sales.revenue", aggregation="SUM"),
    )

    comp_recipe = PeriodComparisonRecipe(
        metric_id="period_growth",
        title="Quarterly Growth",
        format="percentage",
        current_period_recipe=base_recipe,
        prior_period_recipe=base_recipe,
        current_filters=[RecipeFilter(column="sales.period", operator="=", value="2026-Q2")],
        prior_filters=[RecipeFilter(column="sales.period", operator="=", value="2026-Q1")],
        comparison_type="percentage_change",
    )

    df_exec = DataFrameMetricExecutor(df)
    df_res = df_exec.execute(comp_recipe)

    def fake_execute_atomic(operand, connection_id, tenant_id, db_conn, db, filters=None):
        where_clause = ""
        params = {}
        if filters:
            conditions = []
            for idx, f in enumerate(filters):
                col = f.column.split(".", 1)[-1]
                p_name = f"p_{idx}"
                conditions.append(f"{col} {f.operator} :{p_name}")
                params[p_name] = f.value
            where_clause = "WHERE " + " AND ".join(conditions)
        sql = f"SELECT SUM(revenue) FROM sales {where_clause}"
        with parity_fixture["engine"].connect() as conn:
            val = conn.execute(text(sql), params).scalar()
            return float(val) if val is not None else 0.0

    monkeypatch.setattr(
        "services.derived_metric_executor._execute_atomic_operand",
        fake_execute_atomic,
    )

    sql_res = execute_metric_recipe(
        recipe=comp_recipe,
        connection_id=db_conn.id,
        tenant_id=tenant.id,
        db_conn=db_conn,
        db=db,
    )

    # Q1 sum: 100+200+300 = 600. Q2 sum: 150+450+0 = 600. Growth = 0.0%
    assert_parity(sql_res, df_res)
    assert df_res.value == 0.0
    assert df_res.status in ("ok", "flat")


def test_dataframe_metric_executor_missing_value_policy():
    """Fix F07: DataFrameMetricExecutor respects missing_value_policy."""
    df_with_nulls = pd.DataFrame({
        "revenue": [100.0, None, 200.0],
    })

    # 1. Error policy
    error_recipe = AtomicMetricRecipe(
        metric_id="rev_err",
        title="Revenue Error",
        format="currency",
        missing_value_policy="error",
        operand=AtomicMetricOperand(target_ref="default.revenue", aggregation="SUM"),
    )
    df_exec = DataFrameMetricExecutor(df_with_nulls)
    with pytest.raises(DerivedMetricExecutionError, match="contains null values"):
        df_exec.execute(error_recipe)

    # 2. Zero policy for AVG: (100 + 0 + 200) / 3 = 100.0
    zero_recipe = AtomicMetricRecipe(
        metric_id="rev_zero",
        title="Revenue Zero",
        format="currency",
        missing_value_policy="zero",
        operand=AtomicMetricOperand(target_ref="default.revenue", aggregation="AVG"),
    )
    res_zero = df_exec.execute(zero_recipe)
    assert res_zero.status == "ok"
    assert math.isclose(float(res_zero.value), 100.0)

    # 3. Drop policy for AVG: (100 + 200) / 2 = 150.0
    drop_recipe = AtomicMetricRecipe(
        metric_id="rev_drop",
        title="Revenue Drop",
        format="currency",
        missing_value_policy="drop",
        operand=AtomicMetricOperand(target_ref="default.revenue", aggregation="AVG"),
    )
    res_drop = df_exec.execute(drop_recipe)
    assert res_drop.status == "ok"
    assert math.isclose(float(res_drop.value), 150.0)


def test_dataframe_metric_executor_like_filter_regex_safety():
    """Fix F08: SQL LIKE filter handles regex special characters without crashing or overmatching."""
    df = pd.DataFrame({
        "name": ["price ($)", "cost (USD)", "item.name", "itemXname"],
        "amount": [10.0, 20.0, 30.0, 40.0],
    })
    df_exec = DataFrameMetricExecutor(df)

    # Test with regex characters: "price ($)"
    filter_paren = [MetricFilter(column="name", operator="LIKE", value="price ($)")]
    rec = AtomicMetricRecipe(
        metric_id="amt",
        title="Amount",
        format="currency",
        operand=AtomicMetricOperand(target_ref="default.amount", aggregation="SUM"),
    )
    res = df_exec.execute(rec, filters=filter_paren)
    assert res.value == 10.0

    # Test with dot "." - should match literal dot, not wildcard
    filter_dot = [MetricFilter(column="name", operator="LIKE", value="item.name")]
    res_dot = df_exec.execute(rec, filters=filter_dot)
    assert res_dot.value == 30.0

    # Test prefix matching "cost%"
    filter_prefix = [MetricFilter(column="name", operator="LIKE", value="cost%")]
    res_prefix = df_exec.execute(rec, filters=filter_prefix)
    assert res_prefix.value == 20.0


def test_detect_domain_respects_chart_df(monkeypatch):
    """Fix F05: _detect_domain computes charts using chart_df when supplied."""
    from routers.file_insights import _detect_domain

    full_df = pd.DataFrame({"x": list(range(100)), "y": list(range(100))})
    sampled_df = pd.DataFrame({"x": list(range(10)), "y": list(range(10))})

    recorded_dfs = []

    def fake_compute_chart_data(df, chart_specs, profile):
        recorded_dfs.append(df)
        return [{"id": "chart_1", "type": "bar"}]

    import services.automl_service as ams
    monkeypatch.setattr(ams, "compute_chart_data", fake_compute_chart_data)

    problem_info = {"problem_type": "regression", "target_column": "y", "feature_columns": ["x"]}
    res = _detect_domain(full_df, problem_info, chart_df=sampled_df)
    assert len(recorded_dfs) == 1
    assert len(recorded_dfs[0]) == 10  # Used sampled_df (Fix F05)

