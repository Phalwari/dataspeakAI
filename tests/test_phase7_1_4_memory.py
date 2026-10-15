"""
tests/test_phase7_1_4_memory.py
---------------------------------
Unit, concurrency, and regression tests for Phase 7 Task 7.1.4:
Conversation Memory Management (Sliding Window & Asynchronous Summarization).

Verifies:
1. Multi-turn budget: A 25-turn conversation keeps prompt context strictly under a fixed token budget.
2. Threshold crossing: Summary is refreshed only once per threshold crossing.
3. Concurrency guard: Two concurrent summary jobs do not regress the summary version or overwrite newer data.
4. Clean failure fallback: LLM failure during summarization falls back to sliding window without breaking chat.
5. Multi-tenant isolation: A conversation owned by another tenant is never read or summarized.
6. Idempotent schema migration: summary_text and summary_turn_count exist on Conversation.
"""

import os
import sys
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import models
from database import Base
from services.conversation_memory import ConversationMemoryManager
from services.db_migration import run_schema_migrations


class FakeLLMGateway:
    """Fake LLM Gateway for deterministic, offline testing."""
    def __init__(self, summary_response="Summary: User inquired about quarterly sales and database schema.", raise_error=None):
        self.summary_response = summary_response
        self.raise_error = raise_error
        self.call_count = 0
        self.calls = []

    async def generate(self, prompt: str, purpose: str = "general", **kwargs):
        self.call_count += 1
        self.calls.append({"prompt": prompt, "purpose": purpose, **kwargs})
        if self.raise_error:
            raise self.raise_error
        return self.summary_response


