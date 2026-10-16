"""
DataSpeakAI Controlled Migration & Schema Adoption Entrypoint.

Provides safe, audited database migration management:
- Executes read-only preflight before any DDL operations.
- Rejects unknown drift or corrupted schemas without modifying state.
- Supports fresh installation (LAYOUT_EMPTY -> alembic upgrade head).
- Supports verified adoption (LAYOUT_CURRENT -> stamp 001_initial_baseline).
- Supports legacy upgrade (LAYOUT_LEGACY -> legacy sync -> stamp).
- Zero-downtime, safe execution for deployment pipelines and local operations.
"""
import os
import sys
import argparse
import logging
from pathlib import Path
from sqlalchemy import create_engine
from alembic.config import Config
from alembic import command

# Ensure backend root is on sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from scripts.schema_preflight import inspect_database_layout, redact_url
from services.db_migration import run_schema_migrations

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("dataspeak.migrate")


def get_alembic_config(database_url: str) -> Config:
    """Creates an Alembic Config object pointed to backend/alembic.ini."""
    ini_path = Path(backend_dir) / "alembic.ini"
    cfg = Config(str(ini_path))
    cfg.set_main_option("script_location", str(Path(backend_dir) / "migrations"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def apply_migration(database_url: str) -> int:
    """
    Executes controlled migration based on preflight layout classification.
    Returns 0 on success, 1 on error/rejection.
    """
    redacted = redact_url(database_url)
    logger.info(f"[MIGRATE] Preflight inspection on {redacted}")
    
    engine = create_engine(database_url)
    try:
        report = inspect_database_layout(engine)
    finally:
        engine.dispose()
        
    layout = report["layout"]
    logger.info(f"[MIGRATE] Detected layout: {layout} (Alembic: {report['alembic_revision']})")
    
    alembic_cfg = get_alembic_config(database_url)
    
    # Path 1: Unsupported / Drifted -> ABORT
    if layout == "LAYOUT_UNSUPPORTED":
        logger.error("[MIGRATE] REJECTED: Database schema has unsupported drift. No DDL applied.")
        if "rogue_tables" in report:
            logger.error(f"[MIGRATE] Rogue tables: {report['rogue_tables']}")
        if "rogue_columns" in report:
            logger.error(f"[MIGRATE] Rogue columns: {report['rogue_columns']}")
        return 1

    # Path 2: Empty Database -> Fresh Install via Alembic Head
    if layout == "LAYOUT_EMPTY":
        logger.info("[MIGRATE] Empty database detected. Running fresh install: alembic upgrade head")
        command.upgrade(alembic_cfg, "head")
        logger.info("[MIGRATE] Fresh install completed successfully.")
        return 0

    # Path 3: Current Reconciled Database -> Safe Adoption (Stamp baseline if not yet stamped)
    if layout == "LAYOUT_CURRENT":
        if report["alembic_revision"] == "none":
            logger.info("[MIGRATE] Current 46-table schema detected without revision tracking. Stamping 001_initial_baseline.")
            command.stamp(alembic_cfg, "001_initial_baseline")
            logger.info("[MIGRATE] Schema successfully stamped into version control.")
        else:
            logger.info(f"[MIGRATE] Schema already under revision control (rev: {report['alembic_revision']}). Running upgrade head.")
            command.upgrade(alembic_cfg, "head")
        return 0

    # Path 4: Known Legacy Database -> Upgrade columns then stamp
    if layout == "LAYOUT_LEGACY":
        logger.info(f"[MIGRATE] Recognized legacy database (missing tables: {len(report.get('missing_tables', []))}).")
        logger.info("[MIGRATE] Running transitional schema synchronizer.")
        eng = create_engine(database_url)
        try:
            import models
            models.Base.metadata.create_all(bind=eng)
            run_schema_migrations(eng)
        finally:
            eng.dispose()
            
        logger.info("[MIGRATE] Transitional sync complete. Stamping baseline revision.")
        command.stamp(alembic_cfg, "001_initial_baseline")
        logger.info("[MIGRATE] Legacy database successfully upgraded and brought into version control.")
        return 0

    logger.error(f"[MIGRATE] Unexpected layout: {layout}")
    return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DataSpeakAI Controlled Migration Utility")
    parser.add_argument("action", choices=["upgrade", "check", "stamp"], default="upgrade", nargs="?")
    parser.add_argument("--database-url", default=None, help="Database connection URL")
    args = parser.parse_args()
    
    url = args.database_url or os.getenv("DATABASE_URL", "sqlite:///./app.db")
    
    if args.action == "check":
        from scripts.schema_preflight import run_preflight
        sys.exit(run_preflight(url))
    elif args.action == "upgrade":
        sys.exit(apply_migration(url))
    elif args.action == "stamp":
        cfg = get_alembic_config(url)
        command.stamp(cfg, "head")
        sys.exit(0)
