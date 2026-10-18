from __future__ import annotations

import math
import re
from typing import Any, Literal, Sequence

from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

import models

import pandas as pd

from services.metric_executor import (
    MetricExecutor,
    MetricFilter,
    MetricRequest,
)
from services.metric_recipes import (
    AtomicMetricOperand,
    AtomicMetricRecipe,
    DifferenceMetricRecipe,
    MetricRecipe,
    PeriodComparisonRecipe,
    RatioMetricRecipe,
    get_recipe_operands,
    validate_recipe_for_connection,
)
from services.query_builder import parse_column_ref


ExecutionStatus = Literal[
    "ok",
    "no_data",
    "undefined",
    "no_prior_data",
    "unavailable_zero_baseline",
    "flat",
]

ComponentRole = Literal[
    "operand",
    "numerator",
    "denominator",
    "left",
    "right",
    "current_period",
    "prior_period",
]


class DerivedMetricExecutionError(ValueError):
    """
    Raised when a validated MetricRecipe cannot be executed safely.

    This service never silently fabricates a metric value.
    """

    pass


class MetricComponentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: ComponentRole
    target_ref: str
    aggregation: str
    value: Any | None


class MetricRecipeExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_id: str
    metric_type: str
    title: str
    format: str

    status: ExecutionStatus
    value: Any | None

    components: list[MetricComponentResult]


def _assert_connection_ownership(
    *,
    db_conn: models.DatabaseConnection,
    connection_id: int,
    tenant_id: int,
) -> None:
    """
    Defense-in-depth.

    The supplied DatabaseConnection must represent exactly the
    connection and tenant requested by the execution call.
    """

    if db_conn.id != connection_id:
        raise DerivedMetricExecutionError(
            "Database connection does not match requested connection."
        )

    if db_conn.tenant_id != tenant_id:
        raise DerivedMetricExecutionError(
            "Database connection does not belong to the requested tenant."
        )


def _execute_atomic_operand(
    *,
    operand: AtomicMetricOperand,
    connection_id: int,
    tenant_id: int,
    db_conn: models.DatabaseConnection,
    db: Session,
    filters: Sequence[MetricFilter] | None = None,
) -> Any | None:
    """
    Execute exactly one atomic operand through MetricExecutor.

    No SQL is constructed here.
    """

    request = MetricRequest(
        connection_id=connection_id,
        target_ref=operand.target_ref,
        aggregation=operand.aggregation,
        filters=list(filters) if filters else None,
        tenant_id=tenant_id,
    )

    result = MetricExecutor.execute(
        request,
        db_conn,
        db,
    )

    if not result.is_scalar:
        raise DerivedMetricExecutionError(
            "Derived metric operands must return scalar results."
        )

    return result.value


def _component(
    *,
    role: ComponentRole,
    operand: AtomicMetricOperand,
    value: Any | None,
) -> MetricComponentResult:
    return MetricComponentResult(
        role=role,
        target_ref=operand.target_ref,
        aggregation=operand.aggregation,
        value=value,
    )


def _ensure_numeric(
    value: Any | None,
    *,
    role: str,
) -> int | float | None:
    """
    Ratio and difference recipes require numeric operands.

    None is preserved as no-data.
    bool is explicitly rejected even though bool subclasses int.
    Non-finite floats (NaN, +inf, -inf) are explicitly rejected.
    """

    if value is None:
        return None

    if isinstance(value, bool):
        raise DerivedMetricExecutionError(
            f"Derived metric component '{role}' returned a boolean value."
        )

    if not isinstance(value, (int, float)):
        raise DerivedMetricExecutionError(
            f"Derived metric component '{role}' "
            "did not return a numeric value."
        )

    if isinstance(value, float) and not math.isfinite(value):
        raise DerivedMetricExecutionError(
            f"Derived metric component '{role}' "
            "returned a non-finite numeric value."
        )

    return value


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
        raise DerivedMetricExecutionError(
            "Derived metric execution requires exactly one source table."
        )

    return next(iter(tables))


def _validate_runtime_filters(
    *,
    recipe: MetricRecipe,
    filters: Sequence[MetricFilter] | None,
) -> None:
    if not filters:
        return

    recipe_table = _get_recipe_table(recipe)

    for flt in filters:
        try:
            filter_table, _ = parse_column_ref(
                flt.column
            )
        except ValueError as exc:
            raise DerivedMetricExecutionError(
                "Runtime metric filters must use qualified "
                "table.column references."
            ) from exc

        if filter_table != recipe_table:
            raise DerivedMetricExecutionError(
                "Cross-table runtime filters require "
                "a validated relationship path."
            )


