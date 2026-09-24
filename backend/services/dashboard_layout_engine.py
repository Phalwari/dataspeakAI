from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict

from services.chart_recommender import (
    ChartRecommendation,
)
from services.filter_recommender import (
    FilterRecommendation,
    FilterRecommendationResult,
)
from services.metric_recipes import (
    DifferenceMetricRecipe,
    MetricRecipe,
    RatioMetricRecipe,
    get_recipe_operands,
)
from services.query_builder import parse_column_ref


# ============================================================
# CONSTANTS
# ============================================================

GRID_COLUMNS = 12
KPI_CARD_COL_SPAN = 3
CHART_COL_SPAN = 6


# ============================================================
# ERRORS
# ============================================================

class DashboardLayoutError(ValueError):
    pass


# ============================================================
# STRICT BASE MODEL
# ============================================================

class StrictLayoutModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


# ============================================================
# KPI CARD PLACEMENT
# ============================================================

class KpiCardPlacement(StrictLayoutModel):
    metric_id: str
    title: str

    order: int

    col_span: Literal[3] = 3


# ============================================================
# CHART PLACEMENT
# ============================================================

class ChartPlacement(StrictLayoutModel):
    metric_id: str
    title: str

    chart_type: Literal[
        "Line",
        "Bar",
    ]

    group_by_ref: str

    grouping_kind: Literal[
        "time",
        "dimension",
    ]

    order: int

    col_span: Literal[6] = 6

    reason: str


# ============================================================
# FILTER PLACEMENT
# ============================================================

class FilterPlacement(StrictLayoutModel):
    order: int

    recommendation: FilterRecommendation


# ============================================================
# FINAL DASHBOARD PLAN
# ============================================================

class DashboardLayoutPlan(StrictLayoutModel):
    layout_version: Literal["1.0"] = "1.0"

    source_table: str

    grid_columns: Literal[12] = 12

    kpi_cards: list[KpiCardPlacement]

    charts: list[ChartPlacement]

    filters: list[FilterPlacement]


# ============================================================
# RECIPE TABLE
# ============================================================

def _get_recipe_table(
    recipe: MetricRecipe,
) -> str:
    operands = get_recipe_operands(
        recipe
    )

    tables = {
        parse_column_ref(
            operand.target_ref
        )[0]
        for operand in operands
    }

    if len(tables) != 1:
        raise DashboardLayoutError(
            "Metric recipe must resolve to exactly "
            "one source table."
        )

    return next(iter(tables))


# ============================================================
# VALIDATE RECIPE SET
# ============================================================

def _validate_recipes(
    recipes: Sequence[MetricRecipe],
) -> tuple[
    str,
    dict[str, MetricRecipe],
]:
    if not recipes:
        raise DashboardLayoutError(
            "At least one metric recipe is required "
            "to compose a dashboard."
        )

    recipe_by_id: dict[
        str,
        MetricRecipe,
    ] = {}

    source_tables: set[str] = set()

    for recipe in recipes:
        if recipe.metric_id in recipe_by_id:
            raise DashboardLayoutError(
                f"Duplicate metric_id "
                f"'{recipe.metric_id}' "
                "cannot enter one dashboard layout."
            )

        source_table = _get_recipe_table(
            recipe
        )

        source_tables.add(
            source_table
        )

        recipe_by_id[
            recipe.metric_id
        ] = recipe

    if len(source_tables) != 1:
        raise DashboardLayoutError(
            "Phase 2 dashboard composition supports "
            "exactly one source table. "
            "Multi-table composition requires Phase 3."
        )

    return (
        next(iter(source_tables)),
        recipe_by_id,
    )


# ============================================================
# VALIDATE CHART RECOMMENDATIONS
# ============================================================

