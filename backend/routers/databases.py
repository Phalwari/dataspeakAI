from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import models, schemas
from database import get_db
from dependencies import get_current_user, require_source_manager, require_query_executor
import time
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from services.db_utils import get_connection_url, encrypt_password, decrypt_password
from services.db_pool import get_engine

router = APIRouter(prefix="/api/databases", tags=["databases"])


def get_accessible_connection(
    db_id: int, 
    current_user: models.User, 
    db: Session
) -> models.DatabaseConnection:
    """
    Ensures the requested database connection exists, belongs to the current user's tenant,
    and is accessible to the user (direct tenant access for Admins/Developers, explicit grant
    via UserDatabaseAccess for Business Owners/Viewers).
    Returns uniform HTTP 404 on missing, unassigned, or cross-tenant resources without disclosure.
    """
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")

    query = db.query(models.DatabaseConnection).filter(
        models.DatabaseConnection.id == db_id,
        models.DatabaseConnection.tenant_id == current_user.tenant_id
    )

    if not (current_user.role in ("Admin", "Developer") or getattr(current_user, "is_platform_admin", False)):
        query = query.join(
            models.UserDatabaseAccess,
            models.DatabaseConnection.id == models.UserDatabaseAccess.database_id
        ).filter(models.UserDatabaseAccess.user_id == current_user.id)

    conn = query.first()
    if not conn:
        raise HTTPException(status_code=404, detail="Database connection not found")
    return conn


@router.get("", response_model=List[schemas.DatabaseConnectionResponse])
def get_databases(
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")
        
    if current_user.role in ("Admin", "Developer") or getattr(current_user, "is_platform_admin", False):
        databases = db.query(models.DatabaseConnection).filter(models.DatabaseConnection.tenant_id == current_user.tenant_id).all()
    else:
        # Filter by UserDatabaseAccess
        databases = db.query(models.DatabaseConnection).join(
            models.UserDatabaseAccess, 
            models.DatabaseConnection.id == models.UserDatabaseAccess.database_id
        ).filter(
            models.DatabaseConnection.tenant_id == current_user.tenant_id,
            models.UserDatabaseAccess.user_id == current_user.id
        ).all()
        
    return databases


@router.post("", response_model=schemas.DatabaseConnectionResponse)
def add_database(
    db_conn: schemas.DatabaseConnectionCreate,
    current_user: models.User = Depends(require_source_manager), 
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")
    
    from services.connection_factory import DatabaseConnectionFactory
    try:
        if db_conn.db_type.lower() == "sqlite":
            if db_conn.database:
                DatabaseConnectionFactory.validate_sqlite_path(db_conn.database)
        elif db_conn.host:
            DatabaseConnectionFactory.validate_host_ssrf(db_conn.host, db_conn.port)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    
    new_db = models.DatabaseConnection(
        tenant_id=current_user.tenant_id,
        name=db_conn.name,
        db_type=db_conn.db_type,
        host=db_conn.host,
        port=db_conn.port,
        username=db_conn.username,
        password=encrypt_password(db_conn.password),
        database=db_conn.database,
        connection_string=db_conn.connection_string,
        description=db_conn.description,
        status="connected"
    )
    db.add(new_db)
    db.commit()
    db.refresh(new_db)
    return new_db


@router.delete("/{db_id}")
def delete_database(
    db_id: int,
    current_user: models.User = Depends(require_source_manager), 
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")
        
    db_conn = db.query(models.DatabaseConnection).filter(
        models.DatabaseConnection.id == db_id,
        models.DatabaseConnection.tenant_id == current_user.tenant_id
    ).first()
    
    if not db_conn:
        raise HTTPException(status_code=404, detail="Database connection not found")
        
    db.delete(db_conn)
    db.commit()
    return {"message": "Database deleted successfully"}


@router.get("/{db_id}/tables")
def get_database_tables(
    db_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_conn = get_accessible_connection(db_id, current_user, db)

    connection_url = get_connection_url(db_conn)
    if not connection_url:
        return ["users", "orders", "products", "customers"]

    try:
        engine = get_engine(connection_url)
        inspector = inspect(engine)
        return inspector.get_table_names()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch tables: {str(e)}")


@router.get("/{db_id}/tables/{table_name}/data")
def get_table_data(
    db_id: int,
    table_name: str,
    current_user: models.User = Depends(require_query_executor),
    db: Session = Depends(get_db)
):
    db_conn = get_accessible_connection(db_id, current_user, db)

    from services.sql_engine import execute_safe_sql
    try:
        connection_url = get_connection_url(db_conn)
        if not connection_url:
            raise HTTPException(status_code=400, detail="Database connection URL is unavailable")

        engine = get_engine(connection_url)
        inspector = inspect(engine)
        valid_tables = inspector.get_table_names()
        if table_name not in valid_tables:
            raise HTTPException(status_code=400, detail="Invalid table name")

        safe_query = f'SELECT * FROM "{table_name}"'
        res = execute_safe_sql(db_conn, safe_query, max_rows=100)
        return res["rows"]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch data: {str(e)}")


@router.get("/{db_id}/stats")
def get_database_stats(
    db_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_conn = get_accessible_connection(db_id, current_user, db)

    connection_url = get_connection_url(db_conn)
    if not connection_url:
        return {
            "table_count": 4,
            "tables": [
                {"name": "users", "rows": 1250, "columns": 8},
                {"name": "orders", "rows": 5420, "columns": 12},
                {"name": "products", "rows": 850, "columns": 6},
                {"name": "customers", "rows": 1100, "columns": 10},
            ]
        }

    try:
        engine = get_engine(connection_url)
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        
        tables_info = []
        with engine.connect() as conn:
            for t in table_names:
                try:
                    r_cnt = conn.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar()
                except Exception:
                    r_cnt = 0
                tables_info.append({"name": t, "rows": r_cnt})

        stats = {
            "table_count": len(table_names),
            "tables": tables_info
        }
        return stats
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch stats: {str(e)}")


@router.get("/{db_id}/tables/{table_name}/stats")
def get_table_stats(
    db_id: int,
    table_name: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_conn = get_accessible_connection(db_id, current_user, db)

    connection_url = get_connection_url(db_conn)
    if not connection_url:
        return {"rows": 0, "columns": 0}

    try:
        engine = get_engine(connection_url)
        inspector = inspect(engine)
        valid_tables = inspector.get_table_names()
        if table_name not in valid_tables:
            raise HTTPException(status_code=400, detail="Invalid table name")
        
        columns = inspector.get_columns(table_name)
        col_count = len(columns)
        
        with engine.connect() as conn:
            row_count_res = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
            row_count = row_count_res.scalar()
            
        return {"rows": row_count, "columns": col_count}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch table stats: {str(e)}")


@router.post("/test")
def test_database_connection(
    db_conn: schemas.DatabaseConnectionCreate,
    current_user: models.User = Depends(require_source_manager)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")
        
    from services.connection_factory import DatabaseConnectionFactory
    
    success, error_msg = DatabaseConnectionFactory.test_connection(
        db_type=db_conn.db_type,
        host=db_conn.host,
        port=db_conn.port,
        database=db_conn.database,
        username=db_conn.username,
        password=db_conn.password,
    )
    if not success:
        raise HTTPException(status_code=400, detail=error_msg or "Connection test failed")
    return {"status": "success", "message": "Connection successful"}
