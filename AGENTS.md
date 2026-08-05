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
├── dependencies.py                    # get_current_user authentication dependency
├── requirements.txt                   # Backend Python dependencies
└── routers/
    ├── users.py                       # /api/auth (Register, Login, OAuth, OTP, Password Reset)
    ├── tenants.py                     # /api/tenant (Profile, Members, Invites)
    ├── databases.py                   # /api/databases (CRUD, Introspection, 100-row preview)
    ├── api_keys.py                    # /api/keys (Key Creation, Listing, Revocation, Deletion)
    ├── chatbot_config.py              # /api/chatbot-config (Get & Update Widget Settings)
    └── documents.py                   # /api/documents (Upload, FAISS Vector Search, Delete)
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
1. **Frontend Build Check:** Run Vite build check (`npm run build`) to ensure React components compile without TypeScript or syntax errors.
2. **Backend Startup Check:** Confirm FastAPI backend initializes cleanly (`uvicorn main:app --reload` or test execution).
3. **API & Model Consistency:** Ensure Pydantic schemas in `backend/schemas.py` match SQLAlchemy models in `backend/models.py` and React page state.
4. **Handoff Generation:** Create a self-contained 5-component handoff report (`Observation`, `Logic Chain`, `Caveats`, `Conclusion`, `Verification Method`) in `handoff.md`.

---
*End of AGENTS.md — DataSpeakAI AI Agent Context Standard*
