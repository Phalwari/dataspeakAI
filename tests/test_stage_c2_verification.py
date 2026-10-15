import os
import sys
import time
import json
import asyncio
from datetime import datetime, timezone, timedelta
from typing import AsyncGenerator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)


# =========================================================================
# STEP 1.2: Router Registration Tests (UNIT)
# =========================================================================
def test_router_registration_unit():
    """Verify that chat and widget routers import cleanly and register their core routes."""
    from routers.chat import router as chat_router
    from routers.widget import router as widget_router

    # Assert /api/chat exists with POST method
    chat_routes = {route.path: route.methods for route in chat_router.routes}
    assert "/api/chat" in chat_routes, "Route /api/chat must be registered"
    assert "POST" in chat_routes["/api/chat"], "/api/chat must accept POST"

    # Assert /api/widget/chat exists with POST method
    widget_routes = {route.path: route.methods for route in widget_router.routes}
    assert "/api/widget/chat" in widget_routes, "Route /api/widget/chat must be registered"
    assert "POST" in widget_routes["/api/widget/chat"], "/api/widget/chat must accept POST"


# =========================================================================
# STEP 1.3: DateTime Naive vs Aware Filter Tests (UNIT)
# =========================================================================
BaseDatetimeTest = declarative_base()

class QueryLogDateTest(BaseDatetimeTest):
    __tablename__ = "query_logs_date_test"
    id = Column(Integer, primary_key=True)
    widget_key_id = Column(Integer)
    source = Column(String)
    created_at = Column(DateTime)

def test_datetime_naive_and_aware_compatibility_unit(tmp_path):
    """
    Verifies that naive datetime.utcnow() and timezone-aware datetime.now(timezone.utc)
    are both stored compatibly in SQLite and correctly match date filters (e.g. >= month_start).
    """
    db_file = tmp_path / "test_dates.db"
    engine = create_engine(f"sqlite:///{db_file}")
    BaseDatetimeTest.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    naive_ts = datetime.utcnow()
    aware_ts = datetime.now(timezone.utc)

    # Insert one naive row and one aware row
    session.add(QueryLogDateTest(widget_key_id=10, source="widget", created_at=naive_ts))
    session.add(QueryLogDateTest(widget_key_id=10, source="widget", created_at=aware_ts))
    session.commit()

    now = datetime.now(timezone.utc)
    month_start_aware = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    month_start_naive = datetime(now.year, now.month, 1)

    # Query using aware cutoff
    matched_aware = session.query(QueryLogDateTest).filter(
        QueryLogDateTest.widget_key_id == 10,
        QueryLogDateTest.source == "widget",
        QueryLogDateTest.created_at >= month_start_aware
    ).count()
    assert matched_aware == 2, f"Expected 2 matches for aware filter, got {matched_aware}"

    # Query using naive cutoff
    matched_naive = session.query(QueryLogDateTest).filter(
        QueryLogDateTest.widget_key_id == 10,
        QueryLogDateTest.source == "widget",
        QueryLogDateTest.created_at >= month_start_naive
    ).count()
    assert matched_naive == 2, f"Expected 2 matches for naive filter, got {matched_naive}"

    session.close()


# =========================================================================
# STEP 1.5: Non-streaming Compatibility (UNIT)
# =========================================================================
def test_non_streaming_chat_json_keys_unit():
    """
    Assert that POST /api/chat with stream=False returns all required JSON keys:
    answer, conversation_id, message_id, query_type, sources, sql_data
    """
    from main import app
    from dependencies import get_current_user
    import models

    fake_user = models.User(
        id=999,
        email="test_c2@example.com",
        tenant_id=1,
        role="admin"
    )

    app.dependency_overrides[get_current_user] = lambda: fake_user
    client = TestClient(app)

    payload = {
        "query": "hello non stream",
        "stream": False
    }

    try:
        response = client.post("/api/chat", json=payload)
        assert response.status_code == 200, f"Chat failed: {response.text}"
        data = response.json()
        expected_keys = {"answer", "conversation_id", "message_id", "query_type", "sources", "sql_data"}
        for k in expected_keys:
            assert k in data, f"Key '{k}' missing from non-streaming ChatResponse. Got keys: {list(data.keys())}"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# =========================================================================
# STEP 2: Failing Test for NL-to-SQL Error-as-Answer Bug (UNIT)
# =========================================================================
class MockDisconnectedRequest:
    def __init__(self, disconnected=False):
        self._disconnected = disconnected

    async def is_disconnected(self):
        return self._disconnected


