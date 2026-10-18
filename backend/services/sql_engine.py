import os
import re
import sys
import time
import logging
import requests
import concurrent.futures
from typing import Tuple, Dict, Any, List, Optional
from pydantic import BaseModel

logger = logging.getLogger("dataspeak.sql_engine")

# Ensure backend directory is in sys.path for models/crypto imports
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import models
from crypto import decrypt_password
from services.connection_factory import DatabaseConnectionFactory
from services.llm_generation_service import llm_gateway
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import NullPool
from sqlalchemy.exc import SQLAlchemyError


class SafeExecutionRequest(BaseModel):
    sql_query: str
    max_rows: int = 100
    timeout_ceiling: float = 12.0
    statement_timeout_ms: int = 10000
    read_only: bool = True


class SafeExecutionResult(BaseModel):
    columns: List[str]
    rows: List[Dict[str, Any]]
    row_count: int
    is_truncated: bool = False
    execution_time_ms: float
    dialect: Optional[str] = None


def get_connection_url(db_conn: models.DatabaseConnection) -> str | None:
    """
    Constructs a SQLAlchemy connection string from a DatabaseConnection model,
    delegating to DatabaseConnectionFactory for SSRF defense, sandbox enforcement,
    and credential decryption.
    """
    if not db_conn:
        return None
    return DatabaseConnectionFactory.get_connection_url(db_conn)


def sync_database_catalog(db_conn: models.DatabaseConnection, db_session) -> Optional[models.DatabaseSchema]:
    """
    Introspects the target database and persists its schema, tables, and columns
    into DatabaseSchema, TableMetadata, and ColumnMetadata models.
    Flags known PII column patterns (email, password, ssn, phone, credit card, etc.).
    """
    if not db_session:
        return None
    
    connection_url = get_connection_url(db_conn)
    if not connection_url:
        return None
        
    try:
        engine = create_engine(connection_url, poolclass=NullPool)
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        
        schema_name = db_conn.database or "public"
        db_schema = db_session.query(models.DatabaseSchema).filter(
            models.DatabaseSchema.connection_id == db_conn.id,
            models.DatabaseSchema.schema_name == schema_name
        ).first()
        
        if not db_schema:
            db_schema = models.DatabaseSchema(
                connection_id=db_conn.id,
                schema_name=schema_name,
                last_sync=models.utc_now()
            )
            db_session.add(db_schema)
            db_session.flush()
        else:
            db_schema.last_sync = models.utc_now()
            # Clear old metadata to re-sync cleanly:
            # Delete child ColumnMetadata explicitly first to avoid SQLite orphan column accumulation
            old_table_ids = [
                t.id for t in db_session.query(models.TableMetadata.id)
                .filter(models.TableMetadata.schema_id == db_schema.id).all()
            ]
            if old_table_ids:
                db_session.query(models.ColumnMetadata).filter(
                    models.ColumnMetadata.table_id.in_(old_table_ids)
                ).delete(synchronize_session=False)
            db_session.query(models.TableMetadata).filter(
                models.TableMetadata.schema_id == db_schema.id
            ).delete(synchronize_session=False)
            db_session.flush()
            db_session.expunge_all()

        pii_patterns = re.compile(r"(email|password|secret|ssn|token|phone|credit|card|cvv|hash|salary|auth)", re.IGNORECASE)

        for t_name in table_names:
            tbl_meta = models.TableMetadata(
                schema_id=db_schema.id,
                table_name=t_name,
                semantic_description=f"Table {t_name} in {db_conn.name}",
                is_fact_table=bool(re.search(r"(log|event|order|transaction|sale|history|metric)", t_name, re.IGNORECASE)),
                row_count_estimate=0
            )
            db_session.add(tbl_meta)
            db_session.flush()

            columns = inspector.get_columns(t_name)
            pk_constraint = inspector.get_pk_constraint(t_name)
            pk_cols = pk_constraint.get("constrained_columns", []) if pk_constraint else []
            fk_constraints = inspector.get_foreign_keys(t_name) or []

            fk_map = {}
            for fk in fk_constraints:
                for local_col, ref_col in zip(fk.get("constrained_columns", []), fk.get("referred_columns", [])):
                    fk_map[local_col] = f"{fk.get('referred_table')}.{ref_col}"

            for col in columns:
                c_name = col["name"]
                c_type = str(col["type"])
                is_pii_flag = bool(pii_patterns.search(c_name))
                is_pk = c_name in pk_cols
                is_fk = c_name in fk_map
                fk_target = fk_map.get(c_name)

                col_meta = models.ColumnMetadata(
                    table_id=tbl_meta.id,
                    column_name=c_name,
                    data_type=c_type,
                    is_pii=is_pii_flag,
                    is_primary_key=is_pk,
                    is_foreign_key=is_fk,
                    foreign_key_target=fk_target,
                    unit_type=None
                )
                db_session.add(col_meta)

        db_session.commit()
        engine.dispose()
        return db_schema
    except Exception as err:
        db_session.rollback()
        print(f"[CATALOG SYNC] Failed to sync schema catalog for {db_conn.name}: {err}")
        return None


