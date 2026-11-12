from fastapi import APIRouter, Depends, HTTPException, status
import logging
from sqlalchemy.orm import Session
from typing import List
import models, schemas
from database import get_db
from dependencies import get_current_user, require_source_manager, require_query_executor
import time
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from services.db_utils import get_connection_url, encrypt_password, decrypt_password
from services.connection_factory import DatabaseConnectionFactory
from services.db_pool import get_engine, invalidate_engine

router = APIRouter(prefix="/api/databases", tags=["databases"])
logger = logging.getLogger("dataspeak.databases")


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


def _get_mongo_client_and_db(db_conn: models.DatabaseConnection):
    """Initializes a PyMongo client and database object from connection parameters or URI."""
    from pymongo import MongoClient
    raw_str = db_conn.connection_string
    if not raw_str and db_conn.host and ("://" in str(db_conn.host) or "mongodb" in str(db_conn.host)):
        raw_str = db_conn.host

    if raw_str:
        decrypted = decrypt_password(raw_str) or raw_str
        validated = DatabaseConnectionFactory.validate_connection_string(decrypted)
        client = MongoClient(validated, serverSelectionTimeoutMS=5000)
        try:
            db_obj = client.get_default_database()
        except Exception:
            if db_conn.database:
                db_name = db_conn.database
            else:
                user_dbs = [d for d in client.list_database_names() if d not in ("admin", "local", "config")]
                db_name = user_dbs[0] if user_dbs else "test"
            db_obj = client[db_name]
        return client, db_obj
    else:
        validated_host = DatabaseConnectionFactory.validate_host_ssrf(db_conn.host, db_conn.port)
        pwd = decrypt_password(db_conn.password) if db_conn.password else None
        client = MongoClient(
            host=validated_host,
            port=db_conn.port or 27017,
            username=db_conn.username,
            password=pwd,
            serverSelectionTimeoutMS=5000,
        )
        db_name = db_conn.database or "test"
        db_obj = client[db_name]
        return client, db_obj


def _serialize_mongo_val(v):
    """Recursively converts BSON types (ObjectId, Binary/vector bytes, Decimal128, datetime) to JSON-serializable types."""
    if v is None:
        return None
    from bson import ObjectId, Binary, Decimal128
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, (bytes, Binary)):
        return f"<Binary data ({len(v)} bytes)>"
    if isinstance(v, Decimal128):
        return str(v)
    if hasattr(v, "isoformat"):
        return v.isoformat()
    if isinstance(v, dict):
        return {str(k): _serialize_mongo_val(item) for k, item in v.items()}
    if isinstance(v, list):
        return [_serialize_mongo_val(item) for item in v]
    return v


