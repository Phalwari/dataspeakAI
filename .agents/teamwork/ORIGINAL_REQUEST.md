# Original User Request

## 2026-10-20T07:43:12Z

This is a single self-contained fix; keep it small and focused.

Comprehensive full-stack enhancement of DataSpeakAI's conversational chatbot engine: introduce a dedicated conversational intent route to eliminate robotic "no chunks found" dead-ends, enrich multi-turn context memory for follow-up SQL/RAG queries, upgrade prompt synthesis for structured executive Markdown summaries with clickable follow-up suggestions, and enable rich Markdown rendering in the chat interface.

Working directory: `C:\Users\Umer\.gemini\antigravity\worktrees\dataspeakAI\pull_review_all_changes`
Integrity mode: development

## Requirements

### R1. Conversational Intent & Intelligent Routing
- Introduce a dedicated `"conversational"` route in query classification so greetings, platform help inquiries, introductions, and general dialogue do not fall into SQL generation or fail with empty RAG errors.
- Equip the conversational synthesis engine with platform knowledge of DataSpeakAI (NL-to-SQL, RAG, ERD schema visualization, widget customization, multi-tenant security) to answer user questions about the platform accurately.

### R2. Multi-Turn Anaphora & Context Continuity
- Inject prior execution metadata (previous SQL queries, queried table names, and key entity mentions) into the multi-turn context passed to `SQLAgent` and RAG synthesis.
- Ensure follow-up questions (e.g., "filter those by California", "show the top 3", "summarize that in a table") resolve references to preceding queries and results instead of failing or defaulting to disconnected tables.

### R3. High-Quality Structured Prompt Synthesis
- Overhaul synthesis prompts for SQL, RAG, Hybrid, and Conversational modes to deliver structured executive Markdown: direct takeaway, key figures in bold (`**$12,450**`), clean markdown tables for tabular data, and 2-3 logical follow-up question suggestions.
- Ensure the assistant reliably returns 2-3 suggested follow-up questions in its metadata or trailing message block for discovery.
- Ensure SQL errors or missing columns trigger helpful guidance and table suggestions rather than opaque internal database error messages.

### R4. Frontend Rich Markdown & Follow-Up Suggestions UI
- Upgrade `src/app/pages/dashboard/ChatPage.tsx` message body rendering from raw `whitespace-pre-wrap` text to a rich, safe Markdown renderer that displays bold highlights, lists, code blocks, and formatted tables with alternating row styling.
- Render clickable suggestion pills/chips beneath assistant responses that populate the chat input on click.

## Acceptance Criteria

### Conversational & Behavioral Guardrails
- [ ] Non-database queries (e.g. "Hello", "What can you do?", "How do I connect a PostgreSQL database?") return a helpful conversational answer rather than "no relevant document chunks matching your question".
- [ ] Anaphoric follow-up queries (e.g. "Filter those by status 'completed'") resolve against preceding query context.
- [ ] SQL synthesis outputs formatted Markdown tables and clear bulleted insights instead of raw JSON previews or single-line answers.
- [ ] The chat UI displays clickable suggested follow-up pills below assistant messages.
- [ ] Citations in RAG mode remain grounded in retrieved chunks (`[Source: filename]`) without hallucinations.

### Code & System Quality
- [ ] All changes adhere to `AGENTS.md` engineering standards (parameterized queries, non-blocking async LLM streaming, zero PII leakage).
- [ ] Existing automated test suites for backend routers (`pytest backend/tests/`) and frontend components (`npm run test`) pass with zero regressions.