def get_db_schema_context(
    db_conn: models.DatabaseConnection,
    db_session=None,
    allowed_tables: Optional[List[str]] = None
) -> str:
    """
    Introspects the connected database schema and formats tables, columns,
    data types, primary keys, and foreign keys into a clean text prompt context.
    Checks persistent catalog cache (DatabaseSchema) if db_session is provided.
    Filters tables strictly to allowed_tables if specified (NR-1.1-B-T07).
    """
    allowed_set = {t.lower().strip() for t in allowed_tables} if allowed_tables else None

    if db_session:
        cached_schema = db_session.query(models.DatabaseSchema).filter(
            models.DatabaseSchema.connection_id == db_conn.id
        ).first()
        if cached_schema and cached_schema.tables:
            tables_to_format = [
                tbl for tbl in cached_schema.tables
                if not allowed_set or tbl.table_name.lower().strip() in allowed_set
            ]
            schema_lines = [
                f"Database Name: {db_conn.database}",
                f"Database Type: {db_conn.db_type}",
                f"Total Tables: {len(tables_to_format)}",
                "--- SCHEMA DETAILS (PERSISTENT CATALOG) ---"
            ]
            for tbl in tables_to_format:
                schema_lines.append(f"\nTable: {tbl.table_name}")
                for col in tbl.columns:
                    flags = []
                    if getattr(col, "is_primary_key", False):
                        flags.append("PRIMARY KEY")
                    if getattr(col, "is_foreign_key", False) and getattr(col, "foreign_key_target", None):
                        flags.append(f"FOREIGN KEY -> {col.foreign_key_target}")
                    if col.is_pii:
                        flags.append("PII")
                    flag_str = f" [{', '.join(flags)}]" if flags else ""
                    schema_lines.append(f"  - {col.column_name} ({col.data_type}){flag_str}")
            return "\n".join(schema_lines)

    connection_url = get_connection_url(db_conn)
    
    if connection_url:
        try:
            engine = create_engine(connection_url, poolclass=NullPool)
            inspector = inspect(engine)
            table_names = inspector.get_table_names()
            if allowed_set:
                table_names = [t for t in table_names if t.lower().strip() in allowed_set]
            
            schema_lines = [
                f"Database Name: {db_conn.database}",
                f"Database Type: {db_conn.db_type}",
                f"Total Tables: {len(table_names)}",
                "--- SCHEMA DETAILS ---"
            ]
            
            for table_name in table_names:
                schema_lines.append(f"\nTable: {table_name}")
                columns = inspector.get_columns(table_name)
                pk_constraint = inspector.get_pk_constraint(table_name)
                pk_cols = pk_constraint.get("constrained_columns", []) if pk_constraint else []
                fk_constraints = inspector.get_foreign_keys(table_name) or []
                
                fk_map = {}
                for fk in fk_constraints:
                    for local_col, ref_col in zip(fk.get("constrained_columns", []), fk.get("referred_columns", [])):
                        fk_map[local_col] = f"{fk.get('referred_table')}.{ref_col}"
                
                col_descriptions = []
                for col in columns:
                    c_name = col["name"]
                    c_type = str(col["type"])
                    flags = []
                    if c_name in pk_cols:
                        flags.append("PRIMARY KEY")
                    if c_name in fk_map:
                        flags.append(f"FOREIGN KEY -> {fk_map[c_name]}")
                    
                    flag_str = f" [{', '.join(flags)}]" if flags else ""
                    col_descriptions.append(f"  - {c_name} ({c_type}){flag_str}")
                
                schema_lines.extend(col_descriptions)
                
            engine.dispose()

            # Automatically persist into database_schemas, table_metadata, column_metadata if db_session exists
            if db_session:
                try:
                    sync_database_catalog(db_conn, db_session)
                except Exception as sync_err:
                    print(f"[CATALOG SYNC] Opportunistic sync note: {sync_err}")

            return "\n".join(schema_lines)
        except Exception as err:
            # Inspection fallback if physical DB connection fails
            print(f"Database introspection warning for {db_conn.name}: {err}")

    # Fallback simulated schema for demo / non-relational / unreachable DBs
    simulated_tables = {
        "users": [
            "  - id (INTEGER) [PRIMARY KEY]",
            "  - email (VARCHAR)",
            "  - full_name (VARCHAR)",
            "  - role (VARCHAR)",
            "  - is_active (BOOLEAN)",
            "  - created_at (TIMESTAMP)"
        ],
        "orders": [
            "  - id (INTEGER) [PRIMARY KEY]",
            "  - user_id (INTEGER) [FOREIGN KEY -> users.id]",
            "  - total_amount (DECIMAL)",
            "  - status (VARCHAR)",
            "  - created_at (TIMESTAMP)"
        ],
        "products": [
            "  - id (INTEGER) [PRIMARY KEY]",
            "  - name (VARCHAR)",
            "  - category (VARCHAR)",
            "  - price (DECIMAL)",
            "  - stock_quantity (INTEGER)"
        ]
    }
    schema_lines = [
        f"Database Name: {db_conn.database}",
        f"Database Type: {db_conn.db_type}",
        "--- SIMULATED SCHEMA DETAILS ---"
    ]
    for tbl_name, cols in simulated_tables.items():
        if not allowed_set or tbl_name.lower().strip() in allowed_set:
            schema_lines.append(f"\nTable: {tbl_name}")
            schema_lines.extend(cols)
    return "\n".join(schema_lines)


