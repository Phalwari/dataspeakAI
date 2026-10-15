# DataSpeakAI — AI Agent Context Standard & Engineering Guide

Welcome to **DataSpeakAI**. This document (`AGENTS.md`) is the single source of truth and primary context standard for any AI coding agent (Google Antigravity, Cursor, GitHub Copilot, Claude Code) working on this codebase.

All AI agents must strictly adhere to the guidelines, architectural patterns, security rules, and workflows outlined below.

---

## 1. Executive Summary & Project Purpose

### 1.1 Platform Overview
**DataSpeakAI** is an enterprise-grade Conversational AI & Business Intelligence SaaS platform designed to bridge the gap between complex relational databases, unstructured business documents, and end-user decision making. The platform empowers both technical and non-technical business users to query SQL databases (PostgreSQL, MySQL, SQLite) and document knowledge bases using intuitive natural language.

### 1.2 Core Product Capabilities
* **Natural Language to SQL (NL-to-SQL):** Automatic database schema introspection and query generation allowing users to explore tables, inspect columns, and run safe data previews.
* **Retrieval-Augmented Generation (RAG):** Document indexing engine supporting PDF and text upload, chunking via LangChain, vector storage using FAISS, and semantic search powered by HuggingFace embeddings.
* **Multi-Modal Document & Vision Processing:** OCR, chart, table, and visual document analysis powered by Google Gemini 2.5 Flash API and `pdfplumber` / `PyMuPDF`.
* **Multi-Tenant SaaS Management:** Complete tenant isolation, user role management, email/OTP authentication, GitHub OAuth sign-in, API key management, and customizable embeddable chatbot widgets.

### 1.3 Target Persona & System Vision
* **Primary Users:** Business analysts, managers, operational teams, and software engineers seeking instant data insights without writing manual SQL or manually sifting through PDFs.
* **System Design Goal:** A scalable, highly secure, modular hybrid SaaS application featuring a React/Vite single-page frontend and a FastAPI microservice backend.

---

## 2. Tech Stack Breakdown

### 2.1 Frontend Stack (`package.json`, `src/`)
* **Core Framework:** React `18.3.1`, Vite `6.3.5`
* **Routing:** React Router v7 (`react-router` `^7.13.0`) using `createBrowserRouter`
* **Styling & UI System:**
  * Tailwind CSS v4 (`@tailwindcss/vite` `4.1.12`, `tailwindcss` `4.1.12`)
  * Emotion (`@emotion/react` `11.14.0`, `@emotion/styled` `11.14.1`)
  * MUI v7 (`@mui/material` `7.3.5`, `@mui/icons-material` `7.3.5`)
  * Radix UI Primitives (`@radix-ui/react-*`)
  * Framer Motion v12 (`motion` `12.23.24`)
  * Class Utilities: `clsx` `2.1.1`, `tailwind-merge` `3.2.0`, `class-variance-authority` `0.7.1`, `tw-animate-css` `1.3.8`
* **Data Visualization & Components:**
  * Charts: Recharts `2.15.2`
  * Toast Notifications: Sonner `2.0.3`
  * Drawers & Command Palette: Vaul `1.1.2`, CMDK `1.1.1`
  * Icons & UI Elements: Lucide React `0.487.0`, Embla Carousel `8.6.0`
  * Forms & Interactivity: React Hook Form `7.55.0`, React DnD `16.0.1`, React Resizable Panels `2.1.7`

### 2.2 Backend API Stack (`backend/requirements.txt`, `backend/main.py`)
* **Runtime & Framework:** Python 3.10+, FastAPI (`fastapi`), Uvicorn ASGI Server (`uvicorn`)
* **Validation & Serialization:** Pydantic v2 (`pydantic[email]`)
* **Database & ORM:**
  * SQLAlchemy `^2.0.35`
  * Default Engine: SQLite (`sqlite:///./app.db`)
  * Production Connectors: PostgreSQL (`psycopg2-binary`), MySQL / MariaDB (`pymysql`)
