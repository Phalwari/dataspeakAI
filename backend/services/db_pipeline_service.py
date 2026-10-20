"""
Database Analytics Pipeline Service (Phase 2G Orchestrator)
Implements an enterprise-grade 6-Layer Deterministic Pipeline for connected databases:
- Layer 1: Schema Discovery & Multi-Table Statistical Profiling
- Layer 2: Metric Recipes & Mathematical Formulas (Phase 2C Deterministic)
- Layer 3: Deterministic Chart & Filter Planning (Phase 2D & 2E)
- Layer 4: Sub-Second Query Execution & Data Aggregation
- Layer 5: Strategic AI Executive Synthesis & Actionable Playbook
- Layer 6: Statistical Outlier & Anomaly Detection
Designed for high concurrency (200 concurrent users) with Redis L1 and DB L2 caching.
"""

from __future__ import annotations
import json
import math
import re
import datetime
import logging
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session
import models
from services.database_connection_service import db_connection_service, DatabaseConnectionService
from services.encryption_service import encryption_service
from services.metric_recipes import (
    AtomicMetricRecipe,
    RatioMetricRecipe,
    DifferenceMetricRecipe,
    MetricRecipe,
)
from services.dashboard_composer import compose_dashboard_layout, DashboardLayoutPlan
from services.redis_service import cache_get, cache_set, make_cache_key
from services.sql_dialect import (
    UnsupportedDialectError, cast_text, concat, month_bucket, quote_ident,
    round_money,
)

logger = logging.getLogger(__name__)
INSIGHTS_CACHE_VERSION = 4


def _normalize_date_range(
    date_from: Optional[str], date_to: Optional[str],
) -> Tuple[Optional[str], Optional[str], Dict[str, str]]:
    """Validate calendar dates and return an exclusive SQL upper bound."""
    parsed: Dict[str, datetime.date] = {}
    for name, value in (("date_from", date_from), ("date_to", date_to)):
        if value is None or value == "":
            continue
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError("Invalid date filter; expected YYYY-MM-DD")
        try:
            parsed[name] = datetime.date.fromisoformat(value)
        except ValueError:
            raise ValueError("Invalid date filter; expected YYYY-MM-DD") from None
    if parsed.get("date_from") and parsed.get("date_to") and parsed["date_from"] > parsed["date_to"]:
        raise ValueError("Invalid date filter; start must not exceed end")
    bindings: Dict[str, str] = {}
    if "date_from" in parsed:
        bindings["date_from"] = parsed["date_from"].isoformat()
    if "date_to" in parsed:
        try:
            bindings["date_to_excl"] = (parsed["date_to"] + datetime.timedelta(days=1)).isoformat()
        except OverflowError:
            raise ValueError("Invalid date filter; end date is out of range") from None
    return (
        parsed["date_from"].isoformat() if "date_from" in parsed else None,
        parsed["date_to"].isoformat() if "date_to" in parsed else None,
        bindings,
    )


def _pick_date_column(columns: List[str]) -> Optional[str]:
    """Use a transaction date when named; reject ambiguous date roles."""
    priorities = (
        "transaction_date", "order_date", "invoice_date", "sale_date",
        "payment_date", "created_at", "created_on", "date",
    )
    by_name = {column.casefold(): column for column in columns}
    for candidate in priorities:
        if candidate in by_name:
            return by_name[candidate]
    return columns[0] if len(columns) == 1 else None


def _with_date_predicate(query: str, table: str, column: str, bindings: Dict[str, str]) -> Optional[str]:
    """Scope a generated flat SELECT to its fact table, or reject that shape."""
    if not re.search(r"\b(?:FROM|JOIN)\s+" + re.escape(table) + r"(?![\w])", query, re.IGNORECASE):
        return None
    clauses = []
    if "date_from" in bindings:
        clauses.append(f"{table}.{column} >= :date_from")
    if "date_to_excl" in bindings:
        clauses.append(f"{table}.{column} < :date_to_excl")
    if not clauses:
        return query
    boundary = re.search(r"\b(GROUP\s+BY|ORDER\s+BY|HAVING|LIMIT)\b", query, re.IGNORECASE)
    insert_at = boundary.start() if boundary else len(query)
    head, tail = query[:insert_at].rstrip(), query[insert_at:]
    where_match = re.search(r"\bWHERE\b", head, re.IGNORECASE)
    predicate = " AND ".join(clauses)
    if where_match:
        prefix = head[:where_match.end()]
        condition = head[where_match.end():].strip()
        return f"{prefix} ({condition}) AND {predicate} {tail}"
    return f"{head} WHERE {predicate} {tail}"


def _cache_key(
    tenant_id: Optional[int], connection_id: Any, selected_table: Optional[str],
    date_from: Optional[str], date_to: Optional[str], cache_version: int = 0,
) -> str:
    return make_cache_key(
        "db_insights", str(tenant_id), str(connection_id), f"v{cache_version}",
        selected_table or "all", date_from or "none", date_to or "none",
    )


def classify_status(value: Any) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()
    if normalized in {"delivered", "complete", "completed", "shipped", "success", "closed", "paid"}:
        return "delivered"
    if normalized in {"cancel", "canceled", "cancelled", "void", "voided", "abort", "aborted"}:
        return "cancelled"
    if normalized in {"return", "returned", "refund", "refunded"}:
        return "returned"
    if normalized in {"unpaid", "pending payment", "payment pending", "awaiting payment"}:
        return "unpaid"
    return "other"