def _validate_chart_recommendations(
    *,
    chart_recommendations: Sequence[
        ChartRecommendation
    ],
    recipe_by_id: Mapping[
        str,
        MetricRecipe,
    ],
    source_table: str,
) -> dict[
    str,
    ChartRecommendation,
]:
    chart_by_metric: dict[
        str,
        ChartRecommendation,
    ] = {}

    for chart in chart_recommendations:
        metric_id = chart.metric_id

        if metric_id not in recipe_by_id:
            raise DashboardLayoutError(
                f"Chart recommendation references "
                f"unknown metric_id '{metric_id}'."
            )

        if metric_id in chart_by_metric:
            raise DashboardLayoutError(
                f"Duplicate chart recommendation "
                f"for metric_id '{metric_id}'."
            )

        recipe = recipe_by_id[
            metric_id
        ]

        if chart.title != recipe.title:
            raise DashboardLayoutError(
                f"Chart recommendation title for "
                f"'{metric_id}' does not match "
                "the metric recipe title."
            )

        # ----------------------------------------
        # Derived metric capability guard
        # ----------------------------------------

        if isinstance(
            recipe,
            (
                RatioMetricRecipe,
                DifferenceMetricRecipe,
            ),
        ):
            if chart.chart_type != "KPI":
                raise DashboardLayoutError(
                    "Derived metrics currently support "
                    "scalar KPI placement only."
                )

        # ----------------------------------------
        # KPI chart recommendation
        # ----------------------------------------

        if chart.chart_type == "KPI":
            if (
                chart.group_by_ref is not None
                or chart.grouping_kind != "none"
            ):
                raise DashboardLayoutError(
                    f"KPI recommendation for "
                    f"'{metric_id}' cannot contain "
                    "a grouping reference."
                )

        # ----------------------------------------
        # Line / Bar recommendation
        # ----------------------------------------

        else:
            if not chart.group_by_ref:
                raise DashboardLayoutError(
                    f"Grouped chart for "
                    f"'{metric_id}' requires "
                    "group_by_ref."
                )

            group_table, _ = (
                parse_column_ref(
                    chart.group_by_ref
                )
            )

            if group_table != source_table:
                raise DashboardLayoutError(
                    "Cross-table chart placement "
                    "requires a validated "
                    "relationship path."
                )

            if (
                chart.chart_type == "Line"
                and chart.grouping_kind != "time"
            ):
                raise DashboardLayoutError(
                    "Line chart recommendation must "
                    "use grouping_kind='time'."
                )

            if (
                chart.chart_type == "Bar"
                and chart.grouping_kind
                != "dimension"
            ):
                raise DashboardLayoutError(
                    "Bar chart recommendation must "
                    "use grouping_kind='dimension'."
                )

        chart_by_metric[
            metric_id
        ] = chart

    expected_ids = set(
        recipe_by_id.keys()
    )

    actual_ids = set(
        chart_by_metric.keys()
    )

    missing = (
        expected_ids
        - actual_ids
    )

    if missing:
        raise DashboardLayoutError(
            "Missing chart recommendations for "
            f"metric IDs: {sorted(missing)}"
        )

    return chart_by_metric


# ============================================================
# VALIDATE FILTER RESULT MAP
# ============================================================

def _validate_filter_result_keys(
    *,
    filter_results_by_metric: Mapping[
        str,
        FilterRecommendationResult,
    ],
    recipe_by_id: Mapping[
        str,
        MetricRecipe,
    ],
) -> None:
    expected_ids = set(
        recipe_by_id.keys()
    )

    actual_ids = set(
        filter_results_by_metric.keys()
    )

    missing = (
        expected_ids
        - actual_ids
    )

    unknown = (
        actual_ids
        - expected_ids
    )

    if missing:
        raise DashboardLayoutError(
            "Missing filter recommendation results "
            f"for metric IDs: {sorted(missing)}"
        )

    if unknown:
        raise DashboardLayoutError(
            "Filter recommendation results contain "
            f"unknown metric IDs: {sorted(unknown)}"
        )


# ============================================================
# FILTER SIGNATURE
# ============================================================

def _filter_signature(
    recommendation: FilterRecommendation,
) -> dict:
    return recommendation.model_dump(
        mode="json"
    )


# ============================================================
# COMPOSE FILTERS
# ============================================================

