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
from services.filter_recommender import (
    DateRangeFilterRecommendation,
    FilterRecommendationError,
    FilterRecommendationResult,
    SelectFilterRecommendation,
    SkippedFilter,
    _find_registry_column,
    _get_recipe_table,
    _is_identifier_like,
    _make_filter_id,
    _make_label,
    _validate_filter_ref,
    recommend_filters,
)


@pytest.fixture
def mock_registry():
    return [
        SimpleNamespace(
            table_name="orders",
            column_name="order_id",
            semantic_type="ID",
            is_primary_key=True,
            is_foreign_key=False,
            is_measure=False,
            is_dimension=False,
            cardinality=100,
        ),
        SimpleNamespace(
            table_name="orders",
            column_name="customer_id",
            semantic_type="ID",
            is_primary_key=False,
            is_foreign_key=True,
            is_measure=False,
            is_dimension=False,
            cardinality=20,
        ),
        SimpleNamespace(
            table_name="orders",
            column_name="uuid_code",
            semantic_type="UUID",
            is_primary_key=False,
            is_foreign_key=False,
            is_measure=False,
            is_dimension=False,
            cardinality=15,
        ),
        SimpleNamespace(
            table_name="orders",
            column_name="total_amount",
            semantic_type="CURRENCY/AMOUNT",
            is_primary_key=False,
            is_foreign_key=False,
            is_measure=True,
            is_dimension=False,
            cardinality=250,
        ),
        SimpleNamespace(
            table_name="orders",
            column_name="total_cost",
            semantic_type="CURRENCY/AMOUNT",
            is_primary_key=False,
            is_foreign_key=False,
            is_measure=True,
            is_dimension=False,
            cardinality=200,
        ),
        SimpleNamespace(
            table_name="orders",
            column_name="created_at",
            semantic_type="DATETIME",
            is_primary_key=False,
            is_foreign_key=False,
            is_measure=False,
            is_dimension=True,
            is_time_axis=True,
            cardinality=1000,
        ),
        SimpleNamespace(
            table_name="orders",
            column_name="status",
            semantic_type="CATEGORY",
            is_primary_key=False,
            is_foreign_key=False,
            is_measure=False,
            is_dimension=True,
            cardinality=4,
        ),
        SimpleNamespace(
            table_name="orders",
            column_name="shipping_tier",
            semantic_type="CATEGORY",
            is_primary_key=False,
            is_foreign_key=False,
            is_measure=False,
            is_dimension=True,
            cardinality=3,
        ),
        SimpleNamespace(
            table_name="orders",
            column_name="constant_flag",
            semantic_type="CATEGORY",
            is_primary_key=False,
            is_foreign_key=False,
            is_measure=False,
            is_dimension=True,
            cardinality=1,
        ),
        SimpleNamespace(
            table_name="orders",
            column_name="empty_flag",
            semantic_type="CATEGORY",
            is_primary_key=False,
            is_foreign_key=False,
            is_measure=False,
            is_dimension=True,
            cardinality=0,
        ),
        SimpleNamespace(
            table_name="orders",
            column_name="boundary_two",
            semantic_type="CATEGORY",
            is_primary_key=False,
            is_foreign_key=False,
            is_measure=False,
            is_dimension=True,
            cardinality=2,
        ),
        SimpleNamespace(
            table_name="orders",
            column_name="boundary_fifty",
            semantic_type="CATEGORY",
            is_primary_key=False,
            is_foreign_key=False,
            is_measure=False,
            is_dimension=True,
            cardinality=50,
        ),
        SimpleNamespace(
            table_name="orders",
            column_name="boundary_fifty_one",
            semantic_type="CATEGORY",
            is_primary_key=False,
            is_foreign_key=False,
            is_measure=False,
            is_dimension=True,
            cardinality=51,
        ),
        SimpleNamespace(
            table_name="orders",
            column_name="missing_cardinality",
            semantic_type="CATEGORY",
            is_primary_key=False,
            is_foreign_key=False,
            is_measure=False,
            is_dimension=True,
            cardinality=None,
        ),
        SimpleNamespace(
            table_name="customers",
            column_name="id",
            semantic_type="ID",
            is_primary_key=True,
            is_foreign_key=False,
            is_measure=False,
            is_dimension=False,
            cardinality=100,
        ),
        SimpleNamespace(
            table_name="customers",
            column_name="region",
            semantic_type="CATEGORY",
            is_primary_key=False,
            is_foreign_key=False,
            is_measure=False,
            is_dimension=True,
            cardinality=5,
        ),
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
# 1. NO REFS => EMPTY RECOMMENDATIONS
# ============================================================

def test_no_refs_produces_empty_recommendations(revenue_recipe, mock_registry):
    res = recommend_filters(
        recipe=revenue_recipe,
        registry_entries=mock_registry,
    )
    assert res.recommendations == []
    assert res.skipped == []


# ============================================================
# 2. TIME_REF -> DATE_RANGE
# ============================================================

def test_time_ref_recommends_date_range(revenue_recipe, mock_registry):
    res = recommend_filters(
        recipe=revenue_recipe,
        registry_entries=mock_registry,
        time_ref="orders.created_at",
    )
    assert len(res.recommendations) == 1
    rec = res.recommendations[0]
    assert isinstance(rec, DateRangeFilterRecommendation)
    assert rec.filter_type == "date_range"
    assert rec.column_ref == "orders.created_at"
    assert rec.filter_id == "orders_created_at_date_range"
    assert rec.label == "Created At"
    assert rec.priority == 1
    assert "date-range filtering" in rec.reason


# ============================================================
# 3 & 4. DATE RANGE OPERATORS: START >= AND END <=
# ============================================================

def test_date_range_operators(revenue_recipe, mock_registry):
    res = recommend_filters(
        recipe=revenue_recipe,
        registry_entries=mock_registry,
        time_ref="orders.created_at",
    )
    rec = res.recommendations[0]
    assert isinstance(rec, DateRangeFilterRecommendation)
    assert rec.start_operator == ">="
    assert rec.end_operator == "<="


# ============================================================
# 5 & 6. LOW CARDINALITY DIMENSION -> SELECT WITH IN OPERATOR
# ============================================================

def test_low_cardinality_dimension_recommends_select(revenue_recipe, mock_registry):
    res = recommend_filters(
        recipe=revenue_recipe,
        registry_entries=mock_registry,
        dimension_refs=["orders.status"],
    )
    assert len(res.recommendations) == 1
    rec = res.recommendations[0]
    assert isinstance(rec, SelectFilterRecommendation)
    assert rec.filter_type == "select"
    assert rec.column_ref == "orders.status"
    assert rec.operator == "IN"
    assert rec.cardinality == 4
    assert rec.max_options == 50
    assert rec.priority == 2
    assert rec.filter_id == "orders_status_select"
    assert rec.label == "Status"


# ============================================================
# 7. AOV SUPPORTS SELECT FILTER
# ============================================================

def test_aov_supports_select_filter(aov_recipe, mock_registry):
    res = recommend_filters(
        recipe=aov_recipe,
        registry_entries=mock_registry,
        dimension_refs=["orders.status"],
    )
    assert len(res.recommendations) == 1
    rec = res.recommendations[0]
    assert rec.filter_type == "select"
    assert rec.column_ref == "orders.status"
    assert rec.operator == "IN"


# ============================================================
# 8. AOV SUPPORTS TIME FILTER
# ============================================================

def test_aov_supports_time_filter(aov_recipe, mock_registry):
    res = recommend_filters(
        recipe=aov_recipe,
        registry_entries=mock_registry,
        time_ref="orders.created_at",
    )
    assert len(res.recommendations) == 1
    rec = res.recommendations[0]
    assert rec.filter_type == "date_range"
    assert rec.column_ref == "orders.created_at"


# ============================================================
# 9. DIFFERENCE SUPPORTS FILTERS
# ============================================================

def test_difference_supports_filters(gross_profit_recipe, mock_registry):
    res = recommend_filters(
        recipe=gross_profit_recipe,
        registry_entries=mock_registry,
        time_ref="orders.created_at",
        dimension_refs=["orders.status"],
    )
    assert len(res.recommendations) == 2
    assert res.recommendations[0].filter_type == "date_range"
    assert res.recommendations[1].filter_type == "select"


# ============================================================
# 10. CROSS-TABLE DIMENSION REJECTED
# ============================================================

def test_cross_table_dimension_rejected(revenue_recipe, mock_registry):
    with pytest.raises(FilterRecommendationError) as exc_info:
        recommend_filters(
            recipe=revenue_recipe,
            registry_entries=mock_registry,
            dimension_refs=["customers.region"],
        )
    assert "Cross-table filter recommendation requires a validated relationship path." in str(exc_info.value)


# ============================================================
# 11. CROSS-TABLE TIME REJECTED
# ============================================================

def test_cross_table_time_rejected(revenue_recipe, mock_registry):
    with pytest.raises(FilterRecommendationError) as exc_info:
        recommend_filters(
            recipe=revenue_recipe,
            registry_entries=mock_registry,
            time_ref="customers.region",
        )
    assert "Cross-table filter recommendation requires a validated relationship path." in str(exc_info.value)


# ============================================================
# 12. UNQUALIFIED DIMENSION REJECTED
# ============================================================

def test_unqualified_dimension_rejected(revenue_recipe, mock_registry):
    with pytest.raises(FilterRecommendationError) as exc_info:
        recommend_filters(
            recipe=revenue_recipe,
            registry_entries=mock_registry,
            dimension_refs=["status"],
        )
    assert "Filter references must use qualified table.column syntax." in str(exc_info.value)


# ============================================================
# 13. UNQUALIFIED TIME REJECTED
# ============================================================

def test_unqualified_time_rejected(revenue_recipe, mock_registry):
    with pytest.raises(FilterRecommendationError) as exc_info:
        recommend_filters(
            recipe=revenue_recipe,
            registry_entries=mock_registry,
            time_ref="created_at",
        )
    assert "Filter references must use qualified table.column syntax." in str(exc_info.value)


# ============================================================
# 14. UNKNOWN DIMENSION REJECTED
# ============================================================

def test_unknown_dimension_rejected(revenue_recipe, mock_registry):
    with pytest.raises(FilterRecommendationError) as exc_info:
        recommend_filters(
            recipe=revenue_recipe,
            registry_entries=mock_registry,
            dimension_refs=["orders.nonexistent"],
        )
    assert "does not exist in verified SchemaRegistry" in str(exc_info.value)


# ============================================================
# 15. UNKNOWN TIME REJECTED
# ============================================================

def test_unknown_time_rejected(revenue_recipe, mock_registry):
    with pytest.raises(FilterRecommendationError) as exc_info:
        recommend_filters(
            recipe=revenue_recipe,
            registry_entries=mock_registry,
            time_ref="orders.nonexistent_time",
        )
    assert "does not exist in verified SchemaRegistry" in str(exc_info.value)


# ============================================================
# 16. PRIMARY KEY SKIPPED
# ============================================================

def test_primary_key_skipped(revenue_recipe, mock_registry):
    res = recommend_filters(
        recipe=revenue_recipe,
        registry_entries=mock_registry,
        dimension_refs=["orders.order_id"],
    )
    assert res.recommendations == []
    assert len(res.skipped) == 1
    assert res.skipped[0].column_ref == "orders.order_id"
    assert "Identifier-like columns are not recommended" in res.skipped[0].reason


# ============================================================
# 17. SEMANTIC ID SKIPPED
# ============================================================

def test_semantic_id_and_uuid_skipped(revenue_recipe, mock_registry):
    res = recommend_filters(
        recipe=revenue_recipe,
        registry_entries=mock_registry,
        dimension_refs=["orders.customer_id", "orders.uuid_code"],
    )
    assert res.recommendations == []
    assert len(res.skipped) == 2
    assert res.skipped[0].column_ref == "orders.customer_id"
    assert res.skipped[1].column_ref == "orders.uuid_code"
    assert "Identifier-like columns are not recommended" in res.skipped[0].reason


# ============================================================
# 18 & 19. CARDINALITY 0 AND 1 SKIPPED
# ============================================================

def test_cardinality_zero_and_one_skipped(revenue_recipe, mock_registry):
    res = recommend_filters(
        recipe=revenue_recipe,
        registry_entries=mock_registry,
        dimension_refs=["orders.empty_flag", "orders.constant_flag"],
    )
    assert res.recommendations == []
    assert len(res.skipped) == 2
    assert res.skipped[0].column_ref == "orders.empty_flag"
    assert res.skipped[1].column_ref == "orders.constant_flag"
    assert "fewer than two distinct values" in res.skipped[0].reason


# ============================================================
# 20 & 21. CARDINALITY 2 AND 50 ACCEPTED
# ============================================================

def test_cardinality_two_and_fifty_accepted(revenue_recipe, mock_registry):
    res = recommend_filters(
        recipe=revenue_recipe,
        registry_entries=mock_registry,
        dimension_refs=["orders.boundary_two", "orders.boundary_fifty"],
    )
    assert len(res.recommendations) == 2
    assert res.recommendations[0].column_ref == "orders.boundary_two"
    assert res.recommendations[0].cardinality == 2
    assert res.recommendations[1].column_ref == "orders.boundary_fifty"
    assert res.recommendations[1].cardinality == 50


# ============================================================
# 22. CARDINALITY 51 SKIPPED
# ============================================================

def test_cardinality_fifty_one_skipped(revenue_recipe, mock_registry):
    res = recommend_filters(
        recipe=revenue_recipe,
        registry_entries=mock_registry,
        dimension_refs=["orders.boundary_fifty_one"],
    )
    assert res.recommendations == []
    assert len(res.skipped) == 1
    assert res.skipped[0].column_ref == "orders.boundary_fifty_one"
    assert "exceeds the current safe select-filter threshold" in res.skipped[0].reason


# ============================================================
# 23. MISSING CARDINALITY SKIPPED
# ============================================================

def test_missing_cardinality_skipped(revenue_recipe, mock_registry):
    res = recommend_filters(
        recipe=revenue_recipe,
        registry_entries=mock_registry,
        dimension_refs=["orders.missing_cardinality"],
    )
    assert res.recommendations == []
    assert len(res.skipped) == 1
    assert res.skipped[0].column_ref == "orders.missing_cardinality"
    assert "Column cardinality is unavailable" in res.skipped[0].reason


# ============================================================
# 24. DUPLICATES REMOVED
# ============================================================

def test_duplicate_dimension_refs_removed(revenue_recipe, mock_registry):
    res = recommend_filters(
        recipe=revenue_recipe,
        registry_entries=mock_registry,
        dimension_refs=["orders.status", "orders.status", "orders.status"],
    )
    assert len(res.recommendations) == 1
    assert res.recommendations[0].column_ref == "orders.status"


# ============================================================
# 25. TIME/DIMENSION DUPLICATE REMOVED
# ============================================================

def test_time_and_dimension_duplicate_keeps_date_range_only(revenue_recipe, mock_registry):
    res = recommend_filters(
        recipe=revenue_recipe,
        registry_entries=mock_registry,
        time_ref="orders.created_at",
        dimension_refs=["orders.created_at", "orders.status"],
    )
    assert len(res.recommendations) == 2
    assert res.recommendations[0].filter_type == "date_range"
    assert res.recommendations[0].column_ref == "orders.created_at"
    assert res.recommendations[1].filter_type == "select"
    assert res.recommendations[1].column_ref == "orders.status"


# ============================================================
# 26. DETERMINISTIC ORDER
# ============================================================

def test_deterministic_order_time_first_then_dimensions(revenue_recipe, mock_registry):
    res = recommend_filters(
        recipe=revenue_recipe,
        registry_entries=mock_registry,
        time_ref="orders.created_at",
        dimension_refs=["orders.status", "orders.shipping_tier"],
    )
    assert len(res.recommendations) == 3
    assert res.recommendations[0].column_ref == "orders.created_at"
    assert res.recommendations[1].column_ref == "orders.status"
    assert res.recommendations[2].column_ref == "orders.shipping_tier"


# ============================================================
# 27. DETERMINISTIC REPEATED OUTPUT
# ============================================================

def test_deterministic_repeated_output(revenue_recipe, mock_registry):
    res1 = recommend_filters(
        recipe=revenue_recipe,
        registry_entries=mock_registry,
        time_ref="orders.created_at",
        dimension_refs=["orders.status"],
    )
    res2 = recommend_filters(
        recipe=revenue_recipe,
        registry_entries=mock_registry,
        time_ref="orders.created_at",
        dimension_refs=["orders.status"],
    )
    assert res1.model_dump() == res2.model_dump()


# ============================================================
# 28. DETERMINISTIC FILTER IDS
# ============================================================

def test_deterministic_filter_ids():
    assert _make_filter_id(ref="orders.created_at", suffix="date_range") == "orders_created_at_date_range"
    assert _make_filter_id(ref="orders.status", suffix="select") == "orders_status_select"


# ============================================================
# 29. NO ACTUAL FILTER OPTIONS IN OUTPUT
# ============================================================

def test_no_actual_filter_options_in_output(revenue_recipe, mock_registry):
    res = recommend_filters(
        recipe=revenue_recipe,
        registry_entries=mock_registry,
        time_ref="orders.created_at",
        dimension_refs=["orders.status"],
    )
    res_dict = res.model_dump()

    # Verify no options / distinct values are present
    assert "options" not in res_dict
    assert "values" not in res_dict
    for rec in res_dict["recommendations"]:
        assert "options" not in rec
        assert "values" not in rec


# ============================================================
# 30. NO SQL IN FILTER RECOMMENDER
# ============================================================

def test_filter_recommender_contains_no_sql_execution():
    import services.filter_recommender as fr_module
    src = inspect.getsource(fr_module)

    assert "SELECT " not in src
    assert "cursor." not in src
    assert "conn.execute" not in src
    assert "db.execute" not in src
    assert "db.query" not in src


# ============================================================
# 31. NO LLM IN FILTER RECOMMENDER
# ============================================================

def test_filter_recommender_contains_no_llm():
    import services.filter_recommender as fr_module
    src = inspect.getsource(fr_module)

    assert "openai" not in src.lower()
    assert "anthropic" not in src.lower()
    assert "gemini" not in src.lower()
    assert "google.generativeai" not in src.lower()
    assert "langchain" not in src.lower()


# ============================================================
# 32 & 33. METRICEXECUTOR AND DERIVEDMETRICEXECUTOR NEVER CALLED
# ============================================================

def test_executors_never_called(revenue_recipe, aov_recipe, mock_registry):
    with patch("services.metric_executor.MetricExecutor.execute") as mock_exec:
        with patch("services.derived_metric_executor.execute_metric_recipe") as mock_derived:
            recommend_filters(
                recipe=revenue_recipe,
                registry_entries=mock_registry,
                time_ref="orders.created_at",
                dimension_refs=["orders.status"],
            )
            recommend_filters(
                recipe=aov_recipe,
                registry_entries=mock_registry,
                time_ref="orders.created_at",
                dimension_refs=["orders.status"],
            )
            assert mock_exec.call_count == 0
            assert mock_derived.call_count == 0


# ============================================================
# 34. HELPER UNIT TESTS
# ============================================================

def test_min_cardinality_parameter_validation(revenue_recipe, mock_registry):
    with pytest.raises(FilterRecommendationError, match="must be at least 2"):
        recommend_filters(
            recipe=revenue_recipe,
            registry_entries=mock_registry,
            max_categorical_cardinality=1,
        )


def test_dict_registry_entries_supported(revenue_recipe):
    dict_registry = [
        {"table_name": "orders", "column_name": "status", "semantic_type": "CATEGORY", "cardinality": 4, "is_primary_key": False}
    ]
    res = recommend_filters(
        recipe=revenue_recipe,
        registry_entries=dict_registry,
        dimension_refs=["orders.status"],
    )
    assert len(res.recommendations) == 1
    assert res.recommendations[0].column_ref == "orders.status"