def validate_read_only_sql(sql_query: str, dialect: Optional[str] = None) -> Tuple[bool, str]:
    """
    Enforces strict read-only SELECT guardrails via sqlglot AST parsing:
    1. Rejects empty queries or syntax parse failures.
    2. Rejects multiple statements (preventing stacked queries via semicolons).
    3. Requires root statement to be a SELECT or UNION (including CTEs).
    4. Rejects all write expression nodes (INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, MERGE, etc.).
    5. Rejects file writes (INTO OUTFILE/DUMPFILE, SELECT INTO) and administrative commands.
    """
    if not sql_query or not sql_query.strip():
        return False, "Query cannot be empty."

    # Strip inline and block comments to prevent semicolon-hiding tricks
    clean_sql = re.sub(r'--.*$', ' ', sql_query, flags=re.MULTILINE)
    clean_sql = re.sub(r'/\*.*?\*/', ' ', clean_sql, flags=re.DOTALL).strip()

    # Check for trailing semicolon and internal semicolons
    semicolon_count = clean_sql.count(';')
    if semicolon_count > 1 or (semicolon_count == 1 and not clean_sql.endswith(';')):
        return False, "Multiple SQL statements separated by semicolons are strictly forbidden."

    clean_sql_no_semi = clean_sql.rstrip(';').strip()

    # Parse with sqlglot
    import sqlglot
    from sqlglot import exp
    from sqlglot.errors import ParseError

    dialect_clean = (dialect or "").lower()
    glot_dialect = None
    if "postgres" in dialect_clean:
        glot_dialect = "postgres"
    elif "mysql" in dialect_clean or "mariadb" in dialect_clean:
        glot_dialect = "mysql"
    elif "sqlite" in dialect_clean:
        glot_dialect = "sqlite"

    try:
        statements = sqlglot.parse(clean_sql_no_semi, read=glot_dialect)
    except ParseError as err:
        try:
            statements = sqlglot.parse(clean_sql_no_semi)
        except Exception:
            return False, f"SQL parse error: {str(err)}"
    except Exception as e:
        return False, f"SQL validation error: {str(e)}"

    statements = [s for s in statements if s is not None]
    if not statements:
        return False, "Query contains no executable SQL statements."
    if len(statements) > 1:
        return False, "Multiple SQL statements separated by semicolons are strictly forbidden."

    root_stmt = statements[0]

    # Must be a Select or Union
    if not isinstance(root_stmt, (exp.Select, exp.Union)):
        op_label = root_stmt.key.upper() if hasattr(root_stmt, "key") else type(root_stmt).__name__.upper()
        return False, f"Only read-only SELECT or WITH (CTE) queries are permitted. Got statement type: {op_label}."

    # Check for INTO clause (e.g. SELECT ... INTO table)
    if root_stmt.args.get("into"):
        return False, "SELECT INTO table operations are forbidden."

    # Traverse AST to ensure no write operations are present in subqueries, CTEs, or expressions
    FORBIDDEN_EXPRESSIONS = (
        exp.Insert,
        exp.Update,
        exp.Delete,
        exp.Drop,
        exp.Alter,
        exp.Create,
        exp.Merge,
        exp.Command,
    )

    for node in root_stmt.walk():
        if isinstance(node, FORBIDDEN_EXPRESSIONS):
            op_name = node.key.upper() if hasattr(node, "key") else type(node).__name__.upper()
            return False, f"Forbidden write expression detected: '{op_name}'. Read-only SELECT operations only."

    return True, ""


