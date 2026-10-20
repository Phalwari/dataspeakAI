import pytest
from unittest.mock import MagicMock, patch
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models
import schemas
from database import Base
from services.query_router import classify_query_route, QueryRouteDecision, auto_select_database
from services.conversation_memory import ConversationMemoryManager
from routers.chat import (
    extract_suggested_followups,
    get_default_suggestions_for_route,
    generate_sql_error_guidance,
    sanitize_sql_error_message,
    get_available_tables_summary
)


@pytest.fixture
def in_memory_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        # Create a tenant
        tenant = models.Tenant(name="Acme Corp", industry="Tech")
        session.add(tenant)
        session.commit()
        session.refresh(tenant)
        yield session, tenant
    finally:
        session.close()


def test_conversational_routing_greetings(in_memory_db):
    """R1: Test that greetings and platform help route to 'conversational' even with 0 dbs and 0 docs."""
    session, tenant = in_memory_db

    greetings = ["Hello", "Hi!", "Hey there", "Good morning", "What can you do?", "What are your capabilities?"]
    for q in greetings:
        decision = classify_query_route(q, tenant.id, session, source_preference="auto")
        assert decision.route_type == "conversational", f"Expected 'conversational' for '{q}', got '{decision.route_type}'"
        assert decision.confidence >= 0.9


def test_suggestion_extraction():
    """R3: Test extract_suggested_followups parses clean follow-up questions."""
    sample_text = (
        "Here is the revenue breakdown for Q3:\n\n"
        "**Total Revenue:** **$1,250,000**\n\n"
        "| Quarter | Amount |\n"
        "|---|---|\n"
        "| Q3 | $1.25M |\n\n"
        "**Suggested Follow-ups:**\n"
        "1. What were the top 3 selling products?\n"
        "2. How does this compare to Q2?\n"
        "3. Show revenue grouped by region"
    )

    suggestions = extract_suggested_followups(sample_text)
    assert len(suggestions) == 3
    assert suggestions[0] == "What were the top 3 selling products?"
    assert suggestions[1] == "How does this compare to Q2?"
    assert suggestions[2] == "Show revenue grouped by region"


def test_fallback_suggestions():
    """R3: Test get_default_suggestions_for_route provides sensible fallbacks."""
    sugg_conv = get_default_suggestions_for_route("conversational")
    assert len(sugg_conv) >= 3
    assert any("connect" in s.lower() for s in sugg_conv)

    sugg_sql = get_default_suggestions_for_route("sql", tables=["customers", "orders"])
    assert len(sugg_sql) >= 3
    assert any("customers" in s for s in sugg_sql)


def test_sql_error_guidance(in_memory_db):
    """R3: Test that SQL errors generate friendly guidance with available tables."""
    session, tenant = in_memory_db

    # Create a database connection and schema metadata
    db_conn = models.DatabaseConnection(
        tenant_id=tenant.id,
        name="Production DB",
        db_type="sqlite",
        database=":memory:"
    )
    session.add(db_conn)
    session.commit()
    session.refresh(db_conn)

    schema = models.DatabaseSchema(connection_id=db_conn.id, schema_name="public")
    session.add(schema)
    session.commit()
    session.refresh(schema)

    t1 = models.TableMetadata(schema_id=schema.id, table_name="users", is_fact_table=False)
    t2 = models.TableMetadata(schema_id=schema.id, table_name="orders", is_fact_table=True)
    session.add_all([t1, t2])
    session.commit()

    guidance, suggestions = generate_sql_error_guidance(
        db_conn=db_conn,
        user_query="Show revenue for widget X",
        error_msg="No column 'revenue' in table 'users'",
        db_session=session
    )

    assert "I wasn't able to complete the SQL query" in guidance
    assert "`users`" in guidance
    assert "`orders`" in guidance
    assert len(suggestions) >= 2
    assert any("users" in s for s in suggestions)