@pytest.fixture
def test_db():
    """In-memory SQLite database session isolated per test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSession()

    # Seed Tenant 1 and Tenant 2
    t1 = models.Tenant(id=1, name="Tenant One")
    t2 = models.Tenant(id=2, name="Tenant Two")
    session.add_all([t1, t2])
    session.commit()

    try:
        yield session, TestingSession, engine
    finally:
        session.close()


def create_sample_conversation(db, tenant_id: int, turn_count: int) -> models.Conversation:
    """Helper to populate a conversation with a specified number of user/assistant turns."""
    conv = models.Conversation(
        tenant_id=tenant_id,
        title="Test Conversation",
        platform="web"
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)

    for i in range(1, turn_count + 1):
        role = "user" if i % 2 != 0 else "assistant"
        msg = models.Message(
            conversation_id=conv.id,
            sender_role=role,
            content=(
                f"Turn {i}: Detailed discussion topic regarding enterprise data pipelines, "
                f"relational schemas, performance benchmarks, and index optimizations for quarter {i}. "
                f"We observed query execution latencies and need comprehensive guidance on partitioning strategies, "
                f"foreign key indexes, and analytical view materialized caching."
            ),
            query_type="rag" if role == "assistant" else "user"
        )
        db.add(msg)
    db.commit()
    db.refresh(conv)
    return conv


# ==============================================================================
# 1. 25-Turn Conversation Token Budget
# ==============================================================================

def test_25_turn_conversation_token_budget(test_db):
    """
    Asserts that in a 25-turn conversation, full history would exceed token budget,
    but ConversationMemoryManager compresses earlier turns into a summary and
    keeps prompt context strictly within a bounded budget (<= 800 tokens).
    """
    async def _run():
        db, session_factory, _ = test_db
        conv = create_sample_conversation(db, tenant_id=1, turn_count=25)
        messages = db.query(models.Message).filter(
            models.Message.conversation_id == conv.id
        ).order_by(models.Message.created_at.asc()).all()

        # Estimate uncompressed raw token count
        raw_text = "\n".join([f"{m.sender_role}: {m.content}" for m in messages])
        raw_tokens = ConversationMemoryManager.estimate_tokens(raw_text)
        assert raw_tokens > 1000, f"Raw conversation should be long, got {raw_tokens}"

        fake_gateway = FakeLLMGateway(
            summary_response="Summary: User explored pipeline schemas, benchmarks, and indexing optimizations for Q1-Q15."
        )

        # Execute summarization
        summary = await ConversationMemoryManager.summarize_older_turns(
            conversation_id=int(conv.id),
            tenant_id=1,
            older_messages=messages[:-ConversationMemoryManager.MAX_RECENT_TURNS],
            target_turn_count=len(messages) - ConversationMemoryManager.MAX_RECENT_TURNS,
            db=db,
            gateway=fake_gateway
        )

        assert summary is not None
        db.refresh(conv)
        assert conv.summary_text is not None
        assert conv.summary_turn_count == 15

        # Build prompt context
        context = ConversationMemoryManager.build_context(conv, messages)

        # Verify context structure
        assert "[Conversation Summary:" in context
        assert "--- RECENT CONVERSATION HISTORY ---" in context
        # Only the last 10 messages should be in recent history
        assert "Turn 25:" in context
        assert "Turn 16:" in context
        assert "Turn 1:" not in context  # Turn 1 is summarized, not in verbatim recent

        # Assert bounded token budget
        prompt_tokens = ConversationMemoryManager.estimate_tokens(context)
        assert prompt_tokens <= 800, f"Prompt token budget exceeded: {prompt_tokens} tokens"
        assert prompt_tokens < raw_tokens * 0.65

    asyncio.run(_run())


# ==============================================================================
# 2. Threshold Crossing Trigger Behavior
# ==============================================================================

def test_summary_refreshed_only_once_per_threshold_crossing():
    """
    Asserts should_trigger_summary returns True only when exceeding 15 turns for the
    first time, or when subsequent step threshold (5 turns) is crossed.
    """
    # <= 15 turns never triggers summarization
    assert not ConversationMemoryManager.should_trigger_summary(total_turns=10, current_summary_turn_count=0)
    assert not ConversationMemoryManager.should_trigger_summary(total_turns=15, current_summary_turn_count=0)

    # First crossing: 16 turns triggers summarization of older 6 turns
    assert ConversationMemoryManager.should_trigger_summary(total_turns=16, current_summary_turn_count=0)

    # Once summarized up to 6 turns, turns 16..20 should NOT re-trigger
    assert not ConversationMemoryManager.should_trigger_summary(total_turns=16, current_summary_turn_count=6)
    assert not ConversationMemoryManager.should_trigger_summary(total_turns=18, current_summary_turn_count=6)
    assert not ConversationMemoryManager.should_trigger_summary(total_turns=20, current_summary_turn_count=6)

    # Next threshold crossing at turn 21 (older turns = 11, delta = 5 >= STEP)
    assert ConversationMemoryManager.should_trigger_summary(total_turns=21, current_summary_turn_count=6)


# ==============================================================================
# 3. Concurrent Jobs & Non-Regression
# ==============================================================================

def test_two_concurrent_summary_jobs_no_regression(test_db):
    """
    Asserts that if two summary jobs run, a slower job with an older turn count
    will NOT overwrite or regress a newer summary version.
    """
    async def _run():
        db, _, _ = test_db
        conv = create_sample_conversation(db, tenant_id=1, turn_count=20)
        messages = db.query(models.Message).filter(
            models.Message.conversation_id == conv.id
        ).order_by(models.Message.created_at.asc()).all()

        # Pre-set DB to version 15 (as if a newer job finished first)
        setattr(conv, "summary_text", "Newer summary up to turn 15.")
        setattr(conv, "summary_turn_count", 15)
        db.commit()

        fake_gateway = FakeLLMGateway(summary_response="Stale summary up to turn 8.")

        # Slower job attempting to write an older version (target_turn_count = 8)
        older_messages = messages[:8]
        result = await ConversationMemoryManager.summarize_older_turns(
            conversation_id=int(conv.id),
            tenant_id=1,
            older_messages=older_messages,
            target_turn_count=8,
            db=db,
            gateway=fake_gateway
        )

        db.refresh(conv)
        # The version must NOT regress, and summary must remain the newer one
        assert conv.summary_turn_count == 15
        assert conv.summary_text == "Newer summary up to turn 15."

    asyncio.run(_run())


# ==============================================================================
# 4. Summarization Failure Fallback
# ==============================================================================

def test_summarization_failure_falls_back_cleanly(test_db):
    """
    Asserts that when LLM generation fails during summarization, the error is
    caught gracefully without crashing, leaving chat to fall back to the sliding window alone.
    """
    async def _run():
        db, _, _ = test_db
        conv = create_sample_conversation(db, tenant_id=1, turn_count=18)
        messages = db.query(models.Message).filter(
            models.Message.conversation_id == conv.id
        ).order_by(models.Message.created_at.asc()).all()

        failing_gateway = FakeLLMGateway(raise_error=RuntimeError("Rate limit / 429 simulated"))

        # Attempt summarization with failing gateway
        res = await ConversationMemoryManager.summarize_older_turns(
            conversation_id=int(conv.id),
            tenant_id=1,
            older_messages=messages[:-10],
            target_turn_count=8,
            db=db,
            gateway=failing_gateway
        )

        assert res is None  # Handled cleanly
        db.refresh(conv)
        assert conv.summary_text is None  # Summary not populated

        # Build context should fall back gracefully to sliding window alone
        context = ConversationMemoryManager.build_context(conv, messages)
        assert "[Conversation Summary:" not in context
        assert "--- RECENT CONVERSATION HISTORY ---" in context
        assert "Turn 18:" in context
        assert "Turn 9:" in context

    asyncio.run(_run())


# ==============================================================================
# 5. Multi-Tenant Isolation
# ==============================================================================

def test_cross_tenant_isolation(test_db):
    """
    Asserts that a conversation owned by Tenant 1 is never read or summarized by Tenant 2.
    """
    async def _run():
        db, _, _ = test_db
        # Create conversation belonging to Tenant 1
        conv = create_sample_conversation(db, tenant_id=1, turn_count=16)
        messages = db.query(models.Message).filter(
            models.Message.conversation_id == conv.id
        ).all()

        fake_gateway = FakeLLMGateway(summary_response="Compromised data")

        # Attempt cross-tenant access with tenant_id=2
        result = await ConversationMemoryManager.summarize_older_turns(
            conversation_id=int(conv.id),
            tenant_id=2,  # WRONG TENANT
            older_messages=messages[:-10],
            target_turn_count=6,
            db=db,
            gateway=fake_gateway
        )

        # Must be blocked
        assert result is None
        assert fake_gateway.call_count == 0  # Gateway never called
        db.refresh(conv)
        assert conv.summary_text is None  # DB unmodified

    asyncio.run(_run())


# ==============================================================================
# 6. Idempotent Schema Migration
# ==============================================================================

def test_db_migration_idempotent_conversation_columns(test_db):
    """
    Asserts that db_migration.run_schema_migrations ensures summary_text and
    summary_turn_count exist on the conversations table.
    """
    _, _, engine = test_db
    # Run schema migrations against the test engine
    run_schema_migrations(engine)

    from sqlalchemy import inspect
    inspector = inspect(engine)
    col_names = {c["name"] for c in inspector.get_columns("conversations")}
    assert "summary_text" in col_names
    assert "summary_turn_count" in col_names