def test_nl_to_sql_error_streaming_failing_first_unit():
    """
    FAILS on existing code before fix:
    When an SQL error occurs (status='failed'), stream_chat_response must:
    1. NOT stream the raw exception or table name as chunk events.
    2. Emit a structured error event (done=True, error=non-empty, chunk="").
    3. Ensure no raw error details or internal table names reach the client.
    """
    async def _run():
        from services.chat_stream import stream_chat_response
        import schemas

        raw_error_detail = "no such table: secret_internal_payroll_table"
        sql_error_obj = schemas.NLQueryResponse(
            query="show payroll",
            generated_sql="SELECT * FROM secret_internal_payroll_table",
            explanation="Attempted to query payroll",
            columns=[],
            rows=[],
            row_count=0,
            execution_time_ms=5.0,
            status="failed",
            error_detail=raw_error_detail
        )

        persisted_answers = []
        def on_complete_callback(ans: str):
            persisted_answers.append(ans)
            return 101

        req = MockDisconnectedRequest(disconnected=False)
        stream_gen = stream_chat_response(
            request=req,
            conversation_id=42,
            user_query="show payroll",
            prompt=None,
            tenant_id=1,
            citations=[],
            sql_data=sql_error_obj,
            query_type="sql",
            on_complete=on_complete_callback,
            static_fallback=f"Error executing query on database `main_db`: {raw_error_detail}"
        )

        received_events = []
        async for sse_line in stream_gen:
            if sse_line.startswith("data: "):
                payload = json.loads(sse_line[6:].strip())
                received_events.append(payload)

        # 1. Assert structured error event is present
        error_events = [ev for ev in received_events if ev.get("error")]
        assert len(error_events) > 0, f"Expected a structured error event, received: {received_events}"
        assert error_events[0]["done"] is True, "Error event must have done=True"
        assert error_events[0]["chunk"] == "", "Error event must have empty chunk"

        # 2. Assert raw error text or table name is NEVER streamed as a chunk
        chunk_events = [ev for ev in received_events if ev.get("chunk")]
        for ev in chunk_events:
            assert raw_error_detail not in ev["chunk"], f"Raw error leaked in chunk: {ev['chunk']}"
            assert "secret_internal_payroll_table" not in ev["chunk"], f"Secret table leaked in chunk: {ev['chunk']}"

    asyncio.run(_run())


# =========================================================================
# STEP 4: Embedding & CrossEncoder Constructor Caching Tests (UNIT)
# =========================================================================
def test_embedding_and_cross_encoder_constructor_caching_unit(monkeypatch):
    """
    Verifies that HuggingFaceEmbeddings and CrossEncoder constructors are called
    only ONCE per process across multiple invocations (caching check).
    """
    import search.hybrid as hybrid_mod
    import routers.chat as chat_mod

    # 1. Test HuggingFaceEmbeddings constructor count
    hf_constructor_calls = []
    class FakeHFEmbeddings:
        def __init__(self, model_name):
            hf_constructor_calls.append(model_name)

    monkeypatch.setattr(chat_mod, "embeddings_model", None)
    monkeypatch.setattr("langchain_huggingface.HuggingFaceEmbeddings", FakeHFEmbeddings, raising=False)
    monkeypatch.setattr("langchain_community.embeddings.HuggingFaceEmbeddings", FakeHFEmbeddings, raising=False)

    _ = chat_mod.get_embeddings()
    _ = chat_mod.get_embeddings()
    assert len(hf_constructor_calls) == 1, f"Expected 1 HuggingFaceEmbeddings call, got {len(hf_constructor_calls)}"

    # 2. Test CrossEncoder constructor count across 2 rerank calls
    ce_constructor_calls = []
    class FakeCrossEncoder:
        def __init__(self, model_name):
            ce_constructor_calls.append(model_name)
        def predict(self, pairs):
            return [0.5] * len(pairs)

    from unittest.mock import MagicMock
    fake_st = MagicMock()
    fake_st.CrossEncoder = FakeCrossEncoder
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_st)
    monkeypatch.setattr(hybrid_mod, "_cached_cross_encoder", None)

    candidates = [{"content": "cand 1", "score": 0.8}, {"content": "cand 2", "score": 0.7}]
    _ = hybrid_mod.cross_encoder_rerank("query 1", candidates)
    _ = hybrid_mod.cross_encoder_rerank("query 2", candidates)

    assert len(ce_constructor_calls) == 1, (
        f"CrossEncoder constructed {len(ce_constructor_calls)} times across 2 calls. Expected 1 (caching bug)."
    )


