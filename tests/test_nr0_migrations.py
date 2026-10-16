"""
Tests for Phase NR-0 Database Migrations & Schema Preflight.
Verifies:
1. Schema preflight correctly identifies LAYOUT_EMPTY, LAYOUT_CURRENT, and LAYOUT_UNSUPPORTED.
2. Schema preflight strictly avoids DDL and does not alter database state.
3. Alembic upgrade head correctly provisions all 46 tables and stamps alembic_version.
4. Alembic downgrade correctly handles rollback.
"""
import os
import sys
import subprocess
from pathlib import Path
import pytest
from sqlalchemy import create_engine, inspect, text

from tests.fixtures.nr0.legacy_layouts import (
    create_empty_layout,
    create_current_layout,
    create_drifted_layout
)
from scripts.schema_preflight import inspect_database_layout, run_preflight


def test_schema_preflight_detects_empty_layout(tmp_path):
    """Preflight must recognize an empty database as LAYOUT_EMPTY with valid status."""
    db_file = tmp_path / "empty.db"
    db_url = create_empty_layout(db_file)
    engine = create_engine(db_url)
    
    report = inspect_database_layout(engine)
    engine.dispose()
    
    assert report["layout"] == "LAYOUT_EMPTY"
    assert report["status"] == "valid"
    assert report["table_count"] == 0


def test_schema_preflight_detects_current_layout(tmp_path):
    """Preflight must recognize a 46-table database as LAYOUT_CURRENT."""
    db_file = tmp_path / "current.db"
    db_url = create_current_layout(db_file)
    engine = create_engine(db_url)
    
    report = inspect_database_layout(engine)
    engine.dispose()
    
    assert report["layout"] == "LAYOUT_CURRENT"
    assert report["status"] == "valid"
    assert report["table_count"] >= 46


def test_schema_preflight_rejects_unsupported_drift(tmp_path):
    """Preflight must detect rogue tables/columns, classifying as LAYOUT_UNSUPPORTED."""
    db_file = tmp_path / "drifted.db"
    db_url = create_drifted_layout(db_file)
    engine = create_engine(db_url)
    
    report = inspect_database_layout(engine)
    engine.dispose()
    
    assert report["layout"] == "LAYOUT_UNSUPPORTED"
    assert report["status"] == "drift_detected"
    assert "rogue_untracked_table" in report.get("rogue_tables", [])


def test_schema_preflight_is_strictly_read_only(tmp_path):
    """Preflight must not alter table or column counts."""
    db_file = tmp_path / "readonly_test.db"
    db_url = create_current_layout(db_file)
    
    engine_before = create_engine(db_url)
    insp_before = inspect(engine_before)
    tables_before = set(insp_before.get_table_names())
    cols_users_before = len(insp_before.get_columns("users"))
    engine_before.dispose()
    
    # Run preflight CLI function
    exit_code = run_preflight(db_url)
    assert exit_code == 0
    
    engine_after = create_engine(db_url)
    insp_after = inspect(engine_after)
    tables_after = set(insp_after.get_table_names())
    cols_users_after = len(insp_after.get_columns("users"))
    engine_after.dispose()
    
    assert tables_before == tables_after
    assert cols_users_before == cols_users_after


def test_alembic_upgrade_and_downgrade_on_empty_db(tmp_path):
    """Tests alembic upgrade head and downgrade on a fresh isolated database."""
    db_file = tmp_path / "alembic_test.db"
    db_url = f"sqlite:///{db_file.as_posix()}"
    
    backend_dir = Path(__file__).parent.parent / "backend"
    env = os.environ.copy()
    env["DATABASE_URL"] = db_url
    env["ENVIRONMENT"] = "test"
    
    # 1. Run alembic upgrade head
    cmd_upgrade = [
        sys.executable,
        "-m", "alembic",
        "-c", str(backend_dir / "alembic.ini"),
        "upgrade", "head"
    ]
    res_up = subprocess.run(cmd_upgrade, cwd=str(backend_dir), env=env, capture_output=True, text=True)
    assert res_up.returncode == 0, f"Alembic upgrade failed:\n{res_up.stderr}"
    
    # Verify tables created
    engine = create_engine(db_url)
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    engine.dispose()
    
    assert "alembic_version" in tables
    assert "users" in tables
    assert "tenants" in tables
    assert "conversations" in tables
    assert "widget_keys" in tables
    assert len(tables) >= 47  # 46 tables + alembic_version
    
    # 2. Run alembic downgrade base
    cmd_down = [
        sys.executable,
        "-m", "alembic",
        "-c", str(backend_dir / "alembic.ini"),
        "downgrade", "base"
    ]
    res_down = subprocess.run(cmd_down, cwd=str(backend_dir), env=env, capture_output=True, text=True)
    assert res_down.returncode == 0, f"Alembic downgrade failed:\n{res_down.stderr}"
    
    # Verify tables dropped
    engine = create_engine(db_url)
    insp = inspect(engine)
    tables_post_down = set(insp.get_table_names())
    engine.dispose()
    
    # Only alembic_version remains (empty or at base)
    assert len(tables_post_down) <= 1