def test_multi_turn_anaphora_context_injection():
    """R2: Test that prior execution metadata is injected into conversation context."""
    conv = models.Conversation(tenant_id=1, title="Test Anaphora")

    # Turn 1 user
    msg1 = models.Message(
        conversation_id=1,
        sender_role="user",
        content="Show all customers from California",
        query_type="user"
    )

    # Turn 1 assistant with sql_data in metadata
    meta = {
        "sql_data": {
            "generated_sql": "SELECT id, name, state FROM customers WHERE state = 'CA' LIMIT 50;",
            "row_count": 12,
            "columns": ["id", "name", "state"]
        },
        "sources": []
    }
    msg2 = models.Message(
        conversation_id=1,
        sender_role="assistant",
        content="Found 12 customers in California.",
        query_type="sql",
        metadata_json=meta
    )

    # Turn 2 user asking anaphoric follow-up
    msg3 = models.Message(
        conversation_id=1,
        sender_role="user",
        content="Filter those by city Los Angeles",
        query_type="user"
    )

    context = ConversationMemoryManager.build_context(conv, [msg1, msg2, msg3])

    # Assert that Prior Execution metadata was injected into context
    assert "[Prior Execution: SQL=" in context
    assert "customers" in context
    assert "Rows Returned=12" in context


def test_sanitize_sql_error_message():
    """R3: Test that raw database driver exceptions and credentials are sanitized."""
    # 1. Driver OperationalError with no such column
    res1 = sanitize_sql_error_message("(sqlite3.OperationalError) no such column: salary")
    assert "salary" in res1
    assert "sqlite3" not in res1
    assert "does not exist in the queried table" in res1

    # 2. PostgreSQL connection string with password
    res2 = sanitize_sql_error_message("Connection failed: postgresql://admin:supersecret@db.internal:5432/crm")
    assert "supersecret" not in res2
    assert "[REDACTED]" in res2

    # 3. Syntax error
    res3 = sanitize_sql_error_message("syntax error at or near 'WHERE'")
    assert "syntax error" in res3.lower()

    # 4. Empty string
    assert sanitize_sql_error_message("") == "An unexpected database execution error occurred."


def test_auto_select_database_fallback_continuity(in_memory_db):
    """R2: Test that anaphoric follow-up queries continue on prior active database when multiple DBs exist."""
    session, tenant = in_memory_db

    db1 = models.DatabaseConnection(
        tenant_id=tenant.id,
        name="Primary Warehouse",
        db_type="sqlite",
        database="warehouse.db"
    )
    db2 = models.DatabaseConnection(
        tenant_id=tenant.id,
        name="Secondary CRM",
        db_type="sqlite",
        database="crm.db"
    )
    session.add_all([db1, db2])
    session.commit()
    session.refresh(db1)
    session.refresh(db2)

    # When query has no matching table or DB name, fallback_database_id=db2.id must be preferred
    selected = auto_select_database(
        query="filter those by California",
        tenant_id=tenant.id,
        db=session,
        fallback_database_id=db2.id
    )
    assert selected.id == db2.id


def test_anaphora_query_routing_with_prior_db(in_memory_db):
    """R2: Test that conversational anaphora and drill-down phrases route to SQL when prior_database_id exists."""
    session, tenant = in_memory_db

    db1 = models.DatabaseConnection(
        tenant_id=tenant.id,
        name="Sales DB",
        db_type="sqlite",
        database="sales.db"
    )
    doc1 = models.Document(
        tenant_id=tenant.id,
        name="employee_handbook.pdf",
        size=1024,
        file_type="pdf",
        status="Completed"
    )
    session.add_all([db1, doc1])
    session.commit()
    session.refresh(db1)
    session.refresh(doc1)

    anaphoric_queries = [
        "summarize that in a table",
        "what about California?",
        "now only show the top 3",
        "break that down by status",
        "show me more details"
    ]

    for q in anaphoric_queries:
        decision = classify_query_route(
            query=q,
            tenant_id=tenant.id,
            db=session,
            source_preference="auto",
            prior_database_id=db1.id
        )
        assert decision.route_type == "sql", f"Query '{q}' should route to 'sql' under active DB context, got '{decision.route_type}'"
        assert decision.database_id == db1.id

    # But explicit document keywords should still switch away from prior DB
    doc_query = "What does the employee handbook say about travel reimbursement?"
    doc_decision = classify_query_route(
        query=doc_query,
        tenant_id=tenant.id,
        db=session,
        source_preference="auto",
        prior_database_id=db1.id
    )
    assert doc_decision.route_type in ("document", "rag", "conversational")


