"""
Automated unit & behavioral regression tests for Phase 7 Task 7.2.1:
Self-Correcting SQL Agent with AST verification and safe SAVEPOINT rollback dry-runs.
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine, Column, Integer, String, text
from sqlalchemy.orm import declarative_base, sessionmaker

# Add backend directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import models
from services.sql_agent import SQLAgent


SampleModelBase = declarative_base()


class SampleUser(SampleModelBase):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String)
    email = Column(String)


@pytest.fixture
def mock_db_conn(tmp_path):
    """Creates a temporary SQLite database for isolated agent testing."""
    db_file = tmp_path / "test_agent.db"
    db_url = f"sqlite:///{db_file}"

    engine = create_engine(db_url)
    SampleModelBase.metadata.create_all(engine)
    with engine.connect() as conn:
        conn.execute(
            text("INSERT INTO users (id, username, email) VALUES (1, 'alice', 'alice@example.com')")
        )
        conn.commit()

    conn_model = MagicMock(spec=models.DatabaseConnection)
    conn_model.id = 99
    conn_model.tenant_id = 1
    conn_model.database = str(db_file).replace("\\", "/")
    conn_model.db_type = "sqlite"
    conn_model.connection_string = db_url
    conn_model.host = ""
    conn_model.port = None
    conn_model.username = ""
    conn_model.password = ""
    return conn_model


def test_validate_ast_identifiers_valid(mock_db_conn):
    """Valid query referencing existing table and columns passes AST validation."""
    agent = SQLAgent()
    valid_sql = "SELECT id, email FROM users WHERE username = 'alice'"
    is_valid, err = agent.validate_ast_identifiers(valid_sql, mock_db_conn)
    assert is_valid is True
    assert err is None


def test_validate_ast_identifiers_catches_invalid_table(mock_db_conn):
    """AST validation flags non-existent table before hitting the database."""
    agent = SQLAgent()
    invalid_sql = "SELECT * FROM non_existent_customers WHERE id = 1"
    is_valid, err = agent.validate_ast_identifiers(invalid_sql, mock_db_conn)
    assert is_valid is False
    assert "Table 'non_existent_customers' does not exist" in err
    assert "users" in err


def test_validate_ast_identifiers_catches_invalid_column(mock_db_conn):
    """AST validation flags non-existent column qualified on an existing table."""
    agent = SQLAgent()
    invalid_sql = "SELECT users.non_existent_col FROM users"
    is_valid, err = agent.validate_ast_identifiers(invalid_sql, mock_db_conn)
    assert is_valid is False
    assert "Column 'non_existent_col' does not exist on table 'users'" in err


def test_execute_dry_run_rollback_success(mock_db_conn):
    """Dry-run inside SAVEPOINT nested transaction executes and rolls back cleanly."""
    agent = SQLAgent()
    query = "SELECT count(*) FROM users"
    ok, err = agent.execute_dry_run_rollback(mock_db_conn, query)
    assert ok is True
    assert err is None


def test_execute_dry_run_rollback_catches_syntax_error(mock_db_conn):
    """Dry-run catches dialect syntax errors within nested transaction."""
    agent = SQLAgent()
    bad_syntax = "SELECT * FROM users WHERE WHERE id = 1"
    ok, err = agent.execute_dry_run_rollback(mock_db_conn, bad_syntax)
    assert ok is False
    assert err is not None
    assert "syntax error" in err.lower() or "near" in err.lower()


def test_sql_agent_self_corrects_on_second_attempt(mock_db_conn):
    """
    Simulates in-flight self-correction:
    Attempt 1: Generates invalid column 'users.credit_card' -> fails AST check.
    Attempt 2: LLM receives feedback, corrects to 'users.email' -> passes!
    """
    agent = SQLAgent(max_attempts=3)

    responses = [
        # Attempt 1: bad column
        "```sql\nSELECT users.credit_card FROM users\n```\nExplanation: Get user card.",
        # Attempt 2: corrected column
        "```sql\nSELECT users.email FROM users\n```\nExplanation: Get user email address."
    ]

    call_count = 0
    prompts_received = []

    def fake_generate_sync(prompt, **kwargs):
        nonlocal call_count
        prompts_received.append(prompt)
        resp = responses[min(call_count, len(responses) - 1)]
        call_count += 1
        return resp

    with patch("services.sql_agent.llm_gateway.generate_sync", side_effect=fake_generate_sync):
        result = agent.run(mock_db_conn, "Find user emails")

    assert result["status"] == "success"
    assert result["attempts"] == 2
    assert result["corrections_made"] is True
    assert "users.email" in result["sql"]
    assert len(prompts_received) == 2
    assert "Column 'credit_card' does not exist" in prompts_received[1]


def test_sql_agent_blocks_multi_statement_and_ddl(mock_db_conn):
    """Security check strictly blocks dangerous multi-statement or DDL injection."""
    agent = SQLAgent()

    malicious_query = "```sql\nDROP TABLE users; SELECT 1;\n```\nExplanation: Malicious drop"

    with patch("services.sql_agent.llm_gateway.generate_sync", return_value=malicious_query):
        result = agent.run(mock_db_conn, "Delete users")

    assert result["status"] == "failed"
    assert "Security Guardrail Triggered" in result["explanation"]
    assert result["sql"] == ""


def test_sql_agent_exhausted_retries_returns_safe_fallback(mock_db_conn):
    """When all 3 attempts fail validation, agent returns safe preview fallback."""
    agent = SQLAgent(max_attempts=3)

    persistent_error = "```sql\nSELECT * FROM nonexistent_table\n```\nExplanation: Broken query"

    with patch("services.sql_agent.llm_gateway.generate_sync", return_value=persistent_error):
        result = agent.run(mock_db_conn, "Query broken table")

    assert result["status"] == "failed"
    assert result["attempts"] == 3
    assert result["corrections_made"] is True
    assert "SELECT * FROM users LIMIT 10;" in result["sql"]
    assert "safe fallback" in result["explanation"].lower()
