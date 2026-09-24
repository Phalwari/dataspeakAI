import inspect
import os
import sys
from types import SimpleNamespace
from unittest.mock import patch
import pytest

# Setup path so imports work directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from services.metric_recipes import (
    AtomicMetricOperand,
    AtomicMetricRecipe,
    DifferenceMetricRecipe,
    RatioMetricRecipe,
)
from services.chart_recommender import (
    ChartRecommendation,
    ChartRecommendationError,
    _find_registry_column,
    _get_recipe_table,
    _validate_group_ref,
    recommend_chart,
)


@pytest.fixture
def mock_registry_entries():
    """
    Standard test SchemaRegistry metadata representing orders and customers tables.
    """
    return [
        SimpleNamespace(table_name="orders", column_name="order_id", data_type="INTEGER", is_dimension=False),
        SimpleNamespace(table_name="orders", column_name="customer_id", data_type="INTEGER", is_dimension=False),
        SimpleNamespace(table_name="orders", column_name="total_amount", data_type="REAL", is_measure=True),
        SimpleNamespace(table_name="orders", column_name="total_cost", data_type="REAL", is_measure=True),
        SimpleNamespace(table_name="orders", column_name="status", data_type="TEXT", is_dimension=True),
        SimpleNamespace(table_name="orders", column_name="created_at", data_type="DATETIME", is_dimension=True),
        SimpleNamespace(table_name="customers", column_name="id", data_type="INTEGER", is_dimension=False),
        SimpleNamespace(table_name="customers", column_name="name", data_type="TEXT", is_dimension=True),
        SimpleNamespace(table_name="customers", column_name="region", data_type="TEXT", is_dimension=True),
    ]


@pytest.fixture
def revenue_recipe():
    return AtomicMetricRecipe(
        metric_id="total_revenue",
        title="Total Revenue",
        format="currency",
        operand=AtomicMetricOperand(
            target_ref="orders.total_amount",
            aggregation="SUM",
        ),
    )