@router.post("", response_model=schemas.DatabaseConnectionResponse)
def add_database(
    db_conn: schemas.DatabaseConnectionCreate,
    current_user: models.User = Depends(require_source_manager), 
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")
    
    conn_str = db_conn.connection_string
    target_host = db_conn.host
    if not conn_str and target_host and ("://" in target_host or "mongodb" in target_host):
        conn_str = target_host
        target_host = None

    try:
        if conn_str:
            DatabaseConnectionFactory.validate_connection_string(conn_str)
        elif db_conn.db_type.lower() == "sqlite":
            if db_conn.database:
                DatabaseConnectionFactory.validate_sqlite_path(db_conn.database)
        elif target_host:
            DatabaseConnectionFactory.validate_host_ssrf(target_host, db_conn.port)
    except Exception as exc:
        logger.error("Database target validation failed (%s)", type(exc).__name__)
        raise HTTPException(status_code=400, detail="Database target is invalid or unavailable") from None
    
    new_db = models.DatabaseConnection(
        tenant_id=current_user.tenant_id,
        name=db_conn.name,
        db_type=db_conn.db_type,
        host=target_host,
        port=db_conn.port,
        username=db_conn.username,
        password=encrypt_password(db_conn.password) if db_conn.password else None,
        database=db_conn.database,
        connection_string=encrypt_password(conn_str) if conn_str else None,
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

    old_url = DatabaseConnectionFactory.get_connection_url(db_conn)
    if old_url:
        invalidate_engine(old_url)
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

    if (db_conn.db_type or "").lower() == "mongodb":
        try:
            client, db_obj = _get_mongo_client_and_db(db_conn)
            cols = [c for c in db_obj.list_collection_names() if not c.startswith("system.")]
            client.close()
            return sorted(cols)
        except Exception as e:
            logger.error("MongoDB collection listing failed (%s)", type(e).__name__)
            raise HTTPException(status_code=400, detail="Failed to fetch database collections") from None

    connection_url = DatabaseConnectionFactory.get_connection_url(db_conn)
    if not connection_url:
        raise HTTPException(status_code=400, detail="Database connection URL is unavailable or invalid")

    try:
        engine = get_engine(connection_url)
        inspector = inspect(engine)
        return inspector.get_table_names()
    except Exception as e:
        logger.error("Database table listing failed (%s)", type(e).__name__)
        raise HTTPException(status_code=400, detail="Failed to fetch database tables") from None


@router.get("/{db_id}/tables/{table_name}/data")
def get_table_data(
    db_id: int,
    table_name: str,
    current_user: models.User = Depends(require_query_executor),
    db: Session = Depends(get_db)
):
    db_conn = get_accessible_connection(db_id, current_user, db)

    if (db_conn.db_type or "").lower() == "mongodb":
        try:
            client, db_obj = _get_mongo_client_and_db(db_conn)
            cursor = db_obj[table_name].find().limit(100)
            import json
            rows = []
            for doc in cursor:
                row = {}
                for k, v in doc.items():
                    val = _serialize_mongo_val(v)
                    if isinstance(val, (dict, list)):
                        try:
                            row[k] = json.dumps(val, default=str)
                        except Exception:
                            row[k] = str(val)
                    else:
                        row[k] = val
                rows.append(row)
            client.close()
            return rows
        except Exception as e:
            logger.error("MongoDB preview failed (%s)", type(e).__name__)
            raise HTTPException(status_code=400, detail="Failed to fetch table preview") from None

    from services.sql_engine import execute_safe_sql
    try:
        connection_url = DatabaseConnectionFactory.get_connection_url(db_conn)
        if not connection_url:
            raise HTTPException(status_code=400, detail="Database connection URL is unavailable or invalid")

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
        logger.error("Database preview failed (%s)", type(e).__name__)
        raise HTTPException(status_code=400, detail="Failed to fetch table preview") from None


@router.get("/{db_id}/stats")
def get_database_stats(
    db_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_conn = get_accessible_connection(db_id, current_user, db)

    if (db_conn.db_type or "").lower() == "mongodb":
        try:
            client, db_obj = _get_mongo_client_and_db(db_conn)
            collections = [c for c in db_obj.list_collection_names() if not c.startswith("system.")]
            tables_info = []
            for c in collections:
                try:
                    r_cnt = db_obj[c].estimated_document_count()
                except Exception:
                    r_cnt = 0
                tables_info.append({"name": c, "rows": r_cnt})
            client.close()
            if db_conn.status != "connected":
                db_conn.status = "connected"
                db.commit()

            return {
                "table_count": len(collections),
                "tables": tables_info
            }
        except Exception as e:
            logger.error("MongoDB statistics query failed (%s)", type(e).__name__)
            raise HTTPException(status_code=400, detail="Failed to fetch database statistics") from None

    connection_url = DatabaseConnectionFactory.get_connection_url(db_conn)
    if not connection_url:
        raise HTTPException(status_code=400, detail="Database connection URL is unavailable or invalid")

    try:
        from services.sql_engine import execute_safe_sql
        engine = get_engine(connection_url)
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        
        # Fast PostgreSQL metadata query using pg_class to avoid slow sequential COUNT(*) on huge tables
        if (db_conn.db_type or "").lower() == "postgresql":
            try:
                pg_query = (
                    "SELECT c.relname AS name, GREATEST(0, CAST(c.reltuples AS BIGINT)) AS rows "
                    "FROM pg_class c "
                    "JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE c.relkind = 'r' AND n.nspname NOT IN ('pg_catalog', 'information_schema') "
                    "ORDER BY rows DESC"
                )
                pg_res = execute_safe_sql(db_conn, pg_query, max_rows=500)
                if pg_res.get("rows"):
                    tables_info = pg_res["rows"]
                    # If all row counts are 0 (e.g. newly created tables not yet analyzed by autovacuum) on a small table set:
                    if sum(t.get("rows", 0) for t in tables_info) == 0 and len(tables_info) <= 50:
                        for item in tables_info:
                            try:
                                c_res = execute_safe_sql(db_conn, f'SELECT COUNT(*) AS cnt FROM "{item["name"]}"', max_rows=1)
                                item["rows"] = list(c_res["rows"][0].values())[0] if c_res.get("rows") else 0
                            except Exception:
                                pass
                    if db_conn.status != "connected":
                        db_conn.status = "connected"
                        db.commit()
                    return {
                        "table_count": len(tables_info),
                        "tables": tables_info
                    }
            except Exception:
                pass

        tables_info = []
        for t in table_names[:50]:
            try:
                c_res = execute_safe_sql(db_conn, f'SELECT COUNT(*) AS cnt FROM "{t}"', max_rows=1)
                r_cnt = list(c_res["rows"][0].values())[0] if c_res.get("rows") else 0
            except Exception:
                r_cnt = 0
            tables_info.append({"name": t, "rows": r_cnt})

        if db_conn.status != "connected":
            db_conn.status = "connected"
            db.commit()

        stats = {
            "table_count": len(table_names),
            "tables": tables_info
        }
        return stats
    except Exception as e:
        logger.error("Database statistics query failed (%s)", type(e).__name__)
        raise HTTPException(status_code=400, detail="Failed to fetch database statistics") from None


@router.get("/{db_id}/tables/{table_name}/stats")
def get_table_stats(
    db_id: int,
    table_name: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_conn = get_accessible_connection(db_id, current_user, db)

    if (db_conn.db_type or "").lower() == "mongodb":
        try:
            client, db_obj = _get_mongo_client_and_db(db_conn)
            try:
                row_count = db_obj[table_name].estimated_document_count()
            except Exception:
                row_count = 0
            sample = db_obj[table_name].find_one()
            col_count = len(sample.keys()) if sample else 0
            client.close()
            return {"rows": row_count, "columns": col_count}
        except Exception as e:
            logger.error("MongoDB table statistics query failed (%s)", type(e).__name__)
            raise HTTPException(status_code=400, detail="Failed to fetch table statistics") from None

    connection_url = DatabaseConnectionFactory.get_connection_url(db_conn)
    if not connection_url:
        raise HTTPException(status_code=400, detail="Database connection URL is unavailable or invalid")

    try:
        from services.sql_engine import execute_safe_sql
        engine = get_engine(connection_url)
        inspector = inspect(engine)
        valid_tables = inspector.get_table_names()
        if table_name not in valid_tables:
            raise HTTPException(status_code=400, detail="Invalid table name")
        
        try:
            columns = inspector.get_columns(table_name)
            col_count = len(columns)
        except Exception:
            empty_res = execute_safe_sql(db_conn, f'SELECT * FROM "{table_name}" LIMIT 0', max_rows=0)
            col_count = len(empty_res.get("columns", []))
            
        try:
            count_res = execute_safe_sql(db_conn, f'SELECT COUNT(*) AS cnt FROM "{table_name}"', max_rows=1)
            row_count = list(count_res["rows"][0].values())[0] if count_res.get("rows") else 0
        except Exception:
            row_count = 0
            
        return {"rows": row_count, "columns": col_count}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Database table statistics query failed (%s)", type(e).__name__)
        raise HTTPException(status_code=400, detail="Failed to fetch table statistics") from None


@router.post("/test")
def test_database_connection(
    db_conn: schemas.DatabaseConnectionCreate,
    current_user: models.User = Depends(require_source_manager)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")
        
    conn_str = db_conn.connection_string
    target_host = db_conn.host
    if not conn_str and target_host and ("://" in target_host or "mongodb" in target_host):
        conn_str = target_host
        target_host = None

    success, error_msg = DatabaseConnectionFactory.test_connection(
        db_type=db_conn.db_type,
        host=target_host,
        port=db_conn.port,
        database=db_conn.database,
        username=db_conn.username,
        password=db_conn.password,
        connection_string=conn_str,
    )
    if not success:
        raise HTTPException(status_code=400, detail="Database connection test failed")
    return {"status": "success", "message": "Connection successful"}
