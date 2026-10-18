"""
backend/services/metric_executor.py

Canonical Metric Execution Engine for DataSpeakAI.
Single calculation authority for deterministic KPI cards and chart series.
Validates semantic rules, enforces table boundaries, generates parameterized SQL,
and executes queries against verified database connections.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Union
import logging
from sqlalchemy import text
from sqlalchemy.orm import Session

import models
from services.query_builder import (
    build_aggregated_chart_query,
    parse_column_ref,
    quote_ident,
)
from services.metric_semantics import validate_metric_aggregation
from services.db_utils import get_connection_url
from services.db_pool import get_engine

logger = logging.getLogger(__name__)


@dataclass
class MetricFilter:
    column: str
    operator: str  # "=", "!=", ">", "<", ">=", "<=", "LIKE"
    value: Any


@dataclass
class MetricRequest:
    connection_id: int
    target_ref: str
    aggregation: str
    dimension_ref: Optional[str] = None
    filters: Optional[List[MetricFilter]] = None
    limit: int = 10
    tenant_id: Optional[int] = None
    entity_grain: Optional[str] = None
    unit: Optional[str] = None
    date_field: Optional[str] = None
    missing_value_policy: str = "zero"


@dataclass
class MetricResult:
    target: str
    aggregation: str
    is_scalar: bool
    value: Optional[Union[int, float]] = None
    data: Optional[List[Dict[str, Any]]] = None
    dimension: Optional[str] = None
    sql: str = ""


class MetricExecutor:
    """
    Executes structured metric calculations with strict semantic enforcement.
    Guarantees no arbitrary SQL generation, no unvalidated joins, and bound parameter safety.
    """

    ALLOWED_OPERATORS = {"=", "!=", ">", "<", ">=", "<=", "LIKE", "ILIKE", "IN"}

    @classmethod
    def execute(
        cls,
        request: MetricRequest,
        db_conn: models.DatabaseConnection,
        db: Session,
    ) -> MetricResult:
        """
        Main execution pathway for a single metric.
        """
        # Tenant scoping validation
        if request.tenant_id is not None and db_conn.tenant_id != request.tenant_id:
            raise ValueError(
                f"Unauthorized: Connection {db_conn.id} does not belong to tenant {request.tenant_id}"
            )

        db_type = (db_conn.db_type or "sqlite").lower()

        # 1. Parse target reference
        target_ref = (request.target_ref or "").strip()
        if not target_ref:
            raise ValueError("Target column reference cannot be empty.")

        # Canonical handling of row-count wildcard targets (* or all)
        is_row_count_wildcard = target_ref in ("*", "all")
        if is_row_count_wildcard:
            if request.aggregation.upper() != "COUNT":
                raise ValueError(
                    f"Wildcard target '{target_ref}' is only valid for COUNT aggregation. "
                    f"Cannot calculate '{request.aggregation.upper()}*' without a numeric column."
                )
            # If dimension_ref is provided, use its table, otherwise must be qualified table.*
            if request.dimension_ref and "." in request.dimension_ref:
                target_table = request.dimension_ref.split(".", 1)[0].strip()
                target_col = "*"
            else:
                raise ValueError(
                    f"Wildcard target '{target_ref}' requires table qualification (e.g. 'orders.*' or 'orders.all')."
                )
        else:
            target_table, target_col = parse_column_ref(target_ref)

        # 2. Parse dimension reference (if provided)
        dim_table: Optional[str] = None
        dim_col: Optional[str] = None
        if request.dimension_ref:
            dim_table, dim_col = parse_column_ref(request.dimension_ref)

            # Phase 1.5B Constraint: Enforce same-table metrics (no unvalidated joins)
            if dim_table != target_table:
                raise ValueError(
                    f"Cross-table metric requires a validated relationship path. "
                    f"Target '{target_table}' and Dimension '{dim_table}' belong to different tables."
                )

        # 3. Verify Table and Column against SchemaRegistry
        registry_entries = (
            db.query(models.SchemaRegistry)
            .filter(
                models.SchemaRegistry.connection_id == db_conn.id,
                models.SchemaRegistry.table_name == target_table,
            )
            .all()
        )

        if not registry_entries:
            raise ValueError(
                f"Table '{target_table}' does not exist in verified SchemaRegistry for connection {db_conn.id}."
            )

        registry_map = {r.column_name: r for r in registry_entries}

        target_reg: Optional[models.SchemaRegistry] = None
        if target_col != "*":
            if target_col not in registry_map:
                raise ValueError(
                    f"Column '{target_col}' does not exist in table '{target_table}' for connection {db_conn.id}."
                )
            target_reg = registry_map[target_col]

        dim_reg: Optional[models.SchemaRegistry] = None
        if dim_col:
            if dim_col not in registry_map:
                raise ValueError(
                    f"Dimension column '{dim_col}' does not exist in table '{target_table}' for connection {db_conn.id}."
                )
            dim_reg = registry_map[dim_col]

        # 4. Semantic Policy Validation
        validate_metric_aggregation(
            target_ref=f"{target_table}.{target_col}",
            aggregation=request.aggregation,
            col_reg=target_reg,
        )

        # 5. Build Parameterized Filter Clauses (Safe Bound Parameters)
        where_clauses: List[str] = []
        bound_params: Dict[str, Any] = {}

        if request.filters:
            for idx, flt in enumerate(request.filters):
                flt_table, flt_col = parse_column_ref(flt.column)
                if flt_table != target_table:
                    raise ValueError(
                        f"Filter column '{flt.column}' must belong to the metric table '{target_table}'."
                    )
                if flt_col not in registry_map:
                    raise ValueError(
                        f"Filter column '{flt_col}' does not exist in table '{target_table}'."
                    )

                op = flt.operator.strip().upper()
                if op not in cls.ALLOWED_OPERATORS:
                    raise ValueError(f"Unsupported filter operator '{flt.operator}'.")

                col_q = quote_ident(flt_col, db_type)

                if op == "IN":
                    if not isinstance(flt.value, (list, tuple, set)):
                        raise ValueError(
                            f"Filter operator 'IN' requires a list, tuple, or set of values, got {type(flt.value).__name__}."
                        )
                    vals = list(flt.value)
                    if not vals:
                        where_clauses.append("1 = 0")
                    else:
                        in_keys = []
                        for j, v in enumerate(vals):
                            pkey = f"flt_{idx}_{j}"
                            in_keys.append(f":{pkey}")
                            bound_params[pkey] = v
                        where_clauses.append(f"{col_q} IN ({', '.join(in_keys)})")
                else:
                    if isinstance(flt.value, (list, tuple, set)):
                        raise ValueError(
                            f"Scalar filter operator '{op}' does not support list/tuple/set values. Use 'IN' instead."
                        )
                    param_key = f"flt_{idx}"
                    where_clauses.append(f"{col_q} {op} :{param_key}")
                    bound_params[param_key] = flt.value

        # 6. Build SQL Query using centralized query_builder
        sql_query = build_aggregated_chart_query(
            table=target_table,
            target_col=target_col,
            dim_col=dim_col,
            agg_func=request.aggregation,
            limit=request.limit,
            where_clauses=where_clauses,
            db_type=db_type,
        )

        # 7. Execute Query against Connection Engine
        conn_url = get_connection_url(db_conn)
        if not conn_url:
            raise ValueError(f"Could not resolve database connection URL for connection {db_conn.id}")
        engine = get_engine(conn_url)
        with engine.connect() as conn:
            cursor = conn.execute(text(sql_query), bound_params)

            if dim_col is None:
                # Scalar KPI metric result
                row = cursor.fetchone()
                raw_val = row[0] if row and row[0] is not None else 0
                normalized_val: Union[int, float]
                if isinstance(raw_val, float):
                    normalized_val = round(raw_val, 2)
                elif isinstance(raw_val, int):
                    normalized_val = raw_val
                else:
                    try:
                        normalized_val = round(float(raw_val), 2)
                    except (ValueError, TypeError):
                        normalized_val = 0

                return MetricResult(
                    target=f"{target_table}.{target_col}",
                    aggregation=request.aggregation.upper(),
                    is_scalar=True,
                    value=normalized_val,
                    sql=sql_query,
                )
            else:
                # Dimension breakdown series
                rows = cursor.fetchall()
                data_points = []
                for r in rows:
                    dim_val = str(r[0]) if r[0] is not None else "Unknown"
                    metric_raw = r[1] if len(r) > 1 and r[1] is not None else 0
                    try:
                        metric_val = round(float(metric_raw), 2)
                    except (ValueError, TypeError):
                        metric_val = 0.0
                    data_points.append({"dimension": dim_val, "value": metric_val})

                return MetricResult(
                    target=f"{target_table}.{target_col}",
                    aggregation=request.aggregation.upper(),
                    is_scalar=False,
                    dimension=f"{target_table}.{dim_col}",
                    data=data_points,
                    sql=sql_query,
                )