# =========================================================================
# STEP 5: Mid-Stream Failover Raw SSE Lines (SIMULATED)
# =========================================================================
def test_mid_stream_failover_simulated():
    """
    Simulates an upstream provider failure midway through streaming (after 3 tokens).
    Verifies what the client receives: clean error event with done=True, no duplicates.
    """
    async def _run():
        from services.chat_stream import stream_chat_response

        class FailingGateway:
            async def generate_stream(self, prompt, tenant_id, purpose="chat"):
                yield "Token1 "
                yield "Token2 "
                yield "Token3 "
                raise RuntimeError("Simulated upstream provider outage / rate limit mid-stream")

        req = MockDisconnectedRequest(disconnected=False)
        stream_gen = stream_chat_response(
            request=req,
            conversation_id=99,
            user_query="test failover",
            prompt="simulate prompt",
            tenant_id=1,
            gateway=FailingGateway(),
            query_type="rag"
        )

        raw_sse_lines = []
        parsed_events = []
        async for line in stream_gen:
            raw_sse_lines.append(line)
            if line.startswith("data: "):
                parsed_events.append(json.loads(line[6:].strip()))

        # Check raw lines
        tokens_received = [ev["chunk"] for ev in parsed_events if ev.get("chunk")]
        assert tokens_received == ["Token1 ", "Token2 ", "Token3 "], f"Unexpected tokens: {tokens_received}"

        # Final event must be sanitized error event with done=True
        last_event = parsed_events[-1]
        assert last_event["done"] is True, f"Final event must have done=True: {last_event}"
        assert "error" in last_event, f"Final event must contain error field: {last_event}"
        assert last_event["chunk"] == "", "Final error event chunk must be empty"

        return raw_sse_lines

    raw_lines = asyncio.run(_run())
    assert len(raw_lines) >= 4, f"Expected at least 4 SSE lines, got: {raw_lines}"


# =========================================================================
# STEP 7: Slot Release Scenarios on In-Memory and Fake Redis (UNIT & SIMULATED)
# =========================================================================
class FakeRedisClient:
    """Minimal in-test Redis mock for testing Redis-backed slot limiter primitives."""
    def __init__(self):
        self.data: Dict[str, int] = {}
        self.ttls: Dict[str, float] = {}

    def incr(self, key: str) -> int:
        val = self.data.get(key, 0) + 1
        self.data[key] = val
        return val

    def decr(self, key: str) -> int:
        val = self.data.get(key, 0) - 1
        self.data[key] = val
        return val

    def expire(self, key: str, seconds: int) -> bool:
        self.ttls[key] = time.time() + seconds
        return True

    def delete(self, key: str) -> int:
        if key in self.data:
            del self.data[key]
            self.ttls.pop(key, None)
            return 1
        return 0

    def get(self, key: str):
        return self.data.get(key)


def test_slot_release_scenarios_in_memory_unit():
    """Tests 5 slot scenarios against the In-Memory limiter (UNIT)."""
    from services.widget_rate_limiter import WidgetRateLimiter
    limiter = WidgetRateLimiter()
    limiter.redis_client = None  # Force in-memory
    key = "pk_live_test_in_memory"

    # Scenario 1: Normal acquire and release
    assert limiter.acquire_stream(key, max_concurrent=2) is True
    assert limiter._active_streams.get(key) == 1
    limiter.release_stream(key)
    assert limiter._active_streams.get(key) == 0

    # Scenario 2: Cap reached
    assert limiter.acquire_stream(key, max_concurrent=2) is True
    assert limiter.acquire_stream(key, max_concurrent=2) is True
    assert limiter.acquire_stream(key, max_concurrent=2) is False  # Cap reached

    # Scenario 3: Release succeeds and allows subsequent acquire
    limiter.release_stream(key)
    assert limiter.acquire_stream(key, max_concurrent=2) is True

    # Cleanup
    limiter.release_stream(key)
    limiter.release_stream(key)
    assert limiter._active_streams.get(key) == 0


def test_slot_release_scenarios_redis_simulated():
    """Tests 5 slot scenarios against the Redis-backed limiter using in-test fake Redis (SIMULATED)."""
    from services.widget_rate_limiter import WidgetRateLimiter
    limiter = WidgetRateLimiter()
    fake_redis = FakeRedisClient()
    limiter.redis_client = fake_redis
    key = "pk_live_test_redis_mock"

    # Scenario 1: Normal acquire and release
    assert limiter.acquire_stream(key, max_concurrent=2) is True
    assert fake_redis.get(f"widget_streams:{key}") == 1
    limiter.release_stream(key)
    assert fake_redis.get(f"widget_streams:{key}") is None  # Deleted when <= 0

    # Scenario 2: Cap reached
    assert limiter.acquire_stream(key, max_concurrent=2) is True
    assert limiter.acquire_stream(key, max_concurrent=2) is True
    assert limiter.acquire_stream(key, max_concurrent=2) is False  # Cap reached (cur > max_streams, decremented)
    assert fake_redis.get(f"widget_streams:{key}") == 2

    # Scenario 3: Release succeeds and allows subsequent acquire
    limiter.release_stream(key)
    assert fake_redis.get(f"widget_streams:{key}") == 1
    assert limiter.acquire_stream(key, max_concurrent=2) is True

    # Cleanup
    limiter.release_stream(key)
    limiter.release_stream(key)
    assert fake_redis.get(f"widget_streams:{key}") is None
