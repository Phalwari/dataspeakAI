# Original User Request

## Initial Request — 2026-08-05T21:47:50+05:00

You are the Project Orchestrator for DataSpeakAI.
Your working directory is d:\dataspeak\.agents\orchestrator.
Original user request is recorded at d:\dataspeak\.agents\ORIGINAL_REQUEST.md.

Please orchestrate the implementation of the core missing modules of DataSpeakAI:
1. Security Hardening & Bug Fixes (Fernet encryption for stored DB passwords, parameterize raw SQL execution and sanitize dynamic identifiers, remove hardcoded secrets, authorize /admin route, fix SQLite inspection bug, align env vars VITE_API_BASE_URL).
2. Conversational NL-to-SQL Query Engine (backend service backend/services/sql_engine.py, router /api/query with Gemini 2.5 Flash, read-only SELECT guardrails, interactive frontend query chat UI).
3. RAG Knowledge Base Answer Synthesis (upgrade /api/documents/search with LLM answer synthesis).
4. Dashboard Live Data Binding & Analytics (replace static mock data on DashboardOverview, AnalyticsPage, LogsPage, UsagePage, AdminPanel with live backend endpoints).
5. Interactive ERD Visualizer & Widget Bundle (/api/databases/{db_id}/erd dynamic relationship endpoint, compile standalone embeddable JS chatbot widget bundle).

Execute, review, challenge, and audit each milestone systematically. Ensure npm run build passes with 0 errors and python -c "import backend.main" succeeds.
Report back to Sentinel when all milestones are finished and verified.
