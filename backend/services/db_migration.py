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
    # Query log widget key column
    ("query_logs", "widget_key_id", "INTEGER", "INTEGER"),
    # Widget key table allowlist column
    ("widget_keys", "allowed_tables", "JSON", "JSONB"),
    # Widget key reference for query logs (SEC-04)
    ("query_logs", "widget_key_id", "INTEGER", "INTEGER"),
    # Phase 3: Generated Insights & Recommendations columns
    ("generated_insights", "database_id", "INTEGER", "INTEGER"),
    ("generated_insights", "title", "VARCHAR DEFAULT 'AI Insight'", "VARCHAR(255) DEFAULT 'AI Insight'"),
    ("generated_insights", "category", "VARCHAR DEFAULT 'Operational'", "VARCHAR(100) DEFAULT 'Operational'"),
    ("generated_insights", "severity", "VARCHAR DEFAULT 'opportunity'", "VARCHAR(50) DEFAULT 'opportunity'"),
    ("generated_insights", "summary", "TEXT", "TEXT"),
    ("generated_insights", "impact_score", "FLOAT DEFAULT 0.0", "FLOAT DEFAULT 0.0"),
    ("generated_insights", "confidence_score", "FLOAT DEFAULT 1.0", "FLOAT DEFAULT 1.0"),
    ("generated_insights", "status", "VARCHAR DEFAULT 'active'", "VARCHAR(50) DEFAULT 'active'"),
    ("recommendations", "action_step", "TEXT", "TEXT"),
    ("recommendations", "priority", "VARCHAR DEFAULT 'medium'", "VARCHAR(20) DEFAULT 'medium'"),
    ("recommendations", "action_type", "VARCHAR DEFAULT 'general'", "VARCHAR(50) DEFAULT 'general'"),
    ("recommendations", "action_url", "VARCHAR", "VARCHAR(255)"),
    ("recommendations", "status", "VARCHAR DEFAULT 'pending'", "VARCHAR(50) DEFAULT 'pending'"),
    # Phase 4 - Stage 4A: Column Metadata constraints
    ("column_metadata", "is_primary_key", "BOOLEAN DEFAULT 0", "BOOLEAN DEFAULT FALSE"),
    ("column_metadata", "is_foreign_key", "BOOLEAN DEFAULT 0", "BOOLEAN DEFAULT FALSE"),
    ("column_metadata", "foreign_key_target", "VARCHAR", "VARCHAR(255)"),
    # Phase 4 - Stage 4B: Executed Queries extensions
    ("executed_queries", "tenant_id", "INTEGER", "INTEGER"),
    ("executed_queries", "user_id", "INTEGER", "INTEGER"),
    ("executed_queries", "database_id", "INTEGER", "INTEGER"),
    ("executed_queries", "message_id", "INTEGER", "INTEGER"),
    ("executed_queries", "raw_query", "TEXT", "TEXT"),
    ("executed_queries", "sql_generated", "TEXT", "TEXT"),
    ("executed_queries", "execution_time_ms", "FLOAT DEFAULT 0.0", "FLOAT DEFAULT 0.0"),
    ("executed_queries", "rows_returned", "INTEGER DEFAULT 0", "INTEGER DEFAULT 0"),
    ("executed_queries", "status", "VARCHAR DEFAULT 'success'", "VARCHAR(50) DEFAULT 'success'"),
    ("executed_queries", "was_successful", "BOOLEAN DEFAULT 1", "BOOLEAN DEFAULT TRUE"),
    ("executed_queries", "error_message", "TEXT", "TEXT"),
    ("executed_queries", "executed_at", "DATETIME", "TIMESTAMP WITH TIME ZONE"),
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

            # Ensure composite index on query_logs (widget_key_id, created_at)
            if "query_logs" in existing_tables:
                existing_indexes = {idx["name"] for idx in inspector.get_indexes("query_logs")}
                if "idx_query_logs_widget_key_created" not in existing_indexes:
                    try:
                        conn.execute(text('CREATE INDEX IF NOT EXISTS "idx_query_logs_widget_key_created" ON "query_logs" ("widget_key_id", "created_at")'))
                    except Exception as ex:
                        logger.debug(f"[MIGRATION] Index creation notice: {ex}")
    except Exception as e:
        logger.warning(f"[MIGRATION] Schema auto-sync check encountered: {e}")