def extract_sql_referenced_tables(clean_sql: str) -> List[str]:
    """
    Extracts all physical table identifiers referenced in a SQL query using sqlglot AST parsing.
    Correctly handles:
    - Comma joins: SELECT * FROM t1, t2
    - Quoted/backticked identifiers: SELECT * FROM `users`, "orders"
    - Schema-qualified names: SELECT * FROM public.users
    - Subqueries: SELECT * FROM (SELECT * FROM sub_tbl) s
    - UNION / INTERSECT / EXCEPT
    - CTEs: WITH cte AS (SELECT * FROM base_tbl) SELECT * FROM cte -> correctly returns ['base_tbl'], ignoring cte alias
    Fails closed: raises ValueError if AST parsing fails (SEC-02).
    """
    import sqlglot
    from sqlglot import exp

    parsed = None
    for d in [None, "mysql", "postgres", "sqlite"]:
        try:
            parsed = sqlglot.parse_one(clean_sql, read=d)
            if parsed is not None:
                break
        except Exception:
            continue

    if parsed is None:
        raise ValueError("SQL parsing failed: Unable to parse query AST deterministically.")

    try:
        ctes = set()
        for cte in parsed.find_all(exp.CTE):
            if cte.alias_or_name:
                ctes.add(cte.alias_or_name.lower().strip())

        tables = set()
        for t in parsed.find_all(exp.Table):
            name = t.name.lower().strip()
            if name and name not in ctes and not name.startswith("safe_limit_wrapper"):
                if t.catalog:
                    catalog_part = t.catalog.lower().strip()
                    db_part = t.db.lower().strip() if t.db else ""
                    if db_part:
                        tables.add(f"{catalog_part}.{db_part}.{name}")
                    else:
                        tables.add(f"{catalog_part}.{name}")
                elif t.db:
                    tables.add(f"{t.db.lower().strip()}.{name}")
                else:
                    tables.add(name)
        return sorted(list(tables))
    except Exception as exc:
        raise ValueError(f"SQL parsing failed: {exc}")


