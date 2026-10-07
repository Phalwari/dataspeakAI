"""
Database Connections Router for DataSpeakAI & DB AI Insights.
Provides full connection testing, introspection, creation, retesting, and deletion.
Matches the contract required by BusinessInsightsPage and full_backend/routes/connections.py.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from sqlalchemy import inspect
from typing import List, Dict, Any, Optional
from datetime import datetime
import re
from urllib.parse import urlparse, unquote

import models, schemas
from database import get_db, SessionLocal
from dependencies import get_current_user
from services.db_utils import encrypt_password, decrypt_password, get_connection_url
from services.db_pool import get_engine
from services.database_connection_service import db_connection_service

router = APIRouter(prefix="/api/connections", tags=["Database Connections"])


@router.get("/list")
@router.get("")
def list_connections(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all database connections for the current tenant.
    Provides keys for BusinessInsights, DatabasesPage, and standard frontend clients.
    """
    if not current_user.tenant_id:
        return {"connections": [], "total": 0}

    conns = (
        db.query(models.DatabaseConnection)
        .filter(models.DatabaseConnection.tenant_id == current_user.tenant_id)
        .order_by(models.DatabaseConnection.created_at.desc())
        .all()
    )

    result = []
    for c in conns:
        result.append({
            "id": c.id,
            "name": c.name,
            "db_name": c.name,
            "db_type": c.db_type,
            "host": c.host,
            "database": c.database,
            "port": getattr(c, "port", None),
            "status": c.status or "connected",
            "is_active": c.status or "active",
            "tables_metadata": getattr(c, "tables_metadata", None),
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })

    return {"connections": result, "total": len(result)}


