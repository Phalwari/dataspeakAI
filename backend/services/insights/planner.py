"""Pure-Python metric planning. This module deliberately contains no SQL text."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from services.insights import PLANNER_VERSION, ROLE_RULES_VERSION
from services.insights.catalog import Catalog
from services.insights.profiling import ProfileSet
from services.insights.relationships import Relationship, declared_relationships, find_relationship_path
from services.insights.roles import ColumnRole, classify_table_roles


@dataclass(frozen=True)
class JoinSpec:
    from_table: str
    from_columns: tuple[str, ...]
    join_table: str
    join_columns: tuple[str, ...]
    source: str = "declared"
    confidence: float = 1.0


@dataclass(frozen=True)
class MetricSpec:
    id: str
    kind: str
    table: str | None
    measure: str | None = None
    numerator: str | None = None
    denominator: str | None = None
    date_column: str | None = None
    dimension: str | None = None
    dimension_table: str | None = None
    joins: tuple[JoinSpec, ...] = ()
    status_column: str | None = None
    status_values: tuple[str, ...] = ()
    prerequisites: tuple[str, ...] = ()
    required_roles: tuple[str, ...] = ()
    status: str = "available"
    reason: str | None = None
    semantic: str = "neutral"


@dataclass(frozen=True)
class ChartSpec:
    id: str
    kind: str
    table: str | None
    measure: str | None = None
    date_column: str | None = None
    dimension: str | None = None
    dimension_table: str | None = None
    joins: tuple[JoinSpec, ...] = ()
    status: str = "available"
    reason: str | None = None


@dataclass(frozen=True)
class MetricPlan:
    catalog_version: str
    role_rules_version: str
    plan_hash: str
    roles: dict[str, dict[str, ColumnRole]]
    metrics: tuple[MetricSpec, ...]
    charts: tuple[ChartSpec, ...]
    warnings: tuple[str, ...] = ()


def _slug(value: str) -> str:
    result = re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")
    return result[:48] or "unnamed"


def _plan_hash(catalog: Catalog, roles: dict[str, dict[str, ColumnRole]]) -> str:
    serialized = {
        "planner": PLANNER_VERSION,
        "rules": ROLE_RULES_VERSION,
        "catalog": catalog.version,
        "roles": {
            table: {
                column: (value.role, round(value.confidence, 4), value.measure_kind, value.revenue_candidate)
                for column, value in sorted(table_roles.items())
            }
            for table, table_roles in sorted(roles.items())
        },
    }
    raw = json.dumps(serialized, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _transaction_like(table_roles: dict[str, ColumnRole]) -> bool:
    has_date = any(role.role == "date" for role in table_roles.values())
    has_grain = any(role.role == "identifier" for role in table_roles.values())
    has_status = any(role.role == "status" for role in table_roles.values())
    return has_date and (has_grain or has_status)


def _unambiguous_date_column(table_roles: dict[str, ColumnRole]) -> str | None:
    candidates = [
        (name, role.confidence) for name, role in table_roles.items()
        if role.role == "date" and role.confidence >= 0.80
    ]
    if not candidates:
        return None
    highest = max(confidence for _, confidence in candidates)
    strongest = [name for name, confidence in candidates if confidence == highest]
    # Name order alone is not evidence. Ties remain unselected so a date filter
    # cannot silently bind to an arbitrary lifecycle timestamp.
    return strongest[0] if len(strongest) == 1 else None


def _path_joins(path: Any) -> tuple[JoinSpec, ...]:
    result = []
    for index, edge in enumerate(path.relationships):
        current = path.tables[index]
        following = path.tables[index + 1]
        if current == edge.left_table and following == edge.right_table:
            result.append(JoinSpec(current, edge.left_columns, following, edge.right_columns, edge.source, edge.confidence))
        elif current == edge.right_table and following == edge.left_table:
            result.append(JoinSpec(current, edge.right_columns, following, edge.left_columns, edge.source, edge.confidence))
        else:
            raise ValueError("Relationship path edge does not match its table sequence")
    return tuple(result)


def build_metric_plan(
    catalog: Catalog,
    profiles: ProfileSet,
    *,
    relationships: tuple[Relationship, ...] | None = None,
    selected_table: str | None = None,
) -> MetricPlan:
    """Create schema-derived metrics and chart intents without generating SQL."""
    roles: dict[str, dict[str, ColumnRole]] = {}
    for table in catalog.tables:
        profile = profiles.tables.get(table.name)
        foreign_key_columns = {column for foreign_key in table.foreign_keys for column in foreign_key.columns}
        roles[table.name] = classify_table_roles(
            table.columns,
            profile.columns if profile else {},
            foreign_key_columns,
        )

    metrics: list[MetricSpec] = []
    charts: list[ChartSpec] = []
    warnings: list[str] = []
    relationship_edges = relationships if relationships is not None else declared_relationships(catalog)
    if any(edge.source == "inferred" for edge in relationship_edges):
        warnings.append("Some planned joins use inferred relationships")
    if catalog.truncated:
        warnings.append("Catalog table limit reached")
    candidates: list[tuple[str, str]] = []

    analysis_tables = (
        [table for table in catalog.tables if table.name == selected_table]
        if selected_table else list(catalog.tables)
    )
    if not analysis_tables:
        metrics.append(MetricSpec(
            f"row_count_{_slug(selected_table)}" if selected_table else "row_count_all",
            "count", None, status="unavailable", reason="missing_table",
        ))
        metrics.append(MetricSpec(
            "revenue_total", "sum", None, status="unavailable", reason="missing_table",
            prerequisites=("A transaction-like table must exist",), required_roles=("additive_measure",),
            semantic="revenue",
        ))
        metrics.append(MetricSpec(
            "net_revenue", "sum", None, status="unavailable", reason="missing_table",
            prerequisites=("A transaction-like table with delivered status must exist",),
            required_roles=("additive_measure", "status"), semantic="net_revenue",
        ))
    else:
        for table in analysis_tables:
            table_roles = roles[table.name]
            slug = _slug(table.name)
            identifiers = [name for name, role in table_roles.items() if role.role == "identifier"]
            measures = [
                name for name, role in table_roles.items()
                if role.role == "additive_measure" and role.confidence >= 0.80
            ]
            dates = [name for name, role in table_roles.items() if role.role == "date" and role.confidence >= 0.80]
            date_column = _unambiguous_date_column(table_roles)
            if len(dates) > 1 and date_column is None:
                warnings.append("Ambiguous date columns were not selected for filters or trends")
            metrics.append(MetricSpec(
                f"row_count_{slug}", "count", table.name,
                date_column=date_column,
                prerequisites=("Table is present in the discovered catalog",),
            ))
            dimensions = [
                name for name, role in table_roles.items()
                if role.role in {"categorical", "status"} and role.confidence >= 0.80
            ]
            rates = [name for name, role in table_roles.items() if role.role in {"rate", "unit_price", "quantity"}]

            for identifier in identifiers[:2]:
                metrics.append(MetricSpec(
                    f"distinct_{slug}_{_slug(identifier)}", "distinct_count", table.name,
                    measure=identifier, date_column=date_column,
                    required_roles=("identifier",),
                ))
            for measure in measures[:3]:
                spec = table_roles[measure]
                semantic = spec.measure_kind or "neutral"
                metrics.append(MetricSpec(
                    f"sum_{slug}_{_slug(measure)}", "sum", table.name, measure=measure,
                    date_column=date_column,
                    required_roles=("additive_measure",), semantic=semantic,
                ))
                if spec.measure_kind == "money":
                    metrics.append(MetricSpec(
                        f"avg_{slug}_{_slug(measure)}", "avg", table.name, measure=measure,
                        date_column=date_column,
                        required_roles=("additive_measure",), semantic="neutral",
                    ))
                for trend_date_column in ([date_column] if date_column else []):
                    chart = ChartSpec(
                        f"trend_{slug}_{_slug(measure)}", "trend", table.name,
                        measure=measure, date_column=trend_date_column,
                    )
                    charts.append(chart)
                    metrics.append(MetricSpec(
                        chart.id, "trend", table.name, measure=measure,
                        date_column=trend_date_column, required_roles=("date", "additive_measure"),
                    ))
                for dimension in dimensions[:2]:
                    chart = ChartSpec(
                        f"breakdown_{slug}_{_slug(dimension)}_{_slug(measure)}", "breakdown",
                        table.name, measure=measure, dimension=dimension,
                    )
                    charts.append(chart)
                    metrics.append(MetricSpec(
                        chart.id, "breakdown", table.name, measure=measure, dimension=dimension,
                    date_column=date_column,
                        required_roles=("categorical", "additive_measure"),
                    ))
            for measure in rates[:3]:
                metrics.append(MetricSpec(
                    f"avg_{slug}_{_slug(measure)}", "avg", table.name, measure=measure,
                    date_column=date_column,
                    required_roles=(table_roles[measure].role,), semantic="neutral",
                ))
            if _transaction_like(table_roles):
                candidates.extend(
                    (table.name, column)
                    for column, role in table_roles.items()
                    if role.role == "additive_measure" and role.revenue_candidate
                )

        # Plan multi-table breakdowns only along a unique declared or verified inferred path.
        for fact in analysis_tables:
            fact_roles = roles[fact.name]
            if not _transaction_like(fact_roles):
                continue
            fact_measures = [
                (name, role) for name, role in fact_roles.items()
                if role.role == "additive_measure" and role.confidence >= 0.80
            ]
            for dimension_table in catalog.tables:
                if dimension_table.name == fact.name:
                    continue
                dimensions = [
                    (name, role) for name, role in roles[dimension_table.name].items()
                    if role.role in {"categorical", "status"} and role.confidence >= 0.80
                ]
                if not dimensions:
                    continue
                try:
                    path = find_relationship_path(
                        catalog, fact.name, dimension_table.name,
                        relationships=relationship_edges, max_depth=2,
                    )
                except ValueError:
                    warnings.append("An ambiguous relationship path was skipped")
                    continue
                if path is None:
                    continue
                warnings.append(
                    "Joined breakdowns use inner joins; unmatched fact rows are excluded when present"
                )
                joins = _path_joins(path)
                for measure, _ in fact_measures[:2]:
                    for dimension, _ in dimensions[:2]:
                        chart_id = (
                            f"breakdown_{_slug(fact.name)}_{_slug(dimension_table.name)}_"
                            f"{_slug(dimension)}_{_slug(measure)}"
                        )
                        chart = ChartSpec(
                            chart_id, "breakdown", fact.name, measure=measure,
                            dimension=dimension, dimension_table=dimension_table.name, joins=joins,
                        )
                        charts.append(chart)
                        metrics.append(MetricSpec(
                            chart_id, "breakdown", fact.name, measure=measure,
                            dimension=dimension, dimension_table=dimension_table.name, joins=joins,
                            date_column=_unambiguous_date_column(fact_roles),
                            required_roles=("categorical", "additive_measure", "relationship"),
                        ))

    if candidates:
        table_name, measure = sorted(candidates, key=lambda pair: (pair[0].casefold(), pair[1].casefold()))[0]
        metrics.append(MetricSpec(
            "revenue_total", "sum", table_name, measure=measure,
            date_column=_unambiguous_date_column(roles[table_name]),
            prerequisites=("Transaction-like table and revenue-evidence measure",),
            required_roles=("additive_measure", "transaction_grain"), semantic="revenue",
        ))
        status_columns = [
            column for column, role in roles[table_name].items() if role.role == "status"
        ]
        if status_columns:
            metrics.append(MetricSpec(
                "net_revenue", "sum", table_name, measure=measure,
                date_column=_unambiguous_date_column(roles[table_name]),
                status_column=status_columns[0],
                status_values=("complete", "completed", "delivered", "shipped", "success", "closed"),
                prerequisites=("Revenue evidence and a configured delivered status",),
                required_roles=("additive_measure", "status", "transaction_grain"),
                semantic="net_revenue",
            ))
        else:
            metrics.append(MetricSpec(
                "net_revenue", "sum", table_name, measure=measure,
                date_column=_unambiguous_date_column(roles[table_name]),
                prerequisites=("Revenue evidence and a configured delivered status",),
                required_roles=("additive_measure", "status", "transaction_grain"),
                status="unavailable", reason="missing_role", semantic="net_revenue",
            ))
    elif analysis_tables:
        metrics.append(MetricSpec(
            "revenue_total", "sum", None,
            prerequisites=("Transaction-like table with a revenue-evidence measure",),
            required_roles=("additive_measure", "transaction_grain"),
            status="unavailable", reason="missing_role", semantic="revenue",
        ))
        metrics.append(MetricSpec(
            "net_revenue", "sum", None,
            prerequisites=("Revenue evidence and a configured delivered status",),
            required_roles=("additive_measure", "status", "transaction_grain"),
            status="unavailable", reason="missing_role", semantic="net_revenue",
        ))

    return MetricPlan(
        catalog_version=catalog.version,
        role_rules_version=ROLE_RULES_VERSION,
        plan_hash=_plan_hash(catalog, roles),
        roles=roles,
        metrics=tuple(metrics),
        charts=tuple(charts),
        warnings=tuple(dict.fromkeys(warnings)),
    )