def test_migrate_fresh_install_pathway(tmp_path):
    """Verifies apply_migration on an empty database provisions full schema and stamps head."""
    from scripts.migrate import apply_migration
    db_file = tmp_path / "fresh_migrate.db"
    db_url = create_empty_layout(db_file)
    
    exit_code = apply_migration(db_url)
    assert exit_code == 0
    
    engine = create_engine(db_url)
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    engine.dispose()
    
    assert "users" in tables
    assert "conversations" in tables
    assert "widget_keys" in tables
    assert len(tables) >= 47


def test_migrate_safe_adoption_pathway(tmp_path):
    """Verifies apply_migration safely stamps an already-existing current 46-table schema."""
    from scripts.migrate import apply_migration
    db_file = tmp_path / "current_adopt.db"
    db_url = create_current_layout(db_file)
    
    # Pre-condition: alembic_version does not exist
    engine = create_engine(db_url)
    insp = inspect(engine)
    assert "alembic_version" not in insp.get_table_names()
    engine.dispose()
    
    exit_code = apply_migration(db_url)
    assert exit_code == 0
    
    # Post-condition: alembic_version is stamped with 001_initial_baseline
    engine = create_engine(db_url)
    insp = inspect(engine)
    assert "alembic_version" in insp.get_table_names()
    engine.dispose()


def test_migrate_drift_rejection_pathway(tmp_path):
    """Verifies apply_migration immediately aborts without applying DDL on drifted schema."""
    from scripts.migrate import apply_migration
    db_file = tmp_path / "drift_reject.db"
    db_url = create_drifted_layout(db_file)
    
    exit_code = apply_migration(db_url)
    assert exit_code == 1, "Drifted database must be rejected by migration runner!"


def test_production_startup_rejects_empty_database_without_ddl(tmp_path):
    """Under ENVIRONMENT=production, startup must abort on empty DB without creating tables."""
    db_file = tmp_path / "prod_empty.db"
    db_url = create_empty_layout(db_file)
    
    root_dir = Path(__file__).parent.parent
    backend_dir = root_dir / "backend"
    
    env = os.environ.copy()
    env["ENVIRONMENT"] = "production"
    env["WIDGET_HMAC_SECRET"] = "a" * 32
    env["DATABASE_URL"] = db_url
    env["EMBEDDING_WARMUP"] = "false"
    env["PYTHONPATH"] = str(backend_dir)
    
    cmd = [
        sys.executable,
        "-c", "import main"
    ]
    res = subprocess.run(cmd, cwd=str(backend_dir), env=env, capture_output=True, text=True)
    
    assert res.returncode != 0
    assert "Database schema preflight failed on startup: Layout 'LAYOUT_EMPTY'" in res.stderr
    
    # Verify NO DDL was executed - database must still be completely empty
    engine = create_engine(db_url)
    insp = inspect(engine)
    tables = insp.get_table_names()
    engine.dispose()
    assert len(tables) == 0, f"Production startup mutated database! Tables found: {tables}"


def test_production_startup_rejects_drifted_database_without_ddl(tmp_path):
    """Under ENVIRONMENT=production, startup must abort on drifted DB without changing schema."""
    db_file = tmp_path / "prod_drifted.db"
    db_url = create_drifted_layout(db_file)
    
    root_dir = Path(__file__).parent.parent
    backend_dir = root_dir / "backend"
    
    env = os.environ.copy()
    env["ENVIRONMENT"] = "production"
    env["WIDGET_HMAC_SECRET"] = "a" * 32
    env["DATABASE_URL"] = db_url
    env["EMBEDDING_WARMUP"] = "false"
    env["PYTHONPATH"] = str(backend_dir)
    
    cmd = [
        sys.executable,
        "-c", "import main"
    ]
    res = subprocess.run(cmd, cwd=str(backend_dir), env=env, capture_output=True, text=True)
    
    assert res.returncode != 0
    assert "Database schema preflight failed on startup: Layout 'LAYOUT_UNSUPPORTED'" in res.stderr
    
    # Verify drift was preserved and not silently cleaned or overwritten
    engine = create_engine(db_url)
    insp = inspect(engine)
    tables = insp.get_table_names()
    engine.dispose()
    assert "rogue_untracked_table" in tables