def validate_widget_sql(sql_query: str, allowed_tables: Optional[List[str]] = None) -> Tuple[bool, str]:
    """
    Strict deterministic SQL validation for embeddable chatbot widget:
    1. Runs full validate_read_only_sql checks (read-only, no DDL/DML, single statement).
    2. Enforces fail-closed AST parsing via sqlglot (SEC-02).
    3. Blocks access to system catalog tables (pg_*, sqlite_*, information_schema, sys, etc.).
    4. Enforces strict exact table allowlist matching (SEC-01, no tbl.split('.')[-1] bypass).
    5. Detects CTE trickery, UNION to disallowed tables, comma joins, and stacked injection attempts.
    """
    is_valid, reason = validate_read_only_sql(sql_query)
    if not is_valid:
        return False, reason

    clean_sql = re.sub(r'--.*$', ' ', sql_query, flags=re.MULTILINE)
    clean_sql = re.sub(r'/\*.*?\*/', ' ', clean_sql, flags=re.DOTALL).strip()
    upper_sql = clean_sql.upper()

    # System table protections
    system_table_patterns = [
        r'\bPG_\w+',
        r'\bPG_CATALOG\b',
        r'\bINFORMATION_SCHEMA\b',
        r'\bSQLITE_MASTER\b',
        r'\bSQLITE_SCHEMA\b',
        r'\bSQLITE_TEMP_MASTER\b',
        r'\bSQLITE_SEQUENCE\b',
        r'\bMYSQL\.\w+',
        r'\bPERFORMANCE_SCHEMA\b',
        r'\bSYS\.\w+',
        r'\bSYSOBJECTS\b',
        r'\bSYSCOLUMNS\b'
    ]
    for pattern in system_table_patterns:
        if re.search(pattern, upper_sql, re.IGNORECASE):
            return False, "Access to system catalog tables is prohibited."

    # Always enforce AST parsing fail-closed (SEC-02)
    try:
        referenced_tables = extract_sql_referenced_tables(clean_sql)
    except ValueError as parse_err:
        return False, str(parse_err)
    except Exception as exc:
        return False, f"SQL parsing failed: {str(exc)}"

    # If allowed_tables is provided and non-empty, verify all referenced tables with strict exact matching (SEC-01)
    if allowed_tables:
        allowed_set = {t.lower().strip() for t in allowed_tables}
        for tbl in referenced_tables:
            if tbl not in allowed_set:
                return False, f"Access to table '{tbl}' is not permitted for this widget key."

    return True, ""


def generate_sql_from_nl(
    db_conn: models.DatabaseConnection,
    user_question: str,
    db_session=None,
    tenant_id: Optional[int] = None,
    allowed_tables: Optional[List[str]] = None,
    conversation_history: Optional[str] = None
) -> Dict[str, Any]:
    """
    Uses SQLAgent (with AST schema validation, SAVEPOINT rollback dry-runs,
    and automatic in-flight retry loop) to generate a verified, read-only SQL query.
    Enforces allowed_tables restriction if provided (NR-1.1-B-T07).
    """
    try:
        from services.sql_agent import sql_agent
        return sql_agent.run(
            db_conn=db_conn,
            user_question=user_question,
            db_session=db_session,
            tenant_id=tenant_id,
            allowed_tables=allowed_tables,
            conversation_history=conversation_history
        )
    except Exception as agent_err:
        logger.error(f"[SQL Engine] SQLAgent run failed, using standard fallback: {agent_err}")
        schema_ctx = get_db_schema_context(db_conn, db_session, allowed_tables=allowed_tables)
        fallback_table = "users"
        if allowed_tables:
            fallback_table = allowed_tables[0]
        elif "Table: " in schema_ctx:
            tables = re.findall(r'Table:\s*(\w+)', schema_ctx)
            if tables:
                fallback_table = tables[0]

        return {
            "sql": f"SELECT * FROM {fallback_table} LIMIT 10;",
            "explanation": f"Generated safe fallback preview query on table '{fallback_table}'.",
            "schema_context": schema_ctx,
            "attempts": 1,
            "corrections_made": False,
            "status": "failed",
            "error": str(agent_err)
        }



PII_COLUMN_PATTERNS = [
    r'password', r'passwd', r'secret', r'token', r'ssn', r'credit_card',
    r'card_number', r'cvv', r'api_key', r'auth_token', r'private_key'
]


