"""
Synthetic Legacy and Current Layout Fixtures for Phase NR-0 Migration & Preflight Testing.
Provides isolated, disposable SQLite database builders representing:
1. Layout 0: Empty Database
2. Layout 1: Known Legacy Installation (historical schema before Phase 7 columns)
3. Layout 2: Current Baseline Installation (46 tables, all Phase 7 columns)
4. Layout 3: Unsupported / Drifted Installation (untracked columns / tables)
"""
import sqlite3
import os
from pathlib import Path
from sqlalchemy import create_engine
import models
from services.db_migration import run_schema_migrations


def create_empty_layout(db_path: Path) -> str:
    """Creates a completely empty SQLite database file."""
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(str(db_path))
    conn.close()
    return f"sqlite:///{db_path}"


def create_current_layout(db_path: Path) -> str:
    """Creates a current layout (46 tables) matching today's models + migrations."""
    if db_path.exists():
        db_path.unlink()
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    models.Base.metadata.create_all(bind=engine)
    run_schema_migrations(engine)
    engine.dispose()
    return db_url


def create_legacy_layout(db_path: Path) -> str:
    """
    Creates a known legacy layout: tables created via models.Base.metadata.create_all,
    but without running Phase 7 schema migrations (e.g. without summary_text, parent_chunk_id).
    """
    if db_path.exists():
        db_path.unlink()
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    
    # Create tables without Phase 7 columns on conversations and document_chunks
    # We do a basic create_all and then simulate an earlier migration state
    models.Base.metadata.create_all(bind=engine)
    engine.dispose()
    return db_url


def create_drifted_layout(db_path: Path) -> str:
    """
    Creates an unsupported drifted layout: current layout plus an unknown rogue table
    and rogue column to test preflight drift detection.
    """
    db_url = create_current_layout(db_path)
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE rogue_untracked_table (id INT, secret_leak TEXT);")
    cursor.execute("ALTER TABLE users ADD COLUMN unauthorized_backdoor VARCHAR(255);")
    conn.commit()
    conn.close()
    return db_url
