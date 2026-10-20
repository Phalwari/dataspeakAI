"""
backend/services/conversation_memory.py
----------------------------------------
Conversation Memory Management for Phase 7 Task 7.1.4:
- Maintains a strict sliding window of MAX_RECENT_TURNS = 10 verbatim messages.
- Detects threshold crossings (> 15 turns, with 5-turn incremental steps).
- Asynchronously summarizes older conversation turns via the LLM Gateway.
- Employs per-conversation locks and monotonically increasing version checks
  to deterministically prevent concurrent summary jobs from regressing state.
- Strictly respects multi-tenant isolation.
- Falls back safely to sliding window alone on summarization failures without
  logging any sensitive conversational text.
"""

import logging
import asyncio
import json
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

import models
from database import SessionLocal

logger = logging.getLogger(__name__)


class ConversationMemoryManager:
    """
    Manages long-running multi-turn conversation memory, prompt compression,
    and asynchronous background summarization.
    """
    MAX_RECENT_TURNS: int = 10
    SUMMARY_TRIGGER_TURNS: int = 15
    SUMMARY_STEP: int = 5

    # In-memory per-conversation asyncio locks to serialize concurrent background jobs
    _locks: Dict[int, asyncio.Lock] = {}

    @classmethod
    def get_lock(cls, conversation_id: int) -> asyncio.Lock:
        """Retrieves or creates an asyncio.Lock for a specific conversation."""
        if conversation_id not in cls._locks:
            cls._locks[conversation_id] = asyncio.Lock()
        return cls._locks[conversation_id]

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Deterministic, fast tokenizer stub for prompt budgeting.
        Estimates ~1.3 tokens per whitespace-separated word.
        """
        if not text:
            return 0
        words = text.split()
        return max(1, int(len(words) * 1.3))

    @classmethod
    def should_trigger_summary(cls, total_turns: int, current_summary_turn_count: int) -> bool:
        """
        Returns True only when the conversation exceeds SUMMARY_TRIGGER_TURNS (15)
        and crosses a new threshold step (every 5 older turns).
        """
        if total_turns <= cls.SUMMARY_TRIGGER_TURNS:
            return False
        
        older_turns_count = total_turns - cls.MAX_RECENT_TURNS
        if current_summary_turn_count == 0:
            return True
        
        return (older_turns_count - current_summary_turn_count) >= cls.SUMMARY_STEP

    @classmethod
    def build_context(
        cls,
        conversation: models.Conversation,
        messages: List[models.Message],
        max_recent_turns: int = MAX_RECENT_TURNS
    ) -> str:
        """
        Builds the synthesized conversation context for LLM prompt injection:
        Injects [Conversation Summary: ...] if available, followed by the
        most recent verbatim turns (capped at max_recent_turns).
        """
        if not messages and (not conversation or not conversation.summary_text):
            return ""

        context_blocks = []

        # 1. Rolling Summary block if present
        if conversation and conversation.summary_text and conversation.summary_text.strip():
            context_blocks.append(f"[Conversation Summary: {conversation.summary_text.strip()}]")

        # 2. Verbatim sliding window of recent messages
        recent_messages = messages[-max_recent_turns:] if len(messages) > max_recent_turns else messages
        if recent_messages:
            context_blocks.append("--- RECENT CONVERSATION HISTORY ---")
            for msg in recent_messages:
                role_label = "User" if msg.sender_role == "user" else "Assistant"
                snippet = msg.content.strip()
                # Truncate very long historical messages to avoid individual message bloat
                if len(snippet) > 600:
                    snippet = snippet[:600] + "..."
                context_blocks.append(f"{role_label}: {snippet}")

                # Inject prior execution metadata into multi-turn context (R2: Multi-Turn Anaphora & Context Continuity)
                if msg.sender_role == "assistant" and getattr(msg, "metadata_json", None):
                    raw_meta = msg.metadata_json
                    if isinstance(raw_meta, str):
                        try:
                            meta = json.loads(raw_meta)
                        except Exception:
                            meta = {}
                    elif isinstance(raw_meta, dict):
                        meta = raw_meta
                    else:
                        meta = {}

                    sql_data = meta.get("sql_data")
                    if sql_data and isinstance(sql_data, dict):
                        prev_sql = sql_data.get("generated_sql")
                        row_count = sql_data.get("row_count")
                        cols = sql_data.get("columns", [])
                        if prev_sql:
                            try:
                                from services.sql_engine import extract_sql_referenced_tables
                                tables = extract_sql_referenced_tables(prev_sql)
                            except Exception:
                                tables = []
                            db_name = meta.get("database_name") or sql_data.get("database_name")
                            db_str = f"Database=`{db_name}` | " if db_name else ""
                            tbl_str = ", ".join(tables) if tables else "none"
                            col_str = ", ".join(cols[:6]) if cols else "none"
                            context_blocks.append(
                                f"[Prior Execution: {db_str}SQL=`{prev_sql}` | Tables=[{tbl_str}] | Columns=[{col_str}] | Rows Returned={row_count}]"
                            )
                    sources = meta.get("sources")
                    if sources and isinstance(sources, list):
                        doc_names = list(dict.fromkeys(
                            s.get("document_name") for s in sources if isinstance(s, dict) and s.get("document_name")
                        ))
                        if doc_names:
                            context_blocks.append(
                                f"[Prior Execution: Knowledge Base Sources=[{', '.join(doc_names[:4])}]]"
                            )

        return "\n".join(context_blocks)

    @classmethod
    async def summarize_older_turns(
        cls,
        conversation_id: int,
        tenant_id: int,
        older_messages: List[models.Message],
        target_turn_count: int,
        db: Optional[Session] = None,
        gateway: Optional[Any] = None
    ) -> Optional[str]:
        """
        Generates an LLM summary of older conversation turns.
        Guarantees tenant isolation and version non-regression.
        """
        if not older_messages:
            return None

        # Resolve gateway
        if gateway is None:
            from services.llm_generation_service import llm_gateway
            gateway = llm_gateway

        # Resolve DB session
        owns_session = False
        if db is None:
            db = SessionLocal()
            owns_session = True

        try:
            # 1. Multi-Tenant Isolation Check
            conv = db.query(models.Conversation).filter(
                models.Conversation.id == conversation_id,
                models.Conversation.tenant_id == tenant_id
            ).first()

            if not conv:
                logger.warning(
                    f"[CONV_MEMORY] Tenant isolation rejection: conv_id={conversation_id}, tenant_id={tenant_id}"
                )
                return None

            # 2. Acquire per-conversation lock
            lock = cls.get_lock(conversation_id)
            async with lock:
                # Re-verify in-database version under lock
                db.refresh(conv)
                if conv.summary_turn_count >= target_turn_count:
                    logger.info(
                        f"[CONV_MEMORY] Version guard: current {conv.summary_turn_count} >= target {target_turn_count} for conv {conversation_id}"
                    )
                    return conv.summary_text

                # Build prompt for summarization
                older_turns_text = "\n".join([
                    f"{'User' if m.sender_role == 'user' else 'Assistant'}: {m.content.strip()}"
                    for m in older_messages
                ])

                prompt = (
                    "Summarize the following earlier conversation turns concisely in 2-4 sentences. "
                    "Focus strictly on key facts, questions, user preferences, and business context. "
                    "Do not include conversational pleasantries or filler.\n\n"
                    f"{older_turns_text}"
                )

                try:
                    summary = await gateway.generate(
                        prompt=prompt,
                        purpose="conversation_summary"
                    )
                    summary = (summary or "").strip()
                    if not summary:
                        raise ValueError("Empty summary returned by LLM")

                    from sqlalchemy import text
                    current_turn_count = int(conv.summary_turn_count or 0)
                    cas_res = db.execute(
                        text(
                            "UPDATE conversations SET summary_text = :summary, summary_turn_count = :new_count "
                            "WHERE id = :id AND (summary_turn_count = :old_count OR summary_turn_count IS NULL)"
                        ),
                        {
                            "summary": summary,
                            "new_count": target_turn_count,
                            "id": conversation_id,
                            "old_count": current_turn_count
                        }
                    )
                    db.commit()
                    if cas_res.rowcount == 0:
                        logger.warning(
                            f"[CONV_MEMORY] CAS version mismatch for conv {conversation_id}: version was updated concurrently. Discarding stale update."
                        )
                        db.refresh(conv)
                        return conv.summary_text

                    db.refresh(conv)
                    logger.info(f"[CONV_MEMORY] Successfully updated summary for conv {conversation_id} to version {target_turn_count}")
                    return summary
                except Exception as ex:
                    # Clean fallback: log error type without logging user content
                    logger.warning(
                        f"[CONV_MEMORY] Summarization generation error for conv {conversation_id} (error: {type(ex).__name__}). Falling back to sliding window."
                    )
                    return None
        finally:
            if owns_session:
                db.close()

    @classmethod
    async def summarize_in_background(
        cls,
        conversation_id: int,
        tenant_id: int,
        gateway: Optional[Any] = None
    ) -> None:
        """
        Background worker entrypoint (safe for FastAPI BackgroundTasks).
        Loads conversation in an isolated session, determines older turns,
        and triggers summarize_older_turns.
        """
        db = SessionLocal()
        try:
            conv = db.query(models.Conversation).filter(
                models.Conversation.id == conversation_id,
                models.Conversation.tenant_id == tenant_id
            ).first()

            if not conv:
                return

            messages = db.query(models.Message).filter(
                models.Message.conversation_id == conversation_id
            ).order_by(models.Message.created_at.asc()).all()

            if not cls.should_trigger_summary(len(messages), conv.summary_turn_count):
                return

            older_messages = messages[:-cls.MAX_RECENT_TURNS]
            target_turn_count = len(older_messages)

            await cls.summarize_older_turns(
                conversation_id=conversation_id,
                tenant_id=tenant_id,
                older_messages=older_messages,
                target_turn_count=target_turn_count,
                db=db,
                gateway=gateway
            )
        except Exception as e:
            logger.warning(f"[CONV_MEMORY] Background summary task error for conv {conversation_id}: {type(e).__name__}")
        finally:
            db.close()