* **Authentication & Security:**
  * Password Hashing: Passlib with bcrypt (`passlib[bcrypt]`)
  * Token Management: PyJWT (`PyJWT`), FastAPI `OAuth2PasswordBearer`
* **Communications:** Resend API (`resend`), fallback via Python `smtplib`

### 2.3 AI & RAG Engine (`backend/routers/documents.py`, `backend/test_rag.py`)
* **Vector Store:** FAISS (`faiss-cpu`) local index
* **Embeddings:** HuggingFace `SentenceTransformer` (`all-MiniLM-L6-v2`) via `langchain-huggingface`
* **Text Chunking:** LangChain `RecursiveCharacterTextSplitter` (supporting fixed-size, paragraph, line, and sentence splitting strategies)
* **Document & Vision Extraction:**
  * `pdfplumber` (markdown table extraction)
  * `PyMuPDF` / `fitz` (image extraction)
  * Google Gemini API (`gemini-2.5-flash` REST endpoint for OCR and visual chart/diagram comprehension)

### 2.4 Database Architecture & Model Coverage
* **Enterprise SQL Schema:** Defined in `docs/database/Full_Project_Schemas.sql` (35 production tables spanning tenants, users, database connections, query logs, documents, vector records, subscriptions, audit logs, and security policies).
* **Backend ORM Implementation:** Implemented in `backend/models.py` (10 MVP models: `Tenant`, `User`, `UserDatabaseAccess`, `TenantInvite`, `DatabaseConnection`, `ApiKey`, `ChatbotConfig`, `Document`, `DocumentChunk`, `PasswordResetOTP`).
* **Architectural Note:** AI agents must be aware that 25 tables defined in `Full_Project_Schemas.sql` are not yet created in `backend/models.py`. When extending backend features, refer to `Full_Project_Schemas.sql` as the canonical database specification.

---

## 3. Architecture & Key File Map

### 3.1 Project Directory Structure

```
d:\dataspeak\
├── .agents/                           # AI agent metadata, plans, handoffs (INTERNAL ONLY)
├── docs/                              # Consolidated project documentation
│   ├── architecture/                  # System design, workflow diagrams, roadmaps
│   │   ├── TECHNICAL_ANALYSIS_AND_ROADMAP.md
│   │   ├── WORKFLOW.md
│   │   ├── activity_diagrams.md
│   │   ├── database_connection_workflow.md
│   │   └── fyp_phase1_plan.md
│   ├── database/                      # SQL schemas, ERDs, and visual diagrams
│   │   ├── Full_Project_Schemas.sql   # Canonical 35-table enterprise schema
│   │   ├── Database_ERD.md
│   │   ├── DataSpeakAI_Complete_EERD.md
│   │   └── dataspeakai_complete_eerd_visual_1778525676843.png
│   ├── setup/                         # Setup guides and environment instructions
│   │   ├── SETUP_GUIDE.md
│   │   ├── SETUP_GUIDE_v4.md
│   │   ├── setup_guide_v5.md
│   │   ├── Guidelines.md
│   │   └── instructions.txt
│   ├── reports/                       # Technical reports and module walkthroughs
│   │   ├── ATTRIBUTIONS.md
│   │   ├── Ingestion_Summary.md
│   │   ├── implementation_planmodule17
│   │   ├── mockup_analysis.md
│   │   ├── project_implementation_report_30.md
│   │   └── walkthroughmodule17
│   ├── sessions/                      # Developer and AI agent work session logs
│   └── templates/                     # Task delegation templates (AI_TASK_TEMPLATE.md)
├── src/                               # React Frontend source code
├── backend/                           # FastAPI Backend source code
├── package.json                       # Frontend dependencies manifest
├── vite.config.ts                     # Vite build configuration
├── postcss.config.mjs                 # PostCSS configuration
├── index.html                         # SPA HTML entry page
├── proxy.js                           # Node.js dev proxy server (Port 9000)
├── render.yaml / vercel.json          # Deployment manifests
├── .env.example                       # Environment variable template
├── README.md                          # Project overview
├── AGENTS.md                          # AI Agent Context Standard (this file)
└── CHANGELOG.md                       # Project change log and session tracker
```

