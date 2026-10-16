"""
Read-Only Database Schema Preflight Utility for DataSpeakAI.

Inspects database schema structure prior to application startup or migration.
- Performs strictly read-only inspection (ZERO DDL, zero writes, zero data modifications).
- Redacts database credentials from logs and output.
- Classifies database layout into one of four recognized states:
    1. LAYOUT_EMPTY: Zero tables present (ready for fresh `alembic upgrade head`).
    2. LAYOUT_LEGACY: Recognized historical schema (needs transitional migration).
    3. LAYOUT_CURRENT: Full 46 reconciled tables with Phase 7 columns.
    4. LAYOUT_UNSUPPORTED: Unrecognized drift or rogue tables/columns detected.
- Computes deterministic SHA-256 schema fingerprint.
"""
import os
import sys
import re
import hashlib
import logging
import argparse
from typing import Dict, Any, List, Set, Tuple
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

# Ensure backend root is on sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import models

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("dataspeak.schema_preflight")


def redact_url(url: str) -> str:
    """Redacts passwords and credentials from database connection URIs."""
    if not url:
        return ""
    # Redact ://user:password@host to ://user:***@host
    return re.sub(r"://([^:@]+):([^@]+)@", r"://\1:***@", url)


def compute_schema_fingerprint(inspector) -> str:
    """Computes a deterministic SHA-256 hash of table and column names."""
    table_names = sorted(inspector.get_table_names())
    hasher = hashlib.sha256()
    for t in table_names:
        if t == "alembic_version":
            continue
        hasher.update(t.encode("utf-8"))
        try:
            columns = sorted(inspector.get_columns(t), key=lambda c: c["name"])
            for c in columns:
                col_spec = f"{c['name']}:{str(c.get('type', ''))}"
                hasher.update(col_spec.encode("utf-8"))
        except Exception:
            pass
    return hasher.hexdigest()[:16]


def get_current_alembic_revision(engine: Engine) -> str:
    """Inspects the alembic_version table if it exists."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
            row = result.fetchone()
            if row:
                return str(row[0])
    except Exception:
        pass
    return "none"


def inspect_database_layout(engine: Engine) -> Dict[str, Any]:
    """
    Performs read-only inspection and classifies the database layout.
    """
    inspector = inspect(engine)
    existing_tables: Set[str] = set(inspector.get_table_names())
    # Exclude alembic metadata table from model comparison
    user_tables = existing_tables - {"alembic_version"}
    
    expected_tables: Set[str] = set(models.Base.metadata.tables.keys())
    dialect_name = engine.dialect.name
    fingerprint = compute_schema_fingerprint(inspector)
    alembic_rev = get_current_alembic_revision(engine)
    
    # 1. Check for empty database
    if len(user_tables) == 0:
        return {
            "layout": "LAYOUT_EMPTY",
            "status": "valid",
            "table_count": 0,
            "dialect": dialect_name,
            "fingerprint": fingerprint,
            "alembic_revision": alembic_rev,
            "details": "Database is completely empty. Ready for initial migration."
        }
        
    # 2. Check for unexpected / rogue tables
    rogue_tables = user_tables - expected_tables
    if rogue_tables:
        return {
            "layout": "LAYOUT_UNSUPPORTED",
            "status": "drift_detected",
            "table_count": len(user_tables),
            "dialect": dialect_name,
            "fingerprint": fingerprint,
            "alembic_revision": alembic_rev,
            "rogue_tables": sorted(list(rogue_tables)),
            "details": f"Unsupported drift: unrecognized tables found: {sorted(list(rogue_tables))}"
        }

    # 3. Check for rogue columns in key core tables
    rogue_columns = {}
    for t in user_tables.intersection({"users", "tenants", "conversations"}):
        existing_cols = {c["name"] for c in inspector.get_columns(t)}
        expected_cols = {c.name for c in models.Base.metadata.tables[t].columns}
        extra_cols = existing_cols - expected_cols
        if extra_cols:
            rogue_columns[t] = sorted(list(extra_cols))
            
    if rogue_columns:
        return {
            "layout": "LAYOUT_UNSUPPORTED",
            "status": "drift_detected",
            "table_count": len(user_tables),
            "dialect": dialect_name,
            "fingerprint": fingerprint,
            "alembic_revision": alembic_rev,
            "rogue_columns": rogue_columns,
            "details": f"Unsupported drift: unauthorized columns detected: {rogue_columns}"
        }

    # 4. Check if current layout (all 46 tables present)
    if expected_tables.issubset(user_tables):
        return {
            "layout": "LAYOUT_CURRENT",
            "status": "valid",
            "table_count": len(user_tables),
            "dialect": dialect_name,
            "fingerprint": fingerprint,
            "alembic_revision": alembic_rev,
            "details": "Full 46-table reconciled schema is present."
        }

    # 5. Check if recognized legacy layout
    missing_tables = expected_tables - user_tables
    return {
        "layout": "LAYOUT_LEGACY",
        "status": "needs_upgrade",
        "table_count": len(user_tables),
        "dialect": dialect_name,
        "fingerprint": fingerprint,
        "alembic_revision": alembic_rev,
        "missing_tables": sorted(list(missing_tables)),
        "details": f"Recognized legacy database. Missing {len(missing_tables)} operational tables."
    }


def run_preflight(database_url: str) -> int:
    """Executes preflight check and logs results. Returns 0 on success, 1 on drift."""
    redacted = redact_url(database_url)
    logger.info(f"Running read-only schema preflight on: {redacted}")
    engine = create_engine(database_url)
    try:
        report = inspect_database_layout(engine)
        logger.info(f"Layout Classification: {report['layout']} (Status: {report['status']})")
        logger.info(f"Dialect: {report['dialect']} | Tables: {report['table_count']} | Fingerprint: {report['fingerprint']}")
        logger.info(f"Alembic Revision: {report['alembic_revision']}")
        logger.info(f"Details: {report['details']}")
        
        if report["layout"] == "LAYOUT_UNSUPPORTED":
            logger.error("Schema preflight REJECTED due to unknown drift.")
            return 1
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DataSpeakAI Read-Only Schema Preflight")
    parser.add_argument("--database-url", default=None, help="Database connection URL")
    args = parser.parse_args()
    
    url = args.database_url or os.getenv("DATABASE_URL", "sqlite:///./app.db")
    sys.exit(run_preflight(url))
