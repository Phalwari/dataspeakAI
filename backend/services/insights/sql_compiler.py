"""Allowlisted compiler and executor for V2 metric plans."""

from __future__ import annotations

import logging
import time
import datetime as dt
from dataclasses import dataclass
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.engine import Connection

from services.insights.catalog import Catalog, Table
from services.insights.planner import MetricSpec
from services.insights.budget import sqlite_deadline
from services.sql_dialect import UnsupportedDialectError, cast_numeric, cast_text, month_bucket, quote_ident


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CompiledMetric:
    metric_id: str
    kind: str
    sql: str | None
    params: dict[str, Any]
    status: str = "available"
    reason: str | None = None


@dataclass(frozen=True)
class MetricResult:
    metric_id: str
    kind: str
    status: str
    reason: str | None
    value: Any = None


class MetricPlanValidationError(ValueError):
    """Raised when a plan references identifiers outside the discovered catalog."""


def _table(catalog: Catalog, name: str | None) -> Table:
    table = catalog.table(name) if name is not None else None
    if table is None:
        raise MetricPlanValidationError("Metric table is absent from the discovered catalog")
    return table


def _column(table: Table, name: str | None) -> str:
    if name is None or not any(column.name == name for column in table.columns):
        raise MetricPlanValidationError("Metric column is absent from the discovered catalog")
    return name


def _qualified(table: Table, column_name: str | None, catalog: Catalog) -> str:
    table_name = quote_ident(table.name, catalog.dialect)
    if catalog.schema:
        table_name = f"{quote_ident(catalog.schema, catalog.dialect)}.{table_name}"
    if column_name is None:
        return table_name
    return f"{table_name}.{quote_ident(_column(table, column_name), catalog.dialect)}"


def _from_clause(metric: MetricSpec, catalog: Catalog) -> str:
    base = _table(catalog, metric.table)
    clause = _qualified(base, None, catalog)
    current = base.name
    for step in metric.joins:
        if step.from_table != current or len(step.from_columns) != len(step.join_columns) or not step.from_columns:
            raise MetricPlanValidationError("Relationship path is inconsistent with the metric plan")
        left = _table(catalog, step.from_table)
        right = _table(catalog, step.join_table)
        conditions = [
            f"{_qualified(left, left_column, catalog)} = {_qualified(right, right_column, catalog)}"
            for left_column, right_column in zip(step.from_columns, step.join_columns)
        ]
        clause += f" JOIN {_qualified(right, None, catalog)} ON {' AND '.join(conditions)}"
        current = right.name
    if metric.dimension_table and metric.dimension_table != current:
        raise MetricPlanValidationError("Dimension table is not reached by the declared relationship path")
    return clause


