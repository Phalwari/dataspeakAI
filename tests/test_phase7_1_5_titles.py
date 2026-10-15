"""
tests/test_phase7_1_5_titles.py
---------------------------------
Unit, isolation, and async non-blocking tests for Phase 7 Task 7.1.5:
Dynamic Background Conversation Title Generation.

Verifies:
1. Word count and sanitization: 3 to 6 words, strips quotes, newlines, and caps length.
2. Fallback on failure: LLM failure leaves the initial heuristic title intact without crashing.
3. User customization preservation: If the user renames the conversation before the background job completes, the title is NOT overwritten.
4. Tenant isolation: Title generation rejects cross-tenant conversation updates.
5. Non-blocking guarantee: Chat response completes and returns before the background title job completes.
"""

import os
import sys
import asyncio
import pytest
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import models
from database import Base
from services.conversation_title import (
    generate_heuristic_title,
    sanitize_title,
    generate_and_set_conversation_title_in_background
)


class FakeTitleLLMGateway:
    """Fake gateway for title generation testing."""
    def __init__(self, title_response="Quarterly Enterprise Sales Revenue Analysis", raise_error=None, delay=0.0):
        self.title_response = title_response
        self.raise_error = raise_error
        self.delay = delay
        self.call_count = 0

    async def generate(self, prompt: str, purpose: str = "general", **kwargs):
        self.call_count += 1
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        if self.raise_error:
            raise self.raise_error
        return self.title_response


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

    # Seed Tenants
    t1 = models.Tenant(id=1, name="Tenant Alpha")
    t2 = models.Tenant(id=2, name="Tenant Beta")
    session.add_all([t1, t2])
    session.commit()

    try:
        yield session, TestingSession, engine
    finally:
        session.close()


# ==============================================================================
# 1. Word Count & Sanitization Tests
# ==============================================================================

def test_title_word_count_and_sanitization():
    """
    Tests that title sanitization:
    - Strips quotes (", ', `)
    - Strips newlines and tabs
    - Bounds word count between 3 and 6 words
    - Caps overall character length
    """
    fallback_query = "Can you show me the sales breakdown by region for Q3?"

    # 1. Clean 4-word title
    raw1 = '  "Quarterly Sales Performance Analysis"  '
    assert sanitize_title(raw1, fallback_query) == "Quarterly Sales Performance Analysis"

    # 2. Title with newlines and quotes
    raw2 = "```\n'Regional Revenue\nGrowth Trends Breakdown'\n```"
    clean2 = sanitize_title(raw2, fallback_query)
    assert "\n" not in clean2
    assert "'" not in clean2
    assert "`" not in clean2
    assert 3 <= len(clean2.split()) <= 6

    # 3. Overly long title (> 6 words) should be capped at 6 words
    raw3 = "A Very Long Comprehensive Exploration Of Enterprise Pipeline Architecture Metrics"
    clean3 = sanitize_title(raw3, fallback_query)
    words3 = clean3.split()
    assert len(words3) == 6
    assert clean3 == "A Very Long Comprehensive Exploration Of"

    # 4. Under-length title (< 3 words) falls back safely
    raw4 = "Sales"
    clean4 = sanitize_title(raw4, fallback_query)
    assert len(clean4.split()) >= 3

    # 5. Length cap check
    long_single_words = "Supercalifragilisticexpialidocious Incomprehensibilities Pseudopseudohypoparathyroidism Floccinaucinihilipilification Antidisestablishmentarianism Honorificabilitudinitatibus"
    clean5 = sanitize_title(long_single_words, fallback_query)
    assert len(clean5) <= 60


# ==============================================================================
# 2. Fallback on Failure Tests
# ==============================================================================