@router.get("/{connection_id}")
def get_connection(
    connection_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetch a single connection for the tenant."""
    c = (
        db.query(models.DatabaseConnection)
        .filter(
            models.DatabaseConnection.id == connection_id,
            models.DatabaseConnection.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not c:
        raise HTTPException(status_code=404, detail="Database connection not found.")

    return {
        "id": c.id,
        "name": c.name,
        "db_name": c.name,
        "db_type": c.db_type,
        "host": c.host,
        "database": c.database,
        "port": getattr(c, "port", None),
        "status": c.status,
        "tables_metadata": getattr(c, "tables_metadata", None),
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


@router.get("/{connection_id}/schema")
def get_connection_schema(
    connection_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetch stored schema catalog for a connection."""
    c = (
        db.query(models.DatabaseConnection)
        .filter(
            models.DatabaseConnection.id == connection_id,
            models.DatabaseConnection.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not c:
        raise HTTPException(status_code=404, detail="Database connection not found.")

    return c.tables_metadata or {}


@router.post("/{connection_id}/tables")
@router.get("/{connection_id}/tables")
def get_connection_tables(
    connection_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetch list of table names for a connection."""
    c = (
        db.query(models.DatabaseConnection)
        .filter(
            models.DatabaseConnection.id == connection_id,
            models.DatabaseConnection.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not c:
        raise HTTPException(status_code=404, detail="Database connection not found.")

    # Check cached tables_metadata first
    if c.tables_metadata:
        try:
            meta = c.tables_metadata
            if isinstance(meta, str):
                import json
                meta = json.loads(meta)
            if isinstance(meta, dict) and meta:
                return list(meta.keys())
        except Exception:
            pass

    conn_url = get_connection_url(c)
    if not conn_url:
        return []

    try:
        engine = get_engine(conn_url)
        inspector = inspect(engine)
        return inspector.get_table_names()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to inspect tables: {str(e)}")


@router.post("/{connection_id}/retest")
def retest_connection(
    connection_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retest an existing database connection and update schema metadata."""
    c = (
        db.query(models.DatabaseConnection)
        .filter(
            models.DatabaseConnection.id == connection_id,
            models.DatabaseConnection.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not c:
        raise HTTPException(status_code=404, detail="Database connection not found.")

    pwd = decrypt_password(c.password) if c.password else ""
    db_type = (c.db_type or "").lower().strip()
    success = False
    msg = ""
    schema = {}

    try:
        if db_type == "postgresql":
            success, msg = db_connection_service.test_postgresql(
                c.host, c.port or 5432, c.username or "", pwd, c.database or "postgres",
                connection_string=c.connection_string
            )
            if success:
                schema = db_connection_service.get_postgresql_schema(
                    c.host, c.port or 5432, c.username or "", pwd, c.database or "postgres",
                    connection_string=c.connection_string
                )

        elif db_type in ("mysql", "mariadb"):
            success, msg = db_connection_service.test_mysql(
                c.host, c.port or 3306, c.username or "root", pwd, c.database or ""
            )
            if success:
                schema = db_connection_service.get_mysql_schema(
                    c.host, c.port or 3306, c.username or "root", pwd, c.database or ""
                )

        elif db_type == "sqlite":
            db_path = c.database or c.host or "./app.db"
            success, msg = db_connection_service.test_sqlite(db_path)
            if success:
                schema = db_connection_service.get_sqlite_schema(db_path)

        elif db_type == "mongodb":
            conn_str = c.connection_string or c.host or ""
            success, msg = db_connection_service.test_mongodb(conn_str)
            if success:
                schema = db_connection_service.get_mongodb_schema(conn_str)

    except Exception as ex:
        success = False
        msg = str(ex)

    c.status = "connected" if success else "error"
    if schema:
        c.tables_metadata = schema
    db.commit()
    db.refresh(c)

    return {
        "success": success,
        "message": msg or ("Retest successful" if success else "Retest failed"),
        "status": c.status,
        "tables_metadata": c.tables_metadata
    }


@router.delete("/{connection_id}")
def delete_connection(
    connection_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a database connection for the tenant."""
    c = (
        db.query(models.DatabaseConnection)
        .filter(
            models.DatabaseConnection.id == connection_id,
            models.DatabaseConnection.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not c:
        raise HTTPException(status_code=404, detail="Database connection not found.")

    db.delete(c)
    db.commit()
    return {"message": "Database connection deleted successfully", "id": connection_id}


@router.put("/{connection_id}")
def update_connection(
    connection_id: int,
    update_data: schemas.ConnectionUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a database connection for the tenant."""
    c = (
        db.query(models.DatabaseConnection)
        .filter(
            models.DatabaseConnection.id == connection_id,
            models.DatabaseConnection.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not c:
        raise HTTPException(status_code=404, detail="Database connection not found.")

    update_dict = update_data.model_dump(exclude_unset=True)
    if "password" in update_dict and update_dict["password"]:
        c.password = encrypt_password(update_dict["password"])
        update_dict.pop("password")

    for key, value in update_dict.items():
        if hasattr(c, key) and value is not None:
            setattr(c, key, value)

    db.commit()
    db.refresh(c)
    return {
        "id": c.id,
        "name": c.name,
        "db_type": c.db_type,
        "host": c.host,
        "port": c.port,
        "username": c.username,
        "database": c.database,
        "connection_string": c.connection_string,
        "status": c.status,
        "tables_metadata": c.tables_metadata,
        "created_at": c.created_at
    }


@router.post("/{connection_id}/preview")
def preview_connection_table(
    connection_id: int,
    preview_req: schemas.TablePreviewRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetch first N rows from table."""
    c = (
        db.query(models.DatabaseConnection)
        .filter(
            models.DatabaseConnection.id == connection_id,
            models.DatabaseConnection.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not c:
        raise HTTPException(status_code=404, detail="Database connection not found.")

    target_table = preview_req.table_name or preview_req.table
    if not target_table:
        raise HTTPException(status_code=400, detail="Table name is required")

    decrypted_password = decrypt_password(c.password) if c.password else ""
    raw_conn = c.connection_string or (c.host if c.host and ("mongodb" in str(c.host) or "://" in str(c.host)) else None)
    decrypted_conn = decrypt_password(raw_conn) if raw_conn else ""

    return db_connection_service.preview_table(
        db_type=c.db_type,
        host=c.host,
        port=c.port,
        username=c.username,
        password=decrypted_password,
        database=c.database,
        connection_string=decrypted_conn,
        table_name=target_table,
        limit=preview_req.limit or 50,
        filter_dict=preview_req.filter
    )


@router.post("/{connection_id}/query")
def execute_connection_query(
    connection_id: int,
    query_req: schemas.DBQueryRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Execute raw query on connected DB."""
    c = (
        db.query(models.DatabaseConnection)
        .filter(
            models.DatabaseConnection.id == connection_id,
            models.DatabaseConnection.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not c:
        raise HTTPException(status_code=404, detail="Database connection not found.")

    decrypted_password = decrypt_password(c.password) if c.password else ""
    return db_connection_service.execute_query(
        db_type=c.db_type,
        host=c.host,
        port=c.port,
        username=c.username,
        password=decrypted_password,
        database=c.database,
        connection_string=c.connection_string,
        query=query_req.query
    )


@router.post("/{connection_id}/ai-query")
def execute_ai_query(
    connection_id: int,
    ai_req: schemas.AIQueryRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Execute AI query on connected DB."""
    c = (
        db.query(models.DatabaseConnection)
        .filter(
            models.DatabaseConnection.id == connection_id,
            models.DatabaseConnection.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not c:
        raise HTTPException(status_code=404, detail="Database connection not found.")

    schema = {}
    if c.tables_metadata:
        meta = c.tables_metadata
        if isinstance(meta, str):
            import json
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {}
        if isinstance(meta, dict):
            schema = meta.get(ai_req.table_name, {})

    from services.multi_llm import get_multi_llm
    llm = get_multi_llm()
    prompt = f"Table schema: {schema}\nUser question: {ai_req.question}\nWrite {'SQL' if c.db_type != 'mongodb' else 'MongoDB JSON'} query to answer this.\nReturn ONLY the query, nothing else."
    
    generated_query = ""
    try:
        generated_query = llm.generate_insights(prompt)
    except Exception:
        generated_query = f"SELECT * FROM {ai_req.table_name} LIMIT 50"

    if generated_query and generated_query.startswith("```"):
        lines = generated_query.split("\n")
        if len(lines) >= 3:
            generated_query = "\n".join(lines[1:-1]).strip()

    if not generated_query:
        generated_query = f"SELECT * FROM {ai_req.table_name} LIMIT 50"

    decrypted_password = decrypt_password(c.password) if c.password else ""
    results = db_connection_service.execute_query(
        db_type=c.db_type,
        host=c.host,
        port=c.port,
        username=c.username,
        password=decrypted_password,
        database=c.database,
        connection_string=c.connection_string,
        query=generated_query
    )
    return {"query": generated_query, "results": results}