def test_sanitize_sql_error_message_dialects():
    """R3: Test dialect-specific error sanitization (SQLite, MySQL, and security guardrails)."""
    # SQLite missing table
    sqlite_tbl_err = sanitize_sql_error_message("(sqlite3.OperationalError) no such table: invoices")
    assert "invoices" in sqlite_tbl_err
    assert "not found in the database catalog" in sqlite_tbl_err
    assert "sqlite3" not in sqlite_tbl_err

    # MySQL missing table
    mysql_tbl_err = sanitize_sql_error_message("pymysql.err.ProgrammingError: (1146, \"Table 'dataspeak.orders' doesn't exist\")")
    assert "orders" in mysql_tbl_err
    assert "not found in the database catalog" in mysql_tbl_err

    # MySQL unknown column
    mysql_col_err = sanitize_sql_error_message("1054, \"Unknown column 'unit_discount' in 'field list'\"")
    assert "unit_discount" in mysql_col_err
    assert "does not exist in the queried table" in mysql_col_err

    # Read-only guardrail violation
    guardrail_err = sanitize_sql_error_message("Execution blocked by security policy: INSERT statements not permitted")
    assert "security guardrails" in guardrail_err


def test_build_context_handles_unparseable_sql_and_string_metadata():
    """R2: Test that malformed historical SQL and stringified metadata do not crash ConversationMemoryManager."""
    conv = models.Conversation(tenant_id=1, title="Robustness Test")

    # Message with stringified JSON metadata and unparseable SQL
    raw_meta = json.dumps({
        "database_name": "Warehouse",
        "sql_data": {
            "generated_sql": "SELECT FROM WHERE !!! NOT VALID SQL !!!",
            "row_count": 0,
            "columns": []
        }
    })
    msg = models.Message(
        conversation_id=1,
        sender_role="assistant",
        content="Here are the results.",
        query_type="sql",
        metadata_json=raw_meta
    )

    # Should not raise exception
    context = ConversationMemoryManager.build_context(conv, [msg])
    assert "[Prior Execution:" in context
    assert "Database=`Warehouse`" in context


def test_pydantic_message_response_parses_json_string_metadata():
    """R3: Test MessageResponse validator converts raw string JSON into dict seamlessly."""
    raw_payload = {
        "id": 101,
        "conversation_id": 42,
        "sender_role": "assistant",
        "content": "Result summary",
        "query_type": "sql",
        "metadata_json": json.dumps({"database_id": 5, "suggestions": ["Show more"]}),
        "created_at": "2026-10-20T12:00:00"
    }

    validated = schemas.MessageResponse.model_validate(raw_payload)
    assert isinstance(validated.metadata_json, dict)
    assert validated.metadata_json["database_id"] == 5
    assert validated.metadata_json["suggestions"] == ["Show more"]


def test_multiturn_anaphora_continuity_with_intermediate_greeting(in_memory_db):
    """R2: Multi-turn history preserves database affinity even when an intermediate greeting occurs."""
    session, tenant = in_memory_db

    db1 = models.DatabaseConnection(
        tenant_id=tenant.id,
        name="Finance DB",
        db_type="sqlite",
        database="finance.db"
    )
    doc1 = models.Document(
        tenant_id=tenant.id,
        name="policy.pdf",
        size=500,
        file_type="pdf",
        status="Completed"
    )
    session.add_all([db1, doc1])
    session.commit()
    session.refresh(db1)

    # Simulated past messages
    m1 = models.Message(
        conversation_id=99,
        sender_role="user",
        content="Show all expenses over $1000",
        query_type="user"
    )
    m2 = models.Message(
        conversation_id=99,
        sender_role="assistant",
        content="Found 14 expense records over $1000.",
        query_type="sql",
        metadata_json={
            "database_id": db1.id,
            "database_name": db1.name,
            "sql_data": {
                "generated_sql": "SELECT * FROM expenses WHERE amount > 1000;",
                "row_count": 14,
                "columns": ["id", "amount", "category"]
            }
        }
    )
    # Turn 2: Intermediate greeting
    m3 = models.Message(
        conversation_id=99,
        sender_role="user",
        content="Thanks! Quick question: how do you work?",
        query_type="user"
    )
    m4 = models.Message(
        conversation_id=99,
        sender_role="assistant",
        content="I am DataSpeakAI. I can query databases and search documents.",
        query_type="conversational",
        metadata_json={"route": "conversational"}
    )
    past_messages = [m1, m2, m3, m4]

    # In chat.py router, prior_database_id is discovered by scanning backwards:
    discovered_prior_db_id = None
    for pm in reversed(past_messages):
        if pm.sender_role == "assistant" and pm.metadata_json:
            m_data = json.loads(pm.metadata_json) if isinstance(pm.metadata_json, str) else pm.metadata_json
            if isinstance(m_data, dict):
                cand = (
                    m_data.get("database_id")
                    or (m_data.get("sql_agent") or {}).get("database_id")
                    or (m_data.get("sql_data") or {}).get("database_id")
                    or (m_data.get("route_decision") or {}).get("database_id")
                )
                if cand:
                    discovered_prior_db_id = int(cand)
                    break

    assert discovered_prior_db_id == db1.id

    # Turn 3: User resumes SQL inquiry with anaphora
    turn3_decision = classify_query_route(
        query="Now summarize that by category",
        tenant_id=tenant.id,
        db=session,
        source_preference="auto",
        prior_database_id=discovered_prior_db_id
    )
    assert turn3_decision.route_type == "sql"
    assert turn3_decision.database_id == db1.id


