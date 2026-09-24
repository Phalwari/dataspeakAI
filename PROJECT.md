# Project: DataSpeakAI Core Missing Modules Implementation

## Architecture
- React 18 / Vite single-page frontend (`src/`) connected via REST API to FastAPI backend (`backend/`).
- SQLAlchemy ORM (`backend/models.py`, `backend/database.py`), SQLite (`app.db`) for app metadata + multi-database introspector (PostgreSQL, MySQL, SQLite).
- FAISS vector store + HuggingFace `SentenceTransformer` + Google Gemini 2.5 Flash API for RAG answer synthesis and Conversational NL-to-SQL query generation.
- Fernet symmetric encryption (`cryptography`) for DB password storage.
- Custom IIFE standalone bundle (`public/widget.js`) for embeddable chatbot widget.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Fernet DB Password Encryption | Encrypt database passwords at rest using Fernet and decrypt dynamically when generating connection URLs | M1 | survey |
| 2 | SQL Parameterization & Identifier Sanitization | Sanitize table/column identifiers against SQLAlchemy inspector whitelist before query execution | M1 | survey |
| 3 | Remove Hardcoded Secrets | Require GITHUB_CLIENT_ID/SECRET, SECRET_KEY, and FRONTEND_URL via environment variables | M1 | survey |
| 4 | Authorize /admin Route & Role Enforcement | Add frontend route guard for /admin and backend get_current_admin_user dependency | M1 | survey |
| 5 | Fix SQLite Introspection Bug | Remove duplicate get_connection_url definition in backend/routers/databases.py | M1 | survey |
| 6 | Env Var Alignment & Import Fix | Align VITE_API_BASE_URL in .env.example and fix sys.path in backend/main.py | M1 | survey |
| 7 | Conversational NL-to-SQL Query Engine Service | Create backend/services/sql_engine.py with Gemini 2.5 Flash, schema context, and prompt formatting | M2 | survey |
| 8 | Read-Only SELECT Guardrails | Strict SQL AST / regex validation permitting only SELECT/WITH statements and blocking DDL/DML/semicolons | M2 | survey |
| 9 | NL-to-SQL Router /api/query | Backend POST /api/query endpoint executing safe SQL on target DB and logging to QueryLog | M2 | survey |
| 10 | Interactive Frontend Query Chat UI | Interactive AI Query Assistant in DatabasesPage.tsx with natural language chat, SQL preview & data grid | M2 | survey |
| 11 | RAG Answer Synthesis Upgrade | Upgrade POST /api/documents/search in backend/routers/documents.py with Gemini 2.5 Flash synthesis & citations | M3 | survey |
| 12 | RAG Frontend UI Update | KnowledgeBasePage.tsx rendering synthesized AI answer card above collapsible source chunks | M3 | survey |
| 13 | QueryLog ORM Model & Migration | Add QueryLog model to backend/models.py to track user queries, execution times, rows, tokens | M4 | survey |
| 14 | Analytics & Logs Backend Router | Create backend/routers/analytics.py providing /overview, /trends, /logs, /usage, /admin/stats | M4 | survey |
| 15 | Dashboard Frontend Live Data Binding | Bind DashboardOverview, AnalyticsPage, LogsPage, UsagePage, AdminPanel to live backend APIs | M4 | survey |
| 16 | Dynamic ERD Visualizer Endpoint | Backend GET /api/databases/{db_id}/erd introspecting PKs, FKs, and table relationships | M5 | survey |
| 17 | Frontend ERD Diagram Component | Interactive ERD diagram visualizer modal in DatabasesPage.tsx rendering table boxes and SVG connections | M5 | survey |
| 18 | Standalone Embeddable JS Chatbot Widget | GET /api/chatbot-config/public endpoint + vite.widget.config.ts compiling public/widget.js bundle | M5 | survey |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Security Hardening & Bug Fixes | Fernet DB password encryption, SQL identifier sanitization, secret removal, /admin role authorization, SQLite inspection fix, env var alignment | None | DONE |
| 2 | Conversational NL-to-SQL Query Engine | backend/services/sql_engine.py, read-only SELECT guardrails, /api/query router, DatabasesPage.tsx interactive chat UI | M1 | DONE |
| 3 | RAG Knowledge Base Answer Synthesis | Upgrade /api/documents/search with Gemini 2.5 Flash synthesis & citations, KnowledgeBasePage.tsx UI update | M1 | DONE |
| 4 | Dashboard Live Data Binding & Analytics | QueryLog ORM model, backend/routers/analytics.py, live data binding for DashboardOverview, AnalyticsPage, LogsPage, UsagePage, AdminPanel | M1, M2 | PLANNED |
| 5 | Interactive ERD Visualizer & Widget Bundle | GET /api/databases/{db_id}/erd endpoint, ERDVisualizer frontend component, GET /api/chatbot-config/public, vite.widget.config.ts widget.js compilation | M1 | PLANNED |

## Interface Contracts
### Security Hardening ↔ All Routers
- `backend/crypto.py`: `encrypt_password(raw_password: str) -> str`, `decrypt_password(ciphertext: str) -> str`
- `backend/dependencies.py`: `get_current_admin_user(current_user: User = Depends(get_current_user)) -> User`

### NL-to-SQL Engine ↔ Frontend
- `POST /api/query`: Body `{ database_id: int, query: str }` -> Response `{ query: str, generated_sql: str, explanation: str, columns: list[str], rows: list[dict], row_count: int, execution_time_ms: float, status: str }`

### RAG Synthesis ↔ Frontend
- `POST /api/documents/search`: Body `{ query: str, top_k: int = 4 }` -> Response `{ query: str, answer: str, results: list[{ document_id: int, filename: str, chunk_index: int, score: float, content: str }] }`

### Analytics & Logs ↔ Dashboard
- `GET /api/analytics/overview` -> `{ total_queries: int, connected_databases: int, uploaded_documents: int, api_calls_today: int, subscription_plan: str, query_data: list, database_activity: list, recent_queries: list }`
- `GET /api/logs?page=1&limit=20` -> `{ items: list[dict], total: int, page: int, limit: int, total_queries: int, successful: int, failed: int, avg_response_time_ms: float }`

### ERD & Widget ↔ Frontend
- `GET /api/databases/{db_id}/erd` -> `{ database_id: int, database_name: str, tables: list[{ name: str, columns: list[{ name: str, type: str, is_primary: bool, is_foreign: bool }] }], relationships: list[{ source_table: str, source_column: str, target_table: str, target_column: str }] }`
- `GET /api/chatbot-config/public?api_key=...` -> `{ theme_color: str, widget_title: str, greeting_message: str, position: str, welcome_delay: int, sound_enabled: bool }`

## Code Layout
- `backend/`
  - `main.py`, `models.py`, `schemas.py`, `auth.py`, `crypto.py`, `database.py`, `dependencies.py`
  - `services/` (`sql_engine.py`)
  - `routers/` (`users.py`, `tenants.py`, `databases.py`, `api_keys.py`, `chatbot_config.py`, `documents.py`, `query.py`, `analytics.py`)
- `src/`
  - `app/config/api.ts`, `app/routes.ts`, `app/App.tsx`
  - `app/components/` (`ERDVisualizer.tsx`, `QueryChatPanel.tsx`, etc.)
  - `app/pages/` (`LoginPage.tsx`, `SignupPage.tsx`, `admin/AdminPanel.tsx`, `dashboard/*`)
  - `widget/index.ts` (standalone widget entry)
- `public/` (`widget.js`)