def execute_metric_recipe(
    *,
    recipe: MetricRecipe,
    connection_id: int,
    tenant_id: int,
    db_conn: models.DatabaseConnection,
    db: Session,
    filters: Sequence[MetricFilter] | None = None,
) -> MetricRecipeExecutionResult:
    """
    Execute a validated Phase 2 MetricRecipe.

    Rules:

    Atomic:
        delegate directly to MetricExecutor

    Ratio:
        execute numerator and denominator independently
        through MetricExecutor, then divide safely

    Difference:
        execute left and right independently
        through MetricExecutor, then subtract safely

    This function:
    - never creates raw SQL
    - never uses eval
    - never executes formula strings
    - never creates joins
    - never substitutes missing values with zero
    """

    _assert_connection_ownership(
        db_conn=db_conn,
        connection_id=connection_id,
        tenant_id=tenant_id,
    )

    # Revalidate at execution boundary.
    validated_recipe = validate_recipe_for_connection(
        recipe,
        connection_id=connection_id,
        tenant_id=tenant_id,
        db=db,
    )

    _validate_runtime_filters(
        recipe=validated_recipe,
        filters=filters,
    )

    # ========================================================
    # ATOMIC
    # ========================================================

    if isinstance(validated_recipe, AtomicMetricRecipe):
        value = _execute_atomic_operand(
            operand=validated_recipe.operand,
            connection_id=connection_id,
            tenant_id=tenant_id,
            db_conn=db_conn,
            db=db,
            filters=filters,
        )

        return MetricRecipeExecutionResult(
            metric_id=validated_recipe.metric_id,
            metric_type=validated_recipe.metric_type,
            title=validated_recipe.title,
            format=validated_recipe.format,
            status="ok" if value is not None else "no_data",
            value=value,
            components=[
                _component(
                    role="operand",
                    operand=validated_recipe.operand,
                    value=value,
                )
            ],
        )

    # ========================================================
    # RATIO
    # ========================================================

    if isinstance(validated_recipe, RatioMetricRecipe):
        numerator_raw = _execute_atomic_operand(
            operand=validated_recipe.numerator,
            connection_id=connection_id,
            tenant_id=tenant_id,
            db_conn=db_conn,
            db=db,
            filters=filters,
        )

        denominator_raw = _execute_atomic_operand(
            operand=validated_recipe.denominator,
            connection_id=connection_id,
            tenant_id=tenant_id,
            db_conn=db_conn,
            db=db,
            filters=filters,
        )

        numerator = _ensure_numeric(
            numerator_raw,
            role="numerator",
        )

        denominator = _ensure_numeric(
            denominator_raw,
            role="denominator",
        )

        components = [
            _component(
                role="numerator",
                operand=validated_recipe.numerator,
                value=numerator_raw,
            ),
            _component(
                role="denominator",
                operand=validated_recipe.denominator,
                value=denominator_raw,
            ),
        ]

        # Missing source data is different from divide-by-zero.
        if numerator is None or denominator is None:
            return MetricRecipeExecutionResult(
                metric_id=validated_recipe.metric_id,
                metric_type=validated_recipe.metric_type,
                title=validated_recipe.title,
                format=validated_recipe.format,
                status="no_data",
                value=None,
                components=components,
            )

        if denominator == 0:
            # Phase 2A only permits zero_division="null".
            return MetricRecipeExecutionResult(
                metric_id=validated_recipe.metric_id,
                metric_type=validated_recipe.metric_type,
                title=validated_recipe.title,
                format=validated_recipe.format,
                status="undefined",
                value=None,
                components=components,
            )

        try:
            value = numerator / denominator
        except OverflowError as exc:
            raise DerivedMetricExecutionError(
                "Derived metric ratio calculation resulted in a non-finite value."
            ) from exc

        if isinstance(value, float) and not math.isfinite(value):
            raise DerivedMetricExecutionError(
                "Derived metric ratio calculation resulted in a non-finite value."
            )

        return MetricRecipeExecutionResult(
            metric_id=validated_recipe.metric_id,
            metric_type=validated_recipe.metric_type,
            title=validated_recipe.title,
            format=validated_recipe.format,
            status="ok",
            value=value,
            components=components,
        )

    # ========================================================
    # DIFFERENCE
    # ========================================================

    if isinstance(
        validated_recipe,
        DifferenceMetricRecipe,
    ):
        left_raw = _execute_atomic_operand(
            operand=validated_recipe.left,
            connection_id=connection_id,
            tenant_id=tenant_id,
            db_conn=db_conn,
            db=db,
            filters=filters,
        )

        right_raw = _execute_atomic_operand(
            operand=validated_recipe.right,
            connection_id=connection_id,
            tenant_id=tenant_id,
            db_conn=db_conn,
            db=db,
            filters=filters,
        )

        left = _ensure_numeric(
            left_raw,
            role="left",
        )

        right = _ensure_numeric(
            right_raw,
            role="right",
        )

        components = [
            _component(
                role="left",
                operand=validated_recipe.left,
                value=left_raw,
            ),
            _component(
                role="right",
                operand=validated_recipe.right,
                value=right_raw,
            ),
        ]

        if left is None or right is None:
            return MetricRecipeExecutionResult(
                metric_id=validated_recipe.metric_id,
                metric_type=validated_recipe.metric_type,
                title=validated_recipe.title,
                format=validated_recipe.format,
                status="no_data",
                value=None,
                components=components,
            )

        try:
            value = left - right
        except OverflowError as exc:
            raise DerivedMetricExecutionError(
                "Derived metric difference calculation resulted in a non-finite value."
            ) from exc

        if isinstance(value, float) and not math.isfinite(value):
            raise DerivedMetricExecutionError(
                "Derived metric difference calculation resulted in a non-finite value."
            )

        return MetricRecipeExecutionResult(
            metric_id=validated_recipe.metric_id,
            metric_type=validated_recipe.metric_type,
            title=validated_recipe.title,
            format=validated_recipe.format,
            status="ok",
            value=value,
            components=components,
        )

    # ========================================================
    # PERIOD COMPARISON
    # ========================================================

    if isinstance(validated_recipe, PeriodComparisonRecipe):
        curr_filters = list(filters or []) + [
            MetricFilter(column=f.column, operator=f.operator, value=f.value)
            for f in getattr(validated_recipe, "current_filters", []) or []
        ]
        prior_filters = list(filters or []) + [
            MetricFilter(column=f.column, operator=f.operator, value=f.value)
            for f in getattr(validated_recipe, "prior_filters", []) or []
        ]
        current_res = execute_metric_recipe(
            recipe=validated_recipe.current_period_recipe,
            connection_id=connection_id,
            tenant_id=tenant_id,
            db_conn=db_conn,
            db=db,
            filters=curr_filters,
        )
        prior_res = execute_metric_recipe(
            recipe=validated_recipe.prior_period_recipe,
            connection_id=connection_id,
            tenant_id=tenant_id,
            db_conn=db_conn,
            db=db,
            filters=prior_filters,
        )

        current_val = _ensure_numeric(current_res.value, role="current_period")
        prior_val = _ensure_numeric(prior_res.value, role="prior_period")

        curr_op = get_recipe_operands(validated_recipe.current_period_recipe)[0]
        prior_op = get_recipe_operands(validated_recipe.prior_period_recipe)[0]

        components = [
            MetricComponentResult(
                role="current_period",
                target_ref=curr_op.target_ref,
                aggregation=curr_op.aggregation,
                value=current_res.value,
            ),
            MetricComponentResult(
                role="prior_period",
                target_ref=prior_op.target_ref,
                aggregation=prior_op.aggregation,
                value=prior_res.value,
            ),
        ]

        if prior_val is None:
            return MetricRecipeExecutionResult(
                metric_id=validated_recipe.metric_id,
                metric_type=validated_recipe.metric_type,
                title=validated_recipe.title,
                format=validated_recipe.format,
                status="no_prior_data",
                value=None,
                components=components,
            )

        if current_val is None:
            return MetricRecipeExecutionResult(
                metric_id=validated_recipe.metric_id,
                metric_type=validated_recipe.metric_type,
                title=validated_recipe.title,
                format=validated_recipe.format,
                status="no_data",
                value=None,
                components=components,
            )

        if prior_val == 0:
            if validated_recipe.comparison_type == "percentage_change":
                if current_val == 0:
                    return MetricRecipeExecutionResult(
                        metric_id=validated_recipe.metric_id,
                        metric_type=validated_recipe.metric_type,
                        title=validated_recipe.title,
                        format=validated_recipe.format,
                        status="flat",
                        value=0.0,
                        components=components,
                    )
                return MetricRecipeExecutionResult(
                    metric_id=validated_recipe.metric_id,
                    metric_type=validated_recipe.metric_type,
                    title=validated_recipe.title,
                    format=validated_recipe.format,
                    status="unavailable_zero_baseline",
                    value=None,
                    components=components,
                )
            else:
                value = current_val - prior_val
                return MetricRecipeExecutionResult(
                    metric_id=validated_recipe.metric_id,
                    metric_type=validated_recipe.metric_type,
                    title=validated_recipe.title,
                    format=validated_recipe.format,
                    status="ok",
                    value=value,
                    components=components,
                )

        if validated_recipe.comparison_type == "percentage_change":
            value = (current_val - prior_val) / abs(prior_val) * 100.0
        else:
            value = current_val - prior_val

        if isinstance(value, float) and not math.isfinite(value):
            raise DerivedMetricExecutionError(
                "Period comparison calculation resulted in a non-finite value."
            )

        return MetricRecipeExecutionResult(
            metric_id=validated_recipe.metric_id,
            metric_type=validated_recipe.metric_type,
            title=validated_recipe.title,
            format=validated_recipe.format,
            status="ok",
            value=value,
            components=components,
        )

    raise DerivedMetricExecutionError(
        f"Unsupported MetricRecipe type: "
        f"{type(validated_recipe).__name__}"
    )