def _llm_safe_points(kpis: List[Dict[str, Any]], charts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Keep only numeric aggregates and fixed chart categories in LLM input."""
    safe_kpis = []
    for item in kpis:
        value = item.get("raw_value")
        if isinstance(value, (int, float)) and not isinstance(value, bool) and (
            not isinstance(value, float) or math.isfinite(value)
        ):
            safe_kpis.append(value)
    safe_charts = []
    for chart in charts:
        values = []
        for point in chart.get("data", []):
            value = point.get("value", point.get("val")) if isinstance(point, dict) else None
            if isinstance(value, (int, float)) and not isinstance(value, bool) and (
                not isinstance(value, float) or math.isfinite(value)
            ):
                values.append(value)
        if values:
            chart_type = chart.get("type")
            chart_category = {
                "area": "time_series",
                "line": "time_series",
                "bar": "category_aggregate",
                "donut": "category_aggregate",
                "pie": "category_aggregate",
            }.get(chart_type, "aggregate") if isinstance(chart_type, str) else "aggregate"
            safe_charts.append({"category": chart_category, "values": values[:3]})
    return {"metrics": safe_kpis, "chart_aggregates": safe_charts}


def safe_divide(num: Any, den: Any, default: Any = 0.0) -> Any:
    try:
        n = float(num)
        d = float(den)
        if d == 0:
            return default
        return n / d
    except Exception:
        return default


def safe_subtract(a: Any, b: Any, default: Any = 0.0) -> Any:
    try:
        return float(a) - float(b)
    except Exception:
        return default


def format_metric_value(val: Any, format_type: str = "number") -> str:
    if val is None:
        return "—"
    try:
        f = float(val)
        if format_type == "currency":
            return f"${f:,.2f}"
        elif format_type == "percentage":
            return f"{f:.1f}%"
        elif format_type == "integer":
            return f"{round(f):,}"
        return f"{f:,.2f}" if f % 1 != 0 else f"{int(f):,}"
    except Exception:
        return str(val)


SAFE_WORDS_ENDING_ID = {
    "paid", "valid", "grid", "solid", "arid", "avid", "rapid", 
    "liquid", "humid", "frigid", "torrid", "splendid", "horrid", 
    "sordid", "placid", "acid", "lucid", "timid", "morbid", "rabid", 
    "candid", "vivid", "hybrid", "pyramid", "eyelid", "mid", "android", "void"
}


def is_id_column(col_name: str) -> bool:
    """
    Detects identifier, foreign key, or surrogate key columns across naming styles.
    Prevents meaningless metrics like 'Average ReportsTo' or 'Sum of CustomerId'.
    """
    clean = col_name.strip()
    lname = clean.lower()
    if lname in SAFE_WORDS_ENDING_ID:
        return False
    if lname in (
        "id", "pk", "uuid", "guid", "rowid", "key", 
        "reportsto", "supportrepid", "manager", "parent", 
        "artistid", "albumid", "trackid", "genreid", 
        "mediatypeid", "customerid", "invoiceid", "invoicelineid", 
        "employeeid", "playlistid"
    ):
        return True
    if bool(re.search(r'(_id$|^id_|_id_)', lname)):
        return True
    if bool(re.search(r'[a-z0-9]Id$', clean)) or bool(re.search(r'[a-z0-9]ID$', clean)):
        return True
    if lname.endswith("id") and len(lname) > 3:
        return True
    return False


def is_unit_price_column(col_name: str) -> bool:
    """Detects if a column represents an individual unit price or rate rather than total transaction amount."""
    c_lower = col_name.lower().strip()
    return "unit" in c_lower or c_lower in ["price", "unitprice", "unit_price", "rate", "unit_cost", "item_price"]


def sort_monetary_columns_by_priority(cols: List[str]) -> List[str]:
    """
    Sorts monetary columns so total transaction amounts/revenues come FIRST,
    and individual unit rates come LAST.
    Prevents unit_price from ever taking precedence over net_revenue or gross_revenue.
    """
    def score_col(c: str) -> int:
        cl = c.lower().strip()
        if is_unit_price_column(c):
            return 100
        if "net" in cl and any(k in cl for k in ["rev", "sale", "amount"]):
            return 1
        if "gross" in cl and any(k in cl for k in ["rev", "sale", "amount"]):
            return 2
        if any(k in cl for k in ["total_amount", "grand_total", "order_total", "total_price"]):
            return 3
        if cl in ["total", "revenue", "sales", "net"]:
            return 4
        if any(k in cl for k in ["revenue", "sales", "billing", "amount"]):
            return 5
        if "profit" in cl or "margin" in cl:
            return 6
        if any(k in cl for k in ["cost", "expense", "fee"]):
            return 7
        return 50
    return sorted(cols, key=score_col)


def is_monetary_column(col_name: str) -> bool:
    """Identifies currency, revenue, price, or monetary measure columns."""
    if is_id_column(col_name):
        return False
    c_lower = col_name.lower()
    if c_lower.endswith(("_rate", "_pct", "_percent", "_percentage")):
        return False
    if re.search(r"(?:^|_)(?:orders?|items?|units?|quantity|qty|count|records?|rows?)$", c_lower):
        return False
    return any(k in c_lower for k in [
        "total", "amount", "revenue", "sales", "price", "unitprice", 
        "unit_price", "cost", "fee", "salary", "balance", "discount", 
        "subtotal", "grand_total", "spend", "net"
    ])


def is_date_column(col_name: str, col_type: str = "") -> bool:
    """Identifies date, time, or timestamp columns."""
    t_str = col_type.lower()
    c_lower = col_name.lower()
    if any(k in t_str for k in ["date", "time", "timestamp"]):
        return True
    return any(k in c_lower for k in [
        "date", "time", "created_at", "created_on", "updated_at", "updated_on", "joined_at",
        "timestamp", "order_date", "invoicedate", "birthdate", "hiredate"
    ])


def is_dimension_column(col_name: str, col_type: str = "") -> bool:
    """Identifies clean categorical dimensions (country, city, genre, category, status)."""
    if is_id_column(col_name):
        return False
    if is_date_column(col_name, col_type):
        return False
    c_lower = col_name.lower()
    # Exclude addresses, long descriptions, emails, passwords, phones, codes
    if any(k in c_lower for k in [
        "address", "postalcode", "zip", "phone", "fax", "email", 
        "password", "token", "hash", "notes", "description", 
        "comment", "picture", "photo", "url", "avatar", "file"
    ]):
        return False
    return True


def _clean_sql_identifier(name: str, db_type: str) -> str:
    """Quotes an identifier safely based on database type, allowing spaces for valid quoted identifiers."""
    cleaned = re.sub(r'[^a-zA-Z0-9_\s\-]', '', name).strip()
    return quote_ident(cleaned, db_type)


class DatabasePipelineService:
    def __init__(self):
        pass

    def invalidate_connection_cache(
        self, db: Session, tenant_id: int, connection_id: Any,
    ) -> int:
        """Atomically advance one owned connection's cache generation and clear DB L2."""
        if tenant_id is None:
            raise ValueError("Tenant ID is required for cache invalidation")

        updated = (
            db.query(models.DatabaseConnection)
            .filter(
                models.DatabaseConnection.id == connection_id,
                models.DatabaseConnection.tenant_id == tenant_id,
            )
            .update(
                {
                    models.DatabaseConnection.insights_cache_version: (
                        func.coalesce(models.DatabaseConnection.insights_cache_version, 0) + 1
                    ),
                    models.DatabaseConnection.insights_cache: None,
                    models.DatabaseConnection.insights_cached_at: None,
                },
                synchronize_session=False,
            )
        )
        if updated != 1:
            db.rollback()
            raise ValueError("Database connection not found or unauthorized")

        cache_version = (
            db.query(models.DatabaseConnection.insights_cache_version)
            .filter(
                models.DatabaseConnection.id == connection_id,
                models.DatabaseConnection.tenant_id == tenant_id,
            )
            .scalar()
        )
        db.commit()
        return int(cache_version or 0)

    def run_db_pipeline(
        self,
        db: Session,
        connection_id: Any,
        user_id: Optional[Any] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        selected_table: Optional[str] = None,
        force_refresh: bool = False,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        tenant_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Runs the full 6-Layer Deterministic Database Pipeline synchronously.
        """
        if tenant_id is None:
            raise ValueError("Tenant ID is required for database insights")

        date_from, date_to, date_bindings = _normalize_date_range(date_from, date_to)

        # 1. Fetch connection and verify ownership
        query = db.query(models.DatabaseConnection).filter(
            models.DatabaseConnection.id == connection_id
        )
        query = query.filter(models.DatabaseConnection.tenant_id == tenant_id)
        
        db_conn = query.first()

        if not db_conn:
            raise ValueError(f"Database connection {connection_id} not found or unauthorized.")

        cache_version = int(getattr(db_conn, "insights_cache_version", 0) or 0)
        if force_refresh:
            cache_version = self.invalidate_connection_cache(db, tenant_id, connection_id)
            db_conn = query.first()

        # 2. Check Cache if not force_refresh
        cache_key = _cache_key(
            tenant_id, connection_id, selected_table, date_from, date_to, cache_version,
        )
        if not force_refresh:
            cached_data = cache_get(cache_key)
            if (
                isinstance(cached_data, dict)
                and cached_data.get("insights_version") == INSIGHTS_CACHE_VERSION
                and cached_data.get("connection_cache_version") == cache_version
            ):
                cached_data["cached"] = True
                cached_data["cache_source"] = "redis_l1"
                return cached_data
            
            # Check DB L2 cache
            if getattr(db_conn, "insights_cache", None) and getattr(db_conn, "insights_cached_at", None):
                cached_at = db_conn.insights_cached_at
                now_utc = datetime.datetime.now(datetime.timezone.utc)
                if hasattr(cached_at, "tzinfo") and cached_at.tzinfo is not None:
                    age = (now_utc - cached_at).total_seconds()
                else:
                    age = (now_utc.replace(tzinfo=None) - cached_at).total_seconds()
                if age < 86400 and not selected_table and not date_from and not date_to:
                    res = db_conn.insights_cache
                    if isinstance(res, str):
                        try:
                            res = json.loads(res)
                        except Exception:
                            pass
                    if (
                        isinstance(res, dict)
                        and res.get("insights_version") == INSIGHTS_CACHE_VERSION
                        and res.get("connection_cache_version") == cache_version
                    ):
                        res["cached"] = True
                        res["cache_source"] = "db_l2"
                        cache_set(cache_key, res, ttl_seconds=86400)
                        return res

        conn_display_name = getattr(db_conn, "name", None) or getattr(db_conn, "db_name", "Database")
        logger.info("Starting database insights pipeline for connection %s", connection_id)

        # Decrypt credentials safely
        raw_pw = getattr(db_conn, "password", None) or getattr(db_conn, "password_encrypted", None)
        decrypted_password = encryption_service.decrypt(raw_pw) if raw_pw else None
        conn_str = getattr(db_conn, "connection_string", None)
        decrypted_conn_str = encryption_service.decrypt(conn_str) if conn_str else None
        if not decrypted_conn_str and getattr(db_conn, "host", None) and ("mongodb://" in str(db_conn.host) or "mongodb+srv://" in str(db_conn.host)):
            decrypted_conn_str = db_conn.host

        db_type = str(db_conn.db_type).lower()
        is_sql = db_type in {"postgresql", "mysql", "mariadb", "sqlite"}
        if not is_sql and db_type != "mongodb":
            raise UnsupportedDialectError("Unsupported SQL dialect for insights")

        # Helper for executing queries
        query_errors: List[str] = []
        metric_query_states: Dict[str, Dict[str, str]] = {}
        sqlite_live_columns: Dict[str, Optional[set[str]]] = {}

        def record_query_state(metric_ids: List[str], rows: List[Dict[str, Any]], failed: bool = False) -> List[Dict[str, Any]]:
            if failed and not metric_ids:
                warning = "A database query failed; some computed details may be incomplete."
                if warning not in query_errors:
                    query_errors.append(warning)
            for metric_id in metric_ids:
                if failed:
                    metric_query_states[metric_id] = {"status": "error", "reason": "query_failed"}
                    warning = f"{metric_id}: A database query failed; this result may be incomplete."
                    if warning not in query_errors:
                        query_errors.append(warning)
                elif not rows:
                    metric_query_states[metric_id] = {"status": "unavailable", "reason": "no_rows"}
                else:
                    metric_query_states[metric_id] = {"status": "available", "reason": ""}
            return rows

        def mark_missing_role(metric_ids: List[str]) -> None:
            for metric_id in metric_ids:
                metric_query_states[metric_id] = {
                    "status": "unavailable", "reason": "missing_role"
                }

        active_date_filter: Optional[Tuple[str, str]] = None

        def execute_sql(
            query_str: str, metric_ids: Optional[List[str]] = None,
            *, apply_date_filter: bool = True, extra_params: Optional[Dict[str, Any]] = None,
        ) -> List[Dict[str, Any]]:
            tracked_metric_ids = metric_ids or []
            if not is_sql:
                return []
            query_params: Dict[str, Any] = dict(extra_params or {})
            if apply_date_filter and date_bindings:
                if not active_date_filter:
                    mark_missing_role(tracked_metric_ids)
                    return []
                scoped = _with_date_predicate(query_str, *active_date_filter, date_bindings)
                if scoped is None:
                    for metric_id in tracked_metric_ids:
                        metric_query_states[metric_id] = {
                            "status": "unavailable", "reason": "unsupported_with_filter",
                        }
                    return []
                query_str = scoped
                query_params.update(date_bindings)
            # Try native DataSpeakAI pooled engine first
            try:
                from services.db_utils import get_connection_url
                from services.db_pool import get_engine
                from sqlalchemy import text
                conn_url = get_connection_url(db_conn)
                if conn_url:
                    engine = get_engine(conn_url)
                    if str(db_conn.db_type).lower() == "sqlite":
                        try:
                            from sqlalchemy import inspect

                            inspector = inspect(engine)
                            referenced_tables = re.findall(
                                r'\b(?:FROM|JOIN)\s+"([^"]+)"', query_str, re.IGNORECASE
                            )
                            for table_name in referenced_tables:
                                if table_name not in sqlite_live_columns:
                                    sqlite_live_columns[table_name] = (
                                        {col["name"].casefold() for col in inspector.get_columns(table_name)}
                                        if inspector.has_table(table_name) else None
                                    )
                            valid_names = {table.casefold() for table in referenced_tables}
                            for table_name in referenced_tables:
                                columns = sqlite_live_columns[table_name]
                                if columns is not None:
                                    valid_names.update(columns)
                            quoted_names = re.findall(r'"([^"]+)"', query_str)
                            missing_identifier = (
                                not referenced_tables
                                or any(sqlite_live_columns[table] is None for table in referenced_tables)
                                or any(name.casefold() not in valid_names for name in quoted_names)
                                or any(
                                    column.casefold() not in (sqlite_live_columns.get(table) or set())
                                    for table, column in re.findall(
                                        r'"([^"]+)"\s*\.\s*"([^"]+)"', query_str
                                    )
                                )
                            )
                        except Exception:
                            logger.exception("SQLite live schema validation failed")
                            return record_query_state(tracked_metric_ids, [], failed=True)
                        if missing_identifier:
                            logger.warning("SQLite insights query references an identifier missing from live schema")
                            mark_missing_role(tracked_metric_ids)
                            return []
                    with engine.connect() as conn:
                        res = conn.execute(text(query_str), query_params)
                        return record_query_state(tracked_metric_ids, [dict(r._mapping) for r in res])
                if str(db_conn.db_type).lower() == "sqlite":
                    return record_query_state(tracked_metric_ids, [], failed=True)
                if query_params:
                    return record_query_state(tracked_metric_ids, [], failed=True)
            except Exception:
                logger.exception("Pooled SQL query execution failed")
                if query_params:
                    return record_query_state(tracked_metric_ids, [], failed=True)

            try:
                res = db_connection_service.execute_query(
                    db_type=str(db_conn.db_type),
                    host=getattr(db_conn, "host", "localhost") or "localhost",
                    port=int(getattr(db_conn, "port", 0) or 0) if getattr(db_conn, "port", None) is not None else None,
                    username=getattr(db_conn, "username", "") or "",
                    password=decrypted_password or "",
                    database=getattr(db_conn, "database", "") or "",
                    connection_string=decrypted_conn_str or "",
                    query=query_str
                )
                if isinstance(res, list):
                    failed_rows = [row for row in res if isinstance(row, dict) and row.get("error")]
                    if failed_rows:
                        logger.error("Database pipeline query returned an error result")
                        return record_query_state(tracked_metric_ids, [], failed=True)
                    return record_query_state(tracked_metric_ids, [row for row in res if isinstance(row, dict) and "error" not in row])
                logger.error("Database pipeline query returned an unexpected result")
                return record_query_state(tracked_metric_ids, [], failed=True)
            except Exception:
                logger.exception("Database pipeline query execution failed")
                return record_query_state(tracked_metric_ids, [], failed=True)

        def apply_result_status(item: Dict[str, Any], is_chart: bool = False) -> None:
            metric_id = str(item.get("id", ""))
            state = metric_query_states.get(metric_id)
            if state and state["status"] == "error":
                item["status"] = "error"
                item["reason"] = "query_failed"
                if is_chart:
                    item["data"] = []
                else:
                    item["value"] = None
                    item["raw_value"] = None
                    item["trend_text"] = None
                    item["trend_pct"] = None
                return
            if state and state["status"] == "unavailable":
                item["status"] = "unavailable"
                item["reason"] = state["reason"]
                if is_chart:
                    item["data"] = []
                else:
                    item["value"] = None
                    item["raw_value"] = None
                    item["trend_text"] = None
                    item["trend_pct"] = None
                return

            if is_chart:
                values = [point.get("value", point.get("val")) for point in item.get("data", []) if isinstance(point, dict)]
                if not values:
                    item["status"], item["reason"] = "unavailable", "no_rows"
                elif all(value is not None and not isinstance(value, bool) and value == 0 for value in values):
                    item["status"], item["reason"] = "zero", None
                else:
                    item["status"], item["reason"] = "available", None
                return

            raw_value = item.get("raw_value")
            if item.get("value") == "N/A":
                item["status"], item["reason"] = "unavailable", "missing_role"
                item["value"] = None
            elif raw_value is None:
                item["status"], item["reason"] = "unavailable", "no_rows"
                item["value"] = None
            elif not isinstance(raw_value, bool) and raw_value == 0:
                item["status"], item["reason"] = "zero", None
            else:
                item["status"], item["reason"] = "available", None

        # -- LAYER 1: Multi-Table Schema Discovery & Profiling --
        if progress_callback:
            progress_callback(1, "Layer 1: Schema Discovery & Statistical Profiling...")
        logger.info("Database pipeline layer 1: schema discovery and profiling")
        
        schema = getattr(db_conn, "tables_metadata", None) or {}
        if not schema or "error" in schema or force_refresh:
            schema = {}
            # 1. Try SQLAlchemy native inspector
            try:
                from services.db_utils import get_connection_url
                from services.db_pool import get_engine
                from sqlalchemy import inspect
                conn_url = get_connection_url(db_conn)
                if conn_url and db_conn.db_type.lower() != "mongodb":
                    engine = get_engine(conn_url)
                    insp = inspect(engine)
                    table_names = insp.get_table_names()
                    schema = {}
                    for t in table_names:
                        cols = {}
                        for c in insp.get_columns(t):
                            cols[c["name"]] = str(c.get("type", "TEXT"))
                        schema[t] = {"columns": cols, "row_count": 0}
                    if hasattr(db_conn, "tables_metadata"):
                        db_conn.tables_metadata = schema
                        db.commit()
            except Exception as e:
                logger.exception("Database schema inspection failed")

            if not schema:
                try:
                    if db_conn.db_type.lower() == "postgresql":
                        schema = db_connection_service.get_postgresql_schema(
                            host=db_conn.host, port=int(getattr(db_conn, "port", 5432) or 5432), username=db_conn.username,
                            password=decrypted_password or "", database=db_conn.database
                        )
                    elif db_conn.db_type.lower() in {"mysql", "mariadb"}:
                        schema = db_connection_service.get_mysql_schema(
                            host=db_conn.host or "localhost", port=int(getattr(db_conn, "port", 3306) or 3306), username=db_conn.username or "",
                            password=decrypted_password or "", database=db_conn.database or ""
                        )
                    elif db_conn.db_type.lower() == "sqlite":
                        schema = db_connection_service.get_sqlite_schema(getattr(db_conn, "database", None) or db_conn.host or "")
                    elif db_conn.db_type.lower() == "mongodb":
                        schema = db_connection_service.get_mongodb_schema(decrypted_conn_str or "")
                    
                    if hasattr(db_conn, "tables_metadata"):
                        db_conn.tables_metadata = schema
                        db.commit()
                except Exception as e:
                    logger.exception("Database schema discovery failed")
                    schema = schema or {}

        available_tables = [
            t for t in list(schema.keys())
            if not t.startswith("sqlite_") and not t.startswith("system.") and t.lower() != "error"
        ]
        if db_conn.db_type.lower() == "mongodb" and available_tables:
            available_tables.sort(key=lambda t: schema.get(t, {}).get("row_count", 0), reverse=True)

        if not available_tables:
            return {
                "success": False,
                "message": "No accessible tables found in this database connection."
            }

        def normalize_name(s: str) -> str:
            return re.sub(r'[\s_\-]+', '', s.lower())

        table_norm_map = {normalize_name(t): t for t in available_tables}

        def match_table(candidates: List[str]) -> Optional[str]:
            for c in candidates:
                n = normalize_name(c)
                if n in table_norm_map:
                    return table_norm_map[n]
            return None

        # -- DOMAIN & RELATIONAL TOPOLOGY DISCOVERY --
        # Detect primary Fact table (invoices, orders, sales, transactions, payments, rentals)
        fact_table = match_table(["invoice", "invoices", "orders", "order", "sales", "sale", "transactions", "transaction", "payment", "payments", "rental", "rentals"])

        # Detect line items table
        line_item_table = match_table(["invoiceline", "invoicelines", "invoice_lines", "invoice_line", "orderdetails", "order_details", "order_items", "line_items", "orderitems", "order_detail", "rental", "rentals"])

        # Detect customer table
        customer_table = match_table(["customer", "customers", "client", "clients", "users", "user", "member", "members"])

        # Detect catalog/product table
        catalog_table = match_table(["track", "tracks", "product", "products", "item", "items", "books", "course", "courses", "film", "films", "movie", "movies"])

        # Detect category/genre table
        category_table = match_table(["genre", "genres", "category", "categories"])

        # Detect artist/brand/vendor table
        artist_table = match_table(["actor", "actors", "artist", "artists", "supplier", "suppliers", "vendor", "vendors", "brand", "brands"])

        # Profile each table's columns safely
        table_profiles: Dict[str, Any] = {}
        for tbl in available_tables:
            tbl_info = schema.get(tbl, {})
            cols = tbl_info.get("columns", {}) if isinstance(tbl_info, dict) else {}
            
            monetary_cols = []
            date_cols = []
            dim_cols = []
            measure_cols = []

            for c_name, c_type in cols.items():
                t_str = c_type.lower() if isinstance(c_type, str) else str(c_type.get("type", "")).lower()
                c_lower = c_name.lower()
                
                if is_id_column(c_name):
                    continue
                
                if is_monetary_column(c_name):
                    monetary_cols.append(c_name)
                    measure_cols.append(c_name)
                elif is_date_column(c_name, t_str):
                    date_cols.append(c_name)
                elif any(k in t_str for k in ["int", "float", "numeric", "decimal", "real", "double"]):
                    if not any(k in c_lower for k in ["year", "code", "zip", "number", "seq", "version", "coord", "coordinate", "lat", "lon", "lng"]):
                        measure_cols.append(c_name)
                elif is_dimension_column(c_name, t_str):
                    if not any(k in t_str for k in ["list", "array", "dict"]) and not any(k in c_lower for k in ["coord", "coordinate", "geometry", "polygon"]):
                        dim_cols.append(c_name)

            monetary_cols = sort_monetary_columns_by_priority(monetary_cols)
            table_profiles[tbl] = {
                "columns": cols,
                "monetary_cols": monetary_cols,
                "date_cols": date_cols,
                "dim_cols": dim_cols,
                "measure_cols": measure_cols,
            }

        # -- LAYER 2 & 4: DETERMINISTIC RECIPES & AGGREGATIONS --
        if progress_callback:
            progress_callback(2, "Layer 2: Deterministic Metric Recipes Formulation (Phase 2C)...")
        logger.info("Database pipeline layers 2 and 4: metrics and aggregations")

        computed_kpis: List[Dict[str, Any]] = []
        computed_charts: List[Dict[str, Any]] = []
        all_filters: List[Dict[str, Any]] = []

        is_federated_mode = not selected_table or selected_table == "" or selected_table == "All Tables"
        is_mongodb = str(db_conn.db_type).lower() == "mongodb"
        analysis_mode = "mongodb" if is_mongodb else (
            "federated" if is_federated_mode and fact_table else "single"
        )

        def round_aggregate(function: str, expression: str) -> str:
            return round_money(f"{function}({expression})", db_conn.db_type)

        if analysis_mode == "federated":
            # -------------------------------------------------------------
            # MULTI-TABLE RELATIONAL FEDERATION MODE (ENTERPRISE BI)
            # -------------------------------------------------------------
            q_fact = _clean_sql_identifier(fact_table, db_conn.db_type)
            fact_prof = table_profiles.get(fact_table, {})
            fact_date_col = _pick_date_column(fact_prof.get("date_cols") or [])
            if fact_date_col:
                active_date_filter = (q_fact, _clean_sql_identifier(fact_date_col, db_conn.db_type))
            elif date_from or date_to:
                query_errors.append("Date filters were requested, but the fact table has no unambiguous date column.")
            
            # 1. Total Genuine Gross/Net Revenue (Prioritized over unit rates)
            # Check line items table for transactional sales details (e.g. Order Details, InvoiceLine)
            line_money_expr = None
            line_has_revenue = False
            join_col = None
            if line_item_table:
                q_line = _clean_sql_identifier(line_item_table, db_conn.db_type)
                line_prof = table_profiles.get(line_item_table, {})
                line_cols = line_prof.get("columns", {})
                
                # Check for unit price, quantity, and discount in line items
                l_price_col = next((c for c in line_cols.keys() if any(k in c.lower() for k in ["unitprice", "unit_price", "price", "rate", "cost", "amount"])), None)
                l_qty_col = next((c for c in line_cols.keys() if any(k in c.lower() for k in ["quantity", "qty", "units"])), None)
                l_disc_col = next((c for c in line_cols.keys() if any(k in c.lower() for k in ["discount", "disc"])), None)
                
                # Detect join column between fact and line item
                fact_col_names = list(fact_prof.get("columns", {}).keys())
                for fc in fact_col_names:
                    for lc in line_cols.keys():
                        if fc.lower() == lc.lower() and is_id_column(fc):
                            join_col = (fc, lc)
                            break
                    if join_col:
                        break

                if l_price_col and l_qty_col:
                    q_lp = _clean_sql_identifier(l_price_col, db_conn.db_type)
                    q_lq = _clean_sql_identifier(l_qty_col, db_conn.db_type)
                    if l_disc_col:
                        q_ld = _clean_sql_identifier(l_disc_col, db_conn.db_type)
                        line_money_expr = f"({q_lp} * {q_lq} * (1.0 - COALESCE({q_ld}, 0.0)))"
                    else:
                        line_money_expr = f"({q_lp} * {q_lq})"
                    line_has_revenue = True

            money_cols = sort_monetary_columns_by_priority(fact_prof.get("monetary_cols", []))
            has_genuine_fact_revenue = bool(money_cols and not all("freight" in c.lower() or "shipping" in c.lower() for c in money_cols))
            fact_measures = fact_prof.get("measure_cols", [])
            qty_col = next(
                (c for c in fact_measures if any(k in c.lower() for k in ["qty", "quantity", "units"])),
                None,
            )
            q_line: str = _clean_sql_identifier(line_item_table, db_conn.db_type) if line_item_table else ""

            if has_genuine_fact_revenue:
                money_col = money_cols[0]
                q_money = _clean_sql_identifier(money_col, db_conn.db_type)
                if is_unit_price_column(money_col) and qty_col:
                    q_qty = _clean_sql_identifier(qty_col, db_conn.db_type)
                    money_expr = f"({q_money} * {q_qty})"
                    avg_expr = round_aggregate("AVG", f"{q_money} * {q_qty}")
                else:
                    money_expr = q_money
                    avg_expr = round_aggregate("AVG", q_money)

                fact_summary = execute_sql(f"""
                    SELECT 
                        {round_aggregate('SUM', money_expr)} as total_rev,
                        COUNT(*) as total_orders,
                        {avg_expr} as avg_order_val
                    FROM {q_fact}
                """, ["total_revenue", "total_orders", "average_order_value"])
                revenue_raw_value = fact_summary[0].get("total_rev") if fact_summary else None
                rev_val = float(revenue_raw_value or 0) if fact_summary else 0.0
                ord_val = int(fact_summary[0].get("total_orders") or 0) if fact_summary else 0
                aov_raw_value = fact_summary[0].get("avg_order_val") if fact_summary else None
                aov_val = float(aov_raw_value or 0) if fact_summary else 0.0
            else:
                fact_cnt_res = execute_sql(f"SELECT COUNT(*) as total_orders FROM {q_fact}", ["total_orders"])
                ord_val = int(fact_cnt_res[0].get("total_orders") or 0) if fact_cnt_res else 0
                rev_val = 0.0
                revenue_raw_value = None
                aov_val = 0.0
                aov_raw_value = None
                money_expr = None

                if line_has_revenue and line_money_expr and line_item_table:
                    q_line = _clean_sql_identifier(line_item_table, db_conn.db_type)
                    if join_col:
                        q_jf = _clean_sql_identifier(join_col[0], db_conn.db_type)
                        q_jl = _clean_sql_identifier(join_col[1], db_conn.db_type)
                        line_rev_query = f"""
                            SELECT {round_aggregate('SUM', line_money_expr)} as total_rev
                            FROM {q_fact}
                            JOIN {q_line} ON {q_fact}.{q_jf} = {q_line}.{q_jl}
                        """
                    else:
                        line_rev_query = f"SELECT {round_aggregate('SUM', line_money_expr)} as total_rev FROM {q_line}"
                    line_rev_res = execute_sql(line_rev_query, ["total_revenue", "average_order_value"])
                    if line_rev_res and line_rev_res[0].get("total_rev") is not None:
                        revenue_raw_value = line_rev_res[0].get("total_rev")
                        rev_val = float(revenue_raw_value)
                        aov_val = round(rev_val / ord_val, 2) if ord_val > 0 else 0.0
                        aov_raw_value = aov_val
                        money_expr = line_money_expr

            # Status & Lifecycle introspection (Truthful accounting)
            status_col = next((c for c in fact_prof.get("dim_cols", []) + list(fact_prof.get("columns", {}).keys()) 
                               if any(k in c.lower() for k in ["status", "order_status", "delivery_status", "state"]) 
                               and not is_id_column(c)), None)
            delivered_count = 0
            delivered_rev = 0.0
            cancelled_count = 0
            returned_count = 0
            status_distribution: List[Dict[str, Any]] = []
            if status_col and money_expr:
                q_status = _clean_sql_identifier(status_col, db_conn.db_type)
                status_res = execute_sql(f"""
                    SELECT {q_status} as st, COUNT(*) as cnt, {round_aggregate('SUM', money_expr)} as rev
                    FROM {q_fact}
                    WHERE {q_status} IS NOT NULL
                    GROUP BY {q_status}
                    ORDER BY cnt DESC
                """, ["net_revenue_delivered", "order_status_distribution"])
                for sr in status_res:
                    s_name = str(sr.get("st") or "").strip()
                    s_lower = s_name.lower()
                    cnt = int(sr.get("cnt") or 0)
                    r_val = float(sr.get("rev") or 0)
                    status_distribution.append({"name": s_name.title(), "value": cnt, "revenue": r_val})
                    status_class = classify_status(s_name)
                    if status_class == "delivered":
                        delivered_count += cnt
                        delivered_rev += r_val
                    elif status_class == "cancelled":
                        cancelled_count += cnt
                    elif status_class == "returned":
                        returned_count += cnt

            if status_col and (cancelled_count > 0 or returned_count > 0 or delivered_count > 0):
                if delivered_count > 0 and delivered_count < ord_val:
                    ord_trend_text = f"{delivered_count:,} delivered ({ord_val - delivered_count:,} other)"
                else:
                    ord_trend_text = f"{ord_val:,} total records"
            else:
                ord_trend_text = f"{ord_val:,} total transactions"

            # Active Customers
            cust_count = 0
            customer_identifier_available = bool(customer_table)
            if customer_table:
                q_cust = _clean_sql_identifier(customer_table, db_conn.db_type)
                cust_res = execute_sql(f"SELECT COUNT(*) as cnt FROM {q_cust}", ["active_customers", "customer_lifetime_value"])
                cust_count = int(cust_res[0].get("cnt") or 0) if cust_res else 0
            else:
                cust_id_col = next((c for c in fact_prof.get("columns", {}).keys() if any(k in c.lower() for k in ["customer", "client", "user_id", "buyer"])), None)
                if cust_id_col:
                    customer_identifier_available = True
                    q_cid = _clean_sql_identifier(cust_id_col, db_conn.db_type)
                    cust_res = execute_sql(f"SELECT COUNT(DISTINCT {q_cid}) as cnt FROM {q_fact}", ["active_customers", "customer_lifetime_value"])
                    cust_count = int(cust_res[0].get("cnt") or 0) if cust_res else 0

            clv_val = round(rev_val / cust_count, 2) if cust_count > 0 else 0.0

            # Units Sold
            units_sold = 0
            units_raw_value: Optional[int] = None
            units_measure_found = False
            if line_item_table and line_item_table != fact_table:
                q_line = _clean_sql_identifier(line_item_table, db_conn.db_type)
                line_prof = table_profiles.get(line_item_table, {})
                line_cols = line_prof.get("columns", {})
                line_qty_col = next((c for c in line_cols.keys() if any(k in c.lower() for k in ["quantity", "qty", "units"])), None)
                if line_qty_col:
                    units_measure_found = True
                    q_lqty = _clean_sql_identifier(line_qty_col, db_conn.db_type)
                    qty_res = execute_sql(f"SELECT SUM({q_lqty}) as cnt FROM {q_line}", ["units_sold"])
                    units_raw_value = qty_res[0].get("cnt") if qty_res else None
                    units_sold = int(units_raw_value or 0)
                else:
                    qty_res = execute_sql(f"SELECT COUNT(*) as cnt FROM {q_line}", ["units_sold"])
                    units_sold = int(qty_res[0].get("cnt") or 0) if qty_res else 0
            elif qty_col:
                units_measure_found = True
                q_qty = _clean_sql_identifier(qty_col, db_conn.db_type)
                qty_res = execute_sql(f"SELECT SUM({q_qty}) as cnt FROM {q_fact}", ["units_sold"])
                units_raw_value = qty_res[0].get("cnt") if qty_res else None
                units_sold = int(units_raw_value or 0)

            # Catalog Size (Honest reporting: zero Chinook 3,503 fallbacks)
            catalog_count = 0
            catalog_identifier_available = bool(catalog_table)
            if catalog_table:
                q_cat = _clean_sql_identifier(catalog_table, db_conn.db_type)
                cat_res = execute_sql(f"SELECT COUNT(*) as cnt FROM {q_cat}", ["catalog_size"])
                catalog_count = int(cat_res[0].get("cnt") or 0) if cat_res else 0
            else:
                item_id_col = next((c for c in fact_prof.get("columns", {}).keys() if any(k in c.lower() for k in ["product", "item", "track", "sku", "article"])), None)
                if item_id_col:
                    catalog_identifier_available = True
                    q_item = _clean_sql_identifier(item_id_col, db_conn.db_type)
                    cat_res = execute_sql(f"SELECT COUNT(DISTINCT {q_item}) as cnt FROM {q_fact}", ["catalog_size"])
                    catalog_count = int(cat_res[0].get("cnt") or 0) if cat_res else 0

            # Top Revenue Market
            country_col = next((c for c in fact_prof.get("dim_cols", []) if any(k in c.lower() for k in ["country", "state", "region", "city", "market"])), None)
            if not country_col and fact_prof.get("dim_cols"):
                country_col = fact_prof["dim_cols"][0]
            
            top_market_name = "Global"
            top_market_val = 0.0
            country_data: List[Dict[str, Any]] = []
            geo_dim_label = "Market"

            if country_col:
                geo_dim_label = country_col.replace('_', ' ').title()
                q_country = _clean_sql_identifier(country_col, db_conn.db_type)
                if join_col and line_money_expr and not has_genuine_fact_revenue and q_line:
                    q_jf = _clean_sql_identifier(join_col[0], db_conn.db_type)
                    q_jl = _clean_sql_identifier(join_col[1], db_conn.db_type)
                    country_query = f"""
                        SELECT {q_fact}.{q_country} as name, {round_aggregate('SUM', line_money_expr)} as val
                        FROM {q_fact} 
                        JOIN {q_line} ON {q_fact}.{q_jf} = {q_line}.{q_jl}
                        WHERE {q_fact}.{q_country} IS NOT NULL 
                        GROUP BY name 
                        ORDER BY val DESC 
                        LIMIT 10
                    """
                elif money_expr:
                    country_query = f"""
                        SELECT {q_country} as name, {round_aggregate('SUM', money_expr)} as val
                        FROM {q_fact} 
                        WHERE {q_country} IS NOT NULL 
                        GROUP BY {q_country} 
                        ORDER BY val DESC 
                        LIMIT 10
                    """
                else:
                    country_query = f"""
                        SELECT {q_country} as name, COUNT(*) as val 
                        FROM {q_fact} 
                        WHERE {q_country} IS NOT NULL 
                        GROUP BY {q_country} 
                        ORDER BY val DESC 
                        LIMIT 10
                    """
                country_res = execute_sql(country_query, ["top_market", "revenue_by_market"])
                if country_res:
                    top_market_name = country_res[0].get("name") or "Global"
                    top_market_val = float(country_res[0].get("val") or 0)
                    country_data = country_res
            else:
                # Relational geographic discovery (e.g., customer -> address -> city -> country)
                rel_geo_query = None
                has_geo_chain = "country" in table_norm_map and "city" in table_norm_map and "address" in table_norm_map and customer_table
                if has_geo_chain and money_expr:
                    q_co = _clean_sql_identifier(table_norm_map["country"], db_conn.db_type)
                    q_ci = _clean_sql_identifier(table_norm_map["city"], db_conn.db_type)
                    q_ad = _clean_sql_identifier(table_norm_map["address"], db_conn.db_type)
                    q_cu = _clean_sql_identifier(customer_table, db_conn.db_type)
                    rel_geo_query = f"""
                        SELECT {q_co}.country as name, {round_aggregate('SUM', money_expr)} as val
                        FROM {q_fact}
                        JOIN {q_cu} ON {q_fact}.customer_id = {q_cu}.customer_id
                        JOIN {q_ad} ON {q_cu}.address_id = {q_ad}.address_id
                        JOIN {q_ci} ON {q_ad}.city_id = {q_ci}.city_id
                        JOIN {q_co} ON {q_ci}.country_id = {q_co}.country_id
                        GROUP BY name
                        ORDER BY val DESC
                        LIMIT 10
                    """
                    geo_dim_label = "Country"
                elif customer_table and money_expr:
                    cust_prof = table_profiles.get(customer_table, {})
                    c_geo_col = next((c for c in cust_prof.get("dim_cols", []) if any(k in c.lower() for k in ["country", "state", "city", "region"])), None)
                    if c_geo_col:
                        q_cu = _clean_sql_identifier(customer_table, db_conn.db_type)
                        q_cg = _clean_sql_identifier(c_geo_col, db_conn.db_type)
                        rel_geo_query = f"""
                            SELECT {q_cu}.{q_cg} as name, {round_aggregate('SUM', money_expr)} as val
                            FROM {q_fact}
                            JOIN {q_cu} ON {q_fact}.customer_id = {q_cu}.customer_id
                            WHERE {q_cu}.{q_cg} IS NOT NULL
                            GROUP BY name
                            ORDER BY val DESC
                            LIMIT 10
                        """
                        geo_dim_label = c_geo_col.replace('_', ' ').title()

                if rel_geo_query:
                    country_res = execute_sql(rel_geo_query, ["revenue_by_market"])
                    if country_res:
                        top_market_name = country_res[0].get("name") or "Global"
                        top_market_val = float(country_res[0].get("val") or 0)
                        country_data = country_res

            # Calculate authentic period trend (SPLY: Same-Period-Last-Year, avoiding partial vs full distortion)
            trend_pct = None
            trend_dir = "neutral"
            trend_text = None
            date_col = fact_date_col
            q_date = _clean_sql_identifier(date_col, db_conn.db_type) if date_col else ""
            trend_reason = None
            if date_col and has_genuine_fact_revenue and money_expr:
                try:
                    if date_bindings:
                        if not (date_from and date_to):
                            trend_reason = "unsupported_with_filter"
                        else:
                            current_start = datetime.date.fromisoformat(date_from)
                            current_end = datetime.date.fromisoformat(date_bindings["date_to_excl"])
                    else:
                        d_bounds = execute_sql(
                            f"SELECT MIN({q_date}) as min_d, MAX({q_date}) as max_d "
                            f"FROM {q_fact} WHERE {q_date} IS NOT NULL",
                        )
                        if d_bounds and d_bounds[0].get("max_d") and d_bounds[0].get("min_d"):
                            latest = datetime.date.fromisoformat(str(d_bounds[0]["max_d"])[:10])
                            earliest = datetime.date.fromisoformat(str(d_bounds[0]["min_d"])[:10])
                            if latest.year > earliest.year:
                                current_start = datetime.date(latest.year, 1, 1)
                                current_end = latest + datetime.timedelta(days=1)
                            else:
                                trend_reason = "no_rows"
                        else:
                            trend_reason = "no_rows"
                    if trend_reason is None:
                        def previous_year(day: datetime.date) -> datetime.date:
                            try:
                                return day.replace(year=day.year - 1)
                            except ValueError:
                                return day.replace(year=day.year - 1, day=28)

                        previous_start = previous_year(current_start)
                        previous_end = previous_year(current_end)
                        current_case = (
                            f"CASE WHEN {q_date} >= :current_start AND {q_date} < :current_end "
                            f"THEN {money_expr} END"
                        )
                        previous_case = (
                            f"CASE WHEN {q_date} >= :previous_start AND {q_date} < :previous_end "
                            f"THEN {money_expr} END"
                        )
                        sply_query = f"""
                            SELECT
                                {round_aggregate('SUM', current_case)} as curr_val,
                                {round_aggregate('SUM', previous_case)} as prev_val
                            FROM {q_fact}
                        """
                        sply_res = execute_sql(
                            sply_query, apply_date_filter=False,
                            extra_params={
                                "current_start": current_start.isoformat(),
                                "current_end": current_end.isoformat(),
                                "previous_start": previous_start.isoformat(),
                                "previous_end": previous_end.isoformat(),
                            },
                        )
                        current_value = sply_res[0].get("curr_val") if sply_res else None
                        previous_value = sply_res[0].get("prev_val") if sply_res else None
                        if current_value is not None and previous_value is not None and float(previous_value) > 0:
                            raw_growth = round(((float(current_value) - float(previous_value)) / float(previous_value)) * 100, 1)
                            trend_pct = abs(raw_growth)
                            trend_dir = "up" if raw_growth >= 0 else "down"
                            trend_text = f"SPLY ({raw_growth:+.1f}%)"
                        else:
                            trend_reason = "no_rows"
                except Exception:
                    logger.exception("Same-period-last-year calculation failed")
                    trend_reason = "query_failed"
            elif date_bindings:
                trend_reason = "unsupported_with_filter"

            # Formulate Phase 2C Deterministic Recipes (Clean Executive KPIs, Zero Fabricated Constants)
            computed_kpis = [
                {
                    "id": "total_revenue",
                    "label": "Gross Revenue (all statuses)",
                    "value": f"${rev_val:,.2f}" if revenue_raw_value is not None else None,
                    "raw_value": revenue_raw_value,
                    "table": fact_table,
                    "format": "currency",
                    "format_type": "currency",
                    "recipe_type": "atomic",
                    "trend_direction": trend_dir,
                    "trend_pct": trend_pct,
                    "trend_text": trend_text,
                    "trend_reason": trend_reason,
                },
                {
                    "id": "net_revenue_delivered",
                    "label": "Net Revenue (delivered only)",
                    "value": f"${delivered_rev:,.2f}" if status_col and money_expr else "N/A",
                    "raw_value": delivered_rev if status_col and money_expr else None,
                    "table": fact_table,
                    "format": "currency",
                    "format_type": "currency",
                    "recipe_type": "atomic",
                    "trend_direction": "neutral",
                    "trend_pct": None,
                    "trend_text": "delivered transactions only"
                },
                {
                    "id": "total_orders",
                    "label": "Total Order Volume",
                    "value": f"{ord_val:,}",
                    "raw_value": ord_val,
                    "table": fact_table,
                    "format": "integer",
                    "format_type": "integer",
                    "recipe_type": "atomic",
                    "trend_direction": "neutral",
                    "trend_pct": None,
                    "trend_text": ord_trend_text
                },
                {
                    "id": "average_order_value",
                    "label": "Average Order Value (AOV)",
                    "value": f"${aov_val:,.2f}" if aov_raw_value is not None else None,
                    "raw_value": aov_raw_value,
                    "table": fact_table,
                    "format": "currency",
                    "format_type": "currency",
                    "recipe_type": "ratio",
                    "trend_direction": "neutral",
                    "trend_pct": None,
                    "trend_text": "revenue / order"
                },
                {
                    "id": "active_customers",
                    "label": "Active Customers",
                    "value": f"{cust_count:,}",
                    "raw_value": cust_count,
                    "table": customer_table or fact_table,
                    "format": "integer",
                    "format_type": "integer",
                    "recipe_type": "atomic",
                    "trend_direction": "neutral",
                    "trend_pct": None,
                    "trend_text": "unique buyer accounts" if cust_count > 0 else None
                },
                {
                    "id": "customer_lifetime_value",
                    "label": "Customer Lifetime Value (CLV)",
                    "value": f"${clv_val:,.2f}" if cust_count > 0 and revenue_raw_value is not None else None,
                    "raw_value": clv_val if cust_count > 0 and revenue_raw_value is not None else None,
                    "table": customer_table or fact_table,
                    "format": "currency",
                    "format_type": "currency",
                    "recipe_type": "ratio",
                    "trend_direction": "neutral",
                    "trend_pct": None,
                    "trend_text": "spend per account" if clv_val > 0 else None
                },
                {
                    "id": "units_sold",
                    "label": "Total Units Sold",
                    "value": f"{units_sold:,}" if units_raw_value is not None else None,
                    "raw_value": units_raw_value,
                    "table": line_item_table or fact_table,
                    "format": "integer",
                    "format_type": "integer",
                    "recipe_type": "atomic",
                    "trend_direction": "neutral",
                    "trend_pct": None,
                    "trend_text": "items sold" if units_sold > 0 else None
                },
                {
                    "id": "catalog_size",
                    "label": "Active Catalog Size",
                    "value": f"{catalog_count:,}",
                    "raw_value": catalog_count,
                    "table": catalog_table or fact_table,
                    "format": "integer",
                    "format_type": "integer",
                    "recipe_type": "atomic",
                    "trend_direction": "neutral",
                    "trend_pct": None,
                    "trend_text": "catalog entities" if catalog_count > 0 else None
                },
                {
                    "id": "top_market",
                    "label": "Top Market",
                    "value": f"{top_market_name} (${top_market_val:,.2f})" if top_market_val > 0 else str(top_market_name),
                    "raw_value": top_market_val,
                    "table": fact_table,
                    "format": "text",
                    "format_type": "text",
                    "recipe_type": "atomic",
                    "trend_direction": "neutral",
                    "trend_pct": round((top_market_val / max(rev_val, 1)) * 100, 1) if rev_val > 0 and top_market_val > 0 else None,
                    "trend_text": "of total sales" if rev_val > 0 and top_market_val > 0 else None
                }
            ]

            if not money_expr:
                for metric_id in ("total_revenue", "average_order_value", "net_revenue_delivered", "customer_lifetime_value"):
                    metric_query_states[metric_id] = {"status": "unavailable", "reason": "missing_role"}
            if not status_col:
                metric_query_states["net_revenue_delivered"] = {"status": "unavailable", "reason": "missing_role"}
            if not customer_identifier_available:
                for metric_id in ("active_customers", "customer_lifetime_value"):
                    metric_query_states[metric_id] = {"status": "unavailable", "reason": "missing_role"}
            if not units_measure_found:
                metric_query_states["units_sold"] = {"status": "unavailable", "reason": "missing_role"}
            if not catalog_identifier_available:
                metric_query_states["catalog_size"] = {"status": "unavailable", "reason": "missing_role"}
            if date_bindings and metric_query_states.get("revenue_by_market", {}).get("status") == "unavailable":
                metric_query_states["top_market"] = metric_query_states["revenue_by_market"]

            # Chart 1: Time Series Revenue Velocity
            if date_col:
                if join_col and line_money_expr and not has_genuine_fact_revenue:
                    q_jf = _clean_sql_identifier(join_col[0], db_conn.db_type)
                    q_jl = _clean_sql_identifier(join_col[1], db_conn.db_type)
                    month_expr = month_bucket(f"{q_fact}.{q_date}", db_conn.db_type)
                    monthly_query = f"""
                        SELECT {month_expr} as period, {round_aggregate('SUM', line_money_expr)} as value
                        FROM {q_fact} 
                        JOIN {q_line} ON {q_fact}.{q_jf} = {q_line}.{q_jl}
                        WHERE {q_fact}.{q_date} IS NOT NULL 
                        GROUP BY period 
                        ORDER BY period ASC
                    """
                elif money_expr:
                    month_expr = month_bucket(q_date, db_conn.db_type)
                    monthly_query = f"""
                        SELECT {month_expr} as period, {round_aggregate('SUM', money_expr)} as value
                        FROM {q_fact} 
                        WHERE {q_date} IS NOT NULL 
                        GROUP BY period 
                        ORDER BY period ASC
                    """
                else:
                    month_expr = month_bucket(q_date, db_conn.db_type)
                    monthly_query = f"""
                        SELECT {month_expr} as period, COUNT(*) as value 
                        FROM {q_fact} 
                        WHERE {q_date} IS NOT NULL 
                        GROUP BY period 
                        ORDER BY period ASC
                    """
                monthly_data = execute_sql(monthly_query, ["monthly_revenue_velocity"])
                if monthly_data:
                    computed_charts.append({
                        "id": "monthly_revenue_velocity",
                        "title": "Monthly Revenue Velocity",
                        "subtitle": "Deterministic monthly sales trajectory over time",
                        "type": "area",
                        "table": fact_table,
                        "x_column": "Month",
                        "y_column": "Revenue ($)",
                        "xKey": "period",
                        "yKey": "value",
                        "data": monthly_data,
                        "color": "#6c47ff"
                    })

            # Chart 2: Top Categorical Dimension by Metric (e.g., Geographic / Country)
            if country_data:
                computed_charts.append({
                    "id": "revenue_by_market",
                    "title": f"Revenue by {geo_dim_label}",
                    "subtitle": "Top revenue-generating segments across buyer base",
                    "type": "bar",
                    "table": fact_table,
                    "x_column": geo_dim_label,
                    "y_column": "Total Revenue ($)",
                    "xKey": "name",
                    "yKey": "val",
                    "data": country_data[:8],
                    "color": "#00c2cb"
                })

            # Chart 3: Segment / Payment / Channel Breakdown (Donut)
            segment_dim = next((c for c in fact_prof.get("dim_cols", []) 
                                if c != country_col and any(k in c.lower() for k in ["payment", "channel", "category", "type", "method", "plan", "segment"])), None)
            if not segment_dim:
                # Fallback to any remaining dimension column
                segment_dim = next((c for c in fact_prof.get("dim_cols", []) if c != country_col and c != status_col), None)
            
            if segment_dim and money_expr:
                q_seg = _clean_sql_identifier(segment_dim, db_conn.db_type)
                seg_res = execute_sql(f"""
                    SELECT {q_seg} as name, {round_aggregate('SUM', money_expr)} as value
                    FROM {q_fact}
                    WHERE {q_seg} IS NOT NULL
                    GROUP BY {q_seg}
                    ORDER BY value DESC
                    LIMIT 6
                """, ["revenue_by_segment"])
                if seg_res:
                    computed_charts.append({
                        "id": "revenue_by_segment",
                        "title": f"Revenue Share by {segment_dim.replace('_', ' ').title()}",
                        "subtitle": f"Distribution across {segment_dim.replace('_', ' ').lower()} categories",
                        "type": "donut",
                        "table": fact_table,
                        "x_column": segment_dim.replace('_', ' ').title(),
                        "y_column": "Sales ($)",
                        "xKey": "name",
                        "yKey": "value",
                        "data": seg_res,
                        "color": "#8b5cf6"
                    })
            elif fact_table == "payment":
                t_rent = match_table(["rental", "rentals"])
                t_inv = match_table(["inventory"])
                t_fc = match_table(["film_category", "filmcategory"])
                t_cat = match_table(["category", "categories"])
                if t_rent and t_inv and t_fc and t_cat:
                    # Relational category revenue breakdown for media rentals
                    q_rent = _clean_sql_identifier(t_rent, db_conn.db_type)
                    q_inv = _clean_sql_identifier(t_inv, db_conn.db_type)
                    q_fc = _clean_sql_identifier(t_fc, db_conn.db_type)
                    q_cat = _clean_sql_identifier(t_cat, db_conn.db_type)
                    cat_rev_query = f"""
                        SELECT {q_cat}.name as name, {round_aggregate('SUM', money_expr)} as value
                        FROM {q_fact}
                        JOIN {q_rent} ON {q_fact}.rental_id = {q_rent}.rental_id
                        JOIN {q_inv} ON {q_rent}.inventory_id = {q_inv}.inventory_id
                        JOIN {q_fc} ON {q_inv}.film_id = {q_fc}.film_id
                        JOIN {q_cat} ON {q_fc}.category_id = {q_cat}.category_id
                        GROUP BY {q_cat}.name
                        ORDER BY value DESC
                        LIMIT 6
                    """
                    cat_rev_res = execute_sql(cat_rev_query, ["revenue_by_segment"])
                    if cat_rev_res:
                        computed_charts.append({
                            "id": "revenue_by_segment",
                            "title": "Revenue Share by Film Category",
                            "subtitle": "Distribution of rental sales across genres",
                            "type": "donut",
                            "table": t_cat,
                            "x_column": "Category",
                            "y_column": "Sales ($)",
                            "xKey": "name",
                            "yKey": "value",
                            "data": cat_rev_res,
                            "color": "#8b5cf6"
                        })

            # Chart 4: Order Lifecycle & Status Distribution
            if status_distribution:
                computed_charts.append({
                    "id": "order_status_distribution",
                    "title": "Order Lifecycle & Status Distribution",
                    "subtitle": "Breakdown across completed, delivered, and cancelled records",
                    "type": "donut",
                    "table": fact_table,
                    "x_column": "Status",
                    "y_column": "Volume",
                    "xKey": "name",
                    "yKey": "value",
                    "data": status_distribution,
                    "color": "#10b981"
                })

            # Chart 5: Top High-Value Accounts / Customers
            cust_id_col = next((c for c in fact_prof.get("columns", {}).keys() if any(k in c.lower() for k in ["customer", "client", "user_id", "buyer"])), None)
            if cust_id_col:
                q_cid = _clean_sql_identifier(cust_id_col, db_conn.db_type)
                cust_spend_query = None
                
                # Check if customer name can be joined from customer_table
                if customer_table:
                    q_cu = _clean_sql_identifier(customer_table, db_conn.db_type)
                    cu_cols = table_profiles.get(customer_table, {}).get("columns", {})
                    name_expr = None
                    if "first_name" in cu_cols and "last_name" in cu_cols:
                        name_expr = "TRIM(" + concat(
                            [f"{q_cu}.first_name", "' '", f"{q_cu}.last_name"],
                            db_conn.db_type,
                        ) + ")"
                    elif "name" in cu_cols:
                        name_expr = f"{q_cu}.name"
                    elif any("contactname" in c.lower() for c in cu_cols):
                        c_col = next(c for c in cu_cols if "contactname" in c.lower())
                        name_expr = f"{q_cu}.{_clean_sql_identifier(c_col, db_conn.db_type)}"

                    if name_expr and money_expr:
                        cust_spend_query = f"""
                            SELECT {cast_text(f'{q_fact}.{q_cid}', db_conn.db_type)} as name, {round_aggregate('SUM', money_expr)} as value
                            FROM {q_fact}
                            JOIN {q_cu} ON {q_fact}.{q_cid} = {q_cu}.{q_cid}
                            WHERE {q_fact}.{q_cid} IS NOT NULL
                            GROUP BY {q_fact}.{q_cid}
                            ORDER BY value DESC
                            LIMIT 8
                        """

                if not cust_spend_query:
                    if join_col and line_money_expr and not has_genuine_fact_revenue:
                        q_jf = _clean_sql_identifier(join_col[0], db_conn.db_type)
                        q_jl = _clean_sql_identifier(join_col[1], db_conn.db_type)
                        cust_spend_query = f"""
                            SELECT {cast_text(f'{q_fact}.{q_cid}', db_conn.db_type)} as name, {round_aggregate('SUM', line_money_expr)} as value
                            FROM {q_fact}
                            JOIN {q_line} ON {q_fact}.{q_jf} = {q_line}.{q_jl}
                            WHERE {q_fact}.{q_cid} IS NOT NULL
                            GROUP BY {q_fact}.{q_cid}
                            ORDER BY value DESC
                            LIMIT 8
                        """
                    elif money_expr:
                        cust_spend_query = f"""
                            SELECT {cast_text(q_cid, db_conn.db_type)} as name, {round_aggregate('SUM', money_expr)} as value
                            FROM {q_fact}
                            WHERE {q_cid} IS NOT NULL
                            GROUP BY {q_cid}
                            ORDER BY value DESC
                            LIMIT 8
                        """
                    else:
                        cust_spend_query = f"""
                            SELECT {cast_text(q_cid, db_conn.db_type)} as name, COUNT(*) as value
                            FROM {q_fact}
                            WHERE {q_cid} IS NOT NULL
                            GROUP BY {q_cid}
                            ORDER BY value DESC
                            LIMIT 8
                        """
                cust_spend_data = execute_sql(cust_spend_query, ["top_customers_spend"])
                if cust_spend_data:
                    computed_charts.append({
                        "id": "top_customers_spend",
                        "title": "Top High-Value Buyers by Spend",
                        "subtitle": "Leading customer accounts by cumulative lifetime spend",
                        "type": "bar",
                        "table": fact_table,
                        "x_column": "Customer",
                        "y_column": "Cumulative Spend ($)",
                        "xKey": "name",
                        "yKey": "value",
                        "data": cust_spend_data,
                        "color": "#f59e0b"
                    })

            # Chart 6: Product / Line Item or Secondary Dimension Breakdown
            if catalog_table and category_table:
                cat_cols = table_profiles.get(category_table, {}).get("columns", {})
                prod_cols = table_profiles.get(catalog_table, {}).get("columns", {})
                cat_name_col = next((c for c in cat_cols.keys() if not is_id_column(c) and any(k in c.lower() for k in ["name", "category", "genre", "title", "label"])), None)
                cat_id_col = next((c for c in cat_cols.keys() if is_id_column(c)), None)
                prod_cat_fk = next((c for c in prod_cols.keys() if any(k in c.lower() for k in ["category", "genre"]) and is_id_column(c)), None)
                
                bridge_table = match_table([
                    f"{catalog_table}_{category_table}",
                    f"{category_table}_{catalog_table}",
                    f"{catalog_table}{category_table}",
                    f"{category_table}{catalog_table}"
                ])

                prod_cat_res = None
                if bridge_table:
                    q_br = _clean_sql_identifier(bridge_table, db_conn.db_type)
                    q_ctbl = _clean_sql_identifier(category_table, db_conn.db_type)
                    q_ptbl = _clean_sql_identifier(catalog_table, db_conn.db_type)
                    q_cname = _clean_sql_identifier(cat_name_col or "name", db_conn.db_type)
                    prod_cat_res = execute_sql(f"""
                        SELECT {q_ctbl}.{q_cname} as name, COUNT(*) as value
                        FROM {q_ptbl}
                        JOIN {q_br} ON {q_ptbl}.{catalog_table}_id = {q_br}.{catalog_table}_id
                        JOIN {q_ctbl} ON {q_br}.{category_table}_id = {q_ctbl}.{category_table}_id
                        GROUP BY name
                        ORDER BY value DESC
                        LIMIT 8
                    """, ["catalog_category_distribution"])
                elif cat_name_col and cat_id_col and prod_cat_fk:
                    q_ctbl = _clean_sql_identifier(category_table, db_conn.db_type)
                    q_ptbl = _clean_sql_identifier(catalog_table, db_conn.db_type)
                    q_cname = _clean_sql_identifier(cat_name_col, db_conn.db_type)
                    q_cid = _clean_sql_identifier(cat_id_col, db_conn.db_type)
                    q_pfk = _clean_sql_identifier(prod_cat_fk, db_conn.db_type)
                    
                    prod_cat_res = execute_sql(f"""
                        SELECT {q_ctbl}.{q_cname} as name, COUNT(*) as value
                        FROM {q_ptbl}
                        JOIN {q_ctbl} ON {q_ptbl}.{q_pfk} = {q_ctbl}.{q_cid}
                        GROUP BY name
                        ORDER BY value DESC
                        LIMIT 8
                    """, ["catalog_category_distribution"])

                if prod_cat_res:
                    computed_charts.append({
                        "id": "catalog_category_distribution",
                        "title": f"Catalog Distribution by {category_table.replace('_', ' ').title()}",
                        "subtitle": "Product diversity across inventory taxonomy",
                        "type": "bar",
                        "table": catalog_table,
                        "x_column": "Category",
                        "y_column": "Products",
                        "xKey": "name",
                        "yKey": "value",
                        "data": prod_cat_res,
                        "color": "#ec4899"
                    })
            elif catalog_table and "category" in table_profiles.get(catalog_table, {}).get("columns", {}):
                cat_tbl_prof = table_profiles.get(catalog_table, {})
                q_ctbl = _clean_sql_identifier(catalog_table, db_conn.db_type)
                prod_cat_res = execute_sql(f"""
                    SELECT category as name, COUNT(*) as value
                    FROM {q_ctbl}
                    WHERE category IS NOT NULL
                    GROUP BY category
                    ORDER BY value DESC
                    LIMIT 8
                """, ["catalog_category_distribution"])
                if prod_cat_res:
                    computed_charts.append({
                        "id": "catalog_category_distribution",
                        "title": "Catalog Distribution by Category",
                        "subtitle": "Product diversity across inventory taxonomy",
                        "type": "bar",
                        "table": catalog_table,
                        "x_column": "Category",
                        "y_column": "Products",
                        "xKey": "name",
                        "yKey": "value",
                        "data": prod_cat_res,
                        "color": "#ec4899"
                    })

            # Filters for Federated Mode
            all_filters = []
            if country_col:
                all_filters.append({
                    "column": f"{fact_table}.{country_col}",
                    "label": country_col.replace("_", " ").title(),
                    "filter_type": "multiselect",
                    "options": [c["name"] for c in country_data[:10]] if country_data else []
                })
            if date_col:
                all_filters.append({
                    "column": f"{fact_table}.{date_col}",
                    "label": "Date Range",
                    "filter_type": "date_range",
                    "options": []
                })

        elif analysis_mode == "mongodb":
            # -------------------------------------------------------------
            # MONGODB NATIVE AGGREGATION & ANALYTICS PIPELINE
            # -------------------------------------------------------------
            import pymongo

            if not decrypted_conn_str:
                raise ValueError("MongoDB connection URI is not configured")

            # Use the same half-open calendar window as relational queries.
            date_match = {}
            if date_from:
                date_match["$gte"] = datetime.datetime.combine(
                    datetime.date.fromisoformat(date_from), datetime.time.min,
                    tzinfo=datetime.timezone.utc,
                )
            if date_to:
                date_match["$lt"] = datetime.datetime.combine(
                    datetime.date.fromisoformat(date_bindings["date_to_excl"]),
                    datetime.time.min, tzinfo=datetime.timezone.utc,
                )

            tables_to_analyze = [selected_table] if (selected_table and selected_table in schema) else available_tables[:3]
            primary_tbl = tables_to_analyze[0]

            mongo_client = None
            try:
                mongo_client = pymongo.MongoClient(decrypted_conn_str, serverSelectionTimeoutMS=5000)
                try:
                    mongo_db = mongo_client.get_default_database()
                except Exception:
                    mongo_db = mongo_client[getattr(db_conn, "database", None) or "test"]

                chart_colors = ["#00c2cb", "#8b5cf6", "#ec4899", "#f59e0b", "#10b981", "#3b82f6"]

                for tbl in tables_to_analyze:
                    prof = table_profiles.get(tbl, {})
                    coll = mongo_db[tbl]
                    tbl_title = tbl.replace("_", " ").title()
                    date_cols = prof.get("date_cols", [])
                    t_col = _pick_date_column(date_cols)

                    # 1. Total document count (never discard a requested date filter)
                    count_metric_id = f"{tbl}_total_rows"
                    date_filter_requested = bool(date_from or date_to)
                    if date_filter_requested and not t_col:
                        total_records = None
                        trend_sub = "unavailable: no date field was detected"
                        metric_query_states[count_metric_id] = {"status": "unavailable", "reason": "missing_role"}
                        query_errors.append(f"{count_metric_id}: Date-filtered document count is unavailable because no date field was detected.")
                    elif date_filter_requested:
                        try:
                            total_records = coll.count_documents({t_col: {"$ne": None, **date_match}})
                            trend_sub = "documents in filtered horizon"
                        except Exception:
                            logger.exception("MongoDB date-filtered count failed for collection %s", tbl)
                            total_records = None
                            trend_sub = "unavailable: filtered count failed"
                            metric_query_states[count_metric_id] = {"status": "error", "reason": "query_failed"}
                            query_errors.append(f"{count_metric_id}: Date-filtered document count failed.")
                    else:
                        try:
                            total_records = coll.estimated_document_count()
                            trend_sub = "verified documents"
                        except Exception:
                            try:
                                total_records = coll.count_documents({})
                                trend_sub = "verified documents"
                            except Exception:
                                logger.exception("MongoDB document count failed for collection %s", tbl)
                                total_records = None
                                trend_sub = "unavailable: document count failed"
                                metric_query_states[count_metric_id] = {"status": "error", "reason": "query_failed"}
                                query_errors.append(f"{count_metric_id}: Document count failed.")

                    computed_kpis.append({
                        "id": f"{tbl}_total_rows",
                        "label": f"Total {tbl_title} Documents",
                        "value": f"{total_records:,}" if total_records is not None else None,
                        "raw_value": total_records,
                        "table": tbl,
                        "format": "integer",
                        "format_type": "integer",
                        "recipe_type": "atomic",
                        "trend_direction": "neutral",
                        "trend_pct": None,
                        "trend_text": f"{total_records:,} {trend_sub}" if total_records is not None else trend_sub
                    })

                    # A collection without an unambiguous date cannot provide any filtered outputs.
                    if date_filter_requested and not t_col:
                        continue

                    # 2. Measures (sum and avg)
                    for m_col in prof.get("measure_cols", [])[:3]:
                        col_name_title = m_col.split(".")[-1].replace("_", " ").title()
                        fmt = "currency" if is_monetary_column(m_col) else "number"
                        try:
                            m_pipe = []
                            if "." in m_col:
                                parent_arr = m_col.split(".")[0]
                                if schema.get(tbl, {}).get("columns", {}).get(parent_arr) == "list":
                                    m_pipe.append({"$unwind": f"${parent_arr}"})

                            match_criteria = {m_col: {"$ne": None}}
                            if date_match and t_col:
                                match_criteria[t_col] = {"$ne": None, **date_match}
                            m_pipe.append({"$match": match_criteria})
                            m_pipe.append({
                                "$group": {
                                    "_id": None,
                                    "s_val": {"$sum": f"${m_col}"},
                                    "a_val": {"$avg": f"${m_col}"},
                                    "cnt": {"$sum": 1}
                                }
                            })
                            agg_res = list(coll.aggregate(m_pipe))
                            if agg_res:
                                s_v = float(agg_res[0].get("s_val") or 0)
                                a_v = float(agg_res[0].get("a_val") or 0)
                                c_cnt = int(agg_res[0].get("cnt") or 0)

                                if fmt == "currency" or s_v > 100:
                                    computed_kpis.append({
                                        "id": f"{tbl}_{m_col.replace('.', '_')}_sum",
                                        "label": f"Total {col_name_title}",
                                        "value": f"${s_v:,.2f}" if fmt == "currency" else f"{s_v:,.1f}",
                                        "raw_value": s_v,
                                        "table": tbl,
                                        "format": fmt,
                                        "format_type": fmt,
                                        "recipe_type": "atomic",
                                        "trend_direction": "neutral",
                                        "trend_pct": None,
                                        "trend_text": "cumulative sum"
                                    })

                                computed_kpis.append({
                                    "id": f"{tbl}_{m_col.replace('.', '_')}_avg",
                                    "label": f"Average {col_name_title}",
                                    "value": f"${a_v:,.2f}" if fmt == "currency" else f"{a_v:,.1f}",
                                    "raw_value": a_v,
                                    "table": tbl,
                                    "format": fmt,
                                    "format_type": fmt,
                                    "recipe_type": "atomic",
                                    "trend_direction": "neutral",
                                    "trend_pct": None,
                                    "trend_text": f"{c_cnt:,} records evaluated"
                                })
                            else:
                                avg_id = f"{tbl}_{m_col.replace('.', '_')}_avg"
                                metric_query_states[avg_id] = {"status": "unavailable", "reason": "no_rows"}
                                if fmt == "currency":
                                    sum_id = f"{tbl}_{m_col.replace('.', '_')}_sum"
                                    metric_query_states[sum_id] = {"status": "unavailable", "reason": "no_rows"}
                        except Exception as me:
                            logger.exception("MongoDB measure aggregation failed")
                            avg_id = f"{tbl}_{m_col.replace('.', '_')}_avg"
                            metric_query_states[avg_id] = {"status": "error", "reason": "query_failed"}
                            query_errors.append(f"{avg_id}: MongoDB measure aggregation failed.")
                            if fmt == "currency":
                                sum_id = f"{tbl}_{m_col.replace('.', '_')}_sum"
                                metric_query_states[sum_id] = {"status": "error", "reason": "query_failed"}
                                query_errors.append(f"{sum_id}: MongoDB measure aggregation failed.")

                    # 3. Categorical distinct counts
                    for d_col in prof.get("dim_cols", [])[:2]:
                        try:
                            if "." in d_col:
                                parent_arr = d_col.split(".")[0]
                                if schema.get(tbl, {}).get("columns", {}).get(parent_arr) == "list":
                                    continue
                            d_vals = (
                                coll.distinct(d_col, {t_col: {"$ne": None, **date_match}})
                                if date_match else coll.distinct(d_col)
                            )
                            d_cnt = len(d_vals)
                            computed_kpis.append({
                                "id": f"{tbl}_{d_col.replace('.', '_')}_distinct",
                                "label": f"Distinct {d_col.split('.')[-1].replace('_', ' ').title()}",
                                "value": f"{d_cnt:,}",
                                "raw_value": d_cnt,
                                "table": tbl,
                                "format": "integer",
                                "format_type": "integer",
                                "recipe_type": "atomic",
                                "trend_direction": "neutral",
                                "trend_pct": None,
                                "trend_text": "unique segments"
                            })
                        except Exception:
                            logger.exception("MongoDB distinct-value query failed for collection %s", tbl)
                            distinct_id = f"{tbl}_{d_col.replace('.', '_')}_distinct"
                            metric_query_states[distinct_id] = {"status": "error", "reason": "query_failed"}
                            query_errors.append(f"{distinct_id}: MongoDB distinct-value query failed.")

                    # 4. Charts for this collection
                    # Exact aggregates: sampling would turn displayed totals into estimates.
                    sample_stage = []

                    # 4A. Time Series Trend Chart (Area Chart)
                    if t_col:
                        try:
                            t_m_col = (prof.get("measure_cols") or [None])[0]
                            t_expr = {"$sum": f"${t_m_col}"} if t_m_col else {"$sum": 1}
                            t_pipe = list(sample_stage)
                            if "." in t_col:
                                parent_arr = t_col.split(".")[0]
                                if schema.get(tbl, {}).get("columns", {}).get(parent_arr) == "list":
                                    t_pipe.append({"$unwind": f"${parent_arr}"})

                            match_criteria = {t_col: {"$ne": None}}
                            if date_match:
                                match_criteria[t_col].update(date_match)

                            t_pipe.append({"$match": match_criteria})
                            t_pipe.append({
                                "$group": {
                                    "_id": {"$dateToString": {"format": "%Y-%m", "date": f"${t_col}"}},
                                    "value": t_expr
                                }
                            })
                            t_pipe.append({"$sort": {"_id": 1}})
                            t_pipe.append({"$limit": 24})

                            t_res = list(coll.aggregate(t_pipe))
                            t_data = [{"period": str(r["_id"]), "value": round(float(r["value"]), 2)} for r in t_res if r.get("_id")]
                            if t_data:
                                computed_charts.append({
                                    "id": f"{tbl}_trend",
                                    "title": f"{tbl_title} Activity Trend Over Time",
                                    "subtitle": f"Time-series trajectory along {t_col.split('.')[-1].replace('_', ' ').title()}",
                                    "type": "area",
                                    "table": tbl,
                                    "x_column": "Period",
                                    "y_column": t_m_col.split('.')[-1].replace('_', ' ').title() if t_m_col else "Activity",
                                    "xKey": "period",
                                    "yKey": "value",
                                    "data": t_data,
                                    "color": "#6c47ff"
                                })
                            else:
                                metric_query_states[f"{tbl}_trend"] = {"status": "unavailable", "reason": "no_rows"}
                        except Exception as te:
                            logger.exception("MongoDB time series aggregation failed")
                            trend_id = f"{tbl}_trend"
                            metric_query_states[trend_id] = {"status": "error", "reason": "query_failed"}
                            query_errors.append(f"{trend_id}: MongoDB time-series aggregation failed.")

                    # 4B. Categorical Distribution Charts (Bar & Donut)
                    for idx, d_col in enumerate(prof.get("dim_cols", [])[:3]):
                        m_col = (prof.get("measure_cols") or [None])[0]
                        try:
                            chart_pipe = list(sample_stage)
                            if "." in d_col:
                                parent_arr = d_col.split(".")[0]
                                if schema.get(tbl, {}).get("columns", {}).get(parent_arr) == "list":
                                    chart_pipe.append({"$unwind": f"${parent_arr}"})

                            match_criteria = {d_col: {"$ne": None}}
                            if date_match and t_col:
                                match_criteria[t_col] = {"$ne": None, **date_match}
                            if m_col:
                                match_criteria[m_col] = {"$ne": None}

                            chart_pipe.append({"$match": match_criteria})
                            val_expr = {"$sum": f"${m_col}"} if m_col else {"$sum": 1}
                            chart_pipe.append({"$group": {"_id": f"${d_col}", "value": val_expr}})
                            chart_pipe.append({"$sort": {"value": -1}})
                            chart_pipe.append({"$limit": 8})

                            chart_res = list(coll.aggregate(chart_pipe))
                            c_data = []
                            for r in chart_res:
                                val_str = str(r.get("_id", "")).strip()
                                if not val_str or val_str.startswith(("[", "{")) or len(val_str) > 40:
                                    continue
                                c_data.append({"name": val_str, "value": round(float(r["value"]), 2)})

                            if c_data:
                                c_type = "donut" if idx == 1 or len(c_data) <= 6 else "bar"
                                computed_charts.append({
                                    "id": f"{tbl}_{d_col.replace('.', '_')}_breakdown",
                                    "title": f"{tbl_title} Distribution by {d_col.split('.')[-1].replace('_', ' ').title()}",
                                    "subtitle": f"Segment breakdown along {d_col.split('.')[-1]}",
                                    "type": c_type,
                                    "table": tbl,
                                    "x_column": d_col.split('.')[-1].replace("_", " ").title(),
                                    "y_column": m_col.split('.')[-1].replace("_", " ").title() if m_col else "Volume",
                                    "xKey": "name",
                                    "yKey": "value",
                                    "data": c_data,
                                    "color": chart_colors[idx % len(chart_colors)]
                                })
                            else:
                                metric_query_states[f"{tbl}_{d_col.replace('.', '_')}_breakdown"] = {"status": "unavailable", "reason": "no_rows"}
                        except Exception as ce:
                            logger.exception("MongoDB chart aggregation failed")
                            chart_id = f"{tbl}_{d_col.replace('.', '_')}_breakdown"
                            metric_query_states[chart_id] = {"status": "error", "reason": "query_failed"}
                            query_errors.append(f"{chart_id}: MongoDB chart aggregation failed.")

                    # 4C. Special Secondary Collection Charts (e.g. geographic boundaries or entity complexity)
                    if tbl != primary_tbl:
                        try:
                            # Check if collection has coordinates/geometry
                            sample_geom = coll.find_one({"geometry.coordinates": {"$exists": True}})
                            if sample_geom:
                                n_pipe = [
                                    {"$project": {
                                        "name": 1,
                                        "vertex_count": {"$size": {"$arrayElemAt": ["$geometry.coordinates", 0]}}
                                    }},
                                    {"$sort": {"vertex_count": -1}},
                                    {"$limit": 8}
                                ]
                                n_res = list(coll.aggregate(n_pipe))
                                n_data = [{"name": str(r["name"]), "value": float(r["vertex_count"])} for r in n_res if r.get("name")]
                                if n_data:
                                    computed_charts.append({
                                        "id": f"{tbl}_boundary_complexity",
                                        "title": f"Top {tbl_title} by Geographic Complexity",
                                        "subtitle": "Boundary polygon vertex density per zone",
                                        "type": "bar",
                                        "table": tbl,
                                        "x_column": tbl_title,
                                        "y_column": "Boundary Points",
                                        "xKey": "name",
                                        "yKey": "value",
                                        "data": n_data,
                                        "color": "#f59e0b"
                                    })
                        except Exception as ne:
                            logger.exception("MongoDB secondary collection aggregation failed")
                            chart_id = f"{tbl}_boundary_complexity"
                            metric_query_states[chart_id] = {"status": "error", "reason": "query_failed"}
                            query_errors.append(f"{chart_id}: MongoDB secondary collection aggregation failed.")

                    # 5. Populate dimensional filters with distinct options
                    for d_col in prof.get("dim_cols", [])[:3]:
                        try:
                            if "." in d_col:
                                parent_arr = d_col.split(".")[0]
                                if schema.get(tbl, {}).get("columns", {}).get(parent_arr) == "list":
                                    continue
                            raw_opts = (
                                coll.distinct(d_col, {t_col: {"$ne": None, **date_match}})
                                if date_match else coll.distinct(d_col)
                            )
                            clean_opts = [
                                str(v).strip() for v in raw_opts 
                                if v and not str(v).startswith(("[", "{")) and len(str(v)) <= 40
                            ]
                            clean_opts.sort()
                            if clean_opts and not any(f.get("column") == f"{tbl}.{d_col}" for f in all_filters):
                                all_filters.append({
                                    "column": f"{tbl}.{d_col}",
                                    "label": d_col.split(".")[-1].replace("_", " ").title(),
                                    "filter_type": "multiselect",
                                    "options": clean_opts[:15]
                                })
                        except Exception:
                            pass

                    # Date Range filter
                    if t_col and not any(f.get("filter_type") == "date_range" for f in all_filters):
                        all_filters.append({
                            "column": f"{tbl}.{t_col}",
                            "label": "Date Range",
                            "filter_type": "date_range",
                            "options": []
                        })

            except Exception:
                logger.exception("MongoDB analytics failed")
                query_errors.append("MongoDB analytics failed; some results are unavailable.")
            finally:
                if mongo_client is not None:
                    try:
                        mongo_client.close()
                    except Exception:
                        logger.exception("MongoDB client cleanup failed")

        else:
            # -------------------------------------------------------------
            # SINGLE TABLE MODE OR GENERIC DATASET MODE
            # -------------------------------------------------------------
            tbl = selected_table if (selected_table and selected_table in schema) else available_tables[0]
            q_tbl = _clean_sql_identifier(tbl, db_conn.db_type)
            prof = table_profiles.get(tbl, {})
            table_date_col = _pick_date_column(prof.get("date_cols") or [])
            if table_date_col:
                active_date_filter = (q_tbl, _clean_sql_identifier(table_date_col, db_conn.db_type))
            elif date_from or date_to:
                query_errors.append("Date filters were requested, but the selected table has no unambiguous date column.")

            # Table row count
            count_res = execute_sql(f"SELECT COUNT(*) as cnt FROM {q_tbl}", [f"{tbl}_total_rows"])
            total_records = int(count_res[0].get("cnt") or 0) if count_res else 0

            computed_kpis.append({
                "id": f"{tbl}_total_rows",
                "label": f"Total {tbl} Records",
                "value": f"{total_records:,}",
                "raw_value": total_records,
                "table": tbl,
                "format": "integer",
                "format_type": "integer",
                "recipe_type": "atomic",
                "trend_direction": "neutral",
                "trend_pct": None,
                "trend_text": f"{total_records:,} verified rows"
            })

            # Non-ID numeric measures
            for m_col in prof["measure_cols"][:3]:
                col_name_title = m_col.replace("_", " ").title()
                fmt = "currency" if is_monetary_column(m_col) else "number"
                metric_ids = [f"{tbl}_{m_col}_sum", f"{tbl}_{m_col}_avg"]
                live_columns = sqlite_live_columns.get(tbl)
                if str(db_conn.db_type).lower() == "sqlite" and live_columns is not None and m_col.casefold() not in live_columns:
                    mark_missing_role(metric_ids)
                    stats_res = []
                else:
                    q_m = _clean_sql_identifier(m_col, db_conn.db_type)
                    stats_res = execute_sql(
                        f"SELECT {round_aggregate('SUM', q_m)} as s_val, {round_aggregate('AVG', q_m)} as a_val FROM {q_tbl}",
                        metric_ids,
                    )
                stats_row = stats_res[0] if stats_res else {}
                s_raw = stats_row.get("s_val")
                a_raw = stats_row.get("a_val")
                s_v = float(s_raw) if s_raw is not None else None
                a_v = float(a_raw) if a_raw is not None else None

                computed_kpis.append({
                    "id": f"{tbl}_{m_col}_sum",
                    "label": f"Total {col_name_title}",
                    "value": (f"${s_v:,.2f}" if fmt == "currency" else f"{s_v:,.1f}") if s_v is not None else None,
                    "raw_value": s_raw,
                    "table": tbl,
                    "format": fmt,
                    "format_type": fmt,
                    "recipe_type": "atomic",
                    "trend_direction": "neutral",
                    "trend_pct": None,
                    "trend_text": "cumulative sum"
                })

                computed_kpis.append({
                    "id": f"{tbl}_{m_col}_avg",
                    "label": f"Average {col_name_title}",
                    "value": (f"${a_v:,.2f}" if fmt == "currency" else f"{a_v:,.1f}") if a_v is not None else None,
                    "raw_value": a_raw,
                    "table": tbl,
                    "format": fmt,
                    "format_type": fmt,
                    "recipe_type": "atomic",
                    "trend_direction": "neutral",
                    "trend_pct": None,
                    "trend_text": "mean value"
                })

            # Distinct categorical entities
            for d_col in prof["dim_cols"][:2]:
                q_d = _clean_sql_identifier(d_col, db_conn.db_type)
                dist_res = execute_sql(f"SELECT COUNT(DISTINCT {q_d}) as cnt FROM {q_tbl}", [f"{tbl}_{d_col}_distinct"])
                if dist_res:
                    d_cnt = int(dist_res[0].get("cnt") or 0)
                    computed_kpis.append({
                        "id": f"{tbl}_{d_col}_distinct",
                        "label": f"Distinct {d_col.replace('_', ' ').title()}",
                        "value": f"{d_cnt:,}",
                        "raw_value": d_cnt,
                        "table": tbl,
                        "format": "integer",
                        "format_type": "integer",
                        "recipe_type": "atomic",
                        "trend_direction": "neutral",
                        "trend_pct": None,
                        "trend_text": "unique segments"
                    })

            # Time Series Chart for Single Table
            if table_date_col:
                t_col = table_date_col
                q_t = _clean_sql_identifier(t_col, db_conn.db_type)
                m_col = prof["measure_cols"][0] if prof["measure_cols"] else None
                m_expr = round_aggregate("SUM", _clean_sql_identifier(m_col, db_conn.db_type)) if m_col else "COUNT(*)"
                
                t_query = f"""
                    SELECT {month_bucket(q_t, db_conn.db_type)} as period, {m_expr} as value
                    FROM {q_tbl} 
                    WHERE {q_t} IS NOT NULL 
                    GROUP BY period 
                    ORDER BY period ASC 
                    LIMIT 30
                """
                t_data = execute_sql(t_query, [f"{tbl}_trend"])
                if t_data:
                    computed_charts.append({
                        "id": f"{tbl}_trend",
                        "title": f"{tbl} Activity Trend Over Time",
                        "subtitle": f"Time-series trajectory along {t_col}",
                        "type": "area",
                        "table": tbl,
                        "x_column": "Period",
                        "y_column": m_col or "Count",
                        "xKey": "period",
                        "yKey": "value",
                        "data": t_data,
                        "color": "#6c47ff"
                    })

            # Categorical Bar & Donut Charts for Single Table
            for idx, d_col in enumerate(prof["dim_cols"][:2]):
                q_d = _clean_sql_identifier(d_col, db_conn.db_type)
                m_col = prof["measure_cols"][0] if prof["measure_cols"] else None
                m_expr = round_aggregate("SUM", _clean_sql_identifier(m_col, db_conn.db_type)) if m_col else "COUNT(*)"
                
                c_query = f"""
                    SELECT {q_d} as name, {m_expr} as value 
                    FROM {q_tbl} 
                    WHERE {q_d} IS NOT NULL 
                    GROUP BY {q_d} 
                    ORDER BY value DESC 
                    LIMIT 8
                """
                c_data = execute_sql(c_query, [f"{tbl}_{d_col}_breakdown"])
                if c_data:
                    c_type = "donut" if idx == 1 else "bar"
                    computed_charts.append({
                        "id": f"{tbl}_{d_col}_breakdown",
                        "title": f"{tbl} Distribution by {d_col.replace('_', ' ').title()}",
                        "subtitle": f"Segment breakdown by {d_col}",
                        "type": c_type,
                        "table": tbl,
                        "x_column": d_col.replace("_", " ").title(),
                        "y_column": m_col or "Volume",
                        "xKey": "name",
                        "yKey": "value",
                        "data": c_data,
                        "color": "#00c2cb" if idx == 0 else "#8b5cf6"
                    })

            # Secondary Measure Breakdown for Single Table
            if len(prof["measure_cols"]) > 1 and prof["dim_cols"]:
                d_col = prof["dim_cols"][0]
                q_d = _clean_sql_identifier(d_col, db_conn.db_type)
                m_col2 = prof["measure_cols"][1]
                q_m2 = _clean_sql_identifier(m_col2, db_conn.db_type)
                m2_query = f"""
                    SELECT {q_d} as name, {round_aggregate('SUM', q_m2)} as value
                    FROM {q_tbl} 
                    WHERE {q_d} IS NOT NULL AND {q_m2} IS NOT NULL
                    GROUP BY {q_d} 
                    ORDER BY value DESC 
                    LIMIT 8
                """
                m2_data = execute_sql(m2_query, [f"{tbl}_{m_col2}_breakdown"])
                if m2_data:
                    computed_charts.append({
                        "id": f"{tbl}_{m_col2}_breakdown",
                        "title": f"Top {d_col.replace('_', ' ').title()} by {m_col2.replace('_', ' ').title()}",
                        "subtitle": f"Distribution of {m_col2.replace('_', ' ').title()} across key segments",
                        "type": "bar",
                        "table": tbl,
                        "x_column": d_col.replace("_", " ").title(),
                        "y_column": m_col2.replace("_", " ").title(),
                        "xKey": "name",
                        "yKey": "value",
                        "data": m2_data,
                        "color": "#f59e0b"
                    })

            all_filters = [
                {
                    "column": f"{tbl}.{d_col}",
                    "label": d_col.replace("_", " ").title(),
                    "filter_type": "multiselect",
                    "options": []
                }
                for d_col in prof["dim_cols"][:2]
            ]

        # Keep failed query-backed outputs visible instead of silently dropping the metric/chart.
        known_metric_ids = {str(item.get("id", "")) for item in computed_kpis}
        known_chart_ids = {str(item.get("id", "")) for item in computed_charts}
        chart_metric_ids = {
            "monthly_revenue_velocity", "revenue_by_market", "revenue_by_segment",
            "order_status_distribution", "top_customers_spend", "catalog_category_distribution",
        }
        for metric_id, state in metric_query_states.items():
            if state["status"] == "available":
                continue
            if metric_id in chart_metric_ids or metric_id.endswith("_trend") or metric_id.endswith("_breakdown"):
                if metric_id not in known_chart_ids:
                    computed_charts.append({
                        "id": metric_id,
                        "title": "Chart unavailable",
                        "type": "area" if metric_id.endswith("_trend") or metric_id == "monthly_revenue_velocity" else "bar",
                        "data": [],
                        "xKey": "name",
                        "yKey": "value",
                    })
            elif metric_id not in known_metric_ids:
                computed_kpis.append({
                    "id": metric_id,
                    "label": "Metric unavailable",
                    "value": None,
                    "raw_value": None,
                    "format": "number",
                })

        # Preserve metric existence while making missing, zero, and failed results explicit.
        for metric in computed_kpis:
            apply_result_status(metric)
        for chart in computed_charts:
            apply_result_status(chart, is_chart=True)

        # -- LAYER 5 & 6: AI EXECUTIVE PLAYBOOK & ANOMALIES (PARALLEL) --
        if progress_callback:
            progress_callback(5, "Layer 5 & 6: Strategic AI Executive Playbook & Outlier Engine...")
        logger.info("Database pipeline layers 5 and 6: synthesis and anomaly detection")

        def run_ai_synthesis() -> Dict[str, Any]:
            prompt = f"""
            You are DataSpeakAI's Chief Business Intelligence Analyst.
            Analyze this live enterprise database profile and key performance indicators:
            
            Database type: {db_conn.db_type}
            Mode: {"Multi-Table Relational Federation" if is_federated_mode else "Single Table"}

            Aggregated numeric values only:
            {json.dumps(_llm_safe_points(computed_kpis, computed_charts), indent=2, default=str)}
            
            Synthesize a concise executive summary using only the supplied numeric values.
            Do not infer category names, customer identities, geographies, percentages, or trends that are not supplied.
            Return STRICT JSON with business_domain, executive_summary,
            strategic_insights, and tactical_recommendations. Use empty lists
            when the numeric aggregates do not support an insight or recommendation.
            """
            from services.llm_generation_service import LLMFailure, generate
            res_text = generate(prompt, provider="auto", raise_on_failure=True).strip()
            if res_text.startswith("```json"):
                res_text = res_text[7:-3].strip()
            elif res_text.startswith("```"):
                res_text = res_text[3:-3].strip()
            try:
                parsed = json.loads(res_text)
            except (ValueError, TypeError):
                raise LLMFailure("InvalidResponse") from None
            if (not isinstance(parsed, dict)
                    or not isinstance(parsed.get("executive_summary"), str)
                    or not isinstance(parsed.get("strategic_insights"), list)
                    or not isinstance(parsed.get("tactical_recommendations"), list)):
                raise LLMFailure("InvalidResponse")
            parsed["source"] = "llm"
            parsed.pop("llm_error", None)
            return parsed

        def computed_fallback(category: str) -> Dict[str, Any]:
            metrics = {item.get("id"): item for item in computed_kpis}
            money_metric = metrics.get("total_revenue")
            if money_metric is None:
                money_metric = next((item for item in computed_kpis
                    if str(item.get("id", "")).endswith("_sum")
                    and item.get("format") == "currency"), None)
            count_metric = metrics.get("total_orders")
            if count_metric is None:
                count_metric = next((item for item in computed_kpis
                    if str(item.get("id", "")).endswith("_total_rows")), None)
            monetary_sum = money_metric.get("raw_value") if money_metric else None
            record_count = count_metric.get("raw_value") if count_metric else None
            if (isinstance(monetary_sum, (int, float)) and not isinstance(monetary_sum, bool)
                    and isinstance(record_count, (int, float)) and not isinstance(record_count, bool)
                    and money_metric.get("status") in {"available", "zero"}
                    and count_metric.get("status") in {"available", "zero"}):
                monetary_label = "gross revenue" if money_metric.get("id") == "total_revenue" else "monetary sum"
                summary = (
                    f"Computed {monetary_label} is ${monetary_sum:,.2f} across "
                    f"{int(record_count):,} records."
                )
                findings = [{
                    "title": "Computed monetary aggregate", "finding": summary,
                    "impact": "Medium", "category": "Aggregate",
                }]
            else:
                summary = "Insufficient data to generate a reliable business summary."
                findings = []
            return {
                "business_domain": "Unknown",
                "executive_summary": summary,
                "strategic_insights": findings,
                "tactical_recommendations": [],
                "source": "deterministic_fallback",
                "llm_error": category,
            }

        def run_anomaly_detection() -> List[Dict[str, Any]]:
            anomalies: List[Dict[str, Any]] = []
            if not is_sql:
                return anomalies
            target_tbl = fact_table if (is_federated_mode and fact_table) else (selected_table or available_tables[0])
            prof = table_profiles.get(target_tbl, {})
            if prof.get("monetary_cols"):
                col = prof["monetary_cols"][0]
                q_tbl = _clean_sql_identifier(target_tbl, db_conn.db_type)
                q_col = _clean_sql_identifier(col, db_conn.db_type)
                stats_res = execute_sql(f"SELECT AVG({q_col}) as avg_val, MAX({q_col}) as max_val FROM {q_tbl} WHERE {q_col} IS NOT NULL")
                if stats_res:
                    avg_v = float(stats_res[0].get("avg_val") or 0)
                    max_v = float(stats_res[0].get("max_val") or 0)
                    if avg_v > 0 and max_v > (avg_v * 3.0):
                        anomalies.append({
                            "table": target_tbl,
                            "field": col,
                            "value": max_v,
                            "baseline_avg": round(avg_v, 2),
                            "deviation": f"Peak transaction is {max_v / avg_v:.1f}x higher than table average",
                            "severity": "Medium"
                        })
            return anomalies

        from services.llm_generation_service import LLMFailure, _configured_seconds, _classify_failure
        budget = _configured_seconds("LLM_PIPELINE_BUDGET_SECONDS", 30.0)
        deadline = time.monotonic() + budget
        executor = ThreadPoolExecutor(max_workers=2)
        try:
            future_ai = executor.submit(run_ai_synthesis)
            future_anom = executor.submit(run_anomaly_detection)
            try:
                ai_summary = future_ai.result(timeout=max(0, deadline - time.monotonic()))
            except FutureTimeout:
                logger.warning("provider=auto category=Timeout duration_ms=%d", int(budget * 1000))
                ai_summary = computed_fallback("Timeout")
            except Exception as error:
                failure = _classify_failure(error)
                logger.warning("provider=auto category=%s duration_ms=0", failure.category)
                ai_summary = computed_fallback(failure.category)
            try:
                detected_anomalies = future_anom.result(timeout=max(0, deadline - time.monotonic()))
            except FutureTimeout:
                logger.warning("Anomaly detection exceeded pipeline budget")
                detected_anomalies = []
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

        # Final Dashboard Plan
        final_layout = compose_dashboard_layout(
            table_name=selected_table or "All Tables",
            metrics=computed_kpis,
            charts=computed_charts,
            filters=all_filters,
            executive_summary=ai_summary,
            anomalies=detected_anomalies
        )

        response_payload = {
            "insights_version": INSIGHTS_CACHE_VERSION,
            "connection_cache_version": cache_version,
            "success": True,
            "status": "success",
            "connection_id": connection_id,
            "db_name": getattr(db_conn, "name", getattr(db_conn, "db_name", "Database")),
            "name": getattr(db_conn, "name", getattr(db_conn, "db_name", "Database")),
            "db_type": db_conn.db_type,
            "available_tables": available_tables,
            "selected_table": selected_table or "All Tables",
            "key_metrics": computed_kpis,
            "charts": computed_charts,
            "auto_charts": computed_charts,
            "filters": all_filters,
            "executive_summary": ai_summary,
            "business_summary": {
                "business_domain": ai_summary.get("business_domain", "Business operations"),
                "executive_summary": ai_summary.get("executive_summary", ""),
                "key_metrics": computed_kpis
            },
            "insights": [
                {
                    "title": s.get("title", "Insight"),
                    "description": s.get("finding", ""),
                    "impact": s.get("impact", "Medium"),
                    "suggested_action": (ai_summary.get("tactical_recommendations") or ["Take data-driven action"])[
                        idx % len(ai_summary.get("tactical_recommendations") or ["Take data-driven action"])
                    ],
                    "metric": s.get("category", "General")
                }
                for idx, s in enumerate(ai_summary.get("strategic_insights", []))
            ],
            "anomalies": detected_anomalies,
            "data_quality": {"warnings": list(dict.fromkeys(query_errors))},
            "applied_date_from": date_from,
            "applied_date_to": date_to,
            "layout_plan": final_layout.model_dump(),
            "pipeline_layers": [
                {"layer": 1, "name": "Schema Discovery & Multi-Table Statistical Profiling", "status": "completed"},
                {"layer": 2, "name": "Metric Recipes Formulation (Phase 2C Deterministic)", "status": "completed"},
                {"layer": 3, "name": "Chart & Filter Planning (Phase 2D/2E)", "status": "completed"},
                {"layer": 4, "name": "High-Speed Aggregation & Data Computation", "status": "completed"},
                {"layer": 5, "name": "Dual-Engine AI Executive Playbook", "status": "completed"},
                {"layer": 6, "name": "Statistical Anomaly & Outlier Engine", "status": "completed"}
            ],
            "cached": False,
            "cached_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }

        # Cache in Redis L1 and Database L2
        try:
            clean_payload = json.loads(json.dumps(response_payload, default=str))
            cache_set(cache_key, clean_payload, ttl_seconds=86400)
            if not selected_table and not date_from and not date_to:
                updated = (
                    db.query(models.DatabaseConnection)
                    .filter(
                        models.DatabaseConnection.id == connection_id,
                        models.DatabaseConnection.tenant_id == tenant_id,
                        models.DatabaseConnection.insights_cache_version == cache_version,
                    )
                    .update(
                        {
                            models.DatabaseConnection.insights_cache: clean_payload,
                            models.DatabaseConnection.insights_cached_at: datetime.datetime.now(datetime.timezone.utc),
                        },
                        synchronize_session=False,
                    )
                )
                if updated == 1:
                    db.commit()
                else:
                    db.rollback()
                    logger.info(
                        "Skipped stale database insights L2 write for connection %s",
                        connection_id,
                    )
        except Exception as e:
            logger.exception("Database insights cache write failed")

        logger.info("Database insights pipeline completed")
        return response_payload

    def run_db_pipeline_stream(
        self,
        db: Session,
        connection_id: Any,
        user_id: Optional[Any] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        selected_table: Optional[str] = None,
        force_refresh: bool = False,
        tenant_id: Optional[int] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Runs the 6-Layer Deterministic Database Pipeline as an SSE event generator.
        Yields progress steps and finally the result payload.
        """
        if tenant_id is None:
            raise ValueError("Tenant ID is required for database insights")

        date_from, date_to, _ = _normalize_date_range(date_from, date_to)

        query = db.query(models.DatabaseConnection).filter(
            models.DatabaseConnection.id == connection_id
        )
        query = query.filter(models.DatabaseConnection.tenant_id == tenant_id)
        db_conn = query.first()
        if not db_conn:
            raise ValueError("Database connection not found or unauthorized")
        cache_version = int(getattr(db_conn, "insights_cache_version", 0) or 0)
        cache_key = _cache_key(
            tenant_id, connection_id, selected_table, date_from, date_to, cache_version,
        )
        if not force_refresh:
            cached_data = cache_get(cache_key)
            if (
                isinstance(cached_data, dict)
                and cached_data.get("insights_version") == INSIGHTS_CACHE_VERSION
                and cached_data.get("connection_cache_version") == cache_version
            ):
                cached_data["cached"] = True
                cached_data["cache_source"] = "redis_l1"
                yield {"type": "result", "data": cached_data, "cached": True}
                return

            if db_conn and db_conn.insights_cache and db_conn.insights_cached_at:
                cached_at = db_conn.insights_cached_at
                now_utc = datetime.datetime.now(datetime.timezone.utc)
                if hasattr(cached_at, "tzinfo") and cached_at.tzinfo is not None:
                    age = (now_utc - cached_at).total_seconds()
                else:
                    age = (now_utc.replace(tzinfo=None) - cached_at).total_seconds()
                if age < 86400 and not selected_table and not date_from and not date_to:
                    res = db_conn.insights_cache
                    if isinstance(res, str):
                        try:
                            res = json.loads(res)
                        except Exception:
                            pass
                    if (
                        isinstance(res, dict)
                        and res.get("insights_version") == INSIGHTS_CACHE_VERSION
                        and res.get("connection_cache_version") == cache_version
                    ):
                        res["cached"] = True
                        res["cache_source"] = "db_l2"
                        cache_set(cache_key, res, ttl_seconds=86400)
                        yield {"type": "result", "data": res, "cached": True}
                        return

        yield {
            "type": "progress",
            "layer": 1,
            "step": 1,
            "total": 6,
            "name": "Schema Discovery & Multi-Table Statistical Profiling",
            "message": "Discovering database tables, profiling schema types, and isolating foreign keys..."
        }

        yield {
            "type": "progress",
            "layer": 2,
            "step": 2,
            "total": 6,
            "name": "Metric Recipe Formulation (Phase 2C Deterministic)",
            "message": "Formulating Atomic, Ratio, and Difference metric recipes with safe division guards..."
        }

        yield {
            "type": "progress",
            "layer": 3,
            "step": 3,
            "total": 6,
            "name": "Chart & Filter Planning (Phase 2D/2E)",
            "message": "Determining optimal chart visuals (Line, Bar, Donut) and low-cardinality filters..."
        }

        yield {
            "type": "progress",
            "layer": 4,
            "step": 4,
            "total": 6,
            "name": "High-Speed Aggregation & Data Computation",
            "message": "Executing high-speed pushdown aggregations and multi-table relational joins..."
        }

        try:
            result = self.run_db_pipeline(
                db=db,
                connection_id=connection_id,
                user_id=user_id,
                date_from=date_from,
                date_to=date_to,
                selected_table=selected_table,
                force_refresh=force_refresh,
                tenant_id=tenant_id,
            )

            yield {
                "type": "progress",
                "layer": 5,
                "step": 5,
                "total": 6,
                "name": "Dual-Engine AI Executive Playbook",
                "message": "Synthesizing executive intelligence playbook and tactical recommendations..."
            }

            yield {
                "type": "progress",
                "layer": 6,
                "step": 6,
                "total": 6,
                "name": "Statistical Anomaly & Outlier Engine",
                "message": "Finalizing outlier detection and building deterministic DashboardLayoutPlan..."
            }

            yield {"type": "result", "data": result, "cached": False}

        except Exception as e:
            logger.exception("Database pipeline stream failed")
            yield {"type": "error", "message": "Database pipeline execution failed"}


db_pipeline_service = DatabasePipelineService()
