from __future__ import annotations

from typing import Any, Literal, Sequence

from pydantic import BaseModel, ConfigDict

from services.metric_recipes import (
    AtomicMetricRecipe,
    DifferenceMetricRecipe,
    MetricRecipe,
    RatioMetricRecipe,
    get_recipe_operands,
)
from services.query_builder import parse_column_ref


ChartType = Literal[
    "KPI",
    "Line",
    "Bar",
]


GroupingKind = Literal[
    "none",
    "time",
    "dimension",
]


class ChartRecommendationError(ValueError):
    """
    Raised when a chart recommendation cannot be created safely.
    """

    pass


class ChartRecommendation(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    metric_id: str
    title: str

    chart_type: ChartType

    group_by_ref: str | None = None
    grouping_kind: GroupingKind = "none"

    priority: int = 1

    reason: str


# ============================================================
# RECIPE TABLE
# ============================================================

def _get_recipe_table(
    recipe: MetricRecipe,
) -> str:
    """
    Current Phase 2 chart recommendations are single-table only.
    """

    operands = get_recipe_operands(recipe)

    tables = {
        parse_column_ref(
            operand.target_ref
        )[0]
        for operand in operands
    }

    if len(tables) != 1:
        raise ChartRecommendationError(
            "Chart recommendation requires exactly "
            "one validated source table."
        )

    return next(iter(tables))


# ============================================================
# REGISTRY LOOKUP
# ============================================================

def _find_registry_column(
    *,
    ref: str,
    registry_entries: Sequence[Any],
) -> Any:
    """
    Resolve an explicitly supplied qualified reference
    against verified SchemaRegistry metadata.
    """

    table_name, column_name = parse_column_ref(ref)

    for row in registry_entries:
        row_table = getattr(row, "table_name", None)
        row_col = getattr(row, "column_name", None)
        if row_table is None and isinstance(row, dict):
            row_table = row.get("table_name")
            row_col = row.get("column_name")

        if (
            str(row_table) == table_name
            and str(row_col) == column_name
        ):
            return row

    raise ChartRecommendationError(
        f"Chart grouping column "
        f"'{table_name}.{column_name}' "
        "does not exist in verified SchemaRegistry."
    )


# ============================================================
# GROUPING VALIDATION
# ============================================================

def _validate_group_ref(
    *,
    ref: str,
    recipe_table: str,
    registry_entries: Sequence[Any],
) -> str:
    """
    Grouping columns must:

    - be qualified table.column
    - exist in SchemaRegistry
    - belong to the metric's table

    No joins are inferred.
    """

    try:
        table_name, column_name = parse_column_ref(
            ref
        )
    except ValueError as exc:
        raise ChartRecommendationError(
            "Chart grouping references must use "
            "qualified table.column syntax."
        ) from exc

    if table_name != recipe_table:
        raise ChartRecommendationError(
            "Cross-table chart grouping requires "
            "a validated relationship path."
        )

    _find_registry_column(
        ref=ref,
        registry_entries=registry_entries,
    )

    return f"{table_name}.{column_name}"


# ============================================================
# MAIN RECOMMENDER
# ============================================================

def recommend_chart(
    *,
    recipe: MetricRecipe,
    registry_entries: Sequence[Any],
    dimension_ref: str | None = None,
    time_ref: str | None = None,
) -> ChartRecommendation:
    """
    Deterministically recommend one chart representation.

    Phase 2D rules:

    Atomic + time:
        Line

    Atomic + categorical dimension:
        Bar

    Atomic scalar:
        KPI

    Ratio:
        KPI

    Difference:
        KPI

    Derived grouped charts are intentionally deferred because
    Phase 2C executes derived recipes as scalar values only.
    """

    recipe_table = _get_recipe_table(
        recipe
    )

    # ========================================================
    # DERIVED METRICS
    # ========================================================

    if isinstance(
        recipe,
        (
            RatioMetricRecipe,
            DifferenceMetricRecipe,
        ),
    ):
        return ChartRecommendation(
            metric_id=recipe.metric_id,
            title=recipe.title,
            chart_type="KPI",
            group_by_ref=None,
            grouping_kind="none",
            priority=1,
            reason=(
                "Derived metric currently supports "
                "scalar execution only."
            ),
        )

    # ========================================================
    # ATOMIC METRIC
    # ========================================================

    if not isinstance(
        recipe,
        AtomicMetricRecipe,
    ):
        raise ChartRecommendationError(
            f"Unsupported MetricRecipe type: "
            f"{type(recipe).__name__}"
        )

    # ========================================================
    # TIME SERIES
    # ========================================================

    if time_ref:
        validated_ref = _validate_group_ref(
            ref=time_ref,
            recipe_table=recipe_table,
            registry_entries=registry_entries,
        )

        return ChartRecommendation(
            metric_id=recipe.metric_id,
            title=recipe.title,
            chart_type="Line",
            group_by_ref=validated_ref,
            grouping_kind="time",
            priority=1,
            reason=(
                "Atomic metric has an explicitly confirmed "
                "same-table time grouping."
            ),
        )

    # ========================================================
    # DIMENSIONAL COMPARISON
    # ========================================================

    if dimension_ref:
        validated_ref = _validate_group_ref(
            ref=dimension_ref,
            recipe_table=recipe_table,
            registry_entries=registry_entries,
        )

        return ChartRecommendation(
            metric_id=recipe.metric_id,
            title=recipe.title,
            chart_type="Bar",
            group_by_ref=validated_ref,
            grouping_kind="dimension",
            priority=1,
            reason=(
                "Atomic metric has an explicitly confirmed "
                "same-table categorical grouping."
            ),
        )

    # ========================================================
    # SCALAR KPI
    # ========================================================

    return ChartRecommendation(
        metric_id=recipe.metric_id,
        title=recipe.title,
        chart_type="KPI",
        group_by_ref=None,
        grouping_kind="none",
        priority=1,
        reason=(
            "No explicit grouping reference "
            "was supplied."
        ),
    )