### 3.2 Frontend Layout (`src/`)

```
src/
├── main.tsx                           # DOM entry point (renders <App /> into #root)
├── styles/                            # Design tokens, variables, & utility classes
│   ├── index.css                      # Master style entry point
│   ├── tailwind.css                   # Tailwind CSS v4 directives
│   ├── theme.css                      # Custom CSS variables and theme tokens
│   └── fonts.css                      # Font definitions
└── app/
    ├── App.tsx                        # Root component (<RouterProvider>, Sonner <Toaster>)
    ├── routes.ts                      # React Router v7 configuration (17 routes)
    ├── config/
    │   └── api.ts                     # Central API URL exporter (VITE_API_BASE_URL)
    ├── components/
    │   ├── DashboardLayout.tsx        # Protected layout shell (Sidebar, Header, User Profile)
    │   ├── ui/                        # Atomic UI primitives (button, card, dialog, table, etc.)
    │   └── figma/                     # Image fallback components
    └── pages/
        ├── LandingPage.tsx            # Public landing & GitHub OAuth callback
        ├── LoginPage.tsx              # Email/password & OAuth sign-in
        ├── SignupPage.tsx             # Tenant registration & token invite signup
        ├── ForgotPasswordPage.tsx     # 3-step OTP password recovery
        ├── EmailVerificationPage.tsx  # 6-digit email OTP verification
        ├── admin/
        │   └── AdminPanel.tsx         # Platform management [MOCKED]
        └── dashboard/
            ├── DashboardOverview.tsx  # Executive stats & charts [MOCKED]
            ├── DatabasesPage.tsx      # DB connection management [LIVE API]
            ├── KnowledgeBasePage.tsx  # RAG document search [LIVE API]
            ├── UploadDocumentsPage.tsx# Document upload & FAISS indexing [LIVE API]
            ├── AnalyticsPage.tsx      # Visual analytics [MOCKED]
            ├── AIInsightsPage.tsx     # AI-generated insights [MOCKED]
            ├── ApiKeysPage.tsx        # API key management [LIVE API]
            ├── ChatbotWidgetPage.tsx  # Chatbot customization [LIVE API]
            ├── UsagePage.tsx          # Resource meter & usage stats [MOCKED]
            ├── LogsPage.tsx           # Execution audit logs [MOCKED]
            └── SettingsPage.tsx       # Tenant profile settings [LIVE/PARTIAL]
```

### 3.3 Backend Layout (`backend/`)

```
backend/
├── main.py                            # FastAPI app, CORS configuration, router bindings
├── database.py                        # SQLAlchemy engine, SessionLocal, get_db dependency
├── models.py                          # 10 SQLAlchemy ORM models
├── schemas.py                         # Pydantic validation schemas
├── auth.py                            # Passlib bcrypt hashing & PyJWT token utilities
├── dependencies.py                    # get_current_user & get_current_admin_user dependencies
├── requirements.txt                   # Backend Python dependencies
├── routers/
│   ├── users.py                       # /api/auth (Register, Login, OAuth, OTP, Password Reset)
│   ├── tenants.py                     # /api/tenant (Profile, Members, Invites)
│   ├── databases.py                   # /api/databases (CRUD, Introspection, 100-row preview)
│   ├── api_keys.py                    # /api/keys (Key Creation, Listing, Revocation, Deletion, Widget Keys)
│   ├── chatbot_config.py              # /api/chatbot-config (Get & Update Widget Settings)
│   ├── documents.py                   # /api/documents (Upload, FAISS Vector Search, Delete)
│   ├── chat.py                        # /api/chat (Conversations, Messages, Widget Chat)
│   └── widget.py                      # /api/widget (Session, Config, Chat SSE, Embed Page)
└── services/
    ├── llm_generation_service.py      # LLMGateway, multi-key rotation & cooldown fallback
    ├── llm_metrics.py                 # LLMMetrics datastore, percentiles & token telemetry
    └── sql_engine.py                  # execute_safe_sql with dialect & watchdog timeouts
```