def test_platform_help_routing_with_active_assets(in_memory_db):
    """R1: Test that platform help inquiries route to 'conversational' even when tenant has active DBs and docs."""
    session, tenant = in_memory_db

    db_conn = models.DatabaseConnection(
        tenant_id=tenant.id,
        name="Main PostgreSQL DB",
        db_type="postgresql",
        database="app_prod"
    )
    doc = models.Document(
        tenant_id=tenant.id,
        name="sales_report.pdf",
        size=1024,
        file_type="pdf",
        status="Completed"
    )
    session.add_all([db_conn, doc])
    session.commit()

    platform_inquiries = [
        "How do I connect a PostgreSQL database?",
        "How do I upload a document?",
        "How do I upload documents to the Knowledge Base?",
        "What can you do?",
        "How does the ERD schema visualizer work?",
        "How can I embed the chatbot widget?",
        "Tell me about DataSpeakAI capabilities"
    ]

    with patch('services.llm_generation_service.llm_gateway.generate_sync', return_value=''):
        for query in platform_inquiries:
            decision = classify_query_route(query, tenant.id, session, source_preference="auto")
            assert decision.route_type == "conversational", (
                f"Expected 'conversational' for '{query}', got '{decision.route_type}' (reason: {decision.reasoning})"
            )
            assert decision.confidence >= 0.85


def test_operational_queries_route_to_sql_with_active_assets(in_memory_db):
    """R1 & R2: Operational calculation queries should NOT be hijacked by conversational help."""
    session, tenant = in_memory_db

    db_conn = models.DatabaseConnection(
        tenant_id=tenant.id,
        name="Production DB",
        db_type="sqlite",
        database=":memory:"
    )
    session.add(db_conn)
    session.commit()

    operational_queries = [
        "How many users are in the database?",
        "Count total orders by status",
        "Show me the top 5 customers by revenue"
    ]

    with patch('services.llm_generation_service.llm_gateway.generate_sync', return_value=''):
        for query in operational_queries:
            decision = classify_query_route(query, tenant.id, session, source_preference="auto")
            assert decision.route_type == "sql", (
                f"Expected 'sql' for operational query '{query}', got '{decision.route_type}'"
            )


def test_extract_suggested_followups_cleans_markdown_and_narrative():
    """R3: Test that extract_suggested_followups strips markdown bolding and stops at trailing narrative."""
    raw_response = (
        "Here is the executive breakdown of your customer orders.\n\n"
        "**Suggested Follow-ups:**\n"
        "1. **What are the top 3 selling products?**\n"
        "2. *How does this compare to last month?*\n"
        "3. \"Can we filter by region?\"\n\n"
        "I hope this summary helps your team! Please let me know if you need anything else."
    )

    suggestions = extract_suggested_followups(raw_response)
    assert len(suggestions) == 3
    assert suggestions[0] == "What are the top 3 selling products?"
    assert suggestions[1] == "How does this compare to last month?"
    assert suggestions[2] == "Can we filter by region?"
    # Ensure closing narrative was not included
    assert not any("hope this summary" in s.lower() for s in suggestions)


def test_prior_db_id_extraction_handles_explicit_none_subobjects():
    """R2: Verify prior_database_id extraction does not crash on None sub-objects."""
    metadata = {
        "database_id": None,
        "sql_agent": None,
        "sql_data": {"database_id": 42, "generated_sql": "SELECT 1;"},
        "route_decision": None
    }
    # Simulate chat.py backwards scanning logic
    db_id = (
        metadata.get("database_id")
        or (metadata.get("sql_agent") or {}).get("database_id")
        or (metadata.get("sql_data") or {}).get("database_id")
        or (metadata.get("route_decision") or {}).get("database_id")
    )
    assert db_id == 42



