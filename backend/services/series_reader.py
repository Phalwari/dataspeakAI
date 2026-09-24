"""
backend/services/series_reader.py

Validated Series and Raw Sample Reader for DataSpeakAI / NexaBI.
Provides safe, centralized row sampling (such as scatter correlation pairs)
without embedding arbitrary SQL in HTTP API routers or overloading MetricExecutor.
Enforces SchemaRegistry validation, intra-table boundaries, dialect quoting,
and hard row limits.
"""

from typing import List, Dict, Any, Optional
import logging
from sqlalchemy import text
from sqlalchemy.orm import Session

import models
from services.query_builder import quote_ident
from services.db_utils import get_connection_url
from services.db_pool import get_engine

logger = logging.getLogger(__name__)

MAX_SCATTER_LIMIT = 40


def read_scatter_series(
    db_conn: models.DatabaseConnection,
    db: Session,
    table_name: str,
    measure1_col: str,
    measure2_col: str,
    label_col: Optional[str] = None,
    limit: int = 40,
) -> List[Dict[str, Any]]:
    """
    Safely reads scatter sample data points between two numeric measures
    from a single verified table.

    Validations:
    1. table_name must exist in verified SchemaRegistry for connection.
    2. measure1_col and measure2_col must both exist in table_name and be measures.
    3. label_col (if provided) must exist in table_name.
    4. Enforces same-table constraint (all identifiers must belong to table_name).
    5. Applies dialect-aware identifier quoting.
    6. Enforces hard row limit (max 40).
    """
    if not table_name:
        raise ValueError("Table name is required for scatter series.")
    if not measure1_col or not measure2_col:
        raise ValueError("Two measure columns are required for scatter series.")

    clean_limit = min(max(1, limit or 40), MAX_SCATTER_LIMIT)

    registries = (
        db.query(models.SchemaRegistry)
        .filter(
            models.SchemaRegistry.connection_id == db_conn.id,
            models.SchemaRegistry.table_name == table_name,
        )
        .all()
    )

    if not registries:
        raise ValueError(
            f"Table '{table_name}' does not exist in SchemaRegistry for connection {db_conn.id}."
        )

    col_map = {r.column_name: r for r in registries}

    # Validate measure1
    if measure1_col not in col_map:
        raise ValueError(
            f"Scatter column '{measure1_col}' does not exist in table '{table_name}'."
        )
    if not getattr(col_map[measure1_col], "is_measure", False):
        raise ValueError(
            f"Scatter column '{measure1_col}' is not registered as a numeric measure."
        )

    # Validate measure2
    if measure2_col not in col_map:
        raise ValueError(
            f"Scatter column '{measure2_col}' does not exist in table '{table_name}'."
        )
    if not getattr(col_map[measure2_col], "is_measure", False):
        raise ValueError(
            f"Scatter column '{measure2_col}' is not registered as a numeric measure."
        )

    # Validate label_col if specified
    if label_col and label_col not in col_map:
        raise ValueError(
            f"Scatter label column '{label_col}' does not exist in table '{table_name}'."
        )

    db_type = (db_conn.db_type or "sqlite").lower()
    t_q = quote_ident(table_name, db_type)
    m1_q = quote_ident(measure1_col, db_type)
    m2_q = quote_ident(measure2_col, db_type)
    lbl_q = quote_ident(label_col, db_type) if label_col else m1_q

    sql_str = (
        f"SELECT {m1_q}, {m2_q}, {lbl_q} "
        f"FROM {t_q} "
        f"WHERE {m1_q} IS NOT NULL AND {m2_q} IS NOT NULL "
        f"LIMIT :limit"
    )

    conn_url = get_connection_url(db_conn)
    if not conn_url:
        raise ValueError(f"Could not resolve connection URL for connection {db_conn.id}")

    engine = get_engine(conn_url)
    with engine.connect() as conn:
        res = conn.execute(text(sql_str), {"limit": clean_limit}).fetchall()
        scatter_points = []
        for r in res:
            try:
                x_val = round(float(r[0] or 0), 2)
                y_val = round(float(r[1] or 0), 2)
                lbl_val = str(r[2] or "")[:20]
                scatter_points.append({"x": x_val, "y": y_val, "name": lbl_val})
            except (ValueError, TypeError) as ex:
                logger.debug(f"Skipping non-numeric scatter row: {ex}")
                continue
        return scatter_points