def mask_pii_rows(columns: Any, rows: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """
    Masks values in columns containing sensitive PII keywords with '[REDACTED]'.
    Can be called either as mask_pii_rows(rows) or mask_pii_rows(columns, rows).
    """
    if rows is None:
        row_list = columns if isinstance(columns, list) else []
        if not row_list:
            return []
        col_list = set()
        for r in row_list:
            if isinstance(r, dict):
                col_list.update(r.keys())
    else:
        row_list = rows
        if columns:
            col_list = set(columns)
        else:
            col_list = set()
            for r in row_list:
                if isinstance(r, dict):
                    col_list.update(r.keys())

    pii_cols = set()
    for col in col_list:
        col_lower = str(col).lower()
        if any(re.search(pat, col_lower) for pat in PII_COLUMN_PATTERNS):
            pii_cols.add(col)

    if not pii_cols:
        return row_list

    masked_rows = []
    for r in row_list:
        masked_r = {}
        for k, v in r.items():
            if k in pii_cols:
                masked_r[k] = "[REDACTED]"
            else:
                masked_r[k] = v
        masked_rows.append(masked_r)
    return masked_rows


def _make_json_serializable(val: Any) -> Any:
    """Helper to ensure all SQL result values are standard JSON serializable."""
    if val is None:
        return None
    if isinstance(val, (int, float, str, bool)):
        return val
    return str(val)


def execute_safe_sql(
    db_conn: models.DatabaseConnection,
    sql_query: str | SafeExecutionRequest,
    max_rows: int = 100,
    timeout_ceiling: float = 12.0
) -> Dict[str, Any]:
    """
    Validates, caps with outer LIMIT wrapper, and safely executes a read-only SQL query
    against the target database. Enforces statement timeout, read-only mode, and PII masking.
    Returns structured columns, rows, count, is_truncated flag, and execution time.
    """
    if isinstance(sql_query, SafeExecutionRequest):
        req = sql_query
        actual_query = req.sql_query
        max_rows = req.max_rows
        timeout_ceiling = req.timeout_ceiling
    else:
        actual_query = sql_query

    is_valid, reason = validate_read_only_sql(actual_query)
    if not is_valid:
        raise ValueError(f"SQL Guardrail Violation: {reason}")

    clean_sql = actual_query.strip().rstrip(';').strip()

    # Outer LIMIT bounding (Task NR-1.2-B-T05, Defect I-08)
    fetch_limit = max_rows + 1
    capped_sql = f"SELECT * FROM ({clean_sql}) AS _dataspeak_bounded_q LIMIT {fetch_limit}"

    connection_url = DatabaseConnectionFactory.get_connection_url(db_conn)
    if not connection_url:
        raise RuntimeError(
            f"Database connection unavailable or unsupported dialect for database "
            f"'{getattr(db_conn, 'name', 'unknown')}'"
        )

    start_time = time.time()
    connect_args = {}
    db_type = (db_conn.db_type or "").lower()
    if "sqlite" in db_type:
        connect_args = {"timeout": 10.0}
    elif "postgres" in db_type:
        connect_args = {"options": "-c default_transaction_read_only=on -c statement_timeout=10000"}
    elif "mariadb" in db_type:
        connect_args = {
            "connect_timeout": 10,
            "init_command": "SET SESSION max_statement_time=10.0"
        }
    elif "mysql" in db_type:
        connect_args = {
            "connect_timeout": 10,
            "init_command": "SET SESSION max_execution_time=10000"
        }

    def _apply_dialect_guardrails(conn_handle):
        try:
            if "sqlite" in db_type:
                conn_handle.execute(text("PRAGMA query_only = ON;"))
                conn_handle.execute(text("PRAGMA busy_timeout = 10000;"))
            elif "postgres" in db_type:
                conn_handle.execute(text("SET statement_timeout = 10000;"))
                conn_handle.execute(text("SET TRANSACTION READ ONLY;"))
            elif "mariadb" in db_type:
                conn_handle.execute(text("SET SESSION TRANSACTION READ ONLY;"))
                try:
                    conn_handle.execute(text("SET SESSION max_statement_time = 10.0;"))
                except Exception as var_err:
                    logger.warning(f"Could not set MariaDB max_statement_time: {var_err}")
            elif "mysql" in db_type:
                conn_handle.execute(text("SET SESSION TRANSACTION READ ONLY;"))
                try:
                    conn_handle.execute(text("SET SESSION max_execution_time = 10000;"))
                except Exception as var_err:
                    logger.warning(f"Could not set MySQL max_execution_time: {var_err}")
        except Exception as err:
            logger.error(f"[SECURITY GUARDRAIL ERROR] Dialect guardrail failure ({db_type}): {err}")
            raise RuntimeError(f"Database security guardrail application failed: {str(err)}")

    active_conn_info = {"dbapi": None, "engine": None}

    def _run_query_internal():
        try:
            engine = create_engine(connection_url, poolclass=NullPool, connect_args=connect_args)
            active_conn_info["engine"] = engine
            with engine.connect() as conn:
                try:
                    active_conn_info["dbapi"] = conn.connection.dbapi_connection
                except Exception:
                    pass
                _apply_dialect_guardrails(conn)

                result = conn.execute(text(capped_sql))
                columns = list(result.keys())
                raw_rows = result.fetchmany(fetch_limit)

                is_truncated = False
                if len(raw_rows) > max_rows:
                    is_truncated = True
                    raw_rows = raw_rows[:max_rows]

                rows = [
                    {col: _make_json_serializable(val) for col, val in zip(columns, row)}
                    for row in raw_rows
                ]
                rows = mask_pii_rows(columns, rows)

            engine.dispose()
            exec_time_ms = round((time.time() - start_time) * 1000, 2)
            return {
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "is_truncated": is_truncated,
                "execution_time_ms": exec_time_ms
            }
        except SQLAlchemyError as sqle:
            # Fallback if outer subquery wrapper encounters dialect syntax limitation
            try:
                engine = create_engine(connection_url, poolclass=NullPool, connect_args=connect_args)
                active_conn_info["engine"] = engine
                with engine.connect() as conn:
                    try:
                        active_conn_info["dbapi"] = conn.connection.dbapi_connection
                    except Exception:
                        pass
                    _apply_dialect_guardrails(conn)
                    m = re.search(r'\bLIMIT\s+(\d+)', clean_sql, re.IGNORECASE)
                    if m:
                        existing_limit = int(m.group(1))
                        effective_limit = min(existing_limit, fetch_limit)
                        fallback_capped = re.sub(r'\bLIMIT\s+\d+', f'LIMIT {effective_limit}', clean_sql, flags=re.IGNORECASE)
                    else:
                        fallback_capped = f"{clean_sql} LIMIT {fetch_limit}"

                    result = conn.execute(text(fallback_capped))
                    columns = list(result.keys())
                    raw_rows = result.fetchmany(fetch_limit)

                    is_truncated = False
                    if len(raw_rows) > max_rows:
                        is_truncated = True
                        raw_rows = raw_rows[:max_rows]

                    rows = [
                        {col: _make_json_serializable(val) for col, val in zip(columns, row)}
                        for row in raw_rows
                    ]
                    rows = mask_pii_rows(columns, rows)

                engine.dispose()
                exec_time_ms = round((time.time() - start_time) * 1000, 2)
                return {
                    "columns": columns,
                    "rows": rows,
                    "row_count": len(rows),
                    "is_truncated": is_truncated,
                    "execution_time_ms": exec_time_ms
                }
            except Exception as e:
                raise RuntimeError(f"Database execution error: {str(sqle)}")
        except Exception as e:
            raise RuntimeError(f"Execution error: {str(e)}")

    # Execute query within strict fail-safe execution watchdog
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(_run_query_internal)
        return future.result(timeout=timeout_ceiling)
    except concurrent.futures.TimeoutError:
        raw_dbapi = active_conn_info.get("dbapi")
        if raw_dbapi:
            try:
                if hasattr(raw_dbapi, "interrupt"):
                    raw_dbapi.interrupt()
                elif hasattr(raw_dbapi, "cancel"):
                    raw_dbapi.cancel()
            except Exception as cancel_err:
                logger.warning(f"Failed to cancel timed out database connection: {cancel_err}")
        
        eng = active_conn_info.get("engine")
        if eng:
            try:
                eng.dispose()
            except Exception:
                pass

        executor.shutdown(wait=False, cancel_futures=True)
        raise RuntimeError(
            f"Database execution timeout exceeded (10s dialect statement limit / {int(timeout_ceiling)}s watchdog for {db_type})"
        )
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
