import os
import re
import sys
import time
import requests
from typing import Tuple, Dict, Any, List, Optional

# Ensure backend directory is in sys.path for models/crypto imports
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import models
from crypto import decrypt_password
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import NullPool
from sqlalchemy.exc import SQLAlchemyError


def get_connection_url(db_conn: models.DatabaseConnection) -> str | None:
    """
    Constructs a SQLAlchemy connection string from a DatabaseConnection model,
    decrypting the stored password.
    """
    if not db_conn:
        return None
    raw_password = decrypt_password(db_conn.password)
    if db_conn.db_type == "postgresql":
        return f"postgresql://{db_conn.username}:{raw_password}@{db_conn.host}/{db_conn.database}"
    elif db_conn.db_type in ("mysql", "mariadb"):
        return f"mysql+pymysql://{db_conn.username}:{raw_password}@{db_conn.host}/{db_conn.database}"
    elif db_conn.db_type == "sqlite":
        return f"sqlite:///{db_conn.database}"
    return None


def get_db_schema_context(db_conn: models.DatabaseConnection, db_session=None) -> str:
    """
    Introspects the connected database schema and formats tables, columns,
    data types, primary keys, and foreign keys into a clean text prompt context.
    """
    connection_url = get_connection_url(db_conn)
    
    if connection_url:
        try:
            engine = create_engine(connection_url, poolclass=NullPool)
            inspector = inspect(engine)
            table_names = inspector.get_table_names()
            
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
            return "\n".join(schema_lines)
        except Exception as err:
            # Inspection fallback if physical DB connection fails
            print(f"Database introspection warning for {db_conn.name}: {err}")

    # Fallback simulated schema for demo / non-relational / unreachable DBs
    return (
        f"Database Name: {db_conn.database}\n"
        f"Database Type: {db_conn.db_type}\n"
        "--- SIMULATED SCHEMA DETAILS ---\n"
        "\nTable: users\n"
        "  - id (INTEGER) [PRIMARY KEY]\n"
        "  - email (VARCHAR)\n"
        "  - full_name (VARCHAR)\n"
        "  - role (VARCHAR)\n"
        "  - is_active (BOOLEAN)\n"
        "  - created_at (TIMESTAMP)\n"
        "\nTable: orders\n"
        "  - id (INTEGER) [PRIMARY KEY]\n"
        "  - user_id (INTEGER) [FOREIGN KEY -> users.id]\n"
        "  - total_amount (DECIMAL)\n"
        "  - status (VARCHAR)\n"
        "  - created_at (TIMESTAMP)\n"
        "\nTable: products\n"
        "  - id (INTEGER) [PRIMARY KEY]\n"
        "  - name (VARCHAR)\n"
        "  - category (VARCHAR)\n"
        "  - price (DECIMAL)\n"
        "  - stock_quantity (INTEGER)\n"
    )


def validate_read_only_sql(sql_query: str) -> Tuple[bool, str]:
    """
    Enforces strict read-only SELECT guardrails:
    1. Rejects DDL / DML write keywords (INSERT, UPDATE, DELETE, DROP, ALTER, etc.).
    2. Rejects statement chaining via semicolons to prevent stacked query injection.
    3. Requires statement to start with SELECT or WITH (for CTEs leading to SELECT).
    4. Rejects file writes (INTO OUTFILE/DUMPFILE), administrative calls, and copy commands.
    """
    if not sql_query or not sql_query.strip():
        return False, "Query cannot be empty."

    # Strip inline comments (replacing with a space to prevent token-stitching tricks)
    clean_sql = re.sub(r'--.*$', ' ', sql_query, flags=re.MULTILINE)
    clean_sql = re.sub(r'/\*.*?\*/', ' ', clean_sql, flags=re.DOTALL).strip()

    # Check for trailing semicolon and internal semicolons
    semicolon_count = clean_sql.count(';')
    if semicolon_count > 1 or (semicolon_count == 1 and not clean_sql.endswith(';')):
        return False, "Multiple SQL statements separated by semicolons are strictly forbidden."

    clean_sql_no_semi = clean_sql.rstrip(';').strip()

    # Must begin with SELECT or WITH
    upper_sql = clean_sql_no_semi.upper()
    if not (upper_sql.startswith("SELECT") or upper_sql.startswith("WITH")):
        return False, "Only read-only SELECT or WITH (CTE) queries are permitted."

    # Forbidden DDL / DML / Admin operations (including inside CTEs and subqueries)
    forbidden_pattern = (
        r'\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|RENAME|GRANT|REVOKE|'
        r'REPLACE|EXEC|EXECUTE|SHUTDOWN|MERGE|UPSERT|ATTACH|DETACH|INTO|CALL|'
        r'DECLARE|COPY|LOAD|OUTFILE|DUMPFILE|PRAGMA)\b'
    )
    match = re.search(forbidden_pattern, upper_sql)
    if match:
        return False, f"Forbidden keyword detected: '{match.group(1)}'. Read-only SELECT operations only."

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
    Fails closed: raises ValueError if AST parsing fails.
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
        raise ValueError("Failed to parse SQL query AST; query cannot be safely verified.")

    ctes = set()
    for cte in parsed.find_all(exp.CTE):
        if cte.alias_or_name:
            ctes.add(cte.alias_or_name.lower().strip())

    tables = set()
    for t in parsed.find_all(exp.Table):
        name = t.name.lower().strip()
        if name and name not in ctes and not name.startswith("safe_limit_wrapper"):
            if t.db:
                tables.add(f"{t.db.lower().strip()}.{name}")
            else:
                tables.add(name)
    return sorted(list(tables))