def compile_metric(
    metric: MetricSpec,
    catalog: Catalog,
    *,
    date_from: str | None = None,
    date_to_excl: str | None = None,
    filter_column: str | None = None,
    filter_value: str | None = None,
) -> CompiledMetric:
    """Compile only known metric kinds, catalog identifiers, and bound date values."""
    if metric.status != "available":
        return CompiledMetric(metric.id, metric.kind, None, {}, metric.status, metric.reason)
    if catalog.dialect not in {"sqlite", "postgresql", "mysql", "mariadb"}:
        raise UnsupportedDialectError("Unsupported SQL dialect for insights")
    try:
        parsed_from = dt.date.fromisoformat(date_from) if date_from else None
        parsed_to = dt.date.fromisoformat(date_to_excl) if date_to_excl else None
        if (date_from and parsed_from.isoformat() != date_from) or (
            date_to_excl and parsed_to.isoformat() != date_to_excl
        ) or (parsed_from and parsed_to and parsed_from >= parsed_to):
            raise ValueError("Invalid date bounds")
    except (TypeError, ValueError):
        return CompiledMetric(metric.id, metric.kind, None, {}, "error", "invalid_date")
    table = _table(catalog, metric.table)
    from_clause = _from_clause(metric, catalog)
    params: dict[str, Any] = {}
    predicates: list[str] = []
    if date_from or date_to_excl:
        if not metric.date_column:
            return CompiledMetric(metric.id, metric.kind, None, {}, "unavailable", "missing_role")
        date_sql = _qualified(table, metric.date_column, catalog)
        if date_from:
            predicates.append(f"{date_sql} >= :date_from")
            params["date_from"] = date_from
        if date_to_excl:
            predicates.append(f"{date_sql} < :date_to_excl")
            params["date_to_excl"] = date_to_excl

    if filter_column is not None:
        filter_parts = filter_column.split(".", 1)
        filter_table_name = filter_parts[0] if len(filter_parts) == 2 else metric.table
        filter_name = filter_parts[1] if len(filter_parts) == 2 else filter_column
        involved_tables = {metric.table, *(step.join_table for step in metric.joins)}
        if filter_table_name in involved_tables:
            filter_table = _table(catalog, filter_table_name)
            filter_sql = _qualified(filter_table, filter_name, catalog)
            predicates.append(f"{filter_sql} = :dimension_value")
            params["dimension_value"] = filter_value

    where_sql = f" WHERE {' AND '.join(predicates)}" if predicates else ""
    if metric.kind == "trend" and not (date_from or date_to_excl):
        date_sql = _qualified(table, metric.date_column, catalog)
        predicates.append(f"{date_sql} IS NOT NULL")
        where_sql = f" WHERE {' AND '.join(predicates)}"
    if metric.status_values:
        status_table = _table(catalog, metric.table)
        status_column = _qualified(status_table, metric.status_column, catalog)
        predicates.append(f"LOWER({cast_text(status_column, catalog.dialect)}) IN :delivered_statuses")
        params["delivered_statuses"] = tuple(value.casefold() for value in metric.status_values)
        where_sql = f" WHERE {' AND '.join(predicates)}"
    if metric.kind == "count":
        sql = f"SELECT COUNT(*) AS value FROM {from_clause}{where_sql}"
    elif metric.kind in {"sum", "avg", "distinct_count"}:
        measure = _qualified(table, metric.measure, catalog)
        expression = {
            "sum": f"SUM({measure})",
            "avg": f"AVG({measure})",
            "distinct_count": f"COUNT(DISTINCT {measure})",
        }[metric.kind]
        sql = f"SELECT {expression} AS value FROM {from_clause}{where_sql}"
    elif metric.kind == "ratio":
        numerator = _qualified(table, metric.numerator, catalog)
        denominator = _qualified(table, metric.denominator, catalog)
        sql = (
            f"SELECT {cast_numeric(f'SUM({numerator})', catalog.dialect)} "
            f"/ NULLIF(SUM({denominator}), 0) AS value "
            f"FROM {from_clause}{where_sql}"
        )
    elif metric.kind == "trend":
        measure = _qualified(table, metric.measure, catalog)
        date_column = _qualified(table, metric.date_column, catalog)
        bucket = month_bucket(date_column, catalog.dialect)
        sql = (
            f"SELECT {bucket} AS category, SUM({measure}) AS value FROM {from_clause}{where_sql} "
            f"GROUP BY {bucket} ORDER BY {bucket}"
        )
    elif metric.kind == "breakdown":
        measure = _qualified(table, metric.measure, catalog)
        dimension_table = _table(catalog, metric.dimension_table or metric.table)
        dimension = _qualified(dimension_table, metric.dimension, catalog)
        sql = (
            f"SELECT {dimension} AS category, SUM({measure}) AS value FROM {from_clause}{where_sql} "
            f"GROUP BY {dimension} ORDER BY value DESC LIMIT 50"
        )
    else:
        raise MetricPlanValidationError("Metric kind is not supported by the V2 compiler")
    return CompiledMetric(metric.id, metric.kind, sql, params)


def execute_metric(
    connection: Connection, compiled: CompiledMetric, *, deadline: float | None = None,
) -> MetricResult:
    """Execute one compiled plan and preserve zero, unavailable, and error separately."""
    if compiled.status != "available" or compiled.sql is None:
        return MetricResult(compiled.metric_id, compiled.kind, compiled.status, compiled.reason)
    try:
        with sqlite_deadline(connection, deadline) as timed_out:
            if timed_out():
                return MetricResult(compiled.metric_id, compiled.kind, "unavailable", "budget_exceeded")
            statement = text(compiled.sql)
            if "delivered_statuses" in compiled.params:
                statement = statement.bindparams(bindparam("delivered_statuses", expanding=True))
            rows = [dict(row._mapping) for row in connection.execute(statement, compiled.params)]
            if timed_out():
                return MetricResult(compiled.metric_id, compiled.kind, "unavailable", "budget_exceeded")
        if compiled.kind in {"trend", "breakdown"}:
            if not rows:
                return MetricResult(compiled.metric_id, compiled.kind, "unavailable", "no_rows", [])
            if all(row.get("value") is None for row in rows):
                return MetricResult(compiled.metric_id, compiled.kind, "unavailable", "no_rows", [])
            return MetricResult(compiled.metric_id, compiled.kind, "available", None, rows)
        value = rows[0].get("value") if rows else None
        if value is None:
            return MetricResult(compiled.metric_id, compiled.kind, "unavailable", "no_rows")
        try:
            is_zero = float(value) == 0.0
        except (TypeError, ValueError, OverflowError):
            is_zero = False
        return MetricResult(
            compiled.metric_id, compiled.kind, "zero" if is_zero else "available", None, value,
        )
    except Exception:
        logger.warning("Insights metric query failed")
        if deadline is not None and time.monotonic() >= deadline:
            return MetricResult(compiled.metric_id, compiled.kind, "unavailable", "budget_exceeded")
        return MetricResult(compiled.metric_id, compiled.kind, "error", "query_failed")
