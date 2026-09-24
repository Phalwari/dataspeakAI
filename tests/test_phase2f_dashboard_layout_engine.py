import inspect
import os
import sys
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
from services.chart_recommender import ChartRecommendation
from services.filter_recommender import (
    DateRangeFilterRecommendation,
    FilterRecommendationResult,
    SelectFilterRecommendation,
)
from services.dashboard_layout_engine import (
    CHART_COL_SPAN,
    GRID_COLUMNS,
    KPI_CARD_COL_SPAN,
    DashboardLayoutError,
    DashboardLayoutPlan,
    compose_dashboard_layout,
)


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
def orders_count_recipe():
    return AtomicMetricRecipe(
        metric_id="total_orders",
        title="Total Orders",
        format="number",
        operand=AtomicMetricOperand(
            target_ref="orders.order_id",
            aggregation="COUNT",
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


@pytest.fixture
def customer_recipe():
    return AtomicMetricRecipe(
        metric_id="total_customers",
        title="Total Customers",
        format="number",
        operand=AtomicMetricOperand(
            target_ref="customers.id",
            aggregation="COUNT",
        ),
    )


@pytest.fixture
def common_filters():
    date_filter = DateRangeFilterRecommendation(
        filter_id="orders_created_at_date_range",
        label="Created At",
        column_ref="orders.created_at",
        start_operator=">=",
        end_operator="<=",
        priority=1,
        reason="Time filtering",
    )
    status_filter = SelectFilterRecommendation(
        filter_id="orders_status_select",
        label="Status",
        column_ref="orders.status",
        operator="IN",
        cardinality=4,
        max_options=50,
        priority=2,
        reason="Status filtering",
    )
    return {
        "date": date_filter,
        "status": status_filter,
    }


# ============================================================
# 1. EMPTY RECIPE SET REJECTED
# ============================================================

def test_empty_recipe_set_rejected():
    with pytest.raises(DashboardLayoutError, match="At least one metric recipe is required"):
        compose_dashboard_layout(
            recipes=[],
            chart_recommendations=[],
            filter_results_by_metric={},
        )


# ============================================================
# 2. DUPLICATE METRIC_ID REJECTED
# ============================================================

def test_duplicate_metric_id_rejected(revenue_recipe):
    with pytest.raises(DashboardLayoutError, match="Duplicate metric_id 'total_revenue'"):
        compose_dashboard_layout(
            recipes=[revenue_recipe, revenue_recipe],
            chart_recommendations=[],
            filter_results_by_metric={},
        )


# ============================================================
# 3. MULTIPLE SOURCE TABLES REJECTED
# ============================================================

def test_multiple_source_tables_rejected(revenue_recipe, customer_recipe):
    with pytest.raises(DashboardLayoutError, match="supports exactly one source table"):
        compose_dashboard_layout(
            recipes=[revenue_recipe, customer_recipe],
            chart_recommendations=[],
            filter_results_by_metric={},
        )


# ============================================================
# 4. KPI RECOMMENDATION -> CARD ONLY (0 CHARTS)
# ============================================================

def test_kpi_recommendation_card_only(revenue_recipe):
    chart_rec = ChartRecommendation(
        metric_id="total_revenue",
        title="Total Revenue",
        chart_type="KPI",
        group_by_ref=None,
        grouping_kind="none",
        priority=1,
        reason="Scalar KPI",
    )
    plan = compose_dashboard_layout(
        recipes=[revenue_recipe],
        chart_recommendations=[chart_rec],
        filter_results_by_metric={"total_revenue": FilterRecommendationResult(recommendations=[], skipped=[])},
    )

    assert len(plan.kpi_cards) == 1
    assert plan.kpi_cards[0].metric_id == "total_revenue"
    assert len(plan.charts) == 0


# ============================================================
# 5. LINE RECOMMENDATION -> CARD + CHART
# ============================================================

def test_line_recommendation_produces_card_and_chart(revenue_recipe):
    chart_rec = ChartRecommendation(
        metric_id="total_revenue",
        title="Total Revenue",
        chart_type="Line",
        group_by_ref="orders.created_at",
        grouping_kind="time",
        priority=1,
        reason="Time series",
    )
    plan = compose_dashboard_layout(
        recipes=[revenue_recipe],
        chart_recommendations=[chart_rec],
        filter_results_by_metric={"total_revenue": FilterRecommendationResult(recommendations=[], skipped=[])},
    )

    assert len(plan.kpi_cards) == 1
    assert plan.kpi_cards[0].metric_id == "total_revenue"
    assert len(plan.charts) == 1
    assert plan.charts[0].metric_id == "total_revenue"
    assert plan.charts[0].chart_type == "Line"
    assert plan.charts[0].group_by_ref == "orders.created_at"
    assert plan.charts[0].grouping_kind == "time"
    assert plan.charts[0].col_span == 6


# ============================================================
# 6. BAR RECOMMENDATION -> CARD + CHART
# ============================================================

def test_bar_recommendation_produces_card_and_chart(orders_count_recipe):
    chart_rec = ChartRecommendation(
        metric_id="total_orders",
        title="Total Orders",
        chart_type="Bar",
        group_by_ref="orders.status",
        grouping_kind="dimension",
        priority=1,
        reason="Categorical distribution",
    )
    plan = compose_dashboard_layout(
        recipes=[orders_count_recipe],
        chart_recommendations=[chart_rec],
        filter_results_by_metric={"total_orders": FilterRecommendationResult(recommendations=[], skipped=[])},
    )

    assert len(plan.kpi_cards) == 1
    assert len(plan.charts) == 1
    assert plan.charts[0].metric_id == "total_orders"
    assert plan.charts[0].chart_type == "Bar"
    assert plan.charts[0].group_by_ref == "orders.status"
    assert plan.charts[0].grouping_kind == "dimension"
    assert plan.charts[0].col_span == 6


# ============================================================
# 7 & 8. RATIO KPI AND DIFFERENCE KPI -> CARD ONLY
# ============================================================

def test_derived_recipes_produce_kpi_card_only(aov_recipe, gross_profit_recipe):
    aov_chart = ChartRecommendation(
        metric_id="aov",
        title="Average Order Value",
        chart_type="KPI",
        group_by_ref=None,
        grouping_kind="none",
        priority=1,
        reason="Scalar only",
    )
    profit_chart = ChartRecommendation(
        metric_id="gross_profit",
        title="Gross Profit",
        chart_type="KPI",
        group_by_ref=None,
        grouping_kind="none",
        priority=1,
        reason="Scalar only",
    )
    plan = compose_dashboard_layout(
        recipes=[aov_recipe, gross_profit_recipe],
        chart_recommendations=[aov_chart, profit_chart],
        filter_results_by_metric={
            "aov": FilterRecommendationResult(recommendations=[], skipped=[]),
            "gross_profit": FilterRecommendationResult(recommendations=[], skipped=[]),
        },
    )

    assert len(plan.kpi_cards) == 2
    assert plan.kpi_cards[0].metric_id == "aov"
    assert plan.kpi_cards[1].metric_id == "gross_profit"
    assert len(plan.charts) == 0


# ============================================================
# PHASE 2F.1: DERIVED CHART CAPABILITY GUARDS
# ============================================================

def test_ratio_kpi_still_allowed(aov_recipe):
    chart_rec = ChartRecommendation(
        metric_id="aov",
        title="Average Order Value",
        chart_type="KPI",
        group_by_ref=None,
        grouping_kind="none",
        reason="Scalar KPI only",
    )
    plan = compose_dashboard_layout(
        recipes=[aov_recipe],
        chart_recommendations=[chart_rec],
        filter_results_by_metric={"aov": FilterRecommendationResult(recommendations=[], skipped=[])},
    )
    assert len(plan.kpi_cards) == 1
    assert plan.kpi_cards[0].metric_id == "aov"
    assert len(plan.charts) == 0


def test_ratio_line_chart_rejected(aov_recipe):
    chart_rec = ChartRecommendation(
        metric_id="aov",
        title="Average Order Value",
        chart_type="Line",
        group_by_ref="orders.created_at",
        grouping_kind="time",
        reason="Invalid grouped derived",
    )
    with pytest.raises(
        DashboardLayoutError,
        match="Derived metrics currently support scalar KPI placement only\\.",
    ):
        compose_dashboard_layout(
            recipes=[aov_recipe],
            chart_recommendations=[chart_rec],
            filter_results_by_metric={"aov": FilterRecommendationResult(recommendations=[], skipped=[])},
        )


def test_ratio_bar_chart_rejected(aov_recipe):
    chart_rec = ChartRecommendation(
        metric_id="aov",
        title="Average Order Value",
        chart_type="Bar",
        group_by_ref="orders.status",
        grouping_kind="dimension",
        reason="Invalid grouped derived",
    )
    with pytest.raises(
        DashboardLayoutError,
        match="Derived metrics currently support scalar KPI placement only\\.",
    ):
        compose_dashboard_layout(
            recipes=[aov_recipe],
            chart_recommendations=[chart_rec],
            filter_results_by_metric={"aov": FilterRecommendationResult(recommendations=[], skipped=[])},
        )


def test_difference_kpi_still_allowed(gross_profit_recipe):
    chart_rec = ChartRecommendation(
        metric_id="gross_profit",
        title="Gross Profit",
        chart_type="KPI",
        group_by_ref=None,
        grouping_kind="none",
        reason="Scalar KPI only",
    )
    plan = compose_dashboard_layout(
        recipes=[gross_profit_recipe],
        chart_recommendations=[chart_rec],
        filter_results_by_metric={"gross_profit": FilterRecommendationResult(recommendations=[], skipped=[])},
    )
    assert len(plan.kpi_cards) == 1
    assert plan.kpi_cards[0].metric_id == "gross_profit"
    assert len(plan.charts) == 0


def test_difference_line_chart_rejected(gross_profit_recipe):
    chart_rec = ChartRecommendation(
        metric_id="gross_profit",
        title="Gross Profit",
        chart_type="Line",
        group_by_ref="orders.created_at",
        grouping_kind="time",
        reason="Invalid grouped derived",
    )
    with pytest.raises(
        DashboardLayoutError,
        match="Derived metrics currently support scalar KPI placement only\\.",
    ):
        compose_dashboard_layout(
            recipes=[gross_profit_recipe],
            chart_recommendations=[chart_rec],
            filter_results_by_metric={"gross_profit": FilterRecommendationResult(recommendations=[], skipped=[])},
        )


def test_difference_bar_chart_rejected(gross_profit_recipe):
    chart_rec = ChartRecommendation(
        metric_id="gross_profit",
        title="Gross Profit",
        chart_type="Bar",
        group_by_ref="orders.status",
        grouping_kind="dimension",
        reason="Invalid grouped derived",
    )
    with pytest.raises(
        DashboardLayoutError,
        match="Derived metrics currently support scalar KPI placement only\\.",
    ):
        compose_dashboard_layout(
            recipes=[gross_profit_recipe],
            chart_recommendations=[chart_rec],
            filter_results_by_metric={"gross_profit": FilterRecommendationResult(recommendations=[], skipped=[])},
        )



# ============================================================
# 9 & 10. EVERY RECIPE GETS EXACTLY ONE CARD & ORDER PRESERVED
# ============================================================

def test_every_recipe_gets_card_in_order(revenue_recipe, orders_count_recipe, aov_recipe, gross_profit_recipe):
    recipes = [revenue_recipe, orders_count_recipe, aov_recipe, gross_profit_recipe]
    chart_recs = [
        ChartRecommendation(metric_id="total_revenue", title="Total Revenue", chart_type="Line", group_by_ref="orders.created_at", grouping_kind="time", reason="r"),
        ChartRecommendation(metric_id="total_orders", title="Total Orders", chart_type="Bar", group_by_ref="orders.status", grouping_kind="dimension", reason="r"),
        ChartRecommendation(metric_id="aov", title="Average Order Value", chart_type="KPI", reason="r"),
        ChartRecommendation(metric_id="gross_profit", title="Gross Profit", chart_type="KPI", reason="r"),
    ]
    filters = {m.metric_id: FilterRecommendationResult(recommendations=[], skipped=[]) for m in recipes}

    plan = compose_dashboard_layout(
        recipes=recipes,
        chart_recommendations=chart_recs,
        filter_results_by_metric=filters,
    )

    assert len(plan.kpi_cards) == 4
    for idx, expected_id in enumerate(["total_revenue", "total_orders", "aov", "gross_profit"]):
        assert plan.kpi_cards[idx].metric_id == expected_id
        assert plan.kpi_cards[idx].order == idx


# ============================================================
# 11. MISSING CHART RECOMMENDATION REJECTED
# ============================================================

def test_missing_chart_recommendation_rejected(revenue_recipe, orders_count_recipe):
    rev_chart = ChartRecommendation(metric_id="total_revenue", title="Total Revenue", chart_type="KPI", reason="r")
    with pytest.raises(DashboardLayoutError, match="Missing chart recommendations for metric IDs: \\['total_orders'\\]"):
        compose_dashboard_layout(
            recipes=[revenue_recipe, orders_count_recipe],
            chart_recommendations=[rev_chart],
            filter_results_by_metric={
                "total_revenue": FilterRecommendationResult(recommendations=[], skipped=[]),
                "total_orders": FilterRecommendationResult(recommendations=[], skipped=[]),
            },
        )


# ============================================================
# 12. DUPLICATE CHART RECOMMENDATION REJECTED
# ============================================================

def test_duplicate_chart_recommendation_rejected(revenue_recipe):
    rev_chart = ChartRecommendation(metric_id="total_revenue", title="Total Revenue", chart_type="KPI", reason="r")
    with pytest.raises(DashboardLayoutError, match="Duplicate chart recommendation for metric_id 'total_revenue'"):
        compose_dashboard_layout(
            recipes=[revenue_recipe],
            chart_recommendations=[rev_chart, rev_chart],
            filter_results_by_metric={"total_revenue": FilterRecommendationResult(recommendations=[], skipped=[])},
        )


# ============================================================
# 13. UNKNOWN CHART METRIC REJECTED
# ============================================================

def test_unknown_chart_metric_rejected(revenue_recipe):
    unknown_chart = ChartRecommendation(metric_id="unknown_metric", title="Unknown", chart_type="KPI", reason="r")
    with pytest.raises(DashboardLayoutError, match="references unknown metric_id 'unknown_metric'"):
        compose_dashboard_layout(
            recipes=[revenue_recipe],
            chart_recommendations=[unknown_chart],
            filter_results_by_metric={"total_revenue": FilterRecommendationResult(recommendations=[], skipped=[])},
        )


# ============================================================
# 14. CHART TITLE MISMATCH REJECTED
# ============================================================

def test_chart_title_mismatch_rejected(revenue_recipe):
    mismatch_chart = ChartRecommendation(metric_id="total_revenue", title="Wrong Title", chart_type="KPI", reason="r")
    with pytest.raises(DashboardLayoutError, match="does not match the metric recipe title"):
        compose_dashboard_layout(
            recipes=[revenue_recipe],
            chart_recommendations=[mismatch_chart],
            filter_results_by_metric={"total_revenue": FilterRecommendationResult(recommendations=[], skipped=[])},
        )


# ============================================================
# 15. LINE WITHOUT TIME GROUPING REJECTED
# ============================================================

def test_line_without_time_grouping_rejected(revenue_recipe):
    bad_line = ChartRecommendation(
        metric_id="total_revenue",
        title="Total Revenue",
        chart_type="Line",
        group_by_ref="orders.created_at",
        grouping_kind="dimension",  # Invalid for Line!
        reason="r",
    )
    with pytest.raises(DashboardLayoutError, match="Line chart recommendation must use grouping_kind='time'"):
        compose_dashboard_layout(
            recipes=[revenue_recipe],
            chart_recommendations=[bad_line],
            filter_results_by_metric={"total_revenue": FilterRecommendationResult(recommendations=[], skipped=[])},
        )


# ============================================================
# 16. BAR WITHOUT DIMENSION GROUPING REJECTED
# ============================================================

def test_bar_without_dimension_grouping_rejected(orders_count_recipe):
    bad_bar = ChartRecommendation(
        metric_id="total_orders",
        title="Total Orders",
        chart_type="Bar",
        group_by_ref="orders.status",
        grouping_kind="time",  # Invalid for Bar!
        reason="r",
    )
    with pytest.raises(DashboardLayoutError, match="Bar chart recommendation must use grouping_kind='dimension'"):
        compose_dashboard_layout(
            recipes=[orders_count_recipe],
            chart_recommendations=[bad_bar],
            filter_results_by_metric={"total_orders": FilterRecommendationResult(recommendations=[], skipped=[])},
        )


# ============================================================
# 17. CROSS-TABLE CHART GROUPING REJECTED
# ============================================================

def test_cross_table_chart_grouping_rejected(revenue_recipe):
    cross_chart = ChartRecommendation(
        metric_id="total_revenue",
        title="Total Revenue",
        chart_type="Bar",
        group_by_ref="customers.region",  # Cross-table!
        grouping_kind="dimension",
        reason="r",
    )
    with pytest.raises(DashboardLayoutError, match="Cross-table chart placement requires a validated relationship path"):
        compose_dashboard_layout(
            recipes=[revenue_recipe],
            chart_recommendations=[cross_chart],
            filter_results_by_metric={"total_revenue": FilterRecommendationResult(recommendations=[], skipped=[])},
        )


# ============================================================
# 18. MISSING FILTER RESULT REJECTED
# ============================================================

def test_missing_filter_result_rejected(revenue_recipe, orders_count_recipe):
    rev_chart = ChartRecommendation(metric_id="total_revenue", title="Total Revenue", chart_type="KPI", reason="r")
    orders_chart = ChartRecommendation(metric_id="total_orders", title="Total Orders", chart_type="KPI", reason="r")
    with pytest.raises(DashboardLayoutError, match="Missing filter recommendation results for metric IDs: \\['total_orders'\\]"):
        compose_dashboard_layout(
            recipes=[revenue_recipe, orders_count_recipe],
            chart_recommendations=[rev_chart, orders_chart],
            filter_results_by_metric={"total_revenue": FilterRecommendationResult(recommendations=[], skipped=[])},
        )


# ============================================================
# 19. UNKNOWN FILTER-RESULT METRIC REJECTED
# ============================================================

def test_unknown_filter_result_metric_rejected(revenue_recipe):
    rev_chart = ChartRecommendation(metric_id="total_revenue", title="Total Revenue", chart_type="KPI", reason="r")
    with pytest.raises(DashboardLayoutError, match="Filter recommendation results contain unknown metric IDs"):
        compose_dashboard_layout(
            recipes=[revenue_recipe],
            chart_recommendations=[rev_chart],
            filter_results_by_metric={
                "total_revenue": FilterRecommendationResult(recommendations=[], skipped=[]),
                "stray_metric": FilterRecommendationResult(recommendations=[], skipped=[]),
            },
        )


# ============================================================
# 20. IDENTICAL GLOBAL FILTERS DEDUPLICATED
# ============================================================

def test_identical_global_filters_deduplicated(revenue_recipe, orders_count_recipe, common_filters):
    chart_recs = [
        ChartRecommendation(metric_id="total_revenue", title="Total Revenue", chart_type="KPI", reason="r"),
        ChartRecommendation(metric_id="total_orders", title="Total Orders", chart_type="KPI", reason="r"),
    ]
    # Both metrics recommend the same status filter
    filters_map = {
        "total_revenue": FilterRecommendationResult(recommendations=[common_filters["status"]], skipped=[]),
        "total_orders": FilterRecommendationResult(recommendations=[common_filters["status"]], skipped=[]),
    }

    plan = compose_dashboard_layout(
        recipes=[revenue_recipe, orders_count_recipe],
        chart_recommendations=chart_recs,
        filter_results_by_metric=filters_map,
    )

    assert len(plan.filters) == 1
    assert plan.filters[0].recommendation.filter_id == "orders_status_select"
    assert plan.filters[0].order == 0


# ============================================================
# 21. CONFLICTING FILTER_ID REJECTED
# ============================================================

def test_conflicting_filter_id_rejected(revenue_recipe, orders_count_recipe):
    chart_recs = [
        ChartRecommendation(metric_id="total_revenue", title="Total Revenue", chart_type="KPI", reason="r"),
        ChartRecommendation(metric_id="total_orders", title="Total Orders", chart_type="KPI", reason="r"),
    ]
    filter1 = SelectFilterRecommendation(
        filter_id="status_filter",
        label="Status 1",
        column_ref="orders.status",
        cardinality=4,
        reason="r",
    )
    filter2 = SelectFilterRecommendation(
        filter_id="status_filter",
        label="Status 2 Incompatible",
        column_ref="orders.status",
        cardinality=10,  # Incompatible!
        reason="r",
    )
    filters_map = {
        "total_revenue": FilterRecommendationResult(recommendations=[filter1], skipped=[]),
        "total_orders": FilterRecommendationResult(recommendations=[filter2], skipped=[]),
    }

    with pytest.raises(DashboardLayoutError, match="Conflicting filter definitions share filter_id 'status_filter'"):
        compose_dashboard_layout(
            recipes=[revenue_recipe, orders_count_recipe],
            chart_recommendations=chart_recs,
            filter_results_by_metric=filters_map,
        )


# ============================================================
# 22. CONFLICTING SAME-COLUMN FILTERS REJECTED
# ============================================================

def test_conflicting_same_column_filters_rejected(revenue_recipe, orders_count_recipe):
    chart_recs = [
        ChartRecommendation(metric_id="total_revenue", title="Total Revenue", chart_type="KPI", reason="r"),
        ChartRecommendation(metric_id="total_orders", title="Total Orders", chart_type="KPI", reason="r"),
    ]
    filter1 = SelectFilterRecommendation(
        filter_id="filter_a",
        label="Status A",
        column_ref="orders.status",
        cardinality=4,
        reason="r",
    )
    filter2 = SelectFilterRecommendation(
        filter_id="filter_b",
        label="Status B",
        column_ref="orders.status",
        cardinality=10,
        reason="r",
    )
    filters_map = {
        "total_revenue": FilterRecommendationResult(recommendations=[filter1], skipped=[]),
        "total_orders": FilterRecommendationResult(recommendations=[filter2], skipped=[]),
    }

    with pytest.raises(DashboardLayoutError, match="Conflicting filter recommendations exist for column 'orders.status'"):
        compose_dashboard_layout(
            recipes=[revenue_recipe, orders_count_recipe],
            chart_recommendations=chart_recs,
            filter_results_by_metric=filters_map,
        )


# ============================================================
# 23. CROSS-TABLE FILTER PLACEMENT REJECTED
# ============================================================

def test_cross_table_filter_placement_rejected(revenue_recipe):
    rev_chart = ChartRecommendation(metric_id="total_revenue", title="Total Revenue", chart_type="KPI", reason="r")
    cross_filter = SelectFilterRecommendation(
        filter_id="customers_region_select",
        label="Region",
        column_ref="customers.region",  # Cross-table!
        cardinality=5,
        reason="r",
    )
    filters_map = {
        "total_revenue": FilterRecommendationResult(recommendations=[cross_filter], skipped=[]),
    }

    with pytest.raises(DashboardLayoutError, match="Cross-table filter placement requires a validated relationship path"):
        compose_dashboard_layout(
            recipes=[revenue_recipe],
            chart_recommendations=[rev_chart],
            filter_results_by_metric=filters_map,
        )


# ============================================================
# 24. DATE FILTERS ORDERED BEFORE SELECT FILTERS
# ============================================================

def test_date_filters_ordered_before_select_filters(revenue_recipe, common_filters):
    rev_chart = ChartRecommendation(metric_id="total_revenue", title="Total Revenue", chart_type="KPI", reason="r")
    # Supply select first in the list to verify priority sorts date_range (priority 1) first
    filters_map = {
        "total_revenue": FilterRecommendationResult(
            recommendations=[common_filters["status"], common_filters["date"]],
            skipped=[],
        ),
    }

    plan = compose_dashboard_layout(
        recipes=[revenue_recipe],
        chart_recommendations=[rev_chart],
        filter_results_by_metric=filters_map,
    )

    assert len(plan.filters) == 2
    assert plan.filters[0].recommendation.filter_type == "date_range"
    assert plan.filters[0].order == 0
    assert plan.filters[1].recommendation.filter_type == "select"
    assert plan.filters[1].order == 1


# ============================================================
# 25, 26, 27. GRID CONSTANTS & SPAN INTEGRITY
# ============================================================

def test_grid_constants_and_spans(revenue_recipe, orders_count_recipe, common_filters):
    chart_recs = [
        ChartRecommendation(metric_id="total_revenue", title="Total Revenue", chart_type="Line", group_by_ref="orders.created_at", grouping_kind="time", reason="r"),
        ChartRecommendation(metric_id="total_orders", title="Total Orders", chart_type="Bar", group_by_ref="orders.status", grouping_kind="dimension", reason="r"),
    ]
    filters_map = {
        "total_revenue": FilterRecommendationResult(recommendations=[common_filters["date"]], skipped=[]),
        "total_orders": FilterRecommendationResult(recommendations=[common_filters["status"]], skipped=[]),
    }

    plan = compose_dashboard_layout(
        recipes=[revenue_recipe, orders_count_recipe],
        chart_recommendations=chart_recs,
        filter_results_by_metric=filters_map,
    )

    assert plan.grid_columns == GRID_COLUMNS == 12
    assert plan.kpi_cards[0].col_span == KPI_CARD_COL_SPAN == 3
    assert plan.charts[0].col_span == CHART_COL_SPAN == 6


# ============================================================
# 28. REPEATED COMPOSITION IDENTICAL
# ============================================================

def test_repeated_composition_identical(revenue_recipe, common_filters):
    rev_chart = ChartRecommendation(metric_id="total_revenue", title="Total Revenue", chart_type="Line", group_by_ref="orders.created_at", grouping_kind="time", reason="r")
    filters_map = {"total_revenue": FilterRecommendationResult(recommendations=[common_filters["date"]], skipped=[])}

    plan1 = compose_dashboard_layout(recipes=[revenue_recipe], chart_recommendations=[rev_chart], filter_results_by_metric=filters_map)
    plan2 = compose_dashboard_layout(recipes=[revenue_recipe], chart_recommendations=[rev_chart], filter_results_by_metric=filters_map)

    assert plan1.model_dump() == plan2.model_dump()


# ============================================================
# 29. NO SQL IN DASHBOARD LAYOUT ENGINE
# ============================================================

def test_dashboard_layout_engine_contains_no_sql():
    import services.dashboard_layout_engine as dle_module
    src = inspect.getsource(dle_module)

    assert "SELECT " not in src
    assert "cursor." not in src
    assert "conn.execute" not in src
    assert "db.execute" not in src
    assert "db.query" not in src


# ============================================================
# 30. NO LLM IN DASHBOARD LAYOUT ENGINE
# ============================================================

def test_dashboard_layout_engine_contains_no_llm():
    import services.dashboard_layout_engine as dle_module
    src = inspect.getsource(dle_module)

    assert "openai" not in src.lower()
    assert "anthropic" not in src.lower()
    assert "gemini" not in src.lower()
    assert "google.generativeai" not in src.lower()
    assert "langchain" not in src.lower()


# ============================================================
# 31 & 32. METRICEXECUTOR AND DERIVEDMETRICEXECUTOR NEVER CALLED
# ============================================================

def test_executors_never_called(revenue_recipe, common_filters):
    rev_chart = ChartRecommendation(metric_id="total_revenue", title="Total Revenue", chart_type="Line", group_by_ref="orders.created_at", grouping_kind="time", reason="r")
    filters_map = {"total_revenue": FilterRecommendationResult(recommendations=[common_filters["date"]], skipped=[])}

    with patch("services.metric_executor.MetricExecutor.execute") as mock_exec:
        with patch("services.derived_metric_executor.execute_metric_recipe") as mock_derived:
            compose_dashboard_layout(
                recipes=[revenue_recipe],
                chart_recommendations=[rev_chart],
                filter_results_by_metric=filters_map,
            )
            assert mock_exec.call_count == 0
            assert mock_derived.call_count == 0


# ============================================================
# 33. NO PERSISTENCE OR ORM MUTATION
# ============================================================

def test_no_persistence_or_orm_mutation():
    import services.dashboard_layout_engine as dle_module
    src = inspect.getsource(dle_module)

    assert "db.commit" not in src
    assert "db.add" not in src
    assert "db.flush" not in src
    assert "models.DashboardLayout(" not in src
    assert "models.KpiDefinition(" not in src