---

## 4. Code Conventions & Engineering Rules

### 4.1 Naming Patterns
* **React Components & Files:** `PascalCase` (e.g., `DatabasesPage.tsx`, `DashboardLayout.tsx`).
* **React Hooks & Utility Functions:** `camelCase` (e.g., `useAuth()`, `fetchDatabaseSchema()`).
* **Python Modules, Functions, & Variables:** `snake_case` (e.g., `chatbot_config.py`, `get_connection_url()`, `user_id`).
* **SQLAlchemy Models & Pydantic Schemas:** `PascalCase` class names (`DatabaseConnection`, `UserCreate`), `snake_case` attributes and column definitions.
* **Database Tables & Columns:** `snake_case` pluralized for tables (`users`, `database_connections`), `snake_case` singular for columns (`tenant_id`, `created_at`).

### 4.2 SQL Safety & Security Rules (MANDATORY)

> ⚠️ **CRITICAL SECURITY MANDATE:** NEVER use Python f-strings, `%` formatting, or string concatenation to dynamically construct SQL queries with user inputs. Doing so introduces severe SQL Injection vulnerabilities.

* **Always Parameterize SQL Queries:** Use SQLAlchemy's `text()` constructs with explicit parameter bindings:

  ```python
  # CORRECT: Parameterized SQL Execution
  from sqlalchemy import text

  query = text("SELECT * FROM users WHERE tenant_id = :tenant_id AND status = :status")
  result = db.execute(query, {"tenant_id": tenant_id, "status": "active"})
  ```

  ```python
  # FORBIDDEN: Raw String Interpolation (SQL Injection Risk)
  result = db.execute(text(f"SELECT * FROM users WHERE tenant_id = '{tenant_id}'")) # NEVER DO THIS!
  ```

* **Dynamic Identifiers (Table & Column Names):** When table or column names must be dynamically selected (e.g., in data preview endpoints), you MUST sanitize and validate the identifier against database schema metadata or a validated whitelist prior to query execution.

* **Database Password Encryption:** External database passwords saved in `DatabaseConnection` must be encrypted at rest using symmetric encryption (e.g., cryptography `Fernet`) rather than stored in plain text.

* **No Hardcoded Secrets:** Fallback secret values (such as `GITHUB_CLIENT_SECRET`) must NEVER be hardcoded in Python source files. Always require them through environment variables.

### 4.3 Error Handling & Validation Guidelines
* **Input Validation:** All HTTP request bodies, query params, and route parameters must be validated using Pydantic schemas in `backend/schemas.py`.
* **FastAPI Exception Handling:** Raise explicit `HTTPException(status_code=..., detail=...)` exceptions in backend routers rather than returning raw dictionaries or unhandled status codes.
* **Frontend Error Feedback:** Use Sonner toast notifications (`toast.error("Failed to save configuration")`, `toast.success("Connection saved")`) for asynchronous user actions. Avoid silent failures or unhandled promise rejections.
* **Session Lifecycle:** Always wrap database operations in `try/except/finally` or use the `get_db` FastAPI dependency to ensure `db.close()` is invoked cleanly.

### 4.4 Environment Variables & Configuration Mappings

#### Frontend Environment Variables (`src/app/config/api.ts`)
* `VITE_API_BASE_URL` — Base URL for FastAPI backend API calls (Default: `http://localhost:8000`).
* *Note:* Avoid legacy `VITE_API_URL` variable names; standardize on `VITE_API_BASE_URL`.

#### Backend Environment Variables (`backend/.env` or system env)
* `SECRET_KEY` — Cryptographic secret key for signing JWT access tokens.
* `ALGORITHM` — JWT algorithm (e.g., `HS256`).
* `ACCESS_TOKEN_EXPIRE_MINUTES` — Expiration duration for access tokens (e.g., `1440`).
* `DATABASE_URL` — Database connection string (`sqlite:///./app.db` default, or `postgresql://user:pass@host:5432/dbname`).
* `RESEND_API_KEY` — API key for Resend email notification service.
* `GEMINI_API_KEY` — Google Gemini API key for visual chart and PDF analysis.
* `GITHUB_CLIENT_ID` — GitHub OAuth Application Client ID.
* `GITHUB_CLIENT_SECRET` — GitHub OAuth Application Client Secret.
* `DEFAULT_ADMIN_EMAIL` — (Optional override) Default dev superadmin email (default: `admin@dataspeak.ai`).
* `DEFAULT_ADMIN_PASSWORD` — (Optional override) Default dev superadmin password (default: `AdminPassword123!`).

