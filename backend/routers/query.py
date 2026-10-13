from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import os
import sys

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import models
import schemas
import logging
from database import get_db
from dependencies import get_current_user
from services import sql_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/query", tags=["query"])


@router.post("", response_model=schemas.NLQueryResponse)
def execute_nl_to_sql_query(
    payload: schemas.NLQueryRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not belong to an active tenant."
        )

    # 1. Verify tenant access to database connection
    if current_user.role == "Admin":
        db_conn = db.query(models.DatabaseConnection).filter(
            models.DatabaseConnection.id == payload.database_id,
            models.DatabaseConnection.tenant_id == current_user.tenant_id
        ).first()
    else:
        db_conn = db.query(models.DatabaseConnection).join(
            models.UserDatabaseAccess,
            models.DatabaseConnection.id == models.UserDatabaseAccess.database_id
        ).filter(
            models.DatabaseConnection.id == payload.database_id,
            models.DatabaseConnection.tenant_id == current_user.tenant_id,
            models.UserDatabaseAccess.user_id == current_user.id
        ).first()

    if not db_conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database connection ID {payload.database_id} not found or access denied."
        )

    # 2. Generate SQL from Natural Language
    gen_result = sql_engine.generate_sql_from_nl(db_conn, payload.query, db)
    generated_sql = gen_result.get("sql", "")
    explanation = gen_result.get("explanation", "")
    gen_error = gen_result.get("error")

    # Helper for logging
    def log_query(status_str: str, exec_ms: float = 0.0, rows_cnt: int = 0, err_msg: str = None):
        try:
            tokens = max(15, len((payload.query or "").split()) * 2 + len((generated_sql or "").split()) * 2 + 30)
            q_log = models.QueryLog(
                tenant_id=current_user.tenant_id,
                user_id=current_user.id,
                database_id=payload.database_id,
                natural_query=payload.query,
                generated_sql=generated_sql,
                status=status_str,
                execution_time_ms=exec_ms,
                rows_returned=rows_cnt,
                tokens_used=tokens,
                error_message=err_msg
            )
            db.add(q_log)

            # Fine-grained Query Auditing & Safety (Phase 4 - Stage 4B)
            exec_q = models.ExecutedQuery(
                tenant_id=current_user.tenant_id,
                user_id=current_user.id,
                database_id=payload.database_id,
                raw_query=payload.query,
                sql_generated=generated_sql,
                execution_time_ms=exec_ms,
                rows_returned=rows_cnt,
                status=status_str,
                was_successful=(status_str == "success"),
                error_message=err_msg
            )
            db.add(exec_q)
            db.flush()

            safety_log = models.QuerySafetyLog(
                query_id=exec_q.id,
                passed_validation=(status_str == "success"),
                violation_details=err_msg
            )
            db.add(safety_log)

            db.commit()
        except Exception as log_err:
            db.rollback()
            logger.exception(f"[QUERY AUDIT] Failed to persist query execution telemetry: {log_err}")

    if gen_error or not generated_sql:
        log_query(status_str="failed", err_msg=gen_error or "No SQL query generated.")
        return schemas.NLQueryResponse(
            query=payload.query,
            generated_sql=generated_sql,
            explanation=explanation or "Failed to generate SQL query.",
            columns=[],
            rows=[],
            row_count=0,
            execution_time_ms=0.0,
            status="error",
            error_detail=gen_error or "No SQL query generated."
        )

    # 3. Safely Execute SQL
    try:
        exec_res = sql_engine.execute_safe_sql(db_conn, generated_sql)
        exec_ms = exec_res.get("execution_time_ms", 0.0)
        row_cnt = exec_res.get("row_count", 0)
        log_query(status_str="success", exec_ms=exec_ms, rows_cnt=row_cnt)
        return schemas.NLQueryResponse(
            query=payload.query,
            generated_sql=generated_sql,
            explanation=explanation,
            columns=exec_res.get("columns", []),
            rows=exec_res.get("rows", []),
            row_count=row_cnt,
            execution_time_ms=exec_ms,
            status="success",
            error_detail=None
        )
    except Exception as exec_err:
        log_query(status_str="failed", err_msg=str(exec_err))
        return schemas.NLQueryResponse(
            query=payload.query,
            generated_sql=generated_sql,
            explanation=explanation,
            columns=[],
            rows=[],
            row_count=0,
            execution_time_ms=0.0,
            status="error",
            error_detail=str(exec_err)
        )
