# DISPATCH — Worker M3-1

Target: Create AGENTS.md AI Agent Context Standard at project root
Working directory: d:\dataspeak\.agents\worker_m3_1

Task:
Create `d:\dataspeak\AGENTS.md` incorporating all findings from `d:\dataspeak\.agents\explorer_m1_3\handoff.md` and `d:\dataspeak\.agents\ORIGINAL_REQUEST.md`:

1. Executive Summary & Project Purpose:
   - DataSpeakAI overview: Conversational AI & Business Intelligence SaaS platform allowing users to query databases and documents via natural language.

2. Tech Stack Breakdown:
   - Frontend: React 18.3.1, Vite 6.3.5, React Router v7, Tailwind CSS v4, Emotion, MUI 7, Radix UI Primitives, Framer Motion v12, Recharts, Sonner.
   - Backend: Python 3.10+, FastAPI, Uvicorn ASGI server, Pydantic v2, SQLAlchemy 2.0, Passlib bcrypt, PyJWT.
   - AI/RAG Engine: FAISS (`faiss-cpu`), HuggingFace SentenceTransformers (`all-MiniLM-L6-v2`), LangChain `RecursiveCharacterTextSplitter`, `pdfplumber`, `PyMuPDF`, Google Gemini 2.5 Flash API.
   - Database: SQLite (`sqlite:///./app.db` default), PostgreSQL (`psycopg2-binary`), MySQL (`pymysql`). Enterprise schema has 35 tables (`Full_Project_Schemas.sql`), MVP backend implements 10 models (`backend/models.py`).

3. Architecture & Key File Map:
   - Directory locations for `src/` (main.tsx, app/routes.ts, pages, components, ui, styles) and `backend/` (main.py, database.py, models.py, schemas.py, auth.py, routers/).
   - Detailed mapping of `docs/` (`docs/architecture/`, `docs/database/`, `docs/setup/`, `docs/reports/`, `docs/sessions/`, `docs/templates/`).

4. Code Conventions & Engineering Rules:
   - Naming patterns (PascalCase React components, camelCase variables/hooks, snake_case Python functions/models/DB columns).
   - SQL Safety & Security: Use SQLAlchemy parameterized queries or text binding (`conn.execute(text("SELECT * FROM table WHERE id = :id"), {"id": val})`). NEVER use f-string SQL interpolation.
   - Error Handling & Validation: Pydantic request validation, FastAPI HTTPException, Sonner toast notifications in UI.
   - Environment Variables: Frontend uses `VITE_API_BASE_URL` (`src/app/config/api.ts`). Backend uses `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `DATABASE_URL`, `RESEND_API_KEY`, `GEMINI_API_KEY`, `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`.

5. Instructions for AI Agents:
   - Mandatory context reading protocol before starting work.
   - Check `AGENTS.md`, `docs/`, `CHANGELOG.md`, and session logs before writing code.

DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Output: Write report to `d:\dataspeak\.agents\worker_m3_1\handoff.md`.
