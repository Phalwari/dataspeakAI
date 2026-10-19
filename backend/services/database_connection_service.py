"""
Database Connection Service
Handles testing connections and fetching schema information
"""

from typing import Dict, List, Any, Tuple, Optional
import sqlite3
import json
import threading
import re
from functools import lru_cache

psycopg2: Any = None
try:
    import psycopg2
except ImportError:
    pass

pymongo: Any = None
try:
    import pymongo
except ImportError:
    pass

pymysql: Any = None
try:
    import pymysql
except ImportError:
    pass
from functools import lru_cache

import os
import logging
logger = logging.getLogger("dataspeak.db")

# ── Connection pool storage ───────────────────────────────────────────────────
_pg_pools: Dict = {}
_mysql_pools: Dict = {}
_mongo_clients: Dict = {}
_pool_lock = threading.Lock()

PG_MIN_CONN = int(os.getenv("PG_MIN_CONN", "2"))
PG_MAX_CONN = int(os.getenv("PG_MAX_CONN", "25"))


def get_pg_pool(host, port, username, password, database):
    """Get or create a psycopg2 ThreadedConnectionPool (configurable min/max)."""
    try:
        from psycopg2 import pool as pg_pool
        key = f"{host}:{port}:{username}:{database}"
        with _pool_lock:
            if key not in _pg_pools:
                _pg_pools[key] = pg_pool.ThreadedConnectionPool(
                    minconn=PG_MIN_CONN,
                    maxconn=PG_MAX_CONN,
                    host=host,
                    port=port,
                    user=username,
                    password=password,
                    database=database or "postgres",
                    connect_timeout=10
                )
            return _pg_pools[key]
    except Exception as e:
        logger.warning(f"[PG Pool] Failed to create pool: {e}")
        return None


def get_mongo_client(connection_string: str) -> Any:
    """Get or reuse a PyMongo MongoClient instance to maintain PyMongo's internal connection pool."""
    with _pool_lock:
        if connection_string not in _mongo_clients:
            _mongo_clients[connection_string] = pymongo.MongoClient(
                connection_string,
                serverSelectionTimeoutMS=5000,
                maxPoolSize=50,
                minPoolSize=2
            )
        return _mongo_clients[connection_string]


def get_mysql_pool(host, port, username, password, database):
    """Get or create a simple per-key pymysql connection cache.
    pymysql does not ship a native pool; this dict acts as a single reusable
    connection per unique host+db — good enough for low concurrency.
    For production, swap in a proper pool (e.g. DBUtils PooledDB).
    """
    try:
        import pymysql
        key = f"{host}:{port}:{username}:{database}"
        with _pool_lock:
            existing = _mysql_pools.get(key)
            if existing:
                try:
                    existing.ping(reconnect=True)
                    return existing
                except Exception:
                    pass  # stale — create fresh below
            conn = pymysql.connect(
                host=host,
                port=int(port or 3306),
                user=username,
                password=password,
                database=database,
                connect_timeout=10,
                autocommit=True,
            )
            _mysql_pools[key] = conn
            return conn
    except Exception as e:
        logger.warning(f"[MySQL Pool] Failed to create connection: {e}")
        return None


FIRESTORE_MOCK_SCHEMA = {
    "users": {
        "uid": "string",
        "email": "string",
        "displayName": "string",
        "role": "string",
        "createdAt": "timestamp"
    },
    "orders": {
        "orderId": "string",
        "userId": "string",
        "amount": "number",
        "status": "string",
        "items": "array",
        "createdAt": "timestamp"
    },
    "products": {
        "productId": "string",
        "name": "string",
        "price": "number",
        "category": "string",
        "stock": "number"
    }
}