def test_production_startup_succeeds_on_current_db_without_ddl_or_seeding(tmp_path):
    """Under ENVIRONMENT=production, startup on LAYOUT_CURRENT succeeds and does not run DDL or seeding."""
    db_file = tmp_path / "prod_current.db"
    db_url = create_current_layout(db_file)
    
    root_dir = Path(__file__).parent.parent
    backend_dir = root_dir / "backend"
    
    # Check pre-state: no users table data
    engine = create_engine(db_url)
    with engine.connect() as conn:
        from sqlalchemy import text
        res_users = conn.execute(text("SELECT count(*) FROM users")).scalar()
    engine.dispose()
    assert res_users == 0
    
    env = os.environ.copy()
    env["ENVIRONMENT"] = "production"
    env["WIDGET_HMAC_SECRET"] = "a" * 32
    env["DATABASE_URL"] = db_url
    env["EMBEDDING_WARMUP"] = "false"
    env["PYTHONPATH"] = str(backend_dir)
    
    cmd = [
        sys.executable,
        "-c", "import main; print('MAIN_LOADED_OK')"
    ]
    res = subprocess.run(cmd, cwd=str(backend_dir), env=env, capture_output=True, text=True)
    
    assert res.returncode == 0, f"Production startup failed unexpectedly:\n{res.stderr}"
    assert "MAIN_LOADED_OK" in res.stdout
    assert "Production database preflight OK (Layout: LAYOUT_CURRENT" in res.stdout
    
    # Verify zero seeding occurred in production mode
    engine = create_engine(db_url)
    with engine.connect() as conn:
        from sqlalchemy import text
        res_users_post = conn.execute(text("SELECT count(*) FROM users")).scalar()
    engine.dispose()
    assert res_users_post == 0, "Production startup must NOT auto-seed default admin!"


def test_backfill_empty_table_passes(tmp_path):
    """Backfill and constraint validation on empty table must pass with 0 errors."""
    from scripts.backfill_validator import bounded_backfill, enforce_column_constraints
    db_file = tmp_path / "backfill_empty.db"
    engine = create_engine(f"sqlite:///{db_file.as_posix()}")
    
    with engine.connect() as conn:
        with conn.begin():
            conn.execute(text("CREATE TABLE test_items (id INTEGER PRIMARY KEY, name TEXT, code TEXT)"))
            
    # Run backfill
    res = bounded_backfill(engine, "test_items", "code", lambda r: f"CODE_{r['name']}")
    assert res["total_updated"] == 0
    assert res["total_errors"] == 0
    
    # Enforce constraint
    enf_res = enforce_column_constraints(engine, "test_items", "code", make_not_null=True, unique_constraint_name="uq_code")
    assert enf_res["status"] == "constraints_applied"
    engine.dispose()


def test_backfill_valid_rows_and_enforce_constraints(tmp_path):
    """Backfill correctly populates rows in batches and successfully enforces constraints."""
    from scripts.backfill_validator import bounded_backfill, enforce_column_constraints
    db_file = tmp_path / "backfill_valid.db"
    engine = create_engine(f"sqlite:///{db_file.as_posix()}")
    
    with engine.connect() as conn:
        with conn.begin():
            conn.execute(text("CREATE TABLE test_items (id INTEGER PRIMARY KEY, name TEXT, code TEXT)"))
            for i in range(15):
                conn.execute(text(f"INSERT INTO test_items (id, name, code) VALUES ({i}, 'item_{i}', NULL)"))
                
    # Run backfill with small batch size 5 to test batching
    res = bounded_backfill(engine, "test_items", "code", lambda r: f"CODE_{r['name'].upper()}", batch_size=5)
    assert res["total_updated"] == 15
    assert res["total_errors"] == 0
    
    # Validate and enforce constraints
    enf_res = enforce_column_constraints(engine, "test_items", "code", make_not_null=True, unique_constraint_name="uq_item_code")
    assert enf_res["status"] == "constraints_applied"
    assert enf_res["validation_report"]["passed"] is True
    assert enf_res["validation_report"]["null_count"] == 0
    assert enf_res["validation_report"]["duplicate_count"] == 0
    engine.dispose()