def _compose_filters(
    *,
    recipes: Sequence[MetricRecipe],
    source_table: str,
    filter_results_by_metric: Mapping[
        str,
        FilterRecommendationResult,
    ],
) -> list[FilterPlacement]:
    discovered: list[
        tuple[
            int,
            int,
            FilterRecommendation,
        ]
    ] = []

    seen_filter_ids: dict[
        str,
        dict,
    ] = {}

    seen_columns: dict[
        str,
        dict,
    ] = {}

    discovery_index = 0

    for recipe in recipes:
        result = (
            filter_results_by_metric[
                recipe.metric_id
            ]
        )

        for recommendation in (
            result.recommendations
        ):
            column_table, _ = (
                parse_column_ref(
                    recommendation.column_ref
                )
            )

            if column_table != source_table:
                raise DashboardLayoutError(
                    "Cross-table filter placement "
                    "requires a validated "
                    "relationship path."
                )

            signature = (
                _filter_signature(
                    recommendation
                )
            )

            # ----------------------------------------
            # Same filter ID
            # ----------------------------------------

            existing_by_id = (
                seen_filter_ids.get(
                    recommendation.filter_id
                )
            )

            if existing_by_id is not None:
                if (
                    existing_by_id
                    != signature
                ):
                    raise DashboardLayoutError(
                        f"Conflicting filter "
                        f"definitions share filter_id "
                        f"'{recommendation.filter_id}'."
                    )

                continue

            # ----------------------------------------
            # Same column but incompatible config
            # ----------------------------------------

            existing_by_column = (
                seen_columns.get(
                    recommendation.column_ref
                )
            )

            if (
                existing_by_column
                is not None
                and existing_by_column
                != signature
            ):
                raise DashboardLayoutError(
                    f"Conflicting filter "
                    f"recommendations exist for "
                    f"column "
                    f"'{recommendation.column_ref}'."
                )

            seen_filter_ids[
                recommendation.filter_id
            ] = signature

            seen_columns[
                recommendation.column_ref
            ] = signature

            discovered.append(
                (
                    recommendation.priority,
                    discovery_index,
                    recommendation,
                )
            )

            discovery_index += 1

    discovered.sort(
        key=lambda item: (
            item[0],
            item[1],
        )
    )

    return [
        FilterPlacement(
            order=index,
            recommendation=recommendation,
        )
        for index, (
            _,
            _,
            recommendation,
        ) in enumerate(discovered)
    ]


# ============================================================
# MAIN COMPOSER
# ============================================================

def compose_dashboard_layout(
    *,
    recipes: Sequence[MetricRecipe],
    chart_recommendations: Sequence[
        ChartRecommendation
    ],
    filter_results_by_metric: Mapping[
        str,
        FilterRecommendationResult,
    ],
) -> DashboardLayoutPlan:
    (
        source_table,
        recipe_by_id,
    ) = _validate_recipes(
        recipes
    )

    chart_by_metric = (
        _validate_chart_recommendations(
            chart_recommendations=(
                chart_recommendations
            ),
            recipe_by_id=recipe_by_id,
            source_table=source_table,
        )
    )

    _validate_filter_result_keys(
        filter_results_by_metric=(
            filter_results_by_metric
        ),
        recipe_by_id=recipe_by_id,
    )

    # ========================================================
    # KPI CARDS
    # ========================================================

    kpi_cards = [
        KpiCardPlacement(
            metric_id=recipe.metric_id,
            title=recipe.title,
            order=index,
            col_span=KPI_CARD_COL_SPAN,
        )
        for index, recipe in enumerate(
            recipes
        )
    ]

    # ========================================================
    # GROUPED CHARTS
    # ========================================================

    charts: list[
        ChartPlacement
    ] = []

    for recipe in recipes:
        recommendation = (
            chart_by_metric[
                recipe.metric_id
            ]
        )

        # KPI recommendation is already represented
        # by the KPI card above.
        if (
            recommendation.chart_type
            == "KPI"
        ):
            continue

        if not recommendation.group_by_ref:
            raise DashboardLayoutError(
                f"Grouped chart for "
                f"'{recipe.metric_id}' "
                "has no group_by_ref."
            )

        charts.append(
            ChartPlacement(
                metric_id=recipe.metric_id,
                title=recipe.title,
                chart_type=(
                    recommendation.chart_type
                ),
                group_by_ref=(
                    recommendation.group_by_ref
                ),
                grouping_kind=(
                    recommendation.grouping_kind
                ),
                order=len(charts),
                col_span=CHART_COL_SPAN,
                reason=(
                    recommendation.reason
                ),
            )
        )

    # ========================================================
    # GLOBAL FILTERS
    # ========================================================

    filters = _compose_filters(
        recipes=recipes,
        source_table=source_table,
        filter_results_by_metric=(
            filter_results_by_metric
        ),
    )

    return DashboardLayoutPlan(
        layout_version="1.0",
        source_table=source_table,
        grid_columns=GRID_COLUMNS,
        kpi_cards=kpi_cards,
        charts=charts,
        filters=filters,
    )