class DatabaseConnectionService:
    """Handles all database connection operations"""

    @staticmethod
    def _validate_table_name(table_name: str) -> str:
        if not table_name or not re.match(r'^[A-Za-z0-9_]+$', table_name):
            raise ValueError(f"Invalid table name: {table_name}")
        return table_name
    
    @staticmethod
    def _serialize_value(val: Any) -> Any:
        from decimal import Decimal
        import datetime as dt
        import uuid as uuid_mod
        if val is None or isinstance(val, (int, float, bool, str)):
            return val
        if isinstance(val, Decimal):
            return float(val)
        if isinstance(val, (dt.datetime, dt.date)):
            return val.isoformat()
        if isinstance(val, uuid_mod.UUID):
            return str(val)
        if isinstance(val, bytes):
            return val.decode("utf-8", errors="replace")
        if isinstance(val, dict):
            return {str(k): DatabaseConnectionService._serialize_value(v) for k, v in val.items()}
        if isinstance(val, (list, tuple, set)):
            return [DatabaseConnectionService._serialize_value(item) for item in val]
        return str(val)

    @staticmethod
    def _serialize_row(row: dict) -> dict:
        return {str(k): DatabaseConnectionService._serialize_value(v) for k, v in row.items()}

    @staticmethod
    def is_safe_sql(query: str) -> tuple[bool, str]:
        import re
        DANGEROUS_PATTERNS = [
            r'\bDROP\b', r'\bDELETE\b', r'\bTRUNCATE\b',
            r'\bUPDATE\b', r'\bINSERT\b', r'\bALTER\b',
            r'\bCREATE\b', r'\bGRANT\b', r'\bEXEC\b', r'\bEXECUTE\b',
            r'\bUNION\s+SELECT\b', r'\bPG_SLEEP\b', r'\bBENCHMARK\b',
            r'\bXP_CMDSHELL\b', r'\bCOPY\s+TO\b',
            r';\s*\w',  # semicolon chaining
            r'--',       # SQL comments (injection attempt)
            r'/\*'       # block comments
        ]
        q_upper = query.upper()
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, q_upper):
                return False, f"Blocked dangerous pattern detected: {pattern}"
        return True, ""
    
    @staticmethod
    def test_firestore(connection_string: str) -> Tuple[bool, str]:
        """Test Firestore/Firebase connection"""
        try:
            if not connection_string or len(connection_string.strip()) < 3:
                return False, "Firestore requires a valid connection string, project ID, or service account JSON."
            if connection_string.strip().startswith('{'):
                try:
                    json.loads(connection_string)
                except Exception:
                    return False, "Firestore credentials must be a valid JSON string."
            return True, "Firestore connection test successful"
        except Exception as e:
            return False, f"Firestore connection failed: {str(e)}"

    @staticmethod
    def get_firestore_schema(connection_string: str) -> Dict[str, Any]:
        """Fetch real Firestore collections and sample fields.
        Falls back to FIRESTORE_MOCK_SCHEMA if firebase_admin is unavailable.
        """
        try:
            import firebase_admin  # type: ignore[import-not-found,import-untyped]
            from firebase_admin import credentials, firestore as fs_client  # type: ignore[import-not-found,import-untyped]

            conn_str = connection_string.strip() if connection_string else ""
            if not conn_str:
                return FIRESTORE_MOCK_SCHEMA

            # Use a stable per-credential app name to avoid duplicate init
            app_name = f"dataspeak_{abs(hash(conn_str)) % 100000}"

            try:
                # Reuse existing app if already initialised
                app = firebase_admin.get_app(app_name)
            except ValueError:
                # App doesn't exist yet — create it
                if conn_str.startswith('{'):
                    # Service-account JSON string
                    cred_dict = json.loads(conn_str)
                    cred = credentials.Certificate(cred_dict)
                    app = firebase_admin.initialize_app(cred, name=app_name)
                else:
                    # Plain project-ID — use Application Default Credentials
                    cred = credentials.ApplicationDefault()
                    app = firebase_admin.initialize_app(
                        cred,
                        {"projectId": conn_str},
                        name=app_name
                    )

            db = fs_client.client(app)

            # Introspect: list collections and sample up to 3 docs per collection
            schema: Dict[str, Any] = {}
            collections = list(db.collections())

            for col in collections[:20]:          # cap at 20 collections
                col_name = col.id
                fields: Dict[str, str] = {}

                # Sample up to 3 documents to infer field types
                for doc in col.limit(3).stream():
                    for field, value in doc.to_dict().items():
                        if field not in fields:
                            fields[field] = type(value).__name__

                schema[col_name] = fields

            return schema if schema else FIRESTORE_MOCK_SCHEMA

        except ImportError:
            # firebase_admin not installed — return mock so callers don't crash
            print("[Firestore] firebase_admin not installed, returning mock schema")
            return FIRESTORE_MOCK_SCHEMA
        except Exception as e:
            print(f"[Firestore] get_firestore_schema failed: {e}")
            return FIRESTORE_MOCK_SCHEMA

    @staticmethod
    def test_postgresql(host: Optional[str] = None, port: Optional[int] = 5432, username: Optional[str] = None, password: Optional[str] = None, database: Optional[str] = "postgres", connection_string: Optional[str] = None) -> Tuple[bool, str]:
        """Test PostgreSQL connection"""
        try:
            if connection_string:
                conn = psycopg2.connect(connection_string, connect_timeout=20)
            elif host and username and password:
                try:
                    conn = psycopg2.connect(
                        host=host,
                        port=port or 5432,
                        user=username,
                        password=password,
                        database=database or "postgres",
                        sslmode="require",
                        connect_timeout=20
                    )
                except Exception:
                    conn = psycopg2.connect(
                        host=host,
                        port=port or 5432,
                        user=username,
                        password=password,
                        database=database or "postgres",
                        connect_timeout=20
                    )
            else:
                return False, "Missing required PostgreSQL host/credentials or connection_string"
            conn.close()
            return True, "PostgreSQL connection successful"
        except Exception as e:
            return False, f"PostgreSQL connection failed: {str(e)}"
    
    @staticmethod
    def test_mongodb(connection_string: str) -> Tuple[bool, str]:
        """Test MongoDB connection — creates a disposable client so the shared pool is not closed."""
        try:
            # Create a fresh temporary client just for the ping test.
            # Do NOT reuse the pooled client (get_mongo_client) and then close it
            # as that would destroy PyMongo's internal connection pool.
            temp_client = pymongo.MongoClient(connection_string, serverSelectionTimeoutMS=5000)
            temp_client.admin.command('ping')
            temp_client.close()  # safe — this is a one-off test client, not the shared pool
            return True, "MongoDB connection successful"
        except Exception as e:
            return False, f"MongoDB connection failed: {str(e)}"
    
    @staticmethod
    def test_mysql(host: str, port: int, username: str, password: str, database: Optional[str] = None) -> Tuple[bool, str]:
        """Test MySQL/MariaDB connection"""
        try:
            conn = pymysql.connect(
                host=host,
                port=port,
                user=username,
                password=password,
                database=database
            )
            conn.close()
            return True, "MySQL connection successful"
        except Exception as e:
            return False, f"MySQL connection failed: {str(e)}"
            
    @staticmethod
    def test_sqlite(database_path: str) -> Tuple[bool, str]:
        """Test SQLite connection"""
        try:
            import os
            db_path = (database_path or "").strip().strip('"\'')
            if not db_path:
                return False, "SQLite file path is empty"
            if not os.path.exists(db_path):
                return False, f"SQLite database file not found at '{db_path}'"
            conn = sqlite3.connect(db_path)
            conn.close()
            return True, "SQLite connection successful"
        except Exception as e:
            return False, f"SQLite connection failed: {str(e)}"
    
    @staticmethod
    def get_postgresql_schema(host: Optional[str] = None, port: Optional[int] = 5432, username: Optional[str] = None, password: Optional[str] = None, database: Optional[str] = "postgres", connection_string: Optional[str] = None) -> Dict[str, Any]:
        """Fetch PostgreSQL schema information"""
        try:
            if connection_string:
                conn = psycopg2.connect(connection_string, connect_timeout=20)
            else:
                try:
                    conn = psycopg2.connect(
                        host=host,
                        port=port or 5432,
                        user=username,
                        password=password,
                        database=database or "postgres",
                        sslmode="require",
                        connect_timeout=20
                    )
                except Exception:
                    conn = psycopg2.connect(
                        host=host,
                        port=port or 5432,
                        user=username,
                        password=password,
                        database=database or "postgres",
                        connect_timeout=20
                    )
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            tables = cursor.fetchall()
            
            schema = {}
            for (table_name,) in tables:
                # Get columns for each table
                cursor.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = %s
                """, (table_name,))
                columns = {col: dtype for col, dtype in cursor.fetchall()}
                
                # Get foreign keys
                cursor.execute("""
                    SELECT
                        kcu.column_name, 
                        ccu.table_name AS foreign_table_name,
                        ccu.column_name AS foreign_column_name 
                    FROM 
                        information_schema.table_constraints AS tc 
                        JOIN information_schema.key_column_usage AS kcu
                          ON tc.constraint_name = kcu.constraint_name
                          AND tc.table_schema = kcu.table_schema
                        JOIN information_schema.constraint_column_usage AS ccu
                          ON ccu.constraint_name = tc.constraint_name
                          AND ccu.table_schema = tc.table_schema
                    WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name = %s;
                """, (table_name,))
                fks = [{"column": row[0], "foreign_table": row[1], "foreign_column": row[2]} for row in cursor.fetchall()]
                
                schema[table_name] = {"columns": columns, "foreign_keys": fks}
            
            cursor.close()
            conn.close()
            return schema
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def get_mongodb_schema(connection_string: Optional[str] = None) -> Dict[str, Any]:
        """Fetch MongoDB schema — collections mapped to their fields and row count."""
        try:
            client = pymongo.MongoClient(connection_string, serverSelectionTimeoutMS=5000)
            schema = {}

            try:
                db = client.get_default_database()
            except Exception:
                all_dbs = client.list_database_names()
                usable_dbs = [d for d in all_dbs if d not in ['admin', 'config', 'local']]
                db = client[usable_dbs[0]] if usable_dbs else client["test"]

            collections = [c for c in db.list_collection_names() if not c.startswith("system.")]

            for collection_name in collections:
                try:
                    collection = db[collection_name]
                    sample = collection.find_one()
                    fields = {}
                    if sample and isinstance(sample, dict):
                        for k, v in sample.items():
                            fields[k] = type(v).__name__
                    count = 0
                    try:
                        count = collection.estimated_document_count()
                    except Exception:
                        pass
                    schema[collection_name] = {
                        "columns": fields,
                        "row_count": count
                    }
                except Exception:
                    continue

            client.close()
            return schema
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def get_mysql_schema(host: Optional[str] = "localhost", port: Optional[int] = 3306, username: Optional[str] = "", password: Optional[str] = "", database: Optional[str] = "") -> Dict[str, Any]:
        """Fetch MySQL schema information"""
        try:
            conn = pymysql.connect(
                host=host or "localhost",
                port=port or 3306,
                user=username or "",
                password=password or "",
                database=database or ""
            )
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            
            schema = {}
            for (table_name,) in tables:
                # Get columns for each table
                cursor.execute(f"DESC {table_name}")
                columns = {row[0]: row[1] for row in cursor.fetchall()}
                schema[table_name] = columns
            
            cursor.close()
            conn.close()
            return schema
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def get_sqlite_schema(database_path: str) -> Dict[str, Any]:
        """Fetch SQLite schema information"""
        try:
            db_path = database_path.strip('"').strip("'")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            schema = {}
            for (table_name,) in tables:
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = {col[1]: col[2] for col in cursor.fetchall()}
                
                cursor.execute(f"PRAGMA foreign_key_list({table_name})")
                fks = [{"column": row[3], "foreign_table": row[2], "foreign_column": row[4]} for row in cursor.fetchall()]
                
                schema[table_name] = {"columns": columns, "foreign_keys": fks}
                
            cursor.close()
            conn.close()
            return schema
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def get_tables(db_type: str, host: Optional[str] = None, port: Optional[int] = None, username: Optional[str] = None, password: Optional[str] = None, database: Optional[str] = None, connection_string: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch list of tables and their row counts"""
        tables_info = []
        try:
            if db_type.lower() == "postgresql":
                conn = psycopg2.connect(host=host, port=port, user=username, password=password, database=database or "postgres")
                cursor = conn.cursor()
                cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
                tables = [row[0] for row in cursor.fetchall()]
                for t in tables:
                    safe_table = DatabaseConnectionService._validate_table_name(t)
                    cursor.execute(f'SELECT count(*) FROM "{safe_table}"')
                    count = cursor.fetchone()[0]
                    tables_info.append({"name": t, "rows": count})
                cursor.close()
                conn.close()
            elif db_type.lower() == "mysql":
                conn = pymysql.connect(host=host, port=port, user=username, password=password, database=database)
                cursor = conn.cursor()
                cursor.execute("SHOW TABLES")
                tables = [row[0] for row in cursor.fetchall()]
                for t in tables:
                    cursor.execute(f"SELECT count(*) FROM `{t}`")
                    row = cursor.fetchone()
                    count = row[0] if row else 0
                    tables_info.append({"name": t, "rows": count})
                cursor.close()
                conn.close()
            elif db_type.lower() == "mongodb":
                actual_conn = connection_string or (host if host and ("mongodb" in host or "://" in host) else None)
                client = pymongo.MongoClient(actual_conn, serverSelectionTimeoutMS=8000)
                try:
                    db = client.get_default_database()
                except Exception:
                    db = client[database or "test"]
                if db is None or not getattr(db, "name", None):
                    db = client[database or "test"]
                collections = db.list_collection_names()
                for c in collections:
                    if not c.startswith("system."):
                        count = db[c].estimated_document_count()
                        tables_info.append({"name": c, "rows": count})
                client.close()
            elif db_type.lower() == "sqlite":
                db_path = (database or host or "").strip('"\'')
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [row[0] for row in cursor.fetchall()]
                for t in tables:
                    cursor.execute(f'SELECT count(*) FROM "{t}"')
                    row = cursor.fetchone()
                    count = row[0] if row else 0
                    tables_info.append({"name": t, "rows": count})
                cursor.close()
                conn.close()
            elif db_type.lower() in ["firestore", "firebase"]:
                return [
                    {"name": "users", "rows": 150},
                    {"name": "orders", "rows": 85},
                    {"name": "products", "rows": 42}
                ]
            return tables_info
        except Exception as e:
            return [{"error": str(e)}]

    @staticmethod
    def preview_table(db_type: str, host: Optional[str] = None, port: Optional[int] = None, username: Optional[str] = None, password: Optional[str] = None, database: Optional[str] = None, connection_string: Optional[str] = None, table_name: Optional[str] = None, limit: int = 50, filter_dict: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Fetch preview data for a specific table"""
        try:
            safe_table_name = DatabaseConnectionService._validate_table_name(table_name or "")
            where_clause = ""
            params = []
            if filter_dict:
                filter_clauses = []
                for col, val in filter_dict.items():
                    # sanitize col name to alphanumeric & underscore
                    if not re.match(r'^[a-zA-Z0-9_]+$', col):
                        continue
                    quoted_col = f'"{col}"' if db_type.lower() in ["postgresql", "sqlite"] else f"`{col}`"
                    
                    # check if val is a month format YYYY-MM
                    if isinstance(val, str) and re.match(r'^\d{4}-\d{2}$', val):
                        if db_type.lower() == "sqlite":
                            filter_clauses.append(f"strftime('%Y-%m', {quoted_col}) = ?")
                            params.append(val)
                        elif db_type.lower() == "postgresql":
                            filter_clauses.append(f"to_char({quoted_col}, 'YYYY-MM') = %s")
                            params.append(val)
                        elif db_type.lower() == "mysql":
                            filter_clauses.append(f"date_format({quoted_col}, '%Y-%m') = %s")
                            params.append(val)
                        else:
                            filter_clauses.append(f"{quoted_col} LIKE ?")
                            params.append(f"{val}%")
                    else:
                        if db_type.lower() in ["postgresql", "mysql"]:
                            filter_clauses.append(f"{quoted_col} = %s")
                            params.append(val)
                        else:
                            filter_clauses.append(f"{quoted_col} = ?")
                            params.append(val)
                if filter_clauses:
                    where_clause = "WHERE " + " AND ".join(filter_clauses)

            if db_type.lower() == "postgresql":
                pg_pool_conn = get_pg_pool(host, port, username, password, database)
                if pg_pool_conn:
                    conn = pg_pool_conn.getconn()
                    try:
                        cursor = conn.cursor()
                        query = f'SELECT * FROM "{safe_table_name}" {where_clause} LIMIT %s'
                        cursor.execute(query, tuple(params + [limit]))
                        columns = [desc[0] for desc in cursor.description] if cursor.description else []
                        rows = [DatabaseConnectionService._serialize_row(dict(zip(columns, row))) for row in cursor.fetchall()]
                        cursor.close()
                        return {"columns": columns, "rows": rows}
                    finally:
                        pg_pool_conn.putconn(conn)  # always return to pool
                else:
                    # Fallback: direct connection
                    conn = psycopg2.connect(host=host, port=port, user=username, password=password, database=database or "postgres")
                    cursor = conn.cursor()
                    query = f'SELECT * FROM "{safe_table_name}" {where_clause} LIMIT %s'
                    cursor.execute(query, tuple(params + [limit]))
                    columns = [desc[0] for desc in cursor.description] if cursor.description else []
                    rows = [DatabaseConnectionService._serialize_row(dict(zip(columns, row))) for row in cursor.fetchall()]
                    cursor.close()
                    conn.close()
                    return {"columns": columns, "rows": rows}
            elif db_type.lower() == "mysql":
                conn = pymysql.connect(host=host, port=port, user=username, password=password, database=database)
                cursor = conn.cursor()
                query = f"SELECT * FROM `{safe_table_name}` {where_clause} LIMIT %s"
                cursor.execute(query, tuple(params + [limit]))
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                rows = [DatabaseConnectionService._serialize_row(dict(zip(columns, row))) for row in cursor.fetchall()]
                cursor.close()
                conn.close()
                return {"columns": columns, "rows": rows}
            elif db_type.lower() == "mongodb":
                actual_conn = connection_string or (host if host and ("mongodb" in host or "://" in host) else None)
                client = pymongo.MongoClient(actual_conn, serverSelectionTimeoutMS=8000)
                try:
                    db = client.get_default_database()
                except Exception:
                    db = client[database or "test"]
                if db is None or not getattr(db, "name", None):
                    db = client[database or "test"]

                mongo_filter = {}
                if filter_dict and isinstance(filter_dict, dict):
                    for col, val in filter_dict.items():
                        if col and val not in (None, "", "All", "all"):
                            if isinstance(val, str) and re.match(r'^\d{4}-\d{2}$', val):
                                mongo_filter[col] = {"$regex": f"^{val}"}
                            else:
                                mongo_filter[col] = val

                cursor = db[safe_table_name].find(mongo_filter).limit(limit)
                raw_rows = list(cursor)
                rows = [DatabaseConnectionService._serialize_row(r) for r in raw_rows]
                
                columns = []
                if len(rows) > 0:
                    all_keys = []
                    for r in rows:
                        for k in r.keys():
                            if k not in all_keys:
                                all_keys.append(k)
                    columns = all_keys
                client.close()
                return {"columns": columns, "rows": rows}
            elif db_type.lower() == "sqlite":
                db_path = (database or host or "").strip('"\'')
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                query = f'SELECT * FROM "{safe_table_name}" {where_clause} LIMIT ?'
                cursor.execute(query, tuple(params + [limit]))
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                rows = [DatabaseConnectionService._serialize_row(dict(zip(columns, row))) for row in cursor.fetchall()]
                cursor.close()
                conn.close()
                return {"columns": columns, "rows": rows}
            elif db_type.lower() in ["firestore", "firebase"]:
                if table_name == "users":
                    rows = [
                        {"uid": "usr_101", "email": "alice@example.com", "displayName": "Alice Smith", "role": "customer", "createdAt": "2026-05-01T12:00:00Z"},
                        {"uid": "usr_102", "email": "bob@example.com", "displayName": "Bob Jones", "role": "admin", "createdAt": "2026-05-02T14:30:00Z"},
                        {"uid": "usr_103", "email": "charlie@example.com", "displayName": "Charlie Brown", "role": "customer", "createdAt": "2026-05-03T09:15:00Z"}
                    ]
                elif table_name == "orders":
                    rows = [
                        {"orderId": "ord_5001", "userId": "usr_101", "amount": 129.99, "status": "completed", "createdAt": "2026-05-18T10:00:00Z"},
                        {"orderId": "ord_5002", "userId": "usr_103", "amount": 49.50, "status": "pending", "createdAt": "2026-05-19T11:15:00Z"},
                        {"orderId": "ord_5003", "userId": "usr_101", "amount": 89.90, "status": "shipped", "createdAt": "2026-05-20T08:00:00Z"}
                    ]
                elif table_name == "products":
                    rows = [
                        {"productId": "prod_001", "name": "Wireless Mouse", "price": 29.99, "category": "electronics", "stock": 150},
                        {"productId": "prod_002", "name": "Mechanical Keyboard", "price": 99.99, "category": "electronics", "stock": 42},
                        {"productId": "prod_003", "name": "Leather Notebook", "price": 19.50, "category": "office", "stock": 80}
                    ]
                else:
                    rows = []
                columns = list(FIRESTORE_MOCK_SCHEMA.get(table_name or "", {}).keys())
                if not columns and rows:
                    columns = list(rows[0].keys())
                return {"columns": columns, "rows": rows}
            return {"error": "Unsupported database type"}
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def execute_query(db_type: str, host: str = "localhost", port: Optional[int] = None, username: str = "", password: Optional[str] = None, database: Optional[str] = None, connection_string: Optional[str] = None, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """Execute a bounded read-only SQL query or a constrained Mongo read operation."""
        if not query or not query.strip():
            return [{"error": "A query is required."}]

        dialect = (db_type or "").strip().lower()
        if dialect in {"sqlite", "postgresql", "mysql", "mariadb"}:
            from types import SimpleNamespace
            from services.sql_engine import execute_safe_sql, validate_read_only_sql

            is_valid, _reason = validate_read_only_sql(query, dialect=dialect)
            if not is_valid:
                raise ValueError("Only read-only SELECT queries are permitted.")

            connection = SimpleNamespace(
                db_type=dialect,
                host=host,
                port=port,
                username=username,
                password=password,
                database=database,
                connection_string=connection_string,
                name="database connection",
            )
            result = execute_safe_sql(connection, query, max_rows=1000)
            return result["rows"]

        if dialect == "mongodb":
            from services.connection_factory import DatabaseConnectionFactory

            if connection_string:
                validated_uri = DatabaseConnectionFactory.validate_connection_string(connection_string)
            else:
                DatabaseConnectionFactory.validate_host_ssrf(host, port)
                raise ValueError("A validated MongoDB connection URI is required.")

            import json
            from pymongo import MongoClient

            try:
                request = json.loads(query)
            except (TypeError, json.JSONDecodeError):
                raise ValueError("MongoDB read query must be valid JSON.") from None
            if not isinstance(request, dict) or len(request) != 1 or not ("find" in request or "aggregate" in request):
                raise ValueError("Only MongoDB find and aggregate reads are permitted.")

            collection_name = request.get("find", request.get("aggregate"))
            if not isinstance(collection_name, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,120}", collection_name):
                raise ValueError("A valid MongoDB collection is required.")

            client = MongoClient(validated_uri, serverSelectionTimeoutMS=5000)
            try:
                try:
                    mongo_db = client.get_default_database()
                except Exception:
                    mongo_db = client[database or "test"]

                if "find" in request:
                    filter_doc = request.get("filter", {})
                    projection = request.get("projection")
                    if not isinstance(filter_doc, dict) or (projection is not None and not isinstance(projection, dict)):
                        raise ValueError("MongoDB find filter and projection must be objects.")
                    cursor = mongo_db[collection_name].find(filter_doc, projection).limit(1000)
                    rows = list(cursor)
                else:
                    pipeline = request.get("pipeline", [])
                    if not isinstance(pipeline, list) or len(pipeline) > 20:
                        raise ValueError("MongoDB aggregation pipeline is invalid.")
                    blocked_operators = {"$out", "$merge", "$where", "$function", "$accumulator"}
                    serialized_pipeline = json.dumps(pipeline).lower()
                    if any(operator in serialized_pipeline for operator in blocked_operators):
                        raise ValueError("MongoDB aggregation contains a prohibited operator.")
                    rows = list(mongo_db[collection_name].aggregate(pipeline, maxTimeMS=10000))[:1000]

                return [DatabaseConnectionService._serialize_row(row) for row in rows]
            finally:
                client.close()

        raise ValueError("Unsupported database type.")


# Global instance
db_connection_service = DatabaseConnectionService()
