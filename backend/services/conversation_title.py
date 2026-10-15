"""
backend/services/conversation_title.py
---------------------------------------
Dynamic Background Conversation Title Generation for Phase 7 Task 7.1.5:
- Generates 3-6 word descriptive titles via LLM Gateway in a non-blocking background task.
- Sanitizes output by stripping quotes, backticks, newlines, and capping length.
- Preserves user custom renames (never overwrites a title if the user modified it).
- Strictly enforces multi-tenant isolation.
- Falls back safely to initial heuristic title on any LLM or network failure.
"""

import logging
import asyncio
from typing import Optional, Any
from sqlalchemy.orm import Session

import models
from database import SessionLocal

logger = logging.getLogger(__name__)


def generate_heuristic_title(query: str) -> str:
    """
    Constructs the canonical heuristic title from the first 6 words of a user query.
    Used for initial title assignment and as a deterministic fallback.
    """
    if not query:
        return "New Conversation"
    words = query.strip().split()
    if not words:
        return "New Conversation"
    if len(words) <= 6:
        return " ".join(words)
    return " ".join(words[:6]) + "..."


def sanitize_title(title: Optional[str], fallback_query: str) -> str:
    """
    Sanitizes LLM title:
    - Strips quotes (", ', `), markdown markers, and newlines.
    - Enforces 3 to 6 words.
    - Caps overall character length to at most 60 characters.
    - Falls back to heuristic title if empty or malformed.
    """
    if not title:
        return generate_heuristic_title(fallback_query)

    # Strip quotes, backticks, newlines, carriage returns
    cleaned = title.replace("\r", " ").replace("\n", " ")
    for ch in ['"', "'", "`", "*", "#"]:
        cleaned = cleaned.replace(ch, "")

    cleaned = " ".join(cleaned.strip().split())
    # Remove leading common filler prefixes like "Title: "
    if cleaned.lower().startswith("title:"):
        cleaned = cleaned[6:].strip()

    words = cleaned.split()
    if not words:
        return generate_heuristic_title(fallback_query)

    # Under-length check (< 3 words)
    if len(words) < 3:
        heuristic = generate_heuristic_title(fallback_query)
        if len(heuristic.split()) >= len(words):
            return heuristic

    # Cap at 6 words
    if len(words) > 6:
        words = words[:6]

    result = " ".join(words)

    # Character length cap (max 60 chars)
    if len(result) > 60:
        result = result[:57] + "..."

    return result


async def generate_llm_title(user_query: str, assistant_answer: str, gateway: Optional[Any] = None) -> str:
    """
    Calls LLM Gateway to generate a concise 3-6 word title.
    """
    if gateway is None:
        from services.llm_generation_service import llm_gateway
        gateway = llm_gateway

    prompt = (
        "Generate a concise, descriptive conversation title (strictly 3 to 6 words) "
        "summarizing the user request and answer below. "
        "Do not include quotes, markdown, punctuation, or conversational filler like 'Title:' or 'Conversation about'.\n\n"
        f"User Request: {user_query[:300]}\n"
        f"Assistant Answer: {assistant_answer[:300]}\n\n"
        "Title:"
    )

    raw_response = await gateway.generate(prompt=prompt, purpose="conversation_title")
    return sanitize_title(raw_response, fallback_query=user_query)


async def generate_and_set_conversation_title_in_background(
    conversation_id: int,
    tenant_id: int,
    user_query: str,
    assistant_answer: str,
    initial_heuristic_title: str,
    gateway: Optional[Any] = None,
    db: Optional[Session] = None
) -> Optional[str]:
    """
    Background worker:
    1. Validates tenant ownership.
    2. Checks that the user has not customized/renamed the title in the interim.
    3. Generates LLM title and commits update.
    4. Falls back cleanly to initial heuristic title on any exception.
    """
    owns_session = False
    if db is None:
        db = SessionLocal()
        owns_session = True

    try:
        # Multi-Tenant Isolation Check
        conv = db.query(models.Conversation).filter(
            models.Conversation.id == conversation_id,
            models.Conversation.tenant_id == tenant_id
        ).first()

        if not conv:
            logger.warning(
                f"[CONV_TITLE] Tenant isolation violation or conv not found: id={conversation_id}, tenant={tenant_id}"
            )
            return None

        # Verify user has not already renamed the conversation
        db.refresh(conv)
        if conv.title != initial_heuristic_title:
            logger.info(f"[CONV_TITLE] User already renamed conv {conversation_id} to '{conv.title}'. Skipping overwrite.")
            return conv.title

        try:
            new_title = await generate_llm_title(user_query, assistant_answer, gateway=gateway)

            # Re-verify before commit
            db.refresh(conv)
            if conv.title == initial_heuristic_title:
                conv.title = new_title
                db.commit()
                db.refresh(conv)
                logger.info(f"[CONV_TITLE] Updated conv {conversation_id} title to: '{new_title}'")
                return conv.title
            return conv.title
        except Exception as ex:
            logger.warning(
                f"[CONV_TITLE] Title generation failed for conv {conversation_id} (error: {type(ex).__name__}). Preserving heuristic title."
            )
            return initial_heuristic_title
    finally:
        if owns_session:
            db.close()