def test_title_fallback_on_llm_failure(test_db):
    """
    Asserts that if LLM title generation fails with an error, the initial heuristic title
    is preserved and the conversation title is never left empty or corrupted.
    """
    async def _run():
        db, _, _ = test_db
        user_query = "What were our top performing products across EMEA in 2024?"
        heuristic_title = generate_heuristic_title(user_query)

        conv = models.Conversation(
            tenant_id=1,
            title=heuristic_title,
            platform="web"
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

        failing_gateway = FakeTitleLLMGateway(raise_error=RuntimeError("Provider 503 Service Unavailable"))

        # Trigger background title job with failing gateway
        await generate_and_set_conversation_title_in_background(
            conversation_id=int(conv.id),
            tenant_id=1,
            user_query=user_query,
            assistant_answer="In 2024, our top performing products in EMEA were...",
            initial_heuristic_title=heuristic_title,
            gateway=failing_gateway,
            db=db
        )

        db.refresh(conv)
        # Title must stay as heuristic title
        assert conv.title == heuristic_title
        assert conv.title.startswith("What were our top performing")

    asyncio.run(_run())


# ==============================================================================
# 3. User Renaming Preservation
# ==============================================================================

def test_no_title_overwrite_if_user_already_renamed(test_db):
    """
    Asserts that if the user explicitly renames the conversation before or during the
    background title task, the user's custom title is NOT overwritten.
    """
    async def _run():
        db, _, _ = test_db
        user_query = "Show customer churn breakdown by monthly cohorts"
        heuristic_title = generate_heuristic_title(user_query)

        conv = models.Conversation(
            tenant_id=1,
            title=heuristic_title,
            platform="web"
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

        # User renames conversation in the UI
        setattr(conv, "title", "Customer Churn - My Custom Audit")
        db.commit()
        db.refresh(conv)

        fake_gateway = FakeTitleLLMGateway(title_response="Cohort Churn Rate Insights")

        # Background job runs with initial_heuristic_title
        await generate_and_set_conversation_title_in_background(
            conversation_id=int(conv.id),
            tenant_id=1,
            user_query=user_query,
            assistant_answer="Here is the cohort churn analysis...",
            initial_heuristic_title=heuristic_title,
            gateway=fake_gateway,
            db=db
        )

        db.refresh(conv)
        # Title must remain the user's custom title
        assert conv.title == "Customer Churn - My Custom Audit"

    asyncio.run(_run())


# ==============================================================================
# 4. Multi-Tenant Isolation
# ==============================================================================

def test_title_generation_tenant_isolation(test_db):
    """
    Asserts that background title generation checks tenant_id and will never
    modify a conversation belonging to a different tenant.
    """
    async def _run():
        db, _, _ = test_db
        user_query = "Display active marketing campaigns"
        heuristic_title = generate_heuristic_title(user_query)

        # Conversation belongs to Tenant 1
        conv = models.Conversation(
            tenant_id=1,
            title=heuristic_title,
            platform="web"
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

        fake_gateway = FakeTitleLLMGateway(title_response="Compromised Tenant Title")

        # Attacker attempts update with tenant_id=2
        await generate_and_set_conversation_title_in_background(
            conversation_id=int(conv.id),
            tenant_id=2,  # WRONG TENANT
            user_query=user_query,
            assistant_answer="Active campaigns are...",
            initial_heuristic_title=heuristic_title,
            gateway=fake_gateway,
            db=db
        )

        db.refresh(conv)
        assert conv.title == heuristic_title
        assert conv.title != "Compromised Tenant Title"
        assert fake_gateway.call_count == 0  # Gateway never called

    asyncio.run(_run())


# ==============================================================================
# 5. Non-Blocking Execution Guarantee
# ==============================================================================

def test_title_generation_never_blocks_chat_response(test_db):
    """
    Asserts that the chat response is produced and returned immediately without
    blocking on title generation (verified via background task event sync).
    """
    async def _run():
        db, _, _ = test_db
        user_query = "What is the average transaction value?"
        heuristic_title = generate_heuristic_title(user_query)

        conv = models.Conversation(
            tenant_id=1,
            title=heuristic_title,
            platform="web"
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

        gate_opened = asyncio.Event()

        class BlockingTitleGateway:
            async def generate(self, prompt: str, purpose: str = "general", **kwargs):
                # Wait until the gate is opened by the main thread
                await gate_opened.wait()
                return "Average Transaction Value Metrics"

        blocking_gateway = BlockingTitleGateway()

        # Launch the title task as a background task
        title_task = asyncio.create_task(
            generate_and_set_conversation_title_in_background(
                conversation_id=int(conv.id),
                tenant_id=1,
                user_query=user_query,
                assistant_answer="The average transaction value is $145.20.",
                initial_heuristic_title=heuristic_title,
                gateway=blocking_gateway,
                db=db
            )
        )

        # Before gate opens: chat response would already be returned to user
        # Verify title task has NOT finished
        assert not title_task.done()
        db.refresh(conv)
        assert conv.title == heuristic_title  # Still heuristic title

        # Now let the background task finish
        gate_opened.set()
        await title_task

        db.refresh(conv)
        assert conv.title == "Average Transaction Value Metrics"

    asyncio.run(_run())
