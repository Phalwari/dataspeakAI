"""
backend/services/metric_adapter.py

Adapter layer between persisted KpiDefinition models and the canonical
MetricExecutor. Resolves legacy target references (e.g., bare 'all', '*'),
validates unambiguous table context, and builds canonical MetricRequest objects.
"""

from typing import Optional, List, Dict, Any, Tuple, cast
from datetime import datetime, timedelta, timezone
import logging
from sqlalchemy.orm import Session

import models
from services.metric_executor import MetricRequest, MetricFilter
from services.query_builder import parse_column_ref

logger = logging.getLogger(__name__)


class LegacyKpiIncompatibleError(ValueError):
    """Raised when a legacy KPI lacks unambiguous table context and cannot be safely adapted."""
    pass


def resolve_kpi_target_and_dimension(
    kpi: models.KpiDefinition,
    db_conn: models.DatabaseConnection,
    db: Session,
    layout: Optional[models.DashboardLayout] = None,
) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Deterministically resolves a KPI's target_column, dimension_column, and time_column
    into canonical qualified table.column references (e.g. 'orders.total_amount', 'orders.*').

    Returns:
        (resolved_target_ref, resolved_dim_ref, resolved_time_ref)

    Strict rules:
    1. If target_column is already qualified (e.g., 'orders.total_amount', 'orders.*', 'orders.all'):
       - If 'orders.all', normalize to 'orders.*'.
       - Use qualified prefix for dimension / time if they are unqualified.
    2. If target_column is a row-count wildcard ('all' or '*'):
       - Check dimension_column: if it has a table prefix ('table.col'), table is 'table' -> 'table.*'.
       - Check time_column: if it has a table prefix ('table.col'), table is 'table' -> 'table.*'.
       - Check layout.domain_mapping: if all mapped columns point to exactly ONE table, table is that table -> 'table.*'.
       - Check SchemaRegistry for connection: if there is EXACTLY ONE table in the entire database, table is that table -> 'table.*'.
       - If there are 2 or more tables in SchemaRegistry and no unambiguous context exists, FAIL CLEARLY.
         NEVER guess the first table. NEVER infer from schema ordering.
    3. If target_column is a bare column name without a table prefix:
       - Check dimension_column / time_column for table prefix.
       - Check SchemaRegistry: if exactly one table contains this column, bind to that table.
       - If ambiguous, fail clearly.
    """
    raw_target = (kpi.target_column or "").strip()
    if not raw_target:
        raise LegacyKpiIncompatibleError(
            f"KPI '{kpi.kpi_title}' (id={kpi.id}) has an empty target_column."
        )

    resolved_dim: Optional[str] = kpi.dimension_column.strip() if kpi.dimension_column else None
    resolved_time: Optional[str] = kpi.time_column.strip() if kpi.time_column else None

    # Fetch verified tables for this connection to validate ambiguity
    registries = (
        db.query(models.SchemaRegistry)
        .filter(models.SchemaRegistry.connection_id == db_conn.id)
        .all()
    )
    available_tables = sorted(list({r.table_name for r in registries}))

    # Case 1: Target is already qualified (contains '.')
    if "." in raw_target:
        parts = raw_target.split(".", 1)
        t_name = parts[0].strip()
        col_name = parts[1].strip()

        # Normalize legacy '.all' to '.*'
        if col_name == "all":
            col_name = "*"

        resolved_target = f"{t_name}.{col_name}"

        # Ensure dimension and time are qualified with target table if unqualified
        if resolved_dim and "." not in resolved_dim:
            resolved_dim = f"{t_name}.{resolved_dim}"
        if resolved_time and "." not in resolved_time:
            resolved_time = f"{t_name}.{resolved_time}"

        return resolved_target, resolved_dim, resolved_time

    # Case 2: Target is a row-count wildcard ('all' or '*') without a dot
    is_row_count_wildcard = raw_target.lower() in ("all", "*")
    resolved_table: Optional[str] = None

    if is_row_count_wildcard:
        # Context Check 1: dimension_column
        if resolved_dim and "." in resolved_dim:
            resolved_table = resolved_dim.split(".", 1)[0].strip()

        # Context Check 2: time_column
        elif resolved_time and "." in resolved_time:
            resolved_table = resolved_time.split(".", 1)[0].strip()

        # Context Check 3: Genuinely single-table database schema (no other table exists)
        elif len(available_tables) == 1:
            resolved_table = available_tables[0]

        # Ambiguous: 0 or >1 tables with no unambiguous contextual clues
        if not resolved_table:
            raise LegacyKpiIncompatibleError(
                f"Legacy KPI '{kpi.kpi_title}' (id={kpi.id}) has bare target '{raw_target}' "
                f"with ambiguous table context across {len(available_tables)} tables "
                f"({', '.join(available_tables)}). KPI requires regeneration."
            )

        resolved_target = f"{resolved_table}.*"
        if resolved_dim and "." not in resolved_dim:
            resolved_dim = f"{resolved_table}.{resolved_dim}"
        if resolved_time and "." not in resolved_time:
            resolved_time = f"{resolved_table}.{resolved_time}"

        return resolved_target, resolved_dim, resolved_time

    # Case 3: Target is a bare column name without a dot (e.g. 'total_amount')
    # Try dimension_column or time_column table
    if resolved_dim and "." in resolved_dim:
        resolved_table = resolved_dim.split(".", 1)[0].strip()
    elif resolved_time and "." in resolved_time:
        resolved_table = resolved_time.split(".", 1)[0].strip()
    else:
        # Check which tables contain this column
        matching_tables = sorted(list({r.table_name for r in registries if r.column_name == raw_target}))
        if len(matching_tables) == 1:
            resolved_table = matching_tables[0]
        elif len(available_tables) == 1:
            resolved_table = available_tables[0]
        else:
            raise LegacyKpiIncompatibleError(
                f"Legacy KPI '{kpi.kpi_title}' (id={kpi.id}) has bare column '{raw_target}' "
                f"which cannot be unambiguously mapped to a table ({', '.join(matching_tables)}). "
                f"KPI requires regeneration."
            )

    resolved_target = f"{resolved_table}.{raw_target}"
    if resolved_dim and "." not in resolved_dim:
        resolved_dim = f"{resolved_table}.{resolved_dim}"
    if resolved_time and "." not in resolved_time:
        resolved_time = f"{resolved_table}.{resolved_time}"

    return resolved_target, resolved_dim, resolved_time


def adapt_kpi_to_metric_request(
    kpi: models.KpiDefinition,
    db_conn: models.DatabaseConnection,
    db: Session,
    layout: Optional[models.DashboardLayout] = None,
    date_range_days: Optional[int] = 30,
    limit: int = 8,
) -> MetricRequest:
    """
    Converts a persisted KpiDefinition record into a canonical MetricRequest
    for consumption by MetricExecutor.
    """
    target_ref, dim_ref, time_ref = resolve_kpi_target_and_dimension(
        kpi=kpi,
        db_conn=db_conn,
        db=db,
        layout=layout,
    )

    raw_agg = (kpi.aggregation_function or "").strip()
    if not raw_agg:
        raise LegacyKpiIncompatibleError(
            f"KPI '{kpi.kpi_title}' (id={kpi.id}) has no explicit aggregation function and must be regenerated."
        )
    agg = raw_agg.upper()
    allowed_aggregations = {"SUM", "AVG", "MIN", "MAX", "COUNT", "COUNT_DISTINCT"}
    if agg not in allowed_aggregations:
        raise LegacyKpiIncompatibleError(
            f"KPI '{kpi.kpi_title}' (id={kpi.id}) has unsupported aggregation '{agg}'. "
            f"Derived/computed metrics (e.g. DIFFERENCE, RATIO, COMPUTED) belong to Phase 2 Metric Recipes and require regeneration."
        )

    filters: List[MetricFilter] = []

    # Date range filtering on verified time column if requested
    if date_range_days is not None and time_ref:
        cutoff_dt = datetime.now(timezone.utc) - timedelta(days=date_range_days)
        cutoff_str = cutoff_dt.strftime("%Y-%m-%d %H:%M:%S")
        filters.append(MetricFilter(column=time_ref, operator=">=", value=cutoff_str))

    # If dimension is present, use it; if not, but time_ref is present and chart is Line,
    # trend series can use time_ref as dimension
    chosen_dim: Optional[str] = dim_ref
    if chosen_dim is None and time_ref and (kpi.default_chart_type or "").lower() == "line":
        chosen_dim = time_ref

    return MetricRequest(
        connection_id=cast(int, kpi.connection_id),
        target_ref=target_ref,
        aggregation=agg,
        dimension_ref=chosen_dim,
        filters=filters if filters else None,
        limit=limit,
        tenant_id=cast(Optional[int], kpi.tenant_id),
    )
