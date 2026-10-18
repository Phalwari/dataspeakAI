"""Opt-in capability probes; use the isolated launcher in .agents/fyp-verification.

Assertions express desired behavior, including known gaps. Failures are findings.
Providers are doubles; SQL, ORM, chunking, FAISS/BM25 and orchestration are real.
This filename stays outside default pytest discovery.
"""
import asyncio
import hashlib
import json
import re
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import BackgroundTasks, HTTPException, Response
from langchain_core.embeddings import Embeddings
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request
import models
import schemas
from database import Base
from routers import chat, documents, widget
from services import query_router, sql_engine
from services.chat_stream import stream_chat_response
from services.citation_service import CitationService


@pytest.fixture
def fixture_data(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    application = create_engine("sqlite:///:memory:", poolclass=StaticPool,
                                connect_args={"check_same_thread": False})
    Base.metadata.create_all(application)
    db = sessionmaker(bind=application)()
    db.add_all([models.Tenant(id=101, name="Synthetic Alpha"),
                models.Tenant(id=102, name="Synthetic Beta")])
    user = models.User(id=101, tenant_id=101, email="fyp@example.invalid",
                      hashed_password="unused-direct-handler-check", role="Admin",
                      full_name="Synthetic Tester", is_verified=True)
    db.add(user)
    source_path = tmp_path / "sales.sqlite"
    source = create_engine("sqlite:///" + source_path.as_posix())
    with source.begin() as c:
        c.execute(text("CREATE TABLE sales (id INTEGER PRIMARY KEY, amount INTEGER, month INTEGER)"))
        c.execute(text("INSERT INTO sales (id, amount, month) VALUES (:id, :amount, :month)"),
                  [{"id": n, "amount": n * 10, "month": 1 if n <= 125 else 2}
                   for n in range(1, 251)])
    conn = models.DatabaseConnection(id=101, tenant_id=101, name="Synthetic Sales",
                                    db_type="sqlite", database=source_path.as_posix(),
                                    connection_string="sqlite:///" + source_path.as_posix())
    db.add(conn)
    db.commit()
    request = Request({"type": "http", "headers": [(b"origin", b"https://demo.example")],
                       "client": ("127.0.0.1", 12345)})
    yield SimpleNamespace(db=db, user=user, conn=conn, request=request, path=tmp_path)
    db.close()
    application.dispose()
    source.dispose()


def add_document(f, name="policy.txt", content=None):
    doc = models.Document(tenant_id=101, name=name, file_type="txt", status="Completed")
    f.db.add(doc)
    f.db.commit()
    if content is not None:
        path = f.path / name
        path.write_text(content, encoding="utf-8")
        documents.process_document(doc.id, str(path), 101, 160, 20, "fixed", f.db)
        f.db.refresh(doc)
    return doc


@pytest.mark.parametrize("question,preference,expected", [
    ("How many sales records total?", "auto", "sql"),
    ("Explain the policy document", "auto", "rag"),
    ("How many records?", "documents", "rag"),
    ("Explain the policy", "database", "sql"),
])
def test_routing_manual_and_keyword_paths(fixture_data, question, preference, expected):
    f = fixture_data
    add_document(f)
    result = query_router.classify_query_route(question, 101, f.db, preference, 101)
    assert result.route_type == expected


def test_routing_only_database_and_foreign_tenant(fixture_data):
    f = fixture_data
    assert query_router.classify_query_route("Revenue", 101, f.db).route_type == "sql"
    assert query_router.classify_query_route("Revenue", 102, f.db).database_id is None


def test_hybrid_classifier_response_reaches_route(fixture_data, monkeypatch):
    f = fixture_data
    add_document(f)
    monkeypatch.setenv("GEMINI_API_KEY", "synthetic-provider-key")
    fake = SimpleNamespace(status_code=200, json=lambda: {
        "candidates": [{"content": {"parts": [{"text": "HYBRID"}]}}]})
    monkeypatch.setattr(query_router.requests, "post", lambda *a, **k: fake)
    decision = query_router.classify_query_route("Compare total sales with policy", 101, f.db)
    assert decision.route_type == "hybrid"


def test_sql_real_aggregate_matches_independent_total(fixture_data):
    result = sql_engine.execute_safe_sql(fixture_data.conn, "SELECT SUM(amount) AS revenue FROM sales")
    assert result["rows"][0]["revenue"] == sum(n * 10 for n in range(1, 251))


@pytest.mark.parametrize("query", [
    "SELECT * FROM sales", "SELECT * FROM sales LIMIT 250",
    "SELECT * FROM sales WHERE id IN (SELECT id FROM sales LIMIT 250)",
])
def test_sql_never_exceeds_requested_cap(fixture_data, query):
    result = sql_engine.execute_safe_sql(fixture_data.conn, query, max_rows=100)
    assert result["row_count"] <= 100, f"Returned {result['row_count']} rows for cap 100"


def test_sql_rejects_destructive_query(fixture_data):
    with pytest.raises(ValueError):
        sql_engine.execute_safe_sql(fixture_data.conn, "DELETE FROM sales")
    result = sql_engine.execute_safe_sql(fixture_data.conn, "SELECT COUNT(*) AS total FROM sales")
    assert result["rows"][0]["total"] == 250


def test_unsupported_source_does_not_return_invented_rows(fixture_data):
    f = fixture_data
    f.conn.db_type = "unsupported_fyp_test"
    f.conn.connection_string = None
    try:
        result = sql_engine.execute_safe_sql(f.conn, "SELECT * FROM sales")
    except (ValueError, RuntimeError):
        return
    assert not result.get("rows"), "Unsupported source returned example rows as query results"


def test_conversation_persistence_rename_and_read(fixture_data, monkeypatch):
    f = fixture_data
    monkeypatch.setattr(chat.llm_gateway, "generate_sync", lambda **k:
                        "```sql\nSELECT SUM(amount) AS revenue FROM sales\n```\nExplanation: Sum recorded sales."
                        if k.get("purpose") == "nl_to_sql" else "Synthetic result explanation.")
    result = chat.chat_endpoint(schemas.ChatRequest(query="Total sales revenue", source_preference="database",
                                database_id=101), BackgroundTasks(), f.request, f.user, f.db)
    assert result.sql_data["rows"][0]["revenue"] == sum(n * 10 for n in range(1, 251))
    assert len(chat.get_conversation(result.conversation_id, f.user, f.db).messages) == 2
    renamed = chat.update_conversation(result.conversation_id, schemas.ConversationUpdate(title="Verified sales"), f.user, f.db)
    assert renamed.title == "Verified sales"
    assert chat.get_conversation(result.conversation_id, f.user, f.db).title == "Verified sales"


def test_sql_followup_generation_receives_prior_question(fixture_data, monkeypatch):
    f = fixture_data
    conv = models.Conversation(tenant_id=101, user_id=f.user.id, title="Prior sales", platform="web")
    f.db.add(conv)
    f.db.flush()
    previous = "What was total sales revenue in January 2026?"
    f.db.add(models.Message(conversation_id=conv.id, sender_role="user", content=previous))
    f.db.commit()
    sql_prompts = []
    def generation(**kwargs):
        if kwargs.get("purpose") == "nl_to_sql":
            sql_prompts.append(kwargs["prompt"])
            return "```sql\nSELECT SUM(amount) AS revenue FROM sales\n```\nExplanation: Sum sales."
        return "Synthetic result explanation."
    monkeypatch.setattr(chat.llm_gateway, "generate_sync", generation)
    chat.chat_endpoint(schemas.ChatRequest(query="What about the previous month?", conversation_id=conv.id,
                       source_preference="database", database_id=101), BackgroundTasks(), f.request, f.user, f.db)
    assert sql_prompts
    assert previous in sql_prompts[0], "SQL generation receives only the follow-up, without prior question"


def test_widget_cannot_adopt_private_dashboard_conversation(fixture_data):
    f = fixture_data
    conv = models.Conversation(tenant_id=101, user_id=f.user.id, title="Private sales", platform="web")
    key = models.WidgetKey(tenant_id=101, public_key="pk_live_synthetic_fyp_probe",
                          allowed_origins=["https://demo.example"], enabled=True)
    f.db.add_all([conv, key])
    f.db.commit()
    try:
        result = widget.create_widget_session(schemas.WidgetSessionRequest(public_key=key.public_key,
                            conversation_id=conv.id), f.request, Response(), f.db)
    except HTTPException as exc:
        assert exc.status_code in (403, 404)
        return
    assert result.conversation_id != conv.id, "Public widget session adopted a private dashboard conversation"


def test_grounding_error_is_not_positive_verification():
    class BrokenEmbeddings:
        def embed_documents(self, texts):
            raise RuntimeError("Synthetic embedding outage")
    result = CitationService().verify_grounding(
        "The company policy provides twenty days of annual leave to every eligible employee.",
        [{"content": "Annual leave is twenty days.", "score": 0.8,
          "metadata": {"source": "policy.txt"}}], BrokenEmbeddings())
    assert result["grounding_confidence"] == 0 and result["has_low_confidence"], (
        f"Embedding failure reported confidence={result['grounding_confidence']}, "
        f"warning={result['has_low_confidence']}")


class HashEmbeddings(Embeddings):
    """Offline token hashing for storage checks; no semantic-quality claim."""
    model_name = "all-MiniLM-L6-v2"
    def embed_query(self, value):
        vector = [0.0] * 64
        for token in re.findall(r"\w+", value.lower()):
            vector[int.from_bytes(hashlib.sha256(token.encode()).digest()[:2], "big") % 64] += 1
        norm = sum(x * x for x in vector) ** 0.5 or 1
        return [x / norm for x in vector]
    def embed_documents(self, texts):
        return [self.embed_query(value) for value in texts]


@pytest.fixture
def ingested_documents(fixture_data, monkeypatch):
    f = fixture_data
    embeddings = HashEmbeddings()
    monkeypatch.setattr(documents, "embeddings_model", embeddings)
    monkeypatch.setattr(documents, "_load_hf_embeddings", lambda *a: embeddings)
    monkeypatch.setattr(chat, "get_embeddings", lambda: embeddings)
    monkeypatch.setattr(chat, "cross_encoder_rerank", lambda q, results, top_k=5: results[:top_k])
    first = add_document(f, "leave_policy.txt", "Annual leave policy. Every eligible employee receives twenty days of annual leave. Leave requires approval from the team manager.")
    second = add_document(f, "travel_policy.txt", "Travel expense policy. Hotel reimbursement is capped at one hundred units per night. Receipts are required for every travel expense.")
    assert first.status == second.status == "Completed", (first.error_message, second.error_message)
    return f, first, second


def test_document_ingestion_retrieval_and_parent_context(ingested_documents):
    f, first, _ = ingested_documents
    chunks = f.db.query(models.DocumentChunk).filter_by(document_id=first.id).all()
    assert any(c.hierarchy_level == 0 for c in chunks)
    assert any(c.parent_chunk_id is not None for c in chunks)
    hits = chat.retrieve_rag_chunks("annual leave twenty days", 101, f.db)
    assert hits and any("annual leave" in h["content"].lower() for h in hits)
    context, citations = chat.build_grounded_rag_context(hits, f.db)
    assert "twenty days" in context and citations
    assert chat.retrieve_rag_chunks("annual leave twenty days", 102, f.db) == []


def test_sparse_index_retains_own_document_name(ingested_documents):
    f, _, _ = ingested_documents
    index = documents.BM25IndexManager(tenant_id=101)
    # Check persisted attribution independently of BM25's small-corpus IDF scores.
    assert index.doc_ids
    for chunk_id, metadata in zip(index.doc_ids, index.chunk_metadatas):
        chunk = f.db.get(models.DocumentChunk, chunk_id)
        document = f.db.get(models.Document, chunk.document_id)
        assert metadata["source"] == document.name, (
            f"Chunk from {document.name} labelled {metadata['source']}")


def test_stream_persistence_error_is_reported_to_client():
    class Gateway:
        async def generate_stream(self, **kwargs):
            yield "Synthetic answer"
    request = SimpleNamespace(is_disconnected=AsyncMock(return_value=False))
    def cannot_save(answer):
        raise RuntimeError("Synthetic persistence failure")
    async def collect():
        return [json.loads(frame.removeprefix("data: ").strip()) async for frame in
                stream_chat_response(request, 101, "Question", "Prompt", 101,
                                     gateway=Gateway(), on_complete=cannot_save)]
    frames = asyncio.run(collect())
    assert any(frame.get("error") for frame in frames), "Stream reported completion despite failed persistence"