def validate_widget_sql(sql_query: str, allowed_tables: Optional[List[str]] = None) -> Tuple[bool, str]:
    """
    Strict deterministic SQL validation for embeddable chatbot widget:
    1. Runs full validate_read_only_sql checks (read-only, no DDL/DML, single statement).
    2. Enforces AST parsing (fails closed if sqlglot cannot parse).
    3. Blocks access to system catalog tables (pg_*, sqlite_*, information_schema, sys, etc.).
    4. Enforces table allowlist with exact matching against full referenced names (no tbl.split('.')[-1] bypass).
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

    # Parse AST and extract referenced tables (fail closed on invalid/unparseable SQL)
    try:
        referenced_tables = extract_sql_referenced_tables(clean_sql)
    except Exception as e:
        return False, f"SQL parsing failed: {str(e)}"

    # If allowed_tables is provided and non-empty, verify all referenced tables against exact names
    if allowed_tables:
        allowed_set = {t.lower().strip() for t in allowed_tables}
        for tbl in referenced_tables:
            if tbl not in allowed_set:
                return False, f"Access to table '{tbl}' is not permitted for this widget key."

    return True, ""


def generate_sql_from_nl(db_conn: models.DatabaseConnection, user_question: str, db_session=None) -> Dict[str, Any]:
    """
    Uses Google Gemini 2.5 Flash API to generate a read-only SQL query and explanation
    from natural language and schema context. Includes graceful fallback if GEMINI_API_KEY is unset.
    """
    schema_ctx = get_db_schema_context(db_conn, db_session)
    api_key = os.getenv("GEMINI_API_KEY")

    if api_key:
        try:
            gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
            gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={api_key}"
            prompt = (
                f"You are a Senior SQL & Database Engineer. Given the following database schema context and user question, "
                f"generate a valid, read-only SQL query ({db_conn.db_type} dialect) and a short explanation.\n\n"
                "CRITICAL SECURITY RULES:\n"
                "1. Output ONLY a single read-only SELECT or WITH statement.\n"
                "2. NEVER use DDL/DML keywords (INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, etc.).\n"
                "3. Do NOT include multiple statements or semicolons.\n"
                "4. Format your output EXACTLY with the following structure:\n"
                "```sql\n<your SQL query here>\n```\n"
                "Explanation: <1-2 sentence explanation of how the query works>\n\n"
                f"DATABASE SCHEMA:\n{schema_ctx}\n\n"
                f"USER QUESTION: {user_question}"
            )

            payload = {
                "contents": [{"parts": [{"text": prompt}]}]
            }
            headers = {"Content-Type": "application/json"}
            res = requests.post(gemini_url, json=payload, headers=headers, timeout=25)

            if res.status_code == 200:
                res_data = res.json()
                raw_text = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                
                # Extract SQL block
                sql_match = re.search(r'```sql\s*(.*?)\s*```', raw_text, re.DOTALL | re.IGNORECASE)
                if sql_match:
                    generated_sql = sql_match.group(1).strip()
                else:
                    # Fallback extraction if LLM didn't format code blocks
                    generated_sql = raw_text.split('\n')[0].strip()

                # Extract Explanation
                explanation_match = re.search(r'Explanation:\s*(.*)', raw_text, re.IGNORECASE | re.DOTALL)
                if explanation_match:
                    explanation = explanation_match.group(1).strip()
                else:
                    explanation = f"Generated {db_conn.db_type} query to answer: '{user_question}'."

                # Validate generated SQL against security guardrails
                is_valid, reason = validate_read_only_sql(generated_sql)
                if not is_valid:
                    return {
                        "sql": "",
                        "explanation": f"Security Guardrail Triggered: {reason}",
                        "schema_context": schema_ctx,
                        "error": reason
                    }

                return {
                    "sql": generated_sql,
                    "explanation": explanation,
                    "schema_context": schema_ctx,
                    "error": None
                }
            else:
                print(f"Gemini API call failed with status {res.status_code}: {res.text}")
        except Exception as e:
            print(f"Error calling Gemini API for NL-to-SQL: {e}")

    # Fallback if GEMINI_API_KEY is unconfigured or request failed
    fallback_table = "users"
    if "Table: " in schema_ctx:
        tables = re.findall(r'Table:\s*(\w+)', schema_ctx)
        if tables:
            fallback_table = tables[0]

    fallback_sql = f"SELECT * FROM {fallback_table} LIMIT 10;"
    fallback_exp = (
        "Note: GEMINI_API_KEY is not configured or LLM endpoint was unreachable. "
        f"Generated safe fallback preview query on table '{fallback_table}'."
    )

    return {
        "sql": fallback_sql,
        "explanation": fallback_exp,
        "schema_context": schema_ctx,
        "error": None
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


def execute_safe_sql(db_conn: models.DatabaseConnection, sql_query: str, max_rows: int = 100) -> Dict[str, Any]:
    """
    Validates, caps with LIMIT max_rows, and safely executes a read-only SQL query
    against the target database. Enforces statement timeout, read-only mode, and PII masking.
    Returns structured columns, rows, count, and execution time.
    """
    is_valid, reason = validate_read_only_sql(sql_query)
    if not is_valid:
        raise ValueError(f"SQL Guardrail Violation: {reason}")

    # Remove trailing semicolon for LIMIT capping
    clean_sql = sql_query.strip().rstrip(';')

    # Enforce LIMIT max_rows capping
    if not re.search(r'\bLIMIT\s+\d+', clean_sql, re.IGNORECASE):
        # Wrap query in a subquery or append LIMIT
        if clean_sql.upper().startswith("WITH "):
            # For CTEs, append LIMIT max_rows at the end
            capped_sql = f"{clean_sql} LIMIT {max_rows}"
        else:
            capped_sql = f"SELECT * FROM ({clean_sql}) AS safe_limit_wrapper LIMIT {max_rows}"
    else:
        capped_sql = clean_sql

    connection_url = get_connection_url(db_conn)
    start_time = time.time()

    if connection_url:
        connect_args = {}
        db_type = (db_conn.db_type or "").lower()
        if "sqlite" in db_type:
            connect_args = {"timeout": 10}
        elif "postgres" in db_type:
            connect_args = {"options": "-c default_transaction_read_only=on -c statement_timeout=10000"}
        elif "mysql" in db_type or "mariadb" in db_type:
            connect_args = {"connect_timeout": 10}

        def _apply_dialect_guardrails(conn_handle):
            try:
                if "sqlite" in db_type:
                    conn_handle.execute(text("PRAGMA query_only = ON;"))
                elif "postgres" in db_type:
                    conn_handle.execute(text("SET statement_timeout = 10000;"))
                    conn_handle.execute(text("SET TRANSACTION READ ONLY;"))
                elif "mysql" in db_type or "mariadb" in db_type:
                    conn_handle.execute(text("SET SESSION TRANSACTION READ ONLY;"))
                    conn_handle.execute(text("SET SESSION max_execution_time = 10000;"))
            except Exception as err:
                print(f"[SECURITY GUARDRAIL ERROR] Dialect guardrail failure ({db_type}): {err}")
                raise RuntimeError(f"Database security guardrail application failed: {str(err)}")

        try:
            engine = create_engine(connection_url, poolclass=NullPool, connect_args=connect_args)
            with engine.connect() as conn:
                _apply_dialect_guardrails(conn)

                result = conn.execute(text(capped_sql))
                columns = list(result.keys())
                raw_rows = result.fetchall()

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
                "execution_time_ms": exec_time_ms
            }
        except SQLAlchemyError as sqle:
            # If subquery wrapper fails on specific DB syntax, try direct LIMIT append
            try:
                engine = create_engine(connection_url, poolclass=NullPool, connect_args=connect_args)
                with engine.connect() as conn:
                    _apply_dialect_guardrails(conn)
                    fallback_capped = f"{clean_sql} LIMIT {max_rows}"
                    result = conn.execute(text(fallback_capped))
                    columns = list(result.keys())
                    raw_rows = result.fetchall()
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
                    "execution_time_ms": exec_time_ms
                }
            except Exception as e:
                raise RuntimeError(f"Database execution error: {str(sqle)}")
        except Exception as e:
            raise RuntimeError(f"Execution error: {str(e)}")

    # Fallback simulated data execution for non-relational or simulated DBs
    time.sleep(0.05)  # Simulate brief processing delay
    exec_time_ms = round((time.time() - start_time) * 1000, 2)

    mock_columns = ["id", "name", "email", "role", "created_at"]
    mock_rows = [
        {"id": 101, "name": "Alice Smith", "email": "alice@example.com", "role": "Admin", "created_at": "2026-01-15 10:30:00"},
        {"id": 102, "name": "Bob Jones", "email": "bob@example.com", "role": "Developer", "created_at": "2026-02-01 14:20:00"},
        {"id": 103, "name": "Charlie Brown", "email": "charlie@example.com", "role": "Business Owner", "created_at": "2026-03-10 09:15:00"},
        {"id": 104, "name": "Diana Prince", "email": "diana@example.com", "role": "Developer", "created_at": "2026-04-05 16:45:00"},
    ]
    return {
        "columns": mock_columns,
        "rows": mask_pii_rows(mock_columns, mock_rows),
        "row_count": len(mock_rows),
        "execution_time_ms": exec_time_ms
    }
