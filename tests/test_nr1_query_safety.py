"""
Unit and Integration Tests for Sprint NR-1.2-B: One Safe Query Executor & Outer Row Capping.
Verifies:
1. SafeExecutionRequest and SafeExecutionResult contracts.
2. sqlglot AST dialect validation rejecting write operations (INSERT, UPDATE, DELETE, DROP, ALTER) and multi-statements.
3. Strict outer LIMIT subquery wrapping and truncation flag calculation (Fixes I-08 / FYP-02).
4. No synthetic mock rows on unavailable connections or unsupported dialects (Fixes I-16 / FYP-03).
5. Engine read-only guardrails.
"""
import pytest
from sqlalchemy import create_engine, text
from services.sql_engine import (
    execute_safe_sql,
    validate_read_only_sql,
    SafeExecutionRequest,
    SafeExecutionResult,
)
import models


def test_safe_execution_request_contract():
    """Validates SafeExecutionRequest defaults and validation."""
    req = SafeExecutionRequest(sql_query="SELECT * FROM users", max_rows=25)
    assert req.sql_query == "SELECT * FROM users"
    assert req.max_rows == 25
    assert req.timeout_ceiling == 12.0
    assert req.read_only is True


def test_ast_validation_rejects_dml_and_ddl():
    """Rejects all write operations at the AST and keyword level."""
    write_queries = [
        "INSERT INTO users (name) VALUES ('Hacker')",
        "UPDATE users SET role = 'Admin' WHERE id = 1",
        "DELETE FROM users WHERE id = 1",
        "DROP TABLE users",
        "ALTER TABLE users ADD COLUMN is_pwned BOOLEAN",
        "TRUNCATE TABLE audit_logs",
        "CREATE TABLE rogue (id INT)",
    ]
    for q in write_queries:
        is_valid, reason = validate_read_only_sql(q)
        assert is_valid is False
        assert "Forbidden" in reason or "SELECT" in reason


def test_ast_validation_rejects_multi_statements():
    """Rejects stacked / chained SQL statements separated by semicolons."""
    stacked = "SELECT * FROM users; DROP TABLE accounts;"
    is_valid, reason = validate_read_only_sql(stacked)
    assert is_valid is False
    assert "Multiple SQL statements" in reason or "semicolons" in reason


def test_ast_validation_accepts_clean_select_and_cte():
    """Validates that legitimate SELECT and WITH queries pass."""
    valid_queries = [
        "SELECT id, name, email FROM users",
        "SELECT count(*) FROM orders WHERE total > 100",
        "WITH active_users AS (SELECT * FROM users WHERE is_active = 1) SELECT * FROM active_users",
        "SELECT u.name, o.id FROM users u JOIN orders o ON u.id = o.user_id",
    ]
    for q in valid_queries:
        is_valid, reason = validate_read_only_sql(q)
        assert is_valid is True, f"Failed on valid query: {q} with reason: {reason}"


def test_outer_limit_capping_and_truncation_flag(tmp_path):
    """Verifies that queries with inner LIMIT larger than max_rows are capped and flagged as truncated."""
    db_file = tmp_path / "capping_test.sqlite"
    test_db_url = f"sqlite:///{db_file}"
    engine = create_engine(test_db_url)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE items (id INT, name TEXT);"))
        for i in range(1, 31):
            conn.execute(text(f"INSERT INTO items VALUES ({i}, 'item_{i}');"))

    db_conn = models.DatabaseConnection(
        id=101,
        name="Test SQLite",
        db_type="sqlite",
        connection_string=test_db_url
    )

    # 1. Query has LIMIT 25, caller requests max_rows=10
    query = "SELECT * FROM items LIMIT 25"
    result = execute_safe_sql(db_conn, query, max_rows=10)
    
    assert result["row_count"] == 10
    assert len(result["rows"]) == 10
    assert result["is_truncated"] is True

    # 2. Query has LIMIT 5, caller requests max_rows=10 (not truncated)
    query_small = "SELECT * FROM items LIMIT 5"
    result_small = execute_safe_sql(db_conn, query_small, max_rows=10)
    
    assert result_small["row_count"] == 5
    assert len(result_small["rows"]) == 5
    assert result_small["is_truncated"] is False


def test_safe_execution_request_object_invocation(tmp_path):
    """Verifies execute_safe_sql accepts SafeExecutionRequest objects."""
    db_file = tmp_path / "req_test.sqlite"
    test_db_url = f"sqlite:///{db_file}"
    engine = create_engine(test_db_url)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE metrics (val INT);"))
        conn.execute(text("INSERT INTO metrics VALUES (42);"))

    db_conn = models.DatabaseConnection(
        id=102,
        name="Test Metrics",
        db_type="sqlite",
        connection_string=test_db_url
    )

    req = SafeExecutionRequest(sql_query="SELECT * FROM metrics", max_rows=5)
    result = execute_safe_sql(db_conn, req)
    assert result["row_count"] == 1
    assert result["rows"][0]["val"] == 42


def test_no_synthetic_mock_people_on_unsupported_or_missing_connection():
    """Verifies that an unsupported or disconnected database raises RuntimeError instead of returning fake rows."""
    db_conn = models.DatabaseConnection(
        id=103,
        name="Orphan DB",
        db_type="unsupported_engine",
        connection_string=None,
        host=None
    )

    with pytest.raises(RuntimeError, match="unavailable or unsupported dialect"):
        execute_safe_sql(db_conn, "SELECT * FROM users", max_rows=10)
