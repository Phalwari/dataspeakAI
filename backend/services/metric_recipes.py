from __future__ import annotations

import json
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
    TypeAdapter,
    field_validator,
    model_validator,
)
from sqlalchemy.orm import Session

from services.query_builder import parse_column_ref
from services.metric_semantics import ALLOWED_AGGREGATIONS, validate_metric_aggregation


# ============================================================
# CANONICAL TYPES
# ============================================================

AggregationType = Literal[
    "SUM",
    "AVG",
    "MIN",
    "MAX",
    "COUNT",
    "COUNT_DISTINCT",
]

MetricDisplayFormat = Literal[
    "number",
    "integer",
    "currency",
    "percentage",
    "ratio",
]

MetricType = Literal[
    "atomic",
    "ratio",
    "difference",
]


class MetricRecipeValidationError(ValueError):
    """
    Raised when a structurally valid Metric Recipe is not valid
    against the verified database schema / semantic rules.
    """

    pass


# ============================================================
# STRICT BASE MODEL
# ============================================================

class StrictRecipeModel(BaseModel):
    """
    Every Metric Recipe object is strict.

    Unknown fields are forbidden so arbitrary fields such as:
    sql, formula, query, expression, python, code, eval, raw_sql
    cannot silently enter the recipe contract.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


# ============================================================
# ATOMIC OPERAND
# ============================================================

class AtomicMetricOperand(StrictRecipeModel):
    """
    Smallest executable metric unit.

    Examples:
    SUM(orders.total_amount)
    COUNT_DISTINCT(orders.customer_id)
    COUNT(orders.*)
    """

    target_ref: str
    aggregation: AggregationType

    @field_validator("aggregation", mode="before")
    @classmethod
    def normalize_aggregation(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().upper()
        return value

    @field_validator("target_ref")
    @classmethod
    def validate_and_normalize_target_ref(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("target_ref is required.")

        table, column = parse_column_ref(value.strip())

        # parse_column_ref already normalizes table.all -> table.*
        normalized = f"{table}.{column}"
        return normalized

    @model_validator(mode="after")
    def validate_wildcard_semantics(self) -> "AtomicMetricOperand":
        table, column = parse_column_ref(self.target_ref)

        if column == "*" and self.aggregation != "COUNT":
            raise ValueError(
                f"Wildcard target '{table}.*' is only valid with COUNT."
            )

        return self


# ============================================================
# COMMON METADATA
# ============================================================

class BaseMetricRecipe(StrictRecipeModel):
    recipe_version: Literal["1.0"] = "1.0"
    metric_id: str = Field(
        min_length=1,
        pattern=r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$",
    )
    title: str = Field(min_length=1)
    description: str | None = None
    format: MetricDisplayFormat = "number"
    reasoning: str | None = None
    entity_grain: str | None = None
    unit: str | None = None
    date_field: str | None = None
    missing_value_policy: Literal["zero", "drop", "error"] = "zero"


# ============================================================
# ATOMIC RECIPE
# ============================================================

class AtomicMetricRecipe(BaseMetricRecipe):
    metric_type: Literal["atomic"] = "atomic"
    operand: AtomicMetricOperand


# ============================================================
# RATIO RECIPE
# ============================================================

class RatioMetricRecipe(BaseMetricRecipe):
    metric_type: Literal["ratio"] = "ratio"
    numerator: AtomicMetricOperand
    denominator: AtomicMetricOperand

    # Required explicitly. Never silently convert denominator 0 into 1.
    zero_division: Literal["null"]

    @model_validator(mode="after")
    def enforce_same_table(self) -> "RatioMetricRecipe":
        numerator_table, _ = parse_column_ref(self.numerator.target_ref)
        denominator_table, _ = parse_column_ref(self.denominator.target_ref)

        if numerator_table != denominator_table:
            raise ValueError(
                "Cross-table derived metrics require a validated relationship path."
            )

        return self


# ============================================================
# DIFFERENCE RECIPE
# ============================================================

class DifferenceMetricRecipe(BaseMetricRecipe):
    metric_type: Literal["difference"] = "difference"
    left: AtomicMetricOperand
    right: AtomicMetricOperand

    @model_validator(mode="after")
    def enforce_same_table(self) -> "DifferenceMetricRecipe":
        left_table, _ = parse_column_ref(self.left.target_ref)
        right_table, _ = parse_column_ref(self.right.target_ref)

        if left_table != right_table:
            raise ValueError(
                "Cross-table derived metrics require a validated relationship path."
            )

        return self


# ============================================================
# PERIOD COMPARISON RECIPE
# ============================================================

class PeriodComparisonRecipe(BaseMetricRecipe):
    metric_type: Literal["period_comparison"] = "period_comparison"
    current_period_recipe: Union[AtomicMetricRecipe, RatioMetricRecipe, DifferenceMetricRecipe]
    prior_period_recipe: Union[AtomicMetricRecipe, RatioMetricRecipe, DifferenceMetricRecipe]
    comparison_type: Literal["percentage_change", "absolute_difference"] = "percentage_change"


# ============================================================
# DISCRIMINATED RECIPE UNION
# ============================================================

MetricRecipe = Annotated[
    Union[
        AtomicMetricRecipe,
        RatioMetricRecipe,
        DifferenceMetricRecipe,
        PeriodComparisonRecipe,
    ],
    Field(discriminator="metric_type"),
]

METRIC_RECIPE_ADAPTER = TypeAdapter(MetricRecipe)


# ============================================================
# PARSING / SERIALIZATION
# ============================================================

def parse_metric_recipe(payload: dict[str, Any]) -> MetricRecipe:
    """
    Convert untrusted dictionary input into a strict typed recipe.
    Unexpected fields are rejected by Pydantic.
    """
    return METRIC_RECIPE_ADAPTER.validate_python(payload)


def metric_recipe_to_dict(recipe: MetricRecipe) -> dict[str, Any]:
    """Stable JSON-compatible representation."""
    return recipe.model_dump(
        mode="json",
        exclude_none=True,
    )


def metric_recipe_to_json(recipe: MetricRecipe) -> str:
    """
    Deterministic serialized form.
    Useful later for hashing, comparison, version tracking, and persistence.
    """
    return json.dumps(
        metric_recipe_to_dict(recipe),
        sort_keys=True,
        separators=(",", ":"),
    )


# ============================================================
# OPERAND EXTRACTION
# ============================================================

def get_recipe_operands(recipe: MetricRecipe) -> list[AtomicMetricOperand]:
    if isinstance(recipe, AtomicMetricRecipe):
        return [recipe.operand]

    if isinstance(recipe, RatioMetricRecipe):
        return [recipe.numerator, recipe.denominator]

    if isinstance(recipe, DifferenceMetricRecipe):
        return [recipe.left, recipe.right]

    if isinstance(recipe, PeriodComparisonRecipe):
        return (
            get_recipe_operands(recipe.current_period_recipe)
            + get_recipe_operands(recipe.prior_period_recipe)
        )

    raise MetricRecipeValidationError(
        f"Unsupported metric recipe type: {type(recipe).__name__}"
    )


# ============================================================
# REGISTRY VALIDATION
# ============================================================

def validate_recipe_against_registry(
    recipe: MetricRecipe,
    registry_entries: Sequence[Any],
) -> MetricRecipe:
    """
    Validate a Metric Recipe against already verified SchemaRegistry rows.

    This function does NOT:
    - execute SQL
    - calculate metric values
    - create joins
    - persist anything
    """
    tables = {str(row.table_name) for row in registry_entries}
    columns = {
        (str(row.table_name), str(row.column_name)): row
        for row in registry_entries
    }

    operands = get_recipe_operands(recipe)
    operand_tables: set[str] = set()

    for operand in operands:
        table_name, column_name = parse_column_ref(operand.target_ref)
        operand_tables.add(table_name)

        # Table validation
        if table_name not in tables:
            raise MetricRecipeValidationError(
                f"Table '{table_name}' does not exist in verified SchemaRegistry."
            )

        # COUNT(*) special case
        if column_name == "*":
            if operand.aggregation != "COUNT":
                raise MetricRecipeValidationError(
                    f"Wildcard target '{table_name}.*' is only valid with COUNT."
                )
            continue

        # Column validation
        registry_column = columns.get((table_name, column_name))
        if registry_column is None:
            raise MetricRecipeValidationError(
                f"Column '{column_name}' does not exist in table '{table_name}'."
            )

        # Existing Phase 1.5 semantic policy
        try:
            validate_metric_aggregation(
                target_ref=operand.target_ref,
                aggregation=operand.aggregation,
                col_reg=registry_column,
            )
        except ValueError as exc:
            raise MetricRecipeValidationError(str(exc)) from exc

    # Current Phase 2A table boundary: single-table only
    if (
        isinstance(recipe, (RatioMetricRecipe, DifferenceMetricRecipe))
        and len(operand_tables) != 1
    ):
        raise MetricRecipeValidationError(
            "Cross-table derived metrics require a validated relationship path."
        )

    return recipe


# ============================================================
# CONNECTION-AWARE VALIDATION
# ============================================================

def validate_recipe_for_connection(
    recipe: MetricRecipe,
    *,
    connection_id: int,
    tenant_id: int,
    db: Session,
) -> MetricRecipe:
    """
    Tenant-safe convenience wrapper.
    Performs DatabaseConnection ownership verification and SchemaRegistry lookup,
    followed by recipe semantic validation.
    Performs NO metric execution.
    """
    import models

    db_conn = (
        db.query(models.DatabaseConnection)
        .filter(
            models.DatabaseConnection.id == connection_id,
            models.DatabaseConnection.tenant_id == tenant_id,
        )
        .first()
    )

    if not db_conn:
        raise MetricRecipeValidationError(
            f"Database connection {connection_id} not found or unauthorized for tenant {tenant_id}."
        )

    registry_entries = (
        db.query(models.SchemaRegistry)
        .filter(models.SchemaRegistry.connection_id == connection_id)
        .all()
    )

    if not registry_entries:
        raise MetricRecipeValidationError(
            f"No verified schema metadata exists for database connection {connection_id}."
        )

    return validate_recipe_against_registry(recipe, registry_entries)