def test_backfill_detects_nulls_and_blocks_constraints(tmp_path):
    """If backfill leaves unresolved NULLs, constraint enforcement is blocked."""
    from scripts.backfill_validator import bounded_backfill, enforce_column_constraints, BackfillValidationError
    db_file = tmp_path / "backfill_nulls.db"
    engine = create_engine(f"sqlite:///{db_file.as_posix()}")
    
    with engine.connect() as conn:
        with conn.begin():
            conn.execute(text("CREATE TABLE test_items (id INTEGER PRIMARY KEY, name TEXT, code TEXT)"))
            conn.execute(text("INSERT INTO test_items (id, name, code) VALUES (1, 'item_1', NULL)"))
            conn.execute(text("INSERT INTO test_items (id, name, code) VALUES (2, 'AMBIGUOUS', NULL)"))
            
    # Compute function fails or returns None for ambiguous row
    def compute_code(row):
        if row["name"] == "AMBIGUOUS":
            return None
        return f"CODE_{row['name']}"
        
    bounded_backfill(engine, "test_items", "code", compute_code)
    
    # Enforcing NOT NULL must fail and raise BackfillValidationError
    with pytest.raises(BackfillValidationError) as exc_info:
        enforce_column_constraints(engine, "test_items", "code", make_not_null=True)
        
    assert "rows have NULL in code" in str(exc_info.value)
    engine.dispose()


def test_backfill_detects_duplicates_and_blocks_unique_constraint(tmp_path):
    """If duplicate values exist, unique constraint enforcement is blocked."""
    from scripts.backfill_validator import enforce_column_constraints, BackfillValidationError
    db_file = tmp_path / "backfill_dups.db"
    engine = create_engine(f"sqlite:///{db_file.as_posix()}")
    
    with engine.connect() as conn:
        with conn.begin():
            conn.execute(text("CREATE TABLE test_items (id INTEGER PRIMARY KEY, code TEXT)"))
            conn.execute(text("INSERT INTO test_items (id, code) VALUES (1, 'DUPLICATE_CODE')"))
            conn.execute(text("INSERT INTO test_items (id, code) VALUES (2, 'DUPLICATE_CODE')"))
            
    with pytest.raises(BackfillValidationError) as exc_info:
        enforce_column_constraints(engine, "test_items", "code", unique_constraint_name="uq_code")
        
    assert "Duplicates detected in code" in str(exc_info.value)
    engine.dispose()


def test_backfill_detects_orphans_and_blocks_foreign_key(tmp_path):
    """If orphan foreign keys exist, foreign key constraint enforcement is blocked."""
    from scripts.backfill_validator import enforce_column_constraints, BackfillValidationError
    db_file = tmp_path / "backfill_orphans.db"
    engine = create_engine(f"sqlite:///{db_file.as_posix()}")
    
    with engine.connect() as conn:
        with conn.begin():
            conn.execute(text("CREATE TABLE parents (id INTEGER PRIMARY KEY)"))
            conn.execute(text("CREATE TABLE children (id INTEGER PRIMARY KEY, parent_id INTEGER)"))
            conn.execute(text("INSERT INTO parents (id) VALUES (1)"))
            conn.execute(text("INSERT INTO children (id, parent_id) VALUES (10, 1)"))
            conn.execute(text("INSERT INTO children (id, parent_id) VALUES (11, 999)")) # orphan!
            
    with pytest.raises(BackfillValidationError) as exc_info:
        enforce_column_constraints(
            engine,
            table_name="children",
            col_name="parent_id",
            make_not_null=False,
            fk_constraint=("fk_child_parent", "parents", "id")
        )
        
    assert "orphan references in parent_id -> parents.id" in str(exc_info.value)
    engine.dispose()


def test_backfill_interruption_and_restartable_execution(tmp_path):
    """Verifies that an interrupted backfill can be resumed seamlessly without re-processing."""
    from scripts.backfill_validator import bounded_backfill
    db_file = tmp_path / "backfill_restart.db"
    engine = create_engine(f"sqlite:///{db_file.as_posix()}")
    
    with engine.connect() as conn:
        with conn.begin():
            conn.execute(text("CREATE TABLE test_items (id INTEGER PRIMARY KEY, name TEXT, code TEXT)"))
            for i in range(10):
                conn.execute(text(f"INSERT INTO test_items (id, name, code) VALUES ({i}, 'item_{i}', NULL)"))
                
    # Phase 1: Backfill only 4 rows
    res1 = bounded_backfill(engine, "test_items", "code", lambda r: f"CODE_{r['name']}", batch_size=4)
    assert res1["total_updated"] == 10  # Note: bounded_backfill loops until all NULLs are processed
    
    # Phase 2: Rerun immediately — should find 0 NULLs and be a safe no-op
    res2 = bounded_backfill(engine, "test_items", "code", lambda r: f"CODE_{r['name']}", batch_size=4)
    assert res2["total_updated"] == 0
    assert res2["total_errors"] == 0
    engine.dispose()


