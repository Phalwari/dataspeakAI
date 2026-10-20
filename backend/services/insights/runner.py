"""Bounded execution adapters for SQL and Mongo metric plans."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable

from sqlalchemy.engine import Connection

from services.insights.catalog import discover_sql_catalog
from services.insights.mongo import (
    DEFAULT_MAX_DEPTH as DEFAULT_MONGO_MAX_DEPTH, MONGO_PROFILE_VERSION, MongoCatalog, MongoMetricResult,
    build_mongo_plan, discover_mongo_catalog, execute_mongo_metric,
)
from services.insights.planner import MetricSpec, build_metric_plan
from services.insights.profiling import PROFILE_VERSION, ProfileSet, profile_catalog
from services.insights.relationships import infer_relationships
from services.insights.sql_compiler import (
    MetricPlanValidationError, MetricResult, compile_metric, execute_metric,
)
from services.sql_dialect import UnsupportedDialectError


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PreparedSQLPlan:
    catalog: Any
    profiles: Any
    plan: Any
    deadline: float


@dataclass(frozen=True)
class PreparedMongoPlan:
    catalog: Any
    plan: Any
    deadline: float


def _public_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, tuple):
        return [_public_value(item) for item in value]
    if isinstance(value, list):
        return [_public_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _public_value(item) for key, item in value.items()}
    return value


def _label(metric: MetricSpec) -> str:
    if metric.semantic == "revenue":
        return "Gross Revenue (all statuses)"
    if metric.semantic == "net_revenue":
        return "Net Revenue (delivered only)"
    if metric.kind == "count":
        return f"Row count: {metric.table or 'selected table'}"
    if metric.kind == "distinct_count":
        return f"Distinct {metric.measure}"
    if metric.kind == "avg":
        return f"Average {metric.measure}"
    if metric.kind == "sum":
        return f"Sum of {metric.measure}"
    if metric.kind == "trend":
        return f"Trend: {metric.measure}"
    if metric.kind == "breakdown":
        return f"{metric.measure} by {metric.dimension}"
    return "Metric"


def _result_warning(metric_id: str, reason: str) -> str:
    messages = {
        "missing_role": "Required schema evidence was not found.",
        "missing_table": "The selected table was not found in the discovered catalog.",
        "missing_relationship": "No unique validated relationship path was found.",
        "query_failed": "The metric query could not be completed.",
        "no_rows": "The query produced no non-null aggregate value.",
        "budget_exceeded": "The metric was not run because the planning time budget was reached.",
        "unsupported_array_depth": "The Mongo array path exceeds the configured unwind depth.",
        "unsupported_array_shape": "The Mongo plan requires multiple array unwinds and was skipped.",
        "unsupported_dialect": "This SQL dialect is not supported by the planner.",
        "invalid_date": "The requested calendar date range is invalid.",
    }
    return f"{metric_id}: {messages.get(reason, 'The metric is unavailable.') }"


def _metric_payload(metric: MetricSpec, result: Any) -> dict[str, Any]:
    raw = _public_value(result.value)
    formatted = None
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        formatted = f"${raw:,.2f}" if metric.semantic in {"revenue", "net_revenue"} else f"{raw:,.2f}".rstrip("0").rstrip(".")
    elif raw is not None:
        formatted = str(raw)
    return {
        "id": metric.id,
        "label": _label(metric),
        "value": formatted if result.status in {"available", "zero"} else None,
        "raw_value": raw if result.status in {"available", "zero"} else None,
        "status": result.status,
        "reason": result.reason,
        "format": "currency" if metric.semantic in {"revenue", "net_revenue"} else "number",
        "table": metric.table,
        "semantic": metric.semantic,
    }


def prepare_sql_plan(
    connection: Connection,
    *,
    date_from: str | None = None,
    date_to_excl: str | None = None,
    selected_table: str | None = None,
    sample_size: int = 10_000,
    max_tables: int = 100,
    max_columns_per_table: int = 256,
    time_budget_seconds: float = 30.0,
    profile_cache_namespace: str | None = None,
    profile_cache_get: Callable[[str], Any] | None = None,
    profile_cache_set: Callable[[str, Any], Any] | None = None,
) -> PreparedSQLPlan:
    """Perform bounded discovery and planning before cache lookup or metric queries."""
    deadline = time.monotonic() + max(0.1, min(float(time_budget_seconds), 30.0))
    catalog = discover_sql_catalog(connection, max_tables=max_tables)
    profile_key = None
    profiles = None
    if profile_cache_namespace and profile_cache_get:
        profile_key = (
            f"{profile_cache_namespace}:p{PROFILE_VERSION}:{catalog.version}:s{sample_size}:"
            f"c{max_columns_per_table}"
        )
        cached_profiles = profile_cache_get(profile_key)
        if (
            isinstance(cached_profiles, ProfileSet)
            and cached_profiles.catalog_version == catalog.version
            and cached_profiles.sample_size == sample_size
        ):
            profiles = cached_profiles
    if profiles is None:
        profiles = profile_catalog(
            connection, catalog, sample_size=sample_size,
            max_columns_per_table=max_columns_per_table, deadline=deadline,
        )
        profile_complete = all(
            not table.profile_error and not table.budget_exceeded
            for table in profiles.tables.values()
        )
        if profile_key and profile_cache_set and profile_complete:
            profile_cache_set(profile_key, profiles)
    base_plan = build_metric_plan(catalog, profiles, selected_table=selected_table)
    relationships = infer_relationships(
        connection, catalog, base_plan.roles, sample_size=min(sample_size, 1_000),
        min_containment=0.95, deadline=deadline, max_checks=500,
    )
    plan = build_metric_plan(
        catalog, profiles, relationships=relationships, selected_table=selected_table,
    )
    return PreparedSQLPlan(catalog, profiles, plan, deadline)


def execute_prepared_sql_plan(
    connection: Connection,
    prepared: PreparedSQLPlan,
    *,
    date_from: str | None = None,
    date_to_excl: str | None = None,
    selected_table: str | None = None,
) -> dict[str, Any]:
    """Execute a prepared plan; catalog/roles can participate in a generation-safe cache key."""
    catalog, profiles, plan, deadline = (
        prepared.catalog, prepared.profiles, prepared.plan, prepared.deadline,
    )
    results: dict[str, Any] = {}
    charts: list[dict[str, Any]] = []
    warnings = list(profiles.warnings) + list(plan.warnings)
    chart_ids = {chart.id: chart for chart in plan.charts}
    for metric in plan.metrics:
        if metric.status != "available":
            result = MetricResult(metric.id, metric.kind, metric.status, metric.reason)
        elif time.monotonic() >= deadline:
            result = MetricResult(metric.id, metric.kind, "unavailable", "budget_exceeded")
        else:
            try:
                compiled = compile_metric(
                    metric, catalog, date_from=date_from, date_to_excl=date_to_excl,
                )
                result = execute_metric(connection, compiled, deadline=deadline)
            except UnsupportedDialectError:
                logger.warning("Insights metric dialect is unsupported")
                result = MetricResult(metric.id, metric.kind, "unavailable", "unsupported_dialect")
            except MetricPlanValidationError:
                logger.warning("Insights metric plan validation failed")
                result = MetricResult(metric.id, metric.kind, "error", "query_failed")
        results[metric.id] = result
        if result.status in {"unavailable", "error"} and result.reason:
            warnings.append(_result_warning(metric.id, result.reason))
        chart = chart_ids.get(metric.id)
        if chart is not None:
            points = result.value if isinstance(result.value, list) else []
            charts.append({
                "id": chart.id,
                "title": _label(metric),
                "type": "line" if chart.kind == "trend" else "bar",
                "xKey": "name",
                "yKey": "value",
                "data": [{"name": _public_value(point.get("category")), "value": _public_value(point.get("value"))} for point in points],
                "status": result.status,
                "reason": result.reason,
            })

    metrics = [_metric_payload(metric, results[metric.id]) for metric in plan.metrics]
    return {
        "planner_mode": "v2",
        "catalog_version": catalog.version,
        "plan_hash": plan.plan_hash,
        "available_tables": [
            table.name for table in catalog.tables
            if not selected_table or table.name == selected_table
        ],
        "key_metrics": metrics,
        "charts": charts,
        "data_quality": {"warnings": list(dict.fromkeys(warnings))},
    }


def run_sql_plan(
    connection: Connection,
    *,
    date_from: str | None = None,
    date_to_excl: str | None = None,
    selected_table: str | None = None,
    sample_size: int = 10_000,
    max_tables: int = 100,
    max_columns_per_table: int = 256,
    time_budget_seconds: float = 30.0,
) -> dict[str, Any]:
    prepared = prepare_sql_plan(
        connection, selected_table=selected_table, sample_size=sample_size,
        max_tables=max_tables, max_columns_per_table=max_columns_per_table,
        time_budget_seconds=time_budget_seconds,
    )
    return execute_prepared_sql_plan(
        connection, prepared, date_from=date_from,
        date_to_excl=date_to_excl, selected_table=selected_table,
    )


def prepare_mongo_plan(
    database: Any,
    *,
    date_from: str | None = None,
    date_to_excl: str | None = None,
    selected_collection: str | None = None,
    sample_size: int = 1_000,
    max_collections: int = 100,
    time_budget_seconds: float = 30.0,
    catalog_cache_namespace: str | None = None,
    catalog_cache_get: Callable[[str], Any] | None = None,
    catalog_cache_set: Callable[[str, Any], Any] | None = None,
) -> PreparedMongoPlan:
    """Discover and plan Mongo fields before a cache lookup."""
    deadline = time.monotonic() + max(0.1, min(float(time_budget_seconds), 30.0))
    cache_key = (
        f"{catalog_cache_namespace}:p{MONGO_PROFILE_VERSION}:s{sample_size}:"
        f"c{max_collections}:d{DEFAULT_MONGO_MAX_DEPTH}"
        if catalog_cache_namespace else None
    )
    catalog = catalog_cache_get(cache_key) if cache_key and catalog_cache_get else None
    if not isinstance(catalog, MongoCatalog):
        catalog = discover_mongo_catalog(
            database, max_collections=max_collections, sample_size=sample_size,
            deadline=deadline,
        )
        catalog_complete = not any(
            "could not be profiled" in warning or "time budget reached" in warning
            for warning in catalog.warnings
        )
        if cache_key and catalog_cache_set and catalog_complete:
            catalog_cache_set(cache_key, catalog)
    plan = build_mongo_plan(catalog)
    return PreparedMongoPlan(catalog, plan, deadline)


def execute_prepared_mongo_plan(
    database: Any,
    prepared: PreparedMongoPlan,
    *,
    date_from: str | None = None,
    date_to_excl: str | None = None,
    selected_collection: str | None = None,
) -> dict[str, Any]:
    catalog, plan, deadline = prepared.catalog, prepared.plan, prepared.deadline
    metrics: list[dict[str, Any]] = []
    charts: list[dict[str, Any]] = []
    warnings = list(plan.warnings)
    if selected_collection and not any(
        collection.name == selected_collection for collection in catalog.collections
    ):
        warnings.append("The selected Mongo collection is absent from the discovered catalog")
        metrics.extend((
            {
                "id": f"document_count_{selected_collection}", "label": "Document count",
                "value": None, "raw_value": None, "status": "unavailable",
                "reason": "missing_table", "format": "number", "table": selected_collection,
                "semantic": "neutral",
            },
            {
                "id": "revenue_total", "label": "Gross Revenue (all statuses)",
                "value": None, "raw_value": None, "status": "unavailable",
                "reason": "missing_table", "format": "currency", "table": selected_collection,
                "semantic": "revenue",
            },
            {
                "id": "net_revenue", "label": "Net Revenue (delivered only)",
                "value": None, "raw_value": None, "status": "unavailable",
                "reason": "missing_table", "format": "currency", "table": selected_collection,
                "semantic": "net_revenue",
            },
        ))
        return {
            "planner_mode": "v2", "catalog_version": catalog.version,
            "plan_hash": plan.plan_hash,
            "available_tables": [collection.name for collection in catalog.collections],
            "key_metrics": metrics, "charts": charts,
            "data_quality": {"warnings": list(dict.fromkeys(warnings))},
        }
    for metric in plan.metrics:
        if selected_collection and metric.collection != selected_collection:
            continue
        if metric.status != "available":
            result = MongoMetricResult(metric.id, metric.status, metric.reason)
        elif time.monotonic() >= deadline:
            result = MongoMetricResult(metric.id, "unavailable", "budget_exceeded")
        else:
            result = execute_mongo_metric(
                database[metric.collection], metric, date_from=date_from,
                date_to_excl=date_to_excl, deadline=deadline,
            )
        if result.status in {"error", "unavailable"} and result.reason:
            warnings.append(_result_warning(metric.id, result.reason))
        value = _public_value(result.value)
        if metric.semantic == "revenue":
            label = "Gross Revenue (all statuses)"
        elif metric.semantic == "net_revenue":
            label = "Net Revenue (delivered only)"
        elif metric.kind == "count":
            label = f"Document count: {metric.collection}"
        else:
            label = f"{metric.kind.title()}: {metric.measure}"
        raw_value = value if result.status in {"available", "zero"} else None
        formatted = (
            f"${raw_value:,.2f}"
            if isinstance(raw_value, (int, float)) and metric.semantic in {"revenue", "net_revenue"}
            else str(raw_value) if isinstance(raw_value, (int, float)) else raw_value
        )
        metrics.append({
            "id": metric.id, "label": label, "value": formatted, "raw_value": raw_value,
            "status": result.status, "reason": result.reason,
            "format": "currency" if metric.semantic in {"revenue", "net_revenue"} else "number",
            "table": metric.collection, "semantic": "neutral",
        })
        if metric.kind in {"trend", "breakdown"}:
            points = result.value if isinstance(result.value, list) else []
            charts.append({
                "id": metric.id, "title": label,
                "type": "line" if metric.kind == "trend" else "bar",
                "xKey": "name", "yKey": "value",
                "data": [{"name": _public_value(point.get("category")), "value": _public_value(point.get("value"))} for point in points],
                "status": result.status, "reason": result.reason,
            })
    return {
        "planner_mode": "v2",
        "catalog_version": catalog.version,
        "plan_hash": plan.plan_hash,
        "available_tables": [
            collection.name for collection in catalog.collections
            if not selected_collection or collection.name == selected_collection
        ],
        "key_metrics": metrics,
        "charts": charts,
        "data_quality": {"warnings": list(dict.fromkeys(warnings))},
    }


def run_mongo_plan(
    database: Any,
    *,
    date_from: str | None = None,
    date_to_excl: str | None = None,
    selected_collection: str | None = None,
    sample_size: int = 1_000,
    max_collections: int = 100,
    time_budget_seconds: float = 30.0,
) -> dict[str, Any]:
    prepared = prepare_mongo_plan(
        database, sample_size=sample_size, max_collections=max_collections,
        time_budget_seconds=time_budget_seconds,
    )
    return execute_prepared_mongo_plan(
        database, prepared, date_from=date_from, date_to_excl=date_to_excl,
        selected_collection=selected_collection,
    )