@pytest.fixture
def aov_recipe():
    return RatioMetricRecipe(
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


@pytest.fixture
def gross_profit_recipe():
    return DifferenceMetricRecipe(
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


# ============================================================
# 1. ATOMIC NO GROUPING -> KPI
# ============================================================

def test_atomic_no_grouping_recommends_kpi(revenue_recipe, mock_registry_entries):
    rec = recommend_chart(
        recipe=revenue_recipe,
        registry_entries=mock_registry_entries,
    )

    assert rec.metric_id == "total_revenue"
    assert rec.title == "Total Revenue"
    assert rec.chart_type == "KPI"
    assert rec.group_by_ref is None
    assert rec.grouping_kind == "none"
    assert rec.priority == 1
    assert "No explicit grouping reference" in rec.reason


# ============================================================
# 2. ATOMIC WITH TIME_REF -> LINE
# ============================================================

def test_atomic_with_time_ref_recommends_line(revenue_recipe, mock_registry_entries):
    rec = recommend_chart(
        recipe=revenue_recipe,
        registry_entries=mock_registry_entries,
        time_ref="orders.created_at",
    )

    assert rec.metric_id == "total_revenue"
    assert rec.title == "Total Revenue"
    assert rec.chart_type == "Line"
    assert rec.group_by_ref == "orders.created_at"
    assert rec.grouping_kind == "time"
    assert rec.priority == 1
    assert "time grouping" in rec.reason


# ============================================================
# 3. ATOMIC WITH DIMENSION_REF -> BAR
# ============================================================

def test_atomic_with_dimension_ref_recommends_bar(revenue_recipe, mock_registry_entries):
    rec = recommend_chart(
        recipe=revenue_recipe,
        registry_entries=mock_registry_entries,
        dimension_ref="orders.status",
    )

    assert rec.metric_id == "total_revenue"
    assert rec.title == "Total Revenue"
    assert rec.chart_type == "Bar"
    assert rec.group_by_ref == "orders.status"
    assert rec.grouping_kind == "dimension"
    assert rec.priority == 1
    assert "categorical grouping" in rec.reason


# ============================================================
# 4. TIME PRECEDENCE WHEN BOTH SUPPLIED
# ============================================================

def test_time_wins_when_both_time_and_dimension_supplied(revenue_recipe, mock_registry_entries):
    rec = recommend_chart(
        recipe=revenue_recipe,
        registry_entries=mock_registry_entries,
        time_ref="orders.created_at",
        dimension_ref="orders.status",
    )

    assert rec.chart_type == "Line"
    assert rec.group_by_ref == "orders.created_at"
    assert rec.grouping_kind == "time"


# ============================================================
# 5. RATIO -> KPI ONLY
# ============================================================

def test_ratio_without_grouping_recommends_kpi(aov_recipe, mock_registry_entries):
    rec = recommend_chart(
        recipe=aov_recipe,
        registry_entries=mock_registry_entries,
    )

    assert rec.metric_id == "aov"
    assert rec.title == "Average Order Value"
    assert rec.chart_type == "KPI"
    assert rec.group_by_ref is None
    assert rec.grouping_kind == "none"
    assert "scalar execution only" in rec.reason


# ============================================================
# 6. DIFFERENCE -> KPI ONLY
# ============================================================

def test_difference_without_grouping_recommends_kpi(gross_profit_recipe, mock_registry_entries):
    rec = recommend_chart(
        recipe=gross_profit_recipe,
        registry_entries=mock_registry_entries,
    )

    assert rec.metric_id == "gross_profit"
    assert rec.title == "Gross Profit"
    assert rec.chart_type == "KPI"
    assert rec.group_by_ref is None
    assert rec.grouping_kind == "none"
    assert "scalar execution only" in rec.reason


# ============================================================
# 7. RATIO SUPPLIED TIME STILL -> KPI
# ============================================================

def test_ratio_supplied_time_still_recommends_kpi(aov_recipe, mock_registry_entries):
    rec = recommend_chart(
        recipe=aov_recipe,
        registry_entries=mock_registry_entries,
        time_ref="orders.created_at",
    )

    assert rec.chart_type == "KPI"
    assert rec.group_by_ref is None
    assert rec.grouping_kind == "none"
    assert "scalar execution only" in rec.reason


# ============================================================
# 8. RATIO SUPPLIED DIMENSION STILL -> KPI
# ============================================================

def test_ratio_supplied_dimension_still_recommends_kpi(aov_recipe, mock_registry_entries):
    rec = recommend_chart(
        recipe=aov_recipe,
        registry_entries=mock_registry_entries,
        dimension_ref="orders.status",
    )

    assert rec.chart_type == "KPI"
    assert rec.group_by_ref is None
    assert rec.grouping_kind == "none"
    assert "scalar execution only" in rec.reason


# ============================================================
# 9. DIFFERENCE SUPPLIED TIME STILL -> KPI
# ============================================================

def test_difference_supplied_time_still_recommends_kpi(gross_profit_recipe, mock_registry_entries):
    rec = recommend_chart(
        recipe=gross_profit_recipe,
        registry_entries=mock_registry_entries,
        time_ref="orders.created_at",
    )

    assert rec.chart_type == "KPI"
    assert rec.group_by_ref is None
    assert rec.grouping_kind == "none"
    assert "scalar execution only" in rec.reason


# ============================================================
# 10. DIFFERENCE SUPPLIED DIMENSION STILL -> KPI
# ============================================================

def test_difference_supplied_dimension_still_recommends_kpi(gross_profit_recipe, mock_registry_entries):
    rec = recommend_chart(
        recipe=gross_profit_recipe,
        registry_entries=mock_registry_entries,
        dimension_ref="orders.status",
    )

    assert rec.chart_type == "KPI"
    assert rec.group_by_ref is None
    assert rec.grouping_kind == "none"
    assert "scalar execution only" in rec.reason


# ============================================================
# 11. UNKNOWN DIMENSION REJECTED
# ============================================================

def test_unknown_dimension_rejected(revenue_recipe, mock_registry_entries):
    with pytest.raises(ChartRecommendationError) as exc_info:
        recommend_chart(
            recipe=revenue_recipe,
            registry_entries=mock_registry_entries,
            dimension_ref="orders.nonexistent_column",
        )

    assert "does not exist in verified SchemaRegistry" in str(exc_info.value)


# ============================================================
# 12. UNKNOWN TIME REJECTED
# ============================================================

def test_unknown_time_rejected(revenue_recipe, mock_registry_entries):
    with pytest.raises(ChartRecommendationError) as exc_info:
        recommend_chart(
            recipe=revenue_recipe,
            registry_entries=mock_registry_entries,
            time_ref="orders.nonexistent_timestamp",
        )

    assert "does not exist in verified SchemaRegistry" in str(exc_info.value)


# ============================================================
# 13. CROSS-TABLE DIMENSION REJECTED
# ============================================================

def test_cross_table_dimension_rejected(revenue_recipe, mock_registry_entries):
    with pytest.raises(ChartRecommendationError) as exc_info:
        recommend_chart(
            recipe=revenue_recipe,
            registry_entries=mock_registry_entries,
            dimension_ref="customers.region",
        )

    assert "Cross-table chart grouping requires a validated relationship path." in str(exc_info.value)


# ============================================================
# 14. CROSS-TABLE TIME REJECTED
# ============================================================

def test_cross_table_time_rejected(revenue_recipe, mock_registry_entries):
    with pytest.raises(ChartRecommendationError) as exc_info:
        recommend_chart(
            recipe=revenue_recipe,
            registry_entries=mock_registry_entries,
            time_ref="customers.region",
        )

    assert "Cross-table chart grouping requires a validated relationship path." in str(exc_info.value)


# ============================================================
# 15. UNQUALIFIED DIMENSION REJECTED
# ============================================================

def test_unqualified_dimension_rejected(revenue_recipe, mock_registry_entries):
    with pytest.raises(ChartRecommendationError) as exc_info:
        recommend_chart(
            recipe=revenue_recipe,
            registry_entries=mock_registry_entries,
            dimension_ref="status",
        )

    assert "Chart grouping references must use qualified table.column syntax." in str(exc_info.value)


# ============================================================
# 16. UNQUALIFIED TIME REJECTED
# ============================================================

def test_unqualified_time_rejected(revenue_recipe, mock_registry_entries):
    with pytest.raises(ChartRecommendationError) as exc_info:
        recommend_chart(
            recipe=revenue_recipe,
            registry_entries=mock_registry_entries,
            time_ref="created_at",
        )

    assert "Chart grouping references must use qualified table.column syntax." in str(exc_info.value)


# ============================================================
# 17. METRIC_ID PRESERVED
# ============================================================

def test_metric_id_preserved(revenue_recipe, aov_recipe, gross_profit_recipe, mock_registry_entries):
    assert recommend_chart(recipe=revenue_recipe, registry_entries=mock_registry_entries).metric_id == "total_revenue"
    assert recommend_chart(recipe=aov_recipe, registry_entries=mock_registry_entries).metric_id == "aov"
    assert recommend_chart(recipe=gross_profit_recipe, registry_entries=mock_registry_entries).metric_id == "gross_profit"


# ============================================================
# 18. TITLE PRESERVED
# ============================================================

def test_title_preserved(revenue_recipe, aov_recipe, gross_profit_recipe, mock_registry_entries):
    assert recommend_chart(recipe=revenue_recipe, registry_entries=mock_registry_entries).title == "Total Revenue"
    assert recommend_chart(recipe=aov_recipe, registry_entries=mock_registry_entries).title == "Average Order Value"
    assert recommend_chart(recipe=gross_profit_recipe, registry_entries=mock_registry_entries).title == "Gross Profit"


# ============================================================
# 19. REPEATED RESULT DETERMINISTIC
# ============================================================

def test_repeated_recommendation_identical(revenue_recipe, mock_registry_entries):
    rec1 = recommend_chart(recipe=revenue_recipe, registry_entries=mock_registry_entries, time_ref="orders.created_at")
    rec2 = recommend_chart(recipe=revenue_recipe, registry_entries=mock_registry_entries, time_ref="orders.created_at")

    assert rec1.model_dump() == rec2.model_dump()


# ============================================================
# 20. OUTPUT HAS NO SQL/FORMULA/EXPRESSION FIELDS
# ============================================================

def test_output_has_no_sql_formula_expression_fields(revenue_recipe, mock_registry_entries):
    rec = recommend_chart(
        recipe=revenue_recipe,
        registry_entries=mock_registry_entries,
        dimension_ref="orders.status",
    )
    rec_dict = rec.model_dump()

    # Model fields must only be the exact contract fields
    allowed_fields = {"metric_id", "title", "chart_type", "group_by_ref", "grouping_kind", "priority", "reason"}
    assert set(rec_dict.keys()) == allowed_fields

    # None of the values should contain SQL statements
    for val in rec_dict.values():
        if isinstance(val, str):
            assert "SELECT" not in val.upper()
            assert "JOIN" not in val.upper()
            assert "WHERE" not in val.upper()


# ============================================================
# 21. CHART RECOMMENDER CONTAINS NO SQL EXECUTION
# ============================================================

def test_chart_recommender_contains_no_sql_execution():
    import services.chart_recommender as cr_module
    src = inspect.getsource(cr_module)

    assert "SELECT " not in src
    assert "cursor." not in src
    assert "conn.execute" not in src
    assert "db.execute" not in src
    assert "db.query" not in src


# ============================================================
# 22. CHART RECOMMENDER CONTAINS NO LLM IMPORT/CALL
# ============================================================

def test_chart_recommender_contains_no_llm_import_or_call():
    import services.chart_recommender as cr_module
    src = inspect.getsource(cr_module)

    assert "openai" not in src.lower()
    assert "anthropic" not in src.lower()
    assert "gemini" not in src.lower()
    assert "google.generativeai" not in src.lower()
    assert "langchain" not in src.lower()
    assert "chat_completion" not in src.lower()


# ============================================================
# 23. METRICEXECUTOR IS NEVER INVOKED
# ============================================================

def test_metric_executor_is_never_invoked(revenue_recipe, mock_registry_entries):
    with patch("services.metric_executor.MetricExecutor.execute") as mock_exec:
        recommend_chart(
            recipe=revenue_recipe,
            registry_entries=mock_registry_entries,
            time_ref="orders.created_at",
            dimension_ref="orders.status",
        )
        assert mock_exec.call_count == 0


# ============================================================
# 24. DERIVEDMETRICEXECUTOR IS NEVER INVOKED
# ============================================================

def test_derived_metric_executor_is_never_invoked(aov_recipe, mock_registry_entries):
    with patch("services.derived_metric_executor.execute_metric_recipe") as mock_derived:
        recommend_chart(
            recipe=aov_recipe,
            registry_entries=mock_registry_entries,
            time_ref="orders.created_at",
        )
        assert mock_derived.call_count == 0


# ============================================================
# 25. HELPER TESTS & EDGE CASES
# ============================================================

def test_get_recipe_table_helper(revenue_recipe):
    assert _get_recipe_table(revenue_recipe) == "orders"


def test_find_registry_column_dict_support():
    entries = [{"table_name": "orders", "column_name": "status"}]
    found = _find_registry_column(ref="orders.status", registry_entries=entries)
    assert found == {"table_name": "orders", "column_name": "status"}


def test_validate_group_ref_helper(mock_registry_entries):
    val = _validate_group_ref(
        ref="orders.status",
        recipe_table="orders",
        registry_entries=mock_registry_entries,
    )
    assert val == "orders.status"