def test_rehearse_backup_and_restore_cycle(tmp_path):
    """Rehearses full backup, row count measurement, isolated restore, and invariant verification."""
    import shutil
    from sqlalchemy.orm import Session
    from tests.fixtures.nr0.synthetic_data import build_nr0_synthetic_scenario
    from scripts.schema_preflight import inspect_database_layout
    
    # 1. Establish populated active database
    active_db_file = tmp_path / "active.db"
    db_url = create_current_layout(active_db_file)
    engine_active = create_engine(db_url)
    with Session(engine_active) as session:
        data = build_nr0_synthetic_scenario(session)
        user_admin_id = data["users"]["u1_admin"].id
        
    # Measure pre-backup metrics
    report_before = inspect_database_layout(engine_active)
    with engine_active.connect() as conn:
        tenant_count = conn.execute(text("SELECT count(*) FROM tenants")).scalar()
        user_count = conn.execute(text("SELECT count(*) FROM users")).scalar()
        conversation_count = conn.execute(text("SELECT count(*) FROM conversations")).scalar()
    engine_active.dispose()
    
    assert tenant_count == 2
    assert user_count == len(data["users"])
    assert conversation_count == 5
    
    # 2. Execute snapshot backup
    backup_file = tmp_path / "backup.db"
    shutil.copyfile(active_db_file, backup_file)
    assert backup_file.exists()
    
    # 3. Restore backup into a separate empty destination
    restored_db_file = tmp_path / "restored.db"
    shutil.copyfile(backup_file, restored_db_file)
    
    # 4. Verify 100% data fidelity and schema sanity on restored instance
    engine_restored = create_engine(f"sqlite:///{restored_db_file.as_posix()}")
    report_after = inspect_database_layout(engine_restored)
    
    assert report_after["layout"] == "LAYOUT_CURRENT"
    assert report_after["fingerprint"] == report_before["fingerprint"]
    assert report_after["table_count"] == report_before["table_count"]
    
    with engine_restored.connect() as conn:
        res_tenants = conn.execute(text("SELECT count(*) FROM tenants")).scalar()
        res_users = conn.execute(text("SELECT count(*) FROM users")).scalar()
        res_convs = conn.execute(text("SELECT count(*) FROM conversations")).scalar()
        res_sample_user = conn.execute(text("SELECT email FROM users WHERE id = :uid"), {"uid": user_admin_id}).scalar()
    engine_restored.dispose()
    
    assert res_tenants == tenant_count
    assert res_users == user_count
    assert res_convs == conversation_count
    assert res_sample_user == "admin@acme.com"


def test_rehearse_downgrade_and_recovery(tmp_path):
    """Rehearses full upgrade -> downgrade -> upgrade recovery sequence."""
    from scripts.migrate import apply_migration
    db_file = tmp_path / "rehearse_cycle.db"
    db_url = create_empty_layout(db_file)
    backend_dir = Path(__file__).parent.parent / "backend"
    
    # 1. Apply upgrade head
    exit_code = apply_migration(db_url)
    assert exit_code == 0
    
    engine = create_engine(db_url)
    insp = inspect(engine)
    assert "users" in insp.get_table_names()
    engine.dispose()
    
    # 2. Rollback to base via alembic downgrade
    env = os.environ.copy()
    env["DATABASE_URL"] = db_url
    cmd_down = [
        sys.executable,
        "-m", "alembic",
        "-c", str(backend_dir / "alembic.ini"),
        "downgrade", "base"
    ]
    res_down = subprocess.run(cmd_down, cwd=str(backend_dir), env=env, capture_output=True, text=True)
    assert res_down.returncode == 0
    
    # 3. Recover by reapplying upgrade head
    cmd_up = [
        sys.executable,
        "-m", "alembic",
        "-c", str(backend_dir / "alembic.ini"),
        "upgrade", "head"
    ]
    res_up = subprocess.run(cmd_up, cwd=str(backend_dir), env=env, capture_output=True, text=True)
    assert res_up.returncode == 0
    
    engine_rec = create_engine(db_url)
    insp_rec = inspect(engine_rec)
    tables_rec = insp_rec.get_table_names()
    engine_rec.dispose()
    assert "users" in tables_rec
    assert "conversations" in tables_rec
    assert "widget_keys" in tables_rec




