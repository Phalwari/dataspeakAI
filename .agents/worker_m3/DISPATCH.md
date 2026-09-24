## 2026-08-05T22:20:36Z

You are worker_m3.
Your working directory is d:\dataspeak\.agents\worker_m3\.
Please read d:\dataspeak\.agents\ORIGINAL_REQUEST.md, d:\dataspeak\PROJECT.md, and d:\dataspeak\.agents\explorer_sql_rag\handoff.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your Task: Implement Milestone 3 - RAG Knowledge Base Answer Synthesis:
1. Backend RAG Synthesis Upgrade (`backend/routers/documents.py` & `backend/schemas.py`):
   - Upgrade `POST /api/documents/search` in `backend/routers/documents.py`.
   - Update Pydantic schemas in `backend/schemas.py` (`SearchQuery`, `SearchSynthesisResponse`).
   - Retrieve top_k FAISS vector store chunks and pass chunk texts + document filenames into a prompt for Google Gemini 2.5 Flash API.
   - Synthesize a natural language answer with inline citations (`[Source: filename]`).
   - Implement robust fallback logic if `GEMINI_API_KEY` is not set or network call fails.
2. Frontend UI Update (`src/app/pages/dashboard/KnowledgeBasePage.tsx`):
   - Update `KnowledgeBasePage.tsx` search UI to handle synthesized answers.
   - Display a clean "AI Synthesized Answer" card above the list of matching document chunk reference cards.
3. Verification:
   - Test backend: `python -c "import backend.main"`
   - Test frontend: `npm run build`

Write your handoff report to `d:\dataspeak\.agents\worker_m3\handoff.md` and update `progress.md`.
Send a summary message when complete.