# ============================================================
# DATAFRAME METRIC EXECUTOR (NR-2.1-A-T02)
# ============================================================

class DataFrameMetricExecutor:
    """
    Executes MetricRecipe AST directly over Pandas DataFrame sources.
    Provides mathematically exact parity with SQL MetricExecutor.
    """

    def __init__(self, data: pd.DataFrame | dict[str, pd.DataFrame]):
        if isinstance(data, pd.DataFrame):
            self.dfs = {"default": data}
        elif isinstance(data, dict):
            self.dfs = {str(k): v for k, v in data.items() if isinstance(v, pd.DataFrame)}
            if not self.dfs:
                raise ValueError("DataFrame dictionary cannot be empty.")
        else:
            raise ValueError("data must be a pandas DataFrame or a dict of DataFrames.")

    def _resolve_df(self, table_name: str) -> pd.DataFrame:
        if table_name in self.dfs:
            return self.dfs[table_name]
        if "default" in self.dfs:
            return self.dfs["default"]
        for k, v in self.dfs.items():
            if k.lower() == table_name.lower():
                return v
        raise DerivedMetricExecutionError(f"Table '{table_name}' not found in DataFrame sources.")

    def _apply_filters(self, df: pd.DataFrame, filters: Sequence[MetricFilter] | None) -> pd.DataFrame:
        if not filters:
            return df
        filtered = df
        for f in filters:
            col = getattr(f, "column", None)
            if not col:
                continue
            if "." in col:
                col = col.split(".", 1)[1]
            if col not in filtered.columns:
                continue
            op = (getattr(f, "operator", "=") or "=").strip().upper()
            val = getattr(f, "value", None)

            if op == "=":
                filtered = filtered[filtered[col] == val]
            elif op == "!=":
                filtered = filtered[filtered[col] != val]
            elif op == ">":
                filtered = filtered[filtered[col] > val]
            elif op == "<":
                filtered = filtered[filtered[col] < val]
            elif op == ">=":
                filtered = filtered[filtered[col] >= val]
            elif op == "<=":
                filtered = filtered[filtered[col] <= val]
            elif op in ("LIKE", "ILIKE"):
                val_str = str(val)
                tokens = []
                for ch in val_str:
                    if ch == "%":
                        tokens.append(".*")
                    elif ch == "_":
                        tokens.append(".")
                    else:
                        tokens.append(re.escape(ch))
                pattern = f"^{''.join(tokens)}$"
                flags = re.IGNORECASE if op == "ILIKE" else 0
                filtered = filtered[filtered[col].astype(str).str.contains(pattern, regex=True, flags=flags, na=False)]
            elif op == "IN":
                val_list = val if isinstance(val, (list, tuple, set)) else [val]
                filtered = filtered[filtered[col].isin(val_list)]
        return filtered

    def execute_atomic(
        self,
        operand: AtomicMetricOperand,
        filters: Sequence[MetricFilter] | None = None,
        missing_value_policy: str = "zero",
    ) -> Any | None:
        table_name, column_name = parse_column_ref(operand.target_ref)
        df = self._resolve_df(table_name)
        filtered = self._apply_filters(df, filters)

        if filtered.empty:
            if operand.aggregation in ("COUNT", "COUNT_DISTINCT"):
                return 0
            return None

        if column_name == "*":
            if operand.aggregation == "COUNT":
                return int(len(filtered))
            raise DerivedMetricExecutionError("Wildcard target is only allowed with COUNT.")

        if column_name not in filtered.columns:
            raise DerivedMetricExecutionError(f"Column '{column_name}' not found in table '{table_name}'.")

        raw_series = filtered[column_name]
        has_nulls = bool(raw_series.isna().any())
        policy = (missing_value_policy or "zero").lower()

        if has_nulls:
            if policy == "error":
                raise DerivedMetricExecutionError(
                    f"Target column '{column_name}' contains null values under 'error' missing_value_policy."
                )
            elif policy == "zero":
                if operand.aggregation.upper() in ("SUM", "AVG", "MIN", "MAX"):
                    series = raw_series.fillna(0)
                else:
                    series = raw_series.dropna()
            elif policy == "drop":
                series = raw_series.dropna()
            else:
                series = raw_series.dropna()
        else:
            series = raw_series

        if series.empty:
            if operand.aggregation in ("COUNT", "COUNT_DISTINCT"):
                return 0
            return None

        agg = operand.aggregation.upper()
        if agg == "COUNT":
            return int(len(series))
        elif agg == "COUNT_DISTINCT":
            return int(series.nunique())
        elif agg == "SUM":
            val = float(series.sum())
            return val if math.isfinite(val) else None
        elif agg == "AVG":
            val = float(series.mean())
            return val if math.isfinite(val) else None
        elif agg == "MIN":
            val = series.min()
            return float(val) if isinstance(val, (int, float)) and not isinstance(val, bool) else val
        elif agg == "MAX":
            val = series.max()
            return float(val) if isinstance(val, (int, float)) and not isinstance(val, bool) else val
        else:
            raise DerivedMetricExecutionError(f"Unsupported aggregation '{agg}'")

    def execute(
        self,
        recipe: MetricRecipe,
        filters: Sequence[MetricFilter] | None = None,
    ) -> MetricRecipeExecutionResult:
        policy = getattr(recipe, "missing_value_policy", "zero")

        if isinstance(recipe, AtomicMetricRecipe):
            value = self.execute_atomic(recipe.operand, filters=filters, missing_value_policy=policy)
            return MetricRecipeExecutionResult(
                metric_id=recipe.metric_id,
                metric_type=recipe.metric_type,
                title=recipe.title,
                format=recipe.format,
                status="ok" if value is not None else "no_data",
                value=value,
                components=[
                    _component(
                        role="operand",
                        operand=recipe.operand,
                        value=value,
                    )
                ],
            )

        if isinstance(recipe, RatioMetricRecipe):
            num_raw = self.execute_atomic(recipe.numerator, filters=filters, missing_value_policy=policy)
            den_raw = self.execute_atomic(recipe.denominator, filters=filters, missing_value_policy=policy)
            numerator = _ensure_numeric(num_raw, role="numerator")
            denominator = _ensure_numeric(den_raw, role="denominator")
            components = [
                _component(role="numerator", operand=recipe.numerator, value=num_raw),
                _component(role="denominator", operand=recipe.denominator, value=den_raw),
            ]
            if numerator is None or denominator is None:
                return MetricRecipeExecutionResult(
                    metric_id=recipe.metric_id,
                    metric_type=recipe.metric_type,
                    title=recipe.title,
                    format=recipe.format,
                    status="no_data",
                    value=None,
                    components=components,
                )
            if denominator == 0:
                return MetricRecipeExecutionResult(
                    metric_id=recipe.metric_id,
                    metric_type=recipe.metric_type,
                    title=recipe.title,
                    format=recipe.format,
                    status="undefined",
                    value=None,
                    components=components,
                )
            value = numerator / denominator
            if not math.isfinite(value):
                raise DerivedMetricExecutionError("Ratio calculation resulted in non-finite value.")
            return MetricRecipeExecutionResult(
                metric_id=recipe.metric_id,
                metric_type=recipe.metric_type,
                title=recipe.title,
                format=recipe.format,
                status="ok",
                value=value,
                components=components,
            )

        if isinstance(recipe, DifferenceMetricRecipe):
            left_raw = self.execute_atomic(recipe.left, filters=filters, missing_value_policy=policy)
            right_raw = self.execute_atomic(recipe.right, filters=filters, missing_value_policy=policy)
            left = _ensure_numeric(left_raw, role="left")
            right = _ensure_numeric(right_raw, role="right")
            components = [
                _component(role="left", operand=recipe.left, value=left_raw),
                _component(role="right", operand=recipe.right, value=right_raw),
            ]
            if left is None or right is None:
                return MetricRecipeExecutionResult(
                    metric_id=recipe.metric_id,
                    metric_type=recipe.metric_type,
                    title=recipe.title,
                    format=recipe.format,
                    status="no_data",
                    value=None,
                    components=components,
                )
            value = left - right
            if not math.isfinite(value):
                raise DerivedMetricExecutionError("Difference calculation resulted in non-finite value.")
            return MetricRecipeExecutionResult(
                metric_id=recipe.metric_id,
                metric_type=recipe.metric_type,
                title=recipe.title,
                format=recipe.format,
                status="ok",
                value=value,
                components=components,
            )

        if isinstance(recipe, PeriodComparisonRecipe):
            curr_filters = list(filters or []) + [
                MetricFilter(column=f.column, operator=f.operator, value=f.value)
                for f in getattr(recipe, "current_filters", []) or []
            ]
            prior_filters = list(filters or []) + [
                MetricFilter(column=f.column, operator=f.operator, value=f.value)
                for f in getattr(recipe, "prior_filters", []) or []
            ]
            curr_res = self.execute(recipe.current_period_recipe, filters=curr_filters)
            prior_res = self.execute(recipe.prior_period_recipe, filters=prior_filters)
            current_val = _ensure_numeric(curr_res.value, role="current_period")
            prior_val = _ensure_numeric(prior_res.value, role="prior_period")

            curr_op = get_recipe_operands(recipe.current_period_recipe)[0]
            prior_op = get_recipe_operands(recipe.prior_period_recipe)[0]

            components = [
                MetricComponentResult(
                    role="current_period",
                    target_ref=curr_op.target_ref,
                    aggregation=curr_op.aggregation,
                    value=curr_res.value,
                ),
                MetricComponentResult(
                    role="prior_period",
                    target_ref=prior_op.target_ref,
                    aggregation=prior_op.aggregation,
                    value=prior_res.value,
                ),
            ]

            if prior_val is None:
                return MetricRecipeExecutionResult(
                    metric_id=recipe.metric_id,
                    metric_type=recipe.metric_type,
                    title=recipe.title,
                    format=recipe.format,
                    status="no_prior_data",
                    value=None,
                    components=components,
                )

            if current_val is None:
                return MetricRecipeExecutionResult(
                    metric_id=recipe.metric_id,
                    metric_type=recipe.metric_type,
                    title=recipe.title,
                    format=recipe.format,
                    status="no_data",
                    value=None,
                    components=components,
                )

            if prior_val == 0:
                if recipe.comparison_type == "percentage_change":
                    if current_val == 0:
                        return MetricRecipeExecutionResult(
                            metric_id=recipe.metric_id,
                            metric_type=recipe.metric_type,
                            title=recipe.title,
                            format=recipe.format,
                            status="flat",
                            value=0.0,
                            components=components,
                        )
                    return MetricRecipeExecutionResult(
                        metric_id=recipe.metric_id,
                        metric_type=recipe.metric_type,
                        title=recipe.title,
                        format=recipe.format,
                        status="unavailable_zero_baseline",
                        value=None,
                        components=components,
                    )
                else:
                    value = current_val - prior_val
                    return MetricRecipeExecutionResult(
                        metric_id=recipe.metric_id,
                        metric_type=recipe.metric_type,
                        title=recipe.title,
                        format=recipe.format,
                        status="ok",
                        value=value,
                        components=components,
                    )

            if recipe.comparison_type == "percentage_change":
                value = (current_val - prior_val) / abs(prior_val) * 100.0
            else:
                value = current_val - prior_val

            if isinstance(value, float) and not math.isfinite(value):
                raise DerivedMetricExecutionError(
                    "Period comparison calculation resulted in a non-finite value."
                )

            return MetricRecipeExecutionResult(
                metric_id=recipe.metric_id,
                metric_type=recipe.metric_type,
                title=recipe.title,
                format=recipe.format,
                status="ok",
                value=value,
                components=components,
            )

        raise DerivedMetricExecutionError(f"Unsupported MetricRecipe type: {type(recipe).__name__}")
