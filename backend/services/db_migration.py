"""
Lightweight, Zero-Dependency Database Schema Sync & Migration Utility.

Runs automatically on backend startup (`models.Base.metadata.create_all` only creates
tables if they don't exist, but does not alter existing SQLite or PostgreSQL tables).
This utility ensures any new columns added to models (e.g. semantic_type, is_primary_key,
is_foreign_key, foreign_key_target in schema_registry; domain_mapping in dashboard_layouts)
are automatically inspected and added across environments (SQLite and PostgreSQL)
without requiring manual ALTER TABLE scripts or external CLI steps.
"""

import logging
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

MIGRATION_COLUMNS = [
    # (table_name, column_name, sqlite_type, postgres_type)
    ("schema_registry", "semantic_type", "VARCHAR DEFAULT 'UNKNOWN'", "VARCHAR(50) DEFAULT 'UNKNOWN'"),
    ("schema_registry", "is_primary_key", "BOOLEAN DEFAULT 0", "BOOLEAN DEFAULT FALSE"),
    ("schema_registry", "is_foreign_key", "BOOLEAN DEFAULT 0", "BOOLEAN DEFAULT FALSE"),
    ("schema_registry", "foreign_key_target", "VARCHAR", "VARCHAR(255)"),
    ("dashboard_layouts", "domain_mapping", "JSON", "JSONB"),
    ("dashboard_layouts", "document_id", "INTEGER", "INTEGER"),
    ("dashboard_layouts", "source_type", "VARCHAR DEFAULT 'database'", "VARCHAR(50) DEFAULT 'database'"),
    ("dashboard_layouts", "source_archetype", "VARCHAR DEFAULT 'relational_sql'", "VARCHAR(100) DEFAULT 'relational_sql'"),
    # Document processing & progress columns
    ("documents", "progress", "FLOAT DEFAULT 0.0", "FLOAT DEFAULT 0.0"),
    ("documents", "error_message", "TEXT", "TEXT"),
    ("documents", "total_pages", "INTEGER DEFAULT 0", "INTEGER DEFAULT 0"),
    ("documents", "pages_processed", "INTEGER DEFAULT 0", "INTEGER DEFAULT 0"),
    ("documents", "visual_pages", "INTEGER DEFAULT 0", "INTEGER DEFAULT 0"),
    ("documents", "celery_task_id", "VARCHAR", "VARCHAR(255)"),
    ("documents", "embedding_model", "VARCHAR DEFAULT 'all-MiniLM-L6-v2'", "VARCHAR(100) DEFAULT 'all-MiniLM-L6-v2'"),
    # Document chunk metadata columns
    ("document_chunks", "section_heading", "VARCHAR", "VARCHAR(255)"),
    ("document_chunks", "content_type", "VARCHAR DEFAULT 'text'", "VARCHAR(50) DEFAULT 'text'"),
    ("document_chunks", "page_number", "INTEGER", "INTEGER"),
    ("document_chunks", "reference_id", "VARCHAR", "VARCHAR(255)"),
    # Database connections columns
    ("database_connections", "port", "INTEGER", "INTEGER"),
    ("database_connections", "connection_string", "VARCHAR", "VARCHAR(1000)"),
    ("database_connections", "tables_metadata", "JSON", "JSONB"),
    ("database_connections", "insights_cache", "JSON", "JSONB"),
    ("database_connections", "insights_cached_at", "DATETIME", "TIMESTAMP"),
    ("database_connections", "description", "VARCHAR", "VARCHAR(500)"),
    # Tenant subscription plan column
    ("tenants", "plan", "VARCHAR DEFAULT 'Starter'", "VARCHAR(50) DEFAULT 'Starter'"),
    # Query log source column
    ("query_logs", "source", "VARCHAR DEFAULT 'web'", "VARCHAR(50) DEFAULT 'web'"),
    # Widget key table allowlist column
    ("widget_keys", "allowed_tables", "JSON", "JSONB"),
    # Widget key reference for query logs (SEC-04)
    ("query_logs", "widget_key_id", "INTEGER", "INTEGER"),
]



def run_schema_migrations(engine: Engine) -> None:
    """
    Idempotent schema synchronizer: checks existing table columns via SQLAlchemy Inspector
    and executes ALTER TABLE ADD COLUMN for any missing attributes.
    """
    try:
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        is_sqlite = engine.dialect.name == "sqlite"

        with engine.begin() as conn:
            for table_name, column_name, sqlite_type, pg_type in MIGRATION_COLUMNS:
                if table_name not in existing_tables:
                    continue

                existing_cols = {c["name"] for c in inspector.get_columns(table_name)}
                if column_name not in existing_cols:
                    col_type = sqlite_type if is_sqlite else pg_type
                    logger.info(f"[MIGRATION] Adding missing column '{column_name}' ({col_type}) to table '{table_name}'")
                    conn.execute(text(f'ALTER TABLE "{table_name}" ADD COLUMN "{column_name}" {col_type}'))
    except Exception as e:
        logger.warning(f"[MIGRATION] Schema auto-sync check encountered: {e}")
