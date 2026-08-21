from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import models, schemas
from database import get_db
from dependencies import get_current_user
import time
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError

import os, base64, hashlib
from cryptography.fernet import Fernet

router = APIRouter(prefix="/api/databases", tags=["databases"])

ENCRYPTION_SECRET = os.getenv("SECRET_KEY", "dataspeakai-default-encryption-secret-key-32b")
_FERNET_KEY = base64.urlsafe_b64encode(hashlib.sha256(ENCRYPTION_SECRET.encode()).digest())
_fernet = Fernet(_FERNET_KEY)

def encrypt_password(plain_pwd: str) -> str:
    if not plain_pwd:
        return plain_pwd
    return _fernet.encrypt(plain_pwd.encode()).decode()

def decrypt_password(enc_pwd: str) -> str:
    if not enc_pwd:
        return enc_pwd
    try:
        return _fernet.decrypt(enc_pwd.encode()).decode()
    except Exception:
        # Fallback if stored in plain text prior to encryption
        return enc_pwd

def get_connection_url(db_conn: models.DatabaseConnection):
    pwd = decrypt_password(db_conn.password)
    if db_conn.db_type == "postgresql":
        return f"postgresql://{db_conn.username}:{pwd}@{db_conn.host}/{db_conn.database}"
    elif db_conn.db_type in ("mysql", "mariadb"):
        return f"mysql+pymysql://{db_conn.username}:{pwd}@{db_conn.host}/{db_conn.database}"
    elif db_conn.db_type == "sqlite":
        path = (db_conn.database if db_conn.database else db_conn.host) or ""
        path = path.strip('"\'').replace("\\", "/")
        return f"sqlite:///{path}"
    return None



@router.get("", response_model=List[schemas.DatabaseConnectionResponse])
def get_databases(
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")
        
    if current_user.role == "Admin":
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
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")
    
    new_db = models.DatabaseConnection(
        tenant_id=current_user.tenant_id,
        name=db_conn.name,
        db_type=db_conn.db_type,
        host=db_conn.host,
        username=db_conn.username,
        password=encrypt_password(db_conn.password),
        database=db_conn.database,
        status="connected" # Assume connected initially or after successful test
    )
    db.add(new_db)
    db.commit()
    db.refresh(new_db)
    return new_db


@router.delete("/{db_id}")
def delete_database(
    db_id: int,
    current_user: models.User = Depends(get_current_user), 
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
    db_conn = db.query(models.DatabaseConnection).filter(
        models.DatabaseConnection.id == db_id,
        models.DatabaseConnection.tenant_id == current_user.tenant_id
    ).first()

    if not db_conn:
        raise HTTPException(status_code=404, detail="Database connection not found")

    connection_url = get_connection_url(db_conn)
    if not connection_url:
        # For simulated types, return mock tables
        return ["users", "orders", "products", "customers"]

    try:
        engine = create_engine(connection_url)
        inspector = inspect(engine)
        return inspector.get_table_names()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch tables: {str(e)}")

@router.get("/{db_id}/tables/{table_name}/data")
def get_table_data(
    db_id: int,
    table_name: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_conn = db.query(models.DatabaseConnection).filter(
        models.DatabaseConnection.id == db_id,
        models.DatabaseConnection.tenant_id == current_user.tenant_id
    ).first()

    if not db_conn:
        raise HTTPException(status_code=404, detail="Database connection not found")

    connection_url = get_connection_url(db_conn)
    if not connection_url:
        # For simulated types, return mock data
        return [
            {"id": 1, "name": "Mock Item 1", "status": "active"},
            {"id": 2, "name": "Mock Item 2", "status": "inactive"},
            {"id": 3, "name": "Mock Item 3", "status": "pending"},
        ]

    try:
        engine = create_engine(connection_url)
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT * FROM {table_name} LIMIT 100"))
            columns = result.keys()
            data = [dict(zip(columns, row)) for row in result]
            return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch data: {str(e)}")

@router.get("/{db_id}/stats")
def get_database_stats(
    db_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_conn = db.query(models.DatabaseConnection).filter(
        models.DatabaseConnection.id == db_id,
        models.DatabaseConnection.tenant_id == current_user.tenant_id
    ).first()

    if not db_conn:
        raise HTTPException(status_code=404, detail="Database connection not found")

    connection_url = get_connection_url(db_conn)
    if not connection_url:
        # Mock stats for simulated types
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
        from sqlalchemy.pool import NullPool
        engine = create_engine(connection_url, poolclass=NullPool)
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
    db_conn = db.query(models.DatabaseConnection).filter(
        models.DatabaseConnection.id == db_id,
        models.DatabaseConnection.tenant_id == current_user.tenant_id
    ).first()

    if not db_conn:
        raise HTTPException(status_code=404, detail="Database connection not found")

    connection_url = get_connection_url(db_conn)
    if not connection_url:
        return {"rows": 0, "columns": 0}

    try:
        from sqlalchemy.pool import NullPool
        engine = create_engine(connection_url, poolclass=NullPool)
        inspector = inspect(engine)
        
        # Get column count
        columns = inspector.get_columns(table_name)
        col_count = len(columns)
        
        # Get row count
        with engine.connect() as conn:
            row_count_res = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            row_count = row_count_res.scalar()
            
        engine.dispose()
        return {"rows": row_count, "columns": col_count}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch table stats: {str(e)}")

@router.post("/test")
def test_database_connection(
    db_conn: schemas.DatabaseConnectionCreate,
    current_user: models.User = Depends(get_current_user)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")
        
    connection_url = ""
    if db_conn.db_type == "postgresql":
        connection_url = f"postgresql://{db_conn.username}:{db_conn.password}@{db_conn.host}/{db_conn.database}"
    elif db_conn.db_type in ("mysql", "mariadb"):
        connection_url = f"mysql+pymysql://{db_conn.username}:{db_conn.password}@{db_conn.host}/{db_conn.database}"
    elif db_conn.db_type == "sqlite":
        path = (db_conn.database if db_conn.database else db_conn.host) or ""
        path = path.strip('"\'').replace("\\", "/")
        connection_url = f"sqlite:///{path}"

    else:
        # Simulate other types for MVP
        time.sleep(1)
        return {"status": "success", "message": f"Connection simulated for {db_conn.db_type}"}
        
    try:
        from sqlalchemy.pool import NullPool
        connect_args = {'connect_timeout': 5} if db_conn.db_type != "sqlite" else {}
        engine = create_engine(connection_url, connect_args=connect_args, poolclass=NullPool)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return {"status": "success", "message": "Connection successful"}
    except SQLAlchemyError as e:
        raise HTTPException(status_code=400, detail=f"Connection failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"An error occurred: {str(e)}")

