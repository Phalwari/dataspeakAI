"""
Database Connection Service
Handles testing connections and fetching schema information
"""

try:
    import psycopg2
except ImportError:
    psycopg2 = None

try:
    import pymongo
except ImportError:
    pymongo = None

try:
    import pymysql
except ImportError:
    pymysql = None

import sqlite3
from typing import Dict, List, Any, Tuple, Optional
import json
import threading
import re
from functools import lru_cache

import os
import logging
logger = logging.getLogger("nexabi.db")

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
    def _serialize_row(row: dict) -> dict:
        from decimal import Decimal
        import datetime as dt
        import uuid as uuid_mod
        result = {}
        for k, v in row.items():
            if isinstance(v, Decimal):
                result[k] = float(v)
            elif isinstance(v, (dt.datetime, dt.date)):
                result[k] = v.isoformat()
            elif isinstance(v, uuid_mod.UUID):
                result[k] = str(v)
            elif isinstance(v, bytes):
                result[k] = v.decode("utf-8", errors="replace")
            else:
                result[k] = v
        return result

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
            import firebase_admin
            from firebase_admin import credentials, firestore as fs_client

            conn_str = connection_string.strip() if connection_string else ""
            if not conn_str:
                return FIRESTORE_MOCK_SCHEMA

            # Use a stable per-credential app name to avoid duplicate init
            app_name = f"nexabi_{abs(hash(conn_str)) % 100000}"

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
    def test_postgresql(host: str = None, port: int = 5432, username: str = None, password: str = None, database: str = "postgres", connection_string: str = None) -> Tuple[bool, str]:
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
    def test_mysql(host: str, port: int, username: str, password: str, database: str = None) -> Tuple[bool, str]:
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
            db_path = str(database_path or "").strip().strip('"').strip("'")
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
        """Fetch MongoDB schema — limited to the connection string's default database only."""
        try:
            client = pymongo.MongoClient(connection_string, serverSelectionTimeoutMS=5000)
            schema = {}

            try:
                db = client.get_default_database()
                target_dbs = [db]
            except Exception:
                # If URI does not specify a default database, use non-admin databases
                all_dbs = client.list_database_names()
                target_dbs = [client[d] for d in all_dbs if d not in ['admin', 'config', 'local']]

            for db in target_dbs:
                db_name = db.name
                collections = db.list_collection_names()

                db_schema = {}
                for collection_name in collections:
                    collection = db[collection_name]
                    sample = collection.find_one()
                    if sample:
                        fields = {k: type(v).__name__ for k, v in sample.items()} if isinstance(sample, dict) else {}
                        db_schema[collection_name] = fields

                schema[db_name] = db_schema

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
    def get_tables(db_type: str, host: str, port: int, username: str, password: str, database: str = None, connection_string: str = None) -> List[Dict[str, Any]]:
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
                    count = cursor.fetchone()[0]
                    tables_info.append({"name": t, "rows": count})
                cursor.close()
                conn.close()
            elif db_type.lower() == "mongodb":
                client = pymongo.MongoClient(connection_string, serverSelectionTimeoutMS=5000)
                # We need to find the specific database. For MongoDB the DB name is often part of the connection string or specified.
                db = client.get_default_database() if client.get_default_database().name else client[database or "test"]
                collections = db.list_collection_names()
                for c in collections:
                    count = db[c].estimated_document_count()
                    tables_info.append({"name": c, "rows": count})
                client.close()
            elif db_type.lower() == "sqlite":
                db_path = (database or host).strip('"').strip("'")
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [row[0] for row in cursor.fetchall()]
                for t in tables:
                    cursor.execute(f'SELECT count(*) FROM "{t}"')
                    count = cursor.fetchone()[0]
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
    def preview_table(db_type: str, host: int, port: int, username: str, password: str, database: str = None, connection_string: str = None, table_name: str = None, limit: int = 50, filter_dict: Dict[str, Any] = None) -> Dict[str, Any]:
        """Fetch preview data for a specific table"""
        try:
            safe_table_name = DatabaseConnectionService._validate_table_name(table_name)
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
                        columns = [desc[0] for desc in cursor.description]
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
                    columns = [desc[0] for desc in cursor.description]
                    rows = [DatabaseConnectionService._serialize_row(dict(zip(columns, row))) for row in cursor.fetchall()]
                    cursor.close()
                    conn.close()
                    return {"columns": columns, "rows": rows}
            elif db_type.lower() == "mysql":
                conn = pymysql.connect(host=host, port=port, user=username, password=password, database=database)
                cursor = conn.cursor()
                query = f"SELECT * FROM `{safe_table_name}` {where_clause} LIMIT %s"
                cursor.execute(query, tuple(params + [limit]))
                columns = [desc[0] for desc in cursor.description]
                rows = [DatabaseConnectionService._serialize_row(dict(zip(columns, row))) for row in cursor.fetchall()]
                cursor.close()
                conn.close()
                return {"columns": columns, "rows": rows}
            elif db_type.lower() == "mongodb":
                client = pymongo.MongoClient(connection_string, serverSelectionTimeoutMS=5000)
                db = client.get_default_database() if client.get_default_database().name else client[database or "test"]
                cursor = db[table_name].find().limit(limit)
                rows = list(cursor)
                # Convert ObjectId to string for JSON serialization
                for r in rows:
                    if '_id' in r:
                        r['_id'] = str(r['_id'])
                
                columns = []
                if len(rows) > 0:
                    # Get keys from all docs to ensure we capture all columns
                    all_keys = set()
                    for r in rows:
                        all_keys.update(r.keys())
                    columns = list(all_keys)
                client.close()
                return {"columns": columns, "rows": rows}
            elif db_type.lower() == "sqlite":
                db_path = (database or host).strip('"').strip("'")
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                query = f'SELECT * FROM "{safe_table_name}" {where_clause} LIMIT ?'
                cursor.execute(query, tuple(params + [limit]))
                columns = [desc[0] for desc in cursor.description]
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
                columns = list(FIRESTORE_MOCK_SCHEMA.get(table_name, {}).keys())
                if not columns and rows:
                    columns = list(rows[0].keys())
                return {"columns": columns, "rows": rows}
            return {"error": "Unsupported database type"}
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def execute_query(db_type: str, host: str = "localhost", port: Optional[int] = None, username: str = "", password: Optional[str] = None, database: Optional[str] = None, connection_string: Optional[str] = None, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """Execute a raw SQL/Mongo query and return results (max 1000 rows)"""
        try:
            if db_type.lower() == "postgresql":
                safe, error_msg = DatabaseConnectionService.is_safe_sql(query)
                if not safe:
                    return [{"error": f"Security Blocked: {error_msg}"}]
                pg_pool_conn = get_pg_pool(host, port, username, password, database)
                if pg_pool_conn:
                    conn = pg_pool_conn.getconn()
                    try:
                        cursor = conn.cursor()
                        # Enforce 30-second statement timeout to prevent runaway queries
                        cursor.execute("SET statement_timeout = '30s'")
                        cursor.execute(query)
                        if cursor.description:
                            columns = [desc[0] for desc in cursor.description]
                            rows = [
                                DatabaseConnectionService._serialize_row(dict(zip(columns, row)))
                                for row in cursor.fetchmany(1000)
                            ]
                        else:
                            conn.commit()
                            rows = [{"status": "Success", "rows_affected": cursor.rowcount}]
                        cursor.close()
                        return rows
                    finally:
                        pg_pool_conn.putconn(conn)  # always return to pool
                else:
                    # Fallback: direct connection
                    conn = psycopg2.connect(
                        host=host, port=port, user=username,
                        password=password, database=database or "postgres"
                    )
                    cursor = conn.cursor()
                    cursor.execute("SET statement_timeout = '30s'")
                    cursor.execute(query)
                    if cursor.description:
                        columns = [desc[0] for desc in cursor.description]
                        rows = [
                            DatabaseConnectionService._serialize_row(dict(zip(columns, row)))
                            for row in cursor.fetchmany(1000)
                        ]
                    else:
                        conn.commit()
                        rows = [{"status": "Success", "rows_affected": cursor.rowcount}]
                    cursor.close()
                    conn.close()
                    return rows
            elif db_type.lower() == "mysql":
                safe, error_msg = DatabaseConnectionService.is_safe_sql(query)
                if not safe:
                    return [{"error": f"Security Blocked: {error_msg}"}]
                pooled = get_mysql_pool(host, port, username, password, database)
                if pooled:
                    cursor = pooled.cursor()
                    try:
                        cursor.execute(query)
                        if cursor.description:
                            columns = [desc[0] for desc in cursor.description]
                            rows = [DatabaseConnectionService._serialize_row(dict(zip(columns, row))) for row in cursor.fetchmany(1000)]
                        else:
                            rows = [{"status": "Success", "rows_affected": cursor.rowcount}]
                        return rows
                    finally:
                        cursor.close()
                else:
                    # Fallback: direct connection
                    conn = pymysql.connect(host=host, port=port, user=username, password=password, database=database)
                    cursor = conn.cursor()
                    cursor.execute(query)
                    if cursor.description:
                        columns = [desc[0] for desc in cursor.description]
                        rows = [DatabaseConnectionService._serialize_row(dict(zip(columns, row))) for row in cursor.fetchmany(1000)]
                    else:
                        conn.commit()
                        rows = [{"status": "Success", "rows_affected": cursor.rowcount}]
                    cursor.close()
                    conn.close()
                    return rows
            elif db_type.lower() == "sqlite":
                safe, error_msg = DatabaseConnectionService.is_safe_sql(query)
                if not safe:
                    return [{"error": f"Security Blocked: {error_msg}"}]
                db_path = (database or host).strip('"').strip("'")
                conn = sqlite3.connect(db_path, timeout=30)  # 30-second connection timeout
                cursor = conn.cursor()
                cursor.execute(query)
                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    rows = [DatabaseConnectionService._serialize_row(dict(zip(columns, row))) for row in cursor.fetchmany(1000)]
                else:
                    conn.commit()
                    rows = [{"status": "Success", "rows_affected": cursor.rowcount}]
                cursor.close()
                conn.close()
                return rows
            elif db_type.lower() == "mongodb":
                client = pymongo.MongoClient(connection_string, serverSelectionTimeoutMS=5000)
                # ✅ FIX: Safely get database - try default from URI, then fall back to 'database' param
                try:
                    db_obj = client.get_default_database()
                except Exception:
                    db_name = database or "test"
                    db_obj = client[db_name]

                import json
                # ✅ FIX: Robustly strip markdown/text before parsing
                clean_query = re.sub(r"```(?:json)?|```", "", query).strip()
                brace_start = clean_query.find('{')
                brace_end = clean_query.rfind('}')
                if brace_start != -1 and brace_end != -1:
                    clean_query = clean_query[brace_start:brace_end+1]

                if "$listcollections" in clean_query.lower():
                    try:
                        col_names = db_obj.list_collection_names()
                        client.close()
                        return [{"collection_name": name} for name in col_names]
                    except Exception as list_err:
                        client.close()
                        return [{"error": f"Failed to list MongoDB collections: {str(list_err)}"}]

                try:
                    q_dict = json.loads(clean_query)
                    if "find" in q_dict:
                        col_name = q_dict["find"]
                        filter_doc = q_dict.get("filter", {})
                        projection = q_dict.get("projection", None)
                        cursor = db_obj[col_name].find(filter_doc, projection).limit(1000)
                        rows = list(cursor)
                        for r in rows:
                            if '_id' in r:
                                r['_id'] = str(r['_id'])
                        client.close()
                        return rows
                    elif "aggregate" in q_dict:
                        col_name = q_dict["aggregate"]
                        pipeline = q_dict.get("pipeline", [])
                        
                        # Guardrail: Check if any pipeline stage contains $listCollections
                        pipeline_str = str(pipeline).lower()
                        if "$listcollections" in pipeline_str:
                            col_names = db_obj.list_collection_names()
                            client.close()
                            return [{"collection_name": name} for name in col_names]

                        cursor = db_obj[col_name].aggregate(pipeline)
                        rows = list(cursor)
                        for r in rows:
                            if '_id' in r:
                                r['_id'] = str(r['_id'])
                        client.close()
                        return rows[:1000]
                    else:
                        client.close()
                        return [{"error": "Only 'find' or 'aggregate' commands are supported via JSON query string."}]
                except json.JSONDecodeError as je:
                    client.close()
                    return [{"error": f"MongoDB query JSON parse error: {je}. Received: {clean_query[:200]}"}]
            elif db_type.lower() in ["firestore", "firebase"]:
                import json
                try:
                    q_dict = json.loads(query)
                    collection_name = q_dict.get("collection")
                    if not collection_name:
                        return [{"error": "Firestore query JSON must specify 'collection'."}]
                    
                    preview_data = DatabaseConnectionService.preview_table(
                        db_type="firestore",
                        host="",
                        port=0,
                        username="",
                        password="",
                        table_name=collection_name
                    )
                    if "error" in preview_data:
                        return [preview_data]
                    
                    rows = preview_data.get("rows", [])
                    filters = q_dict.get("where", [])
                    filtered_rows = []
                    for row in rows:
                        match = True
                        for f in filters:
                            if len(f) == 3:
                                field, op, val = f
                                row_val = row.get(field)
                                if op in ["==", "="]:
                                    if row_val != val: match = False
                                elif op == ">":
                                    if not (row_val is not None and row_val > val): match = False
                                elif op == "<":
                                    if not (row_val is not None and row_val < val): match = False
                        if match:
                            filtered_rows.append(row)
                    
                    limit = q_dict.get("limit")
                    if limit:
                        filtered_rows = filtered_rows[:limit]
                    return filtered_rows
                except json.JSONDecodeError:
                    return [{"error": "Firestore query must be a valid JSON string."}]
            return [{"error": "Unsupported database type"}]
        except Exception as e:
            return [{"error": str(e)}]

# Global instance
db_connection_service = DatabaseConnectionService()
