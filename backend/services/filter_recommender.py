from __future__ import annotations

import re
from typing import (
    Any,
    Annotated,
    Literal,
    Sequence,
    Union,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from services.metric_recipes import (
    MetricRecipe,
    get_recipe_operands,
)
from services.query_builder import parse_column_ref


# ============================================================
# TYPES
# ============================================================

FilterType = Literal[
    "date_range",
    "select",
]


class FilterRecommendationError(ValueError):
    pass


class StrictFilterModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


# ============================================================
# DATE RANGE FILTER
# ============================================================

class DateRangeFilterRecommendation(
    StrictFilterModel
):
    filter_type: Literal["date_range"] = "date_range"

    filter_id: str
    label: str

    column_ref: str

    start_operator: Literal[">="] = ">="
    end_operator: Literal["<="] = "<="

    priority: int = 1

    reason: str


# ============================================================
# CATEGORICAL DROPDOWN FILTER
# ============================================================

class SelectFilterRecommendation(
    StrictFilterModel
):
    filter_type: Literal["select"] = "select"

    filter_id: str
    label: str

    column_ref: str

    operator: Literal["IN"] = "IN"

    cardinality: int

    max_options: int = 50

    priority: int = 2

    reason: str


# ============================================================
# DISCRIMINATED UNION
# ============================================================

FilterRecommendation = Annotated[
    Union[
        DateRangeFilterRecommendation,
        SelectFilterRecommendation,
    ],
    Field(discriminator="filter_type"),
]


# ============================================================
# SKIPPED FILTER
# ============================================================

class SkippedFilter(StrictFilterModel):
    column_ref: str
    reason: str


class FilterRecommendationResult(
    StrictFilterModel
):
    recommendations: list[FilterRecommendation]
    skipped: list[SkippedFilter]


# ============================================================
# RECIPE TABLE
# ============================================================

def _get_recipe_table(
    recipe: MetricRecipe,
) -> str:
    operands = get_recipe_operands(recipe)

    tables = {
        parse_column_ref(
            operand.target_ref
        )[0]
        for operand in operands
    }

    if len(tables) != 1:
        raise FilterRecommendationError(
            "Filter recommendation requires exactly "
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
    table_name, column_name = parse_column_ref(
        ref
    )

    for row in registry_entries:
        row_table = getattr(
            row,
            "table_name",
            None,
        )

        row_column = getattr(
            row,
            "column_name",
            None,
        )

        if isinstance(row, dict):
            row_table = row.get(
                "table_name",
                row_table,
            )

            row_column = row.get(
                "column_name",
                row_column,
            )

        if (
            str(row_table) == table_name
            and str(row_column) == column_name
        ):
            return row

    raise FilterRecommendationError(
        f"Filter column '{ref}' does not exist "
        "in verified SchemaRegistry."
    )


# ============================================================
# QUALIFIED SAME-TABLE REF
# ============================================================

def _validate_filter_ref(
    *,
    ref: str,
    recipe_table: str,
    registry_entries: Sequence[Any],
) -> tuple[str, Any]:
    try:
        table_name, column_name = (
            parse_column_ref(ref)
        )
    except ValueError as exc:
        raise FilterRecommendationError(
            "Filter references must use qualified "
            "table.column syntax."
        ) from exc

    if table_name != recipe_table:
        raise FilterRecommendationError(
            "Cross-table filter recommendation requires "
            "a validated relationship path."
        )

    normalized_ref = (
        f"{table_name}.{column_name}"
    )

    registry_column = _find_registry_column(
        ref=normalized_ref,
        registry_entries=registry_entries,
    )

    return (
        normalized_ref,
        registry_column,
    )


# ============================================================
# METADATA HELPERS
# ============================================================

def _registry_value(
    row: Any,
    field: str,
    default: Any = None,
) -> Any:
    if isinstance(row, dict):
        return row.get(
            field,
            default,
        )

    return getattr(
        row,
        field,
        default,
    )


def _is_identifier_like(
    registry_column: Any,
) -> bool:
    if bool(
        _registry_value(
            registry_column,
            "is_primary_key",
            False,
        )
    ):
        return True

    semantic_type = str(
        _registry_value(
            registry_column,
            "semantic_type",
            "",
        )
        or ""
    ).strip().upper()

    return semantic_type in {
        "ID",
        "UUID",
        "IDENTIFIER",
        "PRIMARY_KEY",
    }


# ============================================================
# PRESENTATION HELPERS
# ============================================================

def _make_label(
    ref: str,
) -> str:
    _, column_name = parse_column_ref(ref)

    return (
        column_name
        .replace("_", " ")
        .strip()
        .title()
    )


def _make_filter_id(
    *,
    ref: str,
    suffix: str,
) -> str:
    table_name, column_name = (
        parse_column_ref(ref)
    )

    raw = (
        f"{table_name}_"
        f"{column_name}_"
        f"{suffix}"
    )

    normalized = re.sub(
        r"[^A-Za-z0-9_]+",
        "_",
        raw,
    )

    return (
        normalized
        .strip("_")
        .lower()
    )


# ============================================================
# MAIN RECOMMENDER
# ============================================================

def recommend_filters(
    *,
    recipe: MetricRecipe,
    registry_entries: Sequence[Any],
    dimension_refs: Sequence[str] | None = None,
    time_ref: str | None = None,
    max_categorical_cardinality: int = 50,
) -> FilterRecommendationResult:
    if max_categorical_cardinality < 2:
        raise FilterRecommendationError(
            "max_categorical_cardinality "
            "must be at least 2."
        )

    recipe_table = _get_recipe_table(
        recipe
    )

    recommendations: list[
        FilterRecommendation
    ] = []

    skipped: list[SkippedFilter] = []

    seen_refs: set[str] = set()

    # ========================================================
    # TIME FILTER
    # ========================================================

    if time_ref:
        normalized_time_ref, _ = (
            _validate_filter_ref(
                ref=time_ref,
                recipe_table=recipe_table,
                registry_entries=registry_entries,
            )
        )

        recommendations.append(
            DateRangeFilterRecommendation(
                filter_id=_make_filter_id(
                    ref=normalized_time_ref,
                    suffix="date_range",
                ),
                label=_make_label(
                    normalized_time_ref
                ),
                column_ref=normalized_time_ref,
                start_operator=">=",
                end_operator="<=",
                priority=1,
                reason=(
                    "Explicit same-table time reference "
                    "supports deterministic date-range "
                    "filtering."
                ),
            )
        )

        seen_refs.add(
            normalized_time_ref
        )

    # ========================================================
    # CATEGORICAL FILTERS
    # ========================================================

    for dimension_ref in (
        dimension_refs or []
    ):
        normalized_ref, registry_column = (
            _validate_filter_ref(
                ref=dimension_ref,
                recipe_table=recipe_table,
                registry_entries=registry_entries,
            )
        )

        # Prevent duplicates.
        if normalized_ref in seen_refs:
            continue

        seen_refs.add(
            normalized_ref
        )

        # --------------------------------------------
        # Identifier protection
        # --------------------------------------------

        if _is_identifier_like(
            registry_column
        ):
            skipped.append(
                SkippedFilter(
                    column_ref=normalized_ref,
                    reason=(
                        "Identifier-like columns are not "
                        "recommended as dashboard select "
                        "filters."
                    ),
                )
            )

            continue

        # --------------------------------------------
        # Cardinality policy
        # --------------------------------------------

        raw_cardinality = _registry_value(
            registry_column,
            "cardinality",
            None,
        )

        if raw_cardinality is None:
            skipped.append(
                SkippedFilter(
                    column_ref=normalized_ref,
                    reason=(
                        "Column cardinality is unavailable; "
                        "select-filter recommendation is "
                        "deferred."
                    ),
                )
            )

            continue

        try:
            cardinality = int(
                raw_cardinality
            )
        except (
            TypeError,
            ValueError,
        ) as exc:
            raise FilterRecommendationError(
                f"Invalid cardinality metadata "
                f"for '{normalized_ref}'."
            ) from exc

        # 0 or 1 unique value provides no useful
        # interactive filtering.
        if cardinality < 2:
            skipped.append(
                SkippedFilter(
                    column_ref=normalized_ref,
                    reason=(
                        "Column has fewer than two "
                        "distinct values and provides "
                        "no useful filtering."
                    ),
                )
            )

            continue

        if (
            cardinality
            > max_categorical_cardinality
        ):
            skipped.append(
                SkippedFilter(
                    column_ref=normalized_ref,
                    reason=(
                        "Column cardinality exceeds "
                        "the current safe select-filter "
                        "threshold."
                    ),
                )
            )

            continue

        recommendations.append(
            SelectFilterRecommendation(
                filter_id=_make_filter_id(
                    ref=normalized_ref,
                    suffix="select",
                ),
                label=_make_label(
                    normalized_ref
                ),
                column_ref=normalized_ref,
                operator="IN",
                cardinality=cardinality,
                max_options=(
                    max_categorical_cardinality
                ),
                priority=2,
                reason=(
                    "Explicit same-table dimension has "
                    "bounded cardinality suitable for "
                    "a select filter."
                ),
            )
        )

    return FilterRecommendationResult(
        recommendations=recommendations,
        skipped=skipped,
    )
