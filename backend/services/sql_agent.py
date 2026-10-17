"""
DataSpeakAI — Self-Correcting SQL Agent (Phase 7: Task 7.2.1)

Iterative agentic execution loop (MAX_CORRECTION_ATTEMPTS = 3):
1. Generates candidate SQL from natural language prompt + schema context via LLMGateway.
2. Validates SQL security guardrails (read-only, no DDL/DML, no system catalog tables).
3. Validates AST identifiers (tables & columns) against SchemaRegistry / DatabaseSchema using sqlglot.
4. Executes dialect-safe dry-runs inside an isolated nested transaction (SAVEPOINT with immediate rollback).
5. If validation or dry-run fails, feeds exact database error messages back into the LLM for in-flight self-correction.
"""

import re
import logging
from typing import Dict, Any, List, Set, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect, create_engine
from sqlalchemy.pool import NullPool

import models
from services.llm_generation_service import llm_gateway
from services.sql_engine import (
    get_db_schema_context,
    get_connection_url,
    validate_read_only_sql,
    extract_sql_referenced_tables
)

logger = logging.getLogger("dataspeak.sql_agent")


class SQLAgent:
    """
    Agentic SQL generator with AST verification, dialect-safe rollback dry-runs,
    and automatic multi-turn error correction.
    """

    def __init__(self, max_attempts: int = 3):
        self.max_attempts = max_attempts

    def get_known_schema(
        self,
        db_conn: models.DatabaseConnection,
        db_session: Optional[Session] = None
    ) -> Dict[str, Set[str]]:
        """
        Extracts a dictionary of {table_name: set(column_names)} in lowercase
        from DatabaseSchema, SchemaRegistry, or live reflection.
        """
        schema_map: Dict[str, Set[str]] = {}

        # 1. Try persistent DatabaseSchema catalog
        if db_session:
            try:
                cached_schema = db_session.query(models.DatabaseSchema).filter(
                    models.DatabaseSchema.connection_id == db_conn.id
                ).first()
                if cached_schema and cached_schema.tables:
                    for tbl in cached_schema.tables:
                        t_name = tbl.table_name.lower().strip()
                        cols = {c.column_name.lower().strip() for c in tbl.columns}
                        schema_map[t_name] = cols
                    if schema_map:
                        return schema_map
            except Exception as e:
                logger.debug(f"Catalog lookup note: {e}")

        # 2. Try SchemaRegistry
        if db_session:
            try:
                reg_entries = db_session.query(models.SchemaRegistry).filter(
                    models.SchemaRegistry.connection_id == db_conn.id
                ).all()
                if reg_entries:
                    for entry in reg_entries:
                        t_name = entry.table_name.lower().strip()
                        c_name = entry.column_name.lower().strip()
                        schema_map.setdefault(t_name, set()).add(c_name)
                    if schema_map:
                        return schema_map
            except Exception as e:
                logger.debug(f"SchemaRegistry lookup note: {e}")

        # 3. Live reflection fallback
        conn_url = get_connection_url(db_conn)
        if conn_url:
            try:
                engine = create_engine(conn_url, poolclass=NullPool)
                inspector = inspect(engine)
                for tbl_name in inspector.get_table_names():
                    t_lower = tbl_name.lower().strip()
                    columns = inspector.get_columns(tbl_name)
                    c_set = {c["name"].lower().strip() for c in columns}
                    schema_map[t_lower] = c_set
                engine.dispose()
                return schema_map
            except Exception as e:
                logger.debug(f"Live reflection note: {e}")

        # 4. Text-based fallback from schema context
        schema_ctx = get_db_schema_context(db_conn, db_session)
        current_tbl = None
        for line in schema_ctx.splitlines():
            line_str = line.strip()
            if line_str.startswith("Table:"):
                current_tbl = line_str.replace("Table:", "").strip().lower()
                schema_map.setdefault(current_tbl, set())
            elif line_str.startswith("- ") and current_tbl:
                col_part = line_str[2:].split("(")[0].strip().lower()
                if col_part:
                    schema_map[current_tbl].add(col_part)

        return schema_map

    def validate_ast_identifiers(
        self,
        sql_query: str,
        db_conn: models.DatabaseConnection,
        db_session: Optional[Session] = None,
        allowed_tables: Optional[List[str]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validates table and column names using sqlglot AST parsing against known database schema
        and restricts to allowed_tables if specified (NR-1.1-B-T07).
        Returns (is_valid, error_message).
        """
        import sqlglot
        from sqlglot import exp

        clean_sql = re.sub(r'--.*$', ' ', sql_query, flags=re.MULTILINE)
        clean_sql = re.sub(r'/\*.*?\*/', ' ', clean_sql, flags=re.DOTALL).strip()

        dialect = getattr(db_conn, "db_type", None)
        parsed = None
        for d in [dialect, "postgres", "mysql", "sqlite", None]:
            try:
                parsed = sqlglot.parse_one(clean_sql, read=d)
                if parsed is not None:
                    break
            except Exception:
                continue

        if parsed is None:
            return False, "Failed to parse SQL AST deterministically."

        allowed_set = {t.lower().strip() for t in allowed_tables} if allowed_tables else None
        known_schema = self.get_known_schema(db_conn, db_session)
        known_tables = set(known_schema.keys()) if known_schema else set()

        # Collect CTEs and table aliases
        ctes: Set[str] = set()
        for cte in parsed.find_all(exp.CTE):
            if cte.alias_or_name:
                ctes.add(cte.alias_or_name.lower().strip())

        aliases: Dict[str, str] = {}
        for t in parsed.find_all(exp.Table):
            t_name = t.name.lower().strip()
            if t.alias:
                aliases[t.alias.lower().strip()] = t_name
            if t.alias_or_name and t.alias_or_name != t_name:
                aliases[t.alias_or_name.lower().strip()] = t_name

        # 1. Validate referenced tables
        for t in parsed.find_all(exp.Table):
            raw_name = t.name.lower().strip()
            if not raw_name or raw_name in ctes or raw_name.startswith("safe_limit_wrapper"):
                continue

            # Strip schema prefix if present e.g. public.users -> users
            simple_name = raw_name.split(".")[-1]

            if allowed_set is not None:
                if simple_name not in allowed_set and raw_name not in allowed_set:
                    return False, f"Access to table '{raw_name}' is not permitted for this widget key. Allowed tables: {sorted(list(allowed_set))}"

            if known_tables and simple_name not in known_tables and raw_name not in known_tables:
                sorted_tables = sorted(list(known_tables))
                return False, f"Table '{raw_name}' does not exist in the database schema. Available tables: {sorted_tables}"

        # 2. Validate qualified column identifiers (e.g., users.email)
        for col in parsed.find_all(exp.Column):
            col_name = col.name.lower().strip()
            tbl_qualifier = col.table.lower().strip() if col.table else None

            if not col_name or col_name == "*":
                continue

            if tbl_qualifier:
                # Resolve alias to physical table name
                resolved_table = aliases.get(tbl_qualifier, tbl_qualifier).split(".")[-1]
                if resolved_table in ctes:
                    continue  # CTE columns are derived, skip schema table check

                if resolved_table in known_schema:
                    valid_cols = known_schema[resolved_table]
                    if valid_cols and col_name not in valid_cols:
                        sorted_cols = sorted(list(valid_cols))
                        return False, f"Column '{col_name}' does not exist on table '{resolved_table}'. Available columns: {sorted_cols}"

        return True, None

    def execute_dry_run_rollback(
        self,
        db_conn: models.DatabaseConnection,
        sql_query: str,
        allowed_tables: Optional[List[str]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Executes a dialect-safe dry-run inside an isolated nested transaction
        (SAVEPOINT with immediate rollback) to catch dialect syntax or execution errors.
        Guarantees zero persistent database mutations.
        Enforces allowed_tables restriction if provided (NR-1.1-B-T07).
        """
        if allowed_tables:
            allowed_set = {t.lower().strip() for t in allowed_tables}
            try:
                ref_tables = extract_sql_referenced_tables(sql_query)
                for tbl in ref_tables:
                    if tbl.lower().strip() not in allowed_set:
                        return False, f"Access to table '{tbl}' is not permitted for this widget key."
            except Exception as parse_err:
                return False, f"Dry-run table validation failed: {parse_err}"

        conn_url = get_connection_url(db_conn)
        if not conn_url:
            return True, None

        engine = None
        try:
            # Set a fast 6.0 second timeout for dry-run verification
            connect_args = {}
            if db_conn.db_type == "sqlite":
                connect_args = {"timeout": 6.0}
            elif db_conn.db_type == "postgresql":
                connect_args = {"options": "-c statement_timeout=6000"}
            elif db_conn.db_type in ("mysql", "mariadb"):
                connect_args = {"init_command": "SET SESSION MAX_EXECUTION_TIME=6000"}

            engine = create_engine(conn_url, poolclass=NullPool, connect_args=connect_args)
            with engine.connect() as conn:
                nested = conn.begin_nested()
                try:
                    if db_conn.db_type == "sqlite":
                        conn.execute(text("PRAGMA query_only = ON;"))

                    dry_sql = sql_query.strip().rstrip(";")
                    # First attempt wrapped subquery with LIMIT 1
                    try:
                        conn.execute(text(f"SELECT * FROM ({dry_sql}) AS __dry_sub LIMIT 1"))
                    except Exception:
                        # Fallback to direct statement dry-run
                        conn.execute(text(sql_query))
                finally:
                    nested.rollback()
            return True, None
        except Exception as exc:
            err_msg = str(exc).split("\n")[0].strip()
            return False, err_msg
        finally:
            if engine:
                engine.dispose()

    def run(
        self,
        db_conn: models.DatabaseConnection,
        user_question: str,
        db_session: Optional[Session] = None,
        tenant_id: Optional[int] = None,
        allowed_tables: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Runs the self-correcting agent execution loop.
        Returns standard result dictionary:
        {
            "sql": str,
            "explanation": str,
            "schema_context": str,
            "attempts": int,
            "corrections_made": bool,
            "status": "success" | "failed",
            "error": Optional[str]
        }
        """
        schema_ctx = get_db_schema_context(db_conn, db_session, allowed_tables=allowed_tables)
        t_id = tenant_id or getattr(db_conn, "tenant_id", None)
        dialect = getattr(db_conn, "db_type", "SQL")

        base_prompt = (
            f"You are a Senior SQL & Database Engineer. Given the following database schema context and user question, "
            f"generate a valid, read-only SQL query ({dialect} dialect) and a short explanation.\n\n"
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

        feedback_history: List[str] = []
        last_generated_sql = ""
        last_explanation = ""
        last_error = None

        for attempt in range(1, self.max_attempts + 1):
            if feedback_history:
                correction_prompt = (
                    f"{base_prompt}\n\n"
                    "ATTENTION: Your previous query attempt(s) failed validation. Please review the errors below and fix the SQL query:\n"
                    + "\n".join(feedback_history)
                    + f"\n\nRemember: Use ONLY valid tables and columns from the schema, adhering strictly to {dialect} syntax."
                )
            else:
                correction_prompt = base_prompt

            try:
                raw_text = llm_gateway.generate_sync(
                    prompt=correction_prompt,
                    tenant_id=t_id,
                    purpose="nl_to_sql",
                    temperature=0.1 if attempt == 1 else 0.2
                )
            except Exception as llm_err:
                logger.error(f"[SQLAgent] LLM generation error on attempt {attempt}: {llm_err}")
                raw_text = ""

            if not raw_text or raw_text.startswith("Sorry, all AI providers"):
                last_error = "AI generation provider was unreachable or in cooldown."
                break

            # Parse SQL Block
            sql_match = re.search(r'```sql\s*(.*?)\s*```', raw_text, re.DOTALL | re.IGNORECASE)
            if sql_match:
                candidate_sql = sql_match.group(1).strip()
            else:
                candidate_sql = raw_text.split('\n')[0].strip()

            # Parse Explanation
            explanation_match = re.search(r'Explanation:\s*(.*)', raw_text, re.IGNORECASE | re.DOTALL)
            if explanation_match:
                candidate_exp = explanation_match.group(1).strip()
            else:
                candidate_exp = f"Generated {dialect} query to answer: '{user_question}'."

            last_generated_sql = candidate_sql
            last_explanation = candidate_exp

            # 1. Security Check (Fail-closed)
            is_valid, sec_reason = validate_read_only_sql(candidate_sql)
            if not is_valid:
                logger.warning(f"[SQLAgent] Security check failed on attempt {attempt}: {sec_reason}")
                return {
                    "sql": "",
                    "explanation": f"Security Guardrail Triggered: {sec_reason}",
                    "schema_context": schema_ctx,
                    "attempts": attempt,
                    "corrections_made": attempt > 1,
                    "status": "failed",
                    "error": sec_reason
                }

            # 2. AST Identifier Validation
            ast_valid, ast_err = self.validate_ast_identifiers(candidate_sql, db_conn, db_session, allowed_tables=allowed_tables)
            if not ast_valid:
                logger.info(f"[SQLAgent] AST check failed on attempt {attempt}: {ast_err}")
                last_error = ast_err
                feedback_history.append(
                    f"[Attempt {attempt} Error]: {ast_err}\nAttempted SQL was: {candidate_sql}"
                )
                continue

            # 3. SAVEPOINT Rollback Dry-Run
            dry_run_ok, dry_err = self.execute_dry_run_rollback(db_conn, candidate_sql, allowed_tables=allowed_tables)
            if not dry_run_ok:
                logger.info(f"[SQLAgent] SAVEPOINT dry-run failed on attempt {attempt}: {dry_err}")
                last_error = dry_err
                feedback_history.append(
                    f"[Attempt {attempt} Engine Error]: {dry_err}\nAttempted SQL was: {candidate_sql}"
                )
                continue

            # If all checks pass, return success!
            logger.info(f"[SQLAgent] Succeeded on attempt {attempt} (corrections: {attempt > 1})")
            return {
                "sql": candidate_sql,
                "explanation": candidate_exp,
                "schema_context": schema_ctx,
                "attempts": attempt,
                "corrections_made": attempt > 1,
                "status": "success",
                "error": None
            }

        # If all attempts exhausted, trigger safe fallback
        logger.warning(f"[SQLAgent] Failed after {self.max_attempts} attempts. Last error: {last_error}")

        fallback_table = "users"
        if "Table: " in schema_ctx:
            tables = re.findall(r'Table:\s*(\w+)', schema_ctx)
            if tables:
                fallback_table = tables[0]

        fallback_sql = f"SELECT * FROM {fallback_table} LIMIT 10;"
        fallback_exp = (
            f"Note: Agent could not resolve a fully verified query after {self.max_attempts} attempts. "
            f"Generated safe fallback preview query on table '{fallback_table}'."
        )

        return {
            "sql": fallback_sql,
            "explanation": fallback_exp,
            "schema_context": schema_ctx,
            "attempts": self.max_attempts,
            "corrections_made": True,
            "status": "failed",
            "error": last_error or "Max correction attempts exceeded."
        }


# Global SQLAgent instance
sql_agent = SQLAgent(max_attempts=3)
