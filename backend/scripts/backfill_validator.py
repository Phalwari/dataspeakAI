"""
DataSpeakAI Additive Migration, Bounded Backfill & Constraint Validation Utility.

Implements the Expand -> Backfill -> Validate -> Constrain migration pattern:
1. Expand: Add additive nullable/defaulted columns or tables without breaking old readers.
2. Backfill: Bounded, restartable batch execution; handles ambiguous/errored rows safely.
3. Validate: Verifies 0 nulls, 0 duplicates, and 0 orphan foreign keys before constraint enforcement.
4. Constrain: Enforces NOT NULL, UNIQUE, or FOREIGN KEY constraints only when validation succeeds.
5. Safety: Dialect-aware (SQLite batch mode vs PostgreSQL ALTER TABLE); zero credential leakage.
"""
import logging
from typing import Callable, Any, Dict, List, Optional, Tuple
from sqlalchemy import create_engine, text, Engine, inspect

logger = logging.getLogger("dataspeak.backfill")


class BackfillValidationError(Exception):
    """Raised when data invariants fail validation prior to constraint enforcement."""
    def __init__(self, message: str, report: Dict[str, Any]):
        super().__init__(message)
        self.report = report


def bounded_backfill(
    engine: Engine,
    table_name: str,
    target_col: str,
    compute_val_fn: Callable[[Dict[str, Any]], Any],
    batch_size: int = 500,
    key_col: str = "id",
    source_cols: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Executes restartable, bounded batch backfill for target_col where target_col IS NULL.
    
    Args:
        engine: SQLAlchemy Engine
        table_name: Target table name
        target_col: Column to backfill
        compute_val_fn: Callback taking row dictionary and returning computed value
        batch_size: Number of records per transaction batch
        key_col: Primary key or deterministic cursor column
        source_cols: Columns needed by compute_val_fn (None for all columns)
    
    Returns:
        Dict with total_updated, total_errors, and error_details
    """
    cols_to_fetch = ", ".join(source_cols) if source_cols else "*"
    total_updated = 0
    errors = []
    
    logger.info(f"[BACKFILL] Starting bounded backfill on {table_name}.{target_col} (batch_size={batch_size})")
    
    last_key = None
    while True:
        with engine.connect() as conn:
            if last_key is None:
                query = text(
                    f"SELECT {cols_to_fetch} FROM {table_name} "
                    f"WHERE {target_col} IS NULL "
                    f"ORDER BY {key_col} "
                    f"LIMIT :limit"
                )
                params = {"limit": batch_size}
            else:
                query = text(
                    f"SELECT {cols_to_fetch} FROM {table_name} "
                    f"WHERE {target_col} IS NULL AND {key_col} > :last_key "
                    f"ORDER BY {key_col} "
                    f"LIMIT :limit"
                )
                params = {"limit": batch_size, "last_key": last_key}

            rows = conn.execute(query, params).mappings().all()
            if not rows:
                break
                
            last_key = rows[-1][key_col]
            batch_updates = []
            for row in rows:
                row_dict = dict(row)
                row_key = row_dict[key_col]
                try:
                    new_val = compute_val_fn(row_dict)
                    if new_val is not None:
                        batch_updates.append({"key": row_key, "val": new_val})
                    else:
                        errors.append({
                            "key": str(row_key),
                            "error": "compute_val_fn returned None"
                        })
                except Exception as e:
                    errors.append({
                        "key": str(row_key),
                        "error": str(e)
                    })
                    logger.warning(f"[BACKFILL] Error computing backfill for {table_name}.{key_col}={row_key}: {e}")

            # Apply batch updates in transaction
            if batch_updates:
                for upd in batch_updates:
                    update_stmt = text(
                        f"UPDATE {table_name} SET {target_col} = :val WHERE {key_col} = :key"
                    )
                    conn.execute(update_stmt, {"val": upd["val"], "key": upd["key"]})
                conn.commit()
                total_updated += len(batch_updates)

    logger.info(f"[BACKFILL] Completed: {total_updated} updated, {len(errors)} unresolved.")
    return {
        "table": table_name,
        "target_col": target_col,
        "total_updated": total_updated,
        "total_errors": len(errors),
        "errors": errors[:50]  # Cap error list
    }


def validate_column_invariants(
    engine: Engine,
    table_name: str,
    col_name: str,
    check_not_null: bool = True,
    check_unique: bool = False,
    foreign_key_target: Optional[Tuple[str, str]] = None
) -> Dict[str, Any]:
    """
    Validates data integrity on col_name before applying NOT NULL, UNIQUE, or FOREIGN KEY constraints.
    
    Args:
        engine: SQLAlchemy Engine
        table_name: Table to check
        col_name: Column to validate
        check_not_null: Whether to verify 0 null values
        check_unique: Whether to verify 0 duplicate values
        foreign_key_target: Optional (parent_table, parent_col) to verify 0 orphan values
        
    Returns:
        Dict with passed status and counts
    """
    with engine.connect() as conn:
        # 1. Total row count
        count_res = conn.execute(text(f"SELECT count(*) FROM {table_name}")).scalar()
        total_rows = count_res or 0
        
        # 2. Null count
        null_count = 0
        if check_not_null:
            null_res = conn.execute(
                text(f"SELECT count(*) FROM {table_name} WHERE {col_name} IS NULL")
            ).scalar()
            null_count = null_res or 0
            
        # 3. Duplicate count
        duplicate_count = 0
        duplicate_samples = []
        if check_unique and total_rows > 0:
            dup_query = text(
                f"SELECT {col_name}, count(*) as cnt FROM {table_name} "
                f"WHERE {col_name} IS NOT NULL "
                f"GROUP BY {col_name} HAVING count(*) > 1 "
                f"LIMIT 10"
            )
            dup_rows = conn.execute(dup_query).fetchall()
            duplicate_count = len(dup_rows)
            duplicate_samples = [str(r[0]) for r in dup_rows]
            
        # 4. Orphan foreign key count
        orphan_count = 0
        orphan_samples = []
        if foreign_key_target and total_rows > 0:
            parent_table, parent_col = foreign_key_target
            orphan_query = text(
                f"SELECT t.{col_name} FROM {table_name} t "
                f"LEFT JOIN {parent_table} p ON t.{col_name} = p.{parent_col} "
                f"WHERE t.{col_name} IS NOT NULL AND p.{parent_col} IS NULL "
                f"LIMIT 10"
            )
            orphan_rows = conn.execute(orphan_query).fetchall()
            orphan_count = len(orphan_rows)
            orphan_samples = [str(r[0]) for r in orphan_rows]

    # Evaluate validation outcome
    failures = []
    if check_not_null and null_count > 0:
        failures.append(f"{null_count} rows have NULL in {col_name}")
    if check_unique and duplicate_count > 0:
        failures.append(f"Duplicates detected in {col_name} (samples: {duplicate_samples})")
    if foreign_key_target and orphan_count > 0:
        failures.append(f"{orphan_count} orphan references in {col_name} -> {parent_table}.{parent_col}")

    passed = len(failures) == 0
    return {
        "table": table_name,
        "column": col_name,
        "total_rows": total_rows,
        "passed": passed,
        "null_count": null_count,
        "duplicate_count": duplicate_count,
        "orphan_count": orphan_count,
        "failures": failures
    }


def enforce_column_constraints(
    engine: Engine,
    table_name: str,
    col_name: str,
    make_not_null: bool = True,
    unique_constraint_name: Optional[str] = None,
    fk_constraint: Optional[Tuple[str, str, str]] = None
) -> Dict[str, Any]:
    """
    Enforces constraints on table_name.col_name only after validating data invariants.
    Aborts with BackfillValidationError if validation fails.
    
    Args:
        engine: SQLAlchemy Engine
        table_name: Table name
        col_name: Column name
        make_not_null: Require NOT NULL
        unique_constraint_name: Unique constraint name if enforcing uniqueness
        fk_constraint: Optional tuple of (constraint_name, parent_table, parent_col)
    """
    fk_target = (fk_constraint[1], fk_constraint[2]) if fk_constraint else None
    val_report = validate_column_invariants(
        engine,
        table_name=table_name,
        col_name=col_name,
        check_not_null=make_not_null,
        check_unique=bool(unique_constraint_name),
        foreign_key_target=fk_target
    )
    
    if not val_report["passed"]:
        logger.error(f"[CONSTRAIN] Validation FAILED for {table_name}.{col_name}: {val_report['failures']}")
        raise BackfillValidationError(
            f"Constraint enforcement aborted: {val_report['failures']}",
            report=val_report
        )
        
    dialect = engine.dialect.name
    logger.info(f"[CONSTRAIN] Validation PASSED for {table_name}.{col_name}. Applying constraints (dialect: {dialect}).")
    
    with engine.begin() as conn:
        if dialect == "sqlite":
            # For SQLite, unique index is the safe constraint mechanism without full table copy
            if unique_constraint_name:
                conn.execute(
                    text(f"CREATE UNIQUE INDEX IF NOT EXISTS {unique_constraint_name} ON {table_name} ({col_name})")
                )
            elif dialect == "postgresql":
                if make_not_null:
                    conn.execute(text(f"ALTER TABLE {table_name} ALTER COLUMN {col_name} SET NOT NULL"))
                if unique_constraint_name:
                    conn.execute(
                        text(f"ALTER TABLE {table_name} ADD CONSTRAINT {unique_constraint_name} UNIQUE ({col_name})")
                    )
                if fk_constraint:
                    c_name, p_table, p_col = fk_constraint
                    conn.execute(
                        text(f"ALTER TABLE {table_name} ADD CONSTRAINT {c_name} FOREIGN KEY ({col_name}) REFERENCES {p_table}({p_col})")
                    )
            elif dialect == "mysql":
                if unique_constraint_name:
                    conn.execute(
                        text(f"ALTER TABLE {table_name} ADD CONSTRAINT {unique_constraint_name} UNIQUE ({col_name})")
                    )
    
    return {
        "table": table_name,
        "column": col_name,
        "status": "constraints_applied",
        "validation_report": val_report
    }