### 4.5 Development Superadmin Seeding & Production Hardening Checklist

> 🔒 **PRODUCTION DEPLOYMENT NOTICE:** For multi-developer local workflow ease, a pre-verified development superadmin account (`admin@dataspeak.ai` / `AdminPassword123!`) auto-seeds on backend startup via `backend/scripts/seed_admin.py` and has a quick-fill button on `LoginPage.tsx`.
>
> **When preparing for production deployment, you MUST execute the following steps:**
> 1. **Disable Auto-Seeding on Startup:** In [`backend/main.py`](file:///d:/dataspeak/backend/main.py), remove or comment out the `seed_superadmin()` block (or gate it behind `ENVIRONMENT != "production"`).
> 2. **Remove Quick-Fill Button on UI:** In [`src/app/pages/LoginPage.tsx`](file:///d:/dataspeak/src/app/pages/LoginPage.tsx), remove the `<div className="mb-4 p-3 bg-blue-50/80...">` Default Admin auto-fill card.
> 3. **Delete/Update Default DB Credentials:** In the production database, either delete the user `admin@dataspeak.ai` or change its password to a cryptographically secure value via your secrets manager.

### 4.6 Standalone Chatbot Widget Security & Authentication Standard

* **Publishable Key Standard (`pk_live_...`):** Standalone widget scripts embedded on host websites must use a publishable key (`pk_live_...`), never an internal secret API key.
* **Origin-Checked HMAC Handshake:** Browser visitors initiate conversation via `POST /api/widget/session`. The server strictly validates `Origin` (falling back to `Referer`) against the key's `allowed_origins` list before signing an HMAC session token (valid 60 minutes).
* **Strict Tenant Extraction:** In all widget chat routes (`POST /api/widget/chat`, `POST /api/chat/widget`), `tenant_id` is extracted strictly from cryptographically verified HMAC session claims, never from client request bodies or LLM prompts.
* **Rate Limiting & Streaming Caps:** All widget endpoints enforce token bucket rate limits (per key, per IP, per session) returning `429 Too Many Requests` with `Retry-After`. SSE streaming enforces a concurrent stream limit per key to protect ASGI server connection pools.
* **Data-Access Guardrails:** Widget queries default to safe RAG retrieval (`allow_sql = False`). If SQL is explicitly enabled, queries are bounded to `allowed_database_ids`, validated deterministically (SELECT-only, no multi-statement, no catalog access), row capped at 100 preview rows, executed with query timeouts, and columns masked for sensitive PII. Visitors receive summarized natural language answers, never raw database connection credentials or schema dumps.

### 4.7 Entity-Relationship Diagram (ERD) Architecture & Security Standard

* **Catalog-First Architecture (D1):** `GET /api/databases/{id}/erd` serves schema structures directly from the local metadata catalog (`TableMetadata`, `ColumnMetadata`, `TableRelationship`). Live reflection runs only on cache miss or explicit `refresh=true`.
* **Constraint-Level Relationships (D2):** Foreign key constraints are persisted in `table_relationships` with JSON arrays of source and target columns, supporting composite foreign keys and multiple relationships between identical tables.
* **SQLAlchemy 2.0 Bulk Reflection (D3):** Uses `get_multi_columns`, `get_multi_pk_constraint`, and `get_multi_foreign_keys` for minimal round-trip database overhead.
* **Relational DB Scope (D4):** ERD is restricted to relational dialects (`postgresql`, `mysql`, `mariadb`, `sqlite`). Document databases (MongoDB, Firebase) return HTTP 400.
* **Host Validation & SSRF Prevention (D5):** Live database connections block loopback (`127.0.0.0/8`), link-local (`169.254.0.0/16`), and private RFC 1918 subnets unless `ALLOW_PRIVATE_DB_HOSTS=true`. SQLite database paths must physically exist and reject directory traversal (`..`).
* **Tenant Isolation & Cooldown (D6, D7):** Database access is tenant-scoped (cross-tenant returns 404). Schema refresh enforces a per-tenant, per-database cooldown window (default 30 seconds via `ERD_REFRESH_COOLDOWN_SECONDS`) returning HTTP 429 with `Retry-After`.
* **Frontend Visualization (D8):** Implemented via `@xyflow/react` v12, `@dagrejs/dagre`, and `vitest`. Large schemas (>60 tables) automatically enable viewport virtualization (`onlyRenderVisibleElements`) and compact node rendering. Dragged positions are persisted in `localStorage` per `(database_id, schema)`.

### 4.8 LLM Gateway, Diagnostics & Query Timeout Standard

* **Unified Async LLM Gateway (`LLMGateway`):** All LLM generation routes through `LLMGateway` (`backend/services/llm_generation_service.py`), utilizing non-blocking `httpx.AsyncClient` with connection pooling, multi-key harvesting across `GEMINI_API_KEY*` and `GROQ_API_KEY*` (1..15+), round-robin quota rotation, and automatic 429/403 failover with a 60-second quarantine cooldown registry.
* **All-Keys-Cooling Fallback:** When all candidate API keys for a provider are in cooldown (due to heavy concurrent load), the gateway does NOT fail immediately. It attempts cooling keys in priority order to maintain service availability while respecting external quotas.
* **Diagnostics Endpoint Security:** System telemetry (`GET /api/system/llm-metrics`) is strictly restricted to authenticated administrators via `get_current_admin_user`. Unauthenticated calls receive HTTP 401 Unauthorized; non-admin users receive HTTP 403 Forbidden.
* **Dual-Layer Database Query Timeout Defense:** Query execution in `execute_safe_sql` (`backend/services/sql_engine.py`) enforces strict dual-layer protection against runaway queries:
  1. *Engine-level statement timeouts:* PostgreSQL (`options="-c statement_timeout=10000"`), MySQL (`SET SESSION max_execution_time=10000`), SQLite (`timeout=10.0`, `PRAGMA busy_timeout = 10000;`).
  2. *Fail-safe watchdog ceiling:* 12.0s caller watchdog using `concurrent.futures.ThreadPoolExecutor` with manual lifecycle management (`shutdown(wait=False, cancel_futures=True)`) ensuring the caller is released immediately upon timeout without thread deadlock.

### 4.9 Conversation Streaming, Memory Management & Background Titles Standard

* **True Token-Level Streaming:** Dashboard chat (`/api/chat`) and standalone widget (`/api/widget/chat`) stream real tokens directly from `LLMGateway.generate_stream()` via `stream_chat_response` (`backend/services/chat_stream.py`). Artificial word-splitting and sleeps are eliminated. SQL execution remains deterministic and atomic; only post-execution explanations and RAG syntheses stream.
* **Stream Disconnect & Slot Reclaim:** Generators poll `request.is_disconnected()` between tokens. Any client disconnect immediately halts upstream generation and releases widget concurrency slots in `finally:`. Tenant metered quotas are deducted only upon full completion.
* **Conversation Memory Management (`ConversationMemoryManager`):** The last `MAX_RECENT_TURNS = 10` messages are preserved verbatim in context. Conversations crossing 15 turns trigger asynchronous background summarization of older turns. Monotonically increasing versioning (`summary_turn_count`) and per-conversation locks prevent concurrent overwrite or regression. Failures fall back cleanly to sliding window without logging message text.
* **Dynamic Background Title Generation (`services/conversation_title.py`):** Initial conversation creation assigns a fast 6-word heuristic title. Following the first assistant answer, an async task generates a concise 3-6 word sanitized title via LLM Gateway. If the user has already manually renamed the conversation, the custom title is preserved.

### 4.10 Agentic Self-Correcting SQL, Grounding Verification & Retrieval Precision Standard

* **Self-Correcting SQL Agent (`SQLAgent`):** Iterative schema-guided loop (up to `MAX_ATTEMPTS = 3`) that catches dialect errors via isolated `begin_nested()` SAVEPOINT rollback dry-runs before attempting execution. Statement execution timeouts apply to all supported relational engines (SQLite `timeout=6.0`, PostgreSQL `-c statement_timeout=6000`, MySQL/MariaDB `SET SESSION MAX_EXECUTION_TIME=6000`). If repairs fail, executes clean graceful fallback to baseline read without mutating database state.
* **Precision Grounding & Source Attribution (`CitationService`):** Every synthesized answer in RAG and Hybrid routes is claim-split and verified against retrieved parent/child chunks using semantic cosine similarity. Source citations are decorated with explicit `grounding_score` and `is_grounded` boolean flags. Low-confidence syntheses (`confidence < 0.65`) append an advisory disclaimer.
* **Streaming Metadata Transmission:** `stream_chat_response` communicates completion metadata (`grounding`, `sql_agent`, `sources`, `sql_data`) directly within the terminal SSE `done` frame to eliminate race conditions between client-side stream termination and database persistence.
* **Vector Store Isolation & Dimension Integrity:** FAISS vector index directories are partitioned strictly by `tenant_{id}_{model_slug}` where `model_slug` is sanitized with strict regex character filtering (`[^a-zA-Z0-9_\-\.]`) to prevent directory traversal across platforms. Query embeddings strictly validate dimension equality against `index.d`, returning explicit HTTP 400 Bad Request on model mismatch.

---


## 5. Instructions for AI Agents

### 5.1 Pre-Task Context Reading Protocol
Before taking any action, modifying source files, or implementing features, every AI agent MUST complete the following context verification steps:

1. **Read `AGENTS.md`:** Review project purpose, architecture maps, and engineering rules (this document).
2. **Read `CHANGELOG.md`:** Review recent architectural updates, session history, and completed tasks.
3. **Inspect Relevant Documentation in `docs/`:**
   * Architecture tasks: Consult `docs/architecture/`.
   * Database changes: Consult `docs/database/Full_Project_Schemas.sql` and `docs/database/Database_ERD.md`.
   * Setup/config tasks: Consult `docs/setup/`.
4. **Check Active Sessions in `docs/sessions/`:** Verify if another developer or agent left active task notes or context handoffs.
5. **Re-Read Target Files:** Always call `view_file` on target source files before modifying them to confirm current line numbers and imports.

### 5.2 Strict Rules of Engagement & Integrity
* **DO NOT CHEAT:** Never hardcode expected test outputs, fabricate logs, or create facade implementations. All code must contain genuine, functional logic.
* **Minimal Change Principle:** Modify only what is necessary to accomplish the assigned task. Preserve unrelated code style, comments, and docstrings.
* **File Workspace Discipline:** Agent metadata, scratch scripts, plans, and handoff reports belong ONLY in `.agents/`. **NEVER** write source code, tests, or documentation inside `.agents/`.

### 5.3 Session Logging & Handoff Standard
* Maintain your liveness status by updating `progress.md` in your `.agents/` folder after completing major steps.
* Update `CHANGELOG.md` at root when completing milestone features, bug fixes, or structural changes.
* Use `docs/templates/AI_TASK_TEMPLATE.md` to format task prompts when delegating subtasks to other agents or developers.

### 5.4 Step-by-Step Verification Workflow
After making any code changes, perform the following verification steps:
1. **Frontend Build Check:** Run Vite build check (`cmd.exe /c "npm run build"`) to ensure React components compile without TypeScript or syntax errors.
2. **Backend Startup Check:** Confirm FastAPI backend initializes cleanly (`uvicorn main:app --reload` or test execution).
3. **API & Model Consistency:** Ensure Pydantic schemas in `backend/schemas.py` match SQLAlchemy models in `backend/models.py` and React page state.
4. **Handoff Generation:** Create a self-contained 5-component handoff report (`Observation`, `Logic Chain`, `Caveats`, `Conclusion`, `Verification Method`) in `handoff.md`.

### 5.5 Task Lifecycle, `todo.md` & `CHANGELOG.md` Maintenance Protocol (MANDATORY)

Every AI coding agent is strictly required to keep [`todo.md`](file:///d:/dataspeak/todo.md) and [`CHANGELOG.md`](file:///d:/dataspeak/CHANGELOG.md) synchronized with ongoing and completed work:

1. **Task Selection from `todo.md`**:
   * Prior to writing code, check [`todo.md`](file:///d:/dataspeak/todo.md) for pending tasks (`- [ ]`) in priority sequence (P0 → P1 → P2 → P3) or target the user-specified task.
   * Verify target files, acceptance criteria, and constraints in `todo.md` before proceeding.

2. **Completing a Task & Archiving in `todo.md`**:
   * Once a task is implemented and verified (via `cmd.exe /c "npm run build"` or backend verification):
     * Mark the task checkbox as completed: `- [x]`.
     * Append completion metadata: `[Completed: YYYY-MM-DD | <Agent/Role> | <Summary of outcome>]`.
     * **Move the completed task line out of the active phase** and into the `## 📦 Archived / Completed Tasks` section at the bottom of [`todo.md`](file:///d:/dataspeak/todo.md).
     * The active phase lists in `todo.md` must only contain remaining, uncompleted tasks (`- [ ]`).

3. **Logging in `CHANGELOG.md`**:
   * Immediately upon completing a task, record a descriptive bullet point under `## [Unreleased]` in [`CHANGELOG.md`](file:///d:/dataspeak/CHANGELOG.md).
   * Group entries under standard Keep a Changelog categories: `### Added`, `### Changed`, `### Fixed`, or `### Security`.
   * Reference affected components, files, and endpoints.

---
*End of AGENTS.md — DataSpeakAI AI Agent Context Standard*

<!-- graft:start -->
## Graft — repo context graph

This repo is indexed in `graft/`: small linked markdown nodes that explain each
system and carry exact file:line spans, kept in sync with the code through git.

For ANY task here — understanding how something works, finding where code lives,
or scoping a change — get context from the graph before grepping or opening
source files. Re-ask freely (it's cheap) and reuse literal identifiers you
already have (symbol, error string, file name) as the query. New to this repo?
Run `graft map` first — a token-budgeted orientation (dir clusters, hubs,
hotspots), no LLM, no key.

- Run `graft ask "<your question>" --source` → ranked nodes with the relevant
  code spans inlined (each hit's ≤8-line crux by default; `--full` for whole
  definitions when the crux isn't enough). Match the tool to the task shape:
  for understanding or editing, the top node IS the answer — cite its
  `covers:` file:line spans and edit straight from `--source`. For
  exhaustive tasks ("every occurrence / every caller of this pattern"), ranked
  results are top-N, not complete — run `graft grep "<literal>"` instead
  (exhaustive over indexed files, grouped by enclosing symbol), falling back
  to raw `grep -rn` only for unindexed files.
- `graft skeleton <file>` → every definition's signature + span, ~10× cheaper
  than reading the file; use it to skim an API surface.
- `graft callers <symbol>` gives precomputed, exact edges — who calls this.
  Add `--direction out` for what it calls, or `--depth N` to walk
  transitively for the full blast radius. For structural questions, skip
  ranking and use this directly.
- Or browse: `graft/INDEX.md` lists every node; follow the links.
- Monorepos and folders of multiple repos rank fairly across sub-projects —
  hits carry `[scope/]` labels naming which one they're from. Narrow with
  `graft ask "<task>" --in <scope>/` once you know where you're working.

If a returned span is truncated ("+N more lines"), open the file at that exact
range before finalizing. Only open source files when a node genuinely lacks a
needed detail, and then at the exact file:line the node points to — never
re-read whole files.

After big code changes, refresh the graph with `graft build` (deterministic,
no API key, $0).
<!-- graft:end -->
