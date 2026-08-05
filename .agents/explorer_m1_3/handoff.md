# Handoff Report — Codebase Architecture & Context Discovery (Milestone 1)

**Agent ID:** explorer_m1_3  
**Working Directory:** `d:\dataspeak\.agents\explorer_m1_3`  
**Target Project:** DataSpeakAI (`d:\dataspeak`)  
**Date:** 2026-08-05  

---

## 1. Observation

Direct investigation of the DataSpeakAI repository at `d:\dataspeak` revealed the following exact technical layout, codebase contents, tech stack configurations, database models, and architectural characteristics:

### 1.1 Root Directory Inventory
A call to `list_dir` on `d:\dataspeak` identified **6 subdirectories** and **30 root-level files**:
* **Directories:** `.agents`, `.git`, `.github`, `backend`, `guidelines`, `src`.
* **Runtime & Config Files:** `package.json`, `package-lock.json`, `postcss.config.mjs`, `vite.config.ts`, `index.html`, `.env.example`, `.gitignore`, `README.md`, `ATTRIBUTIONS.md`, `proxy.js`, `render.yaml`, `vercel.json`.
* **Root Documentation & SQL Files (Pending relocation under R1 to `docs/`):**
  * `DataSpeakAI_Complete_EERD.md`, `Database_ERD.md`, `Full_Project_Schemas.sql`
  * `Ingestion_Summary.md`, `SETUP_GUIDE.md`, `SETUP_GUIDE_v4.md`, `setup_guide_v5.md`
  * `TECHNICAL_ANALYSIS_AND_ROADMAP.md`, `WORKFLOW.md`, `activity_diagrams.md`
  * `database_connection_workflow.md`, `dataspeakai_complete_eerd_visual_1778525676843.png`
  * `fyp_phase1_plan.md`, `implementation_planmodule17`, `instructions.txt`
  * `mockup_analysis.md`, `project_implementation_report_30.md`, `walkthroughmodule17`
  * `guidelines/Guidelines.md`

### 1.2 Tech Stack Breakdown

#### Frontend (`package.json`, `src/`)
* **Core Framework:** React `18.3.1`, Vite `6.3.5`, React Router v7 (`react-router` `^7.13.0`)
* **Styling & Design System:** Tailwind CSS v4 (`@tailwindcss/vite` `4.1.12`, `tailwindcss` `4.1.12`), Emotion (`@emotion/react` `11.14.0`, `@emotion/styled` `11.14.1`), MUI (`@mui/material` `7.3.5`, `@mui/icons-material` `7.3.5`), Radix UI Primitives (`@radix-ui/react-*`), Framer Motion v12 (`motion` `12.23.24`), `clsx` `2.1.1`, `tailwind-merge` `3.2.0`, `class-variance-authority` `0.7.1`, `tw-animate-css` `1.3.8`
* **UI Components & Visualization:** Recharts `2.15.2`, Sonner `2.0.3` (toasts), Vaul `1.1.2` (drawers), CMDK `1.1.1` (command palette), Lucide React `0.487.0`, Embla Carousel `8.6.0`, React DnD `16.0.1`, React Hook Form `7.55.0`, React Resizable Panels `2.1.7`
* **Package Name Note:** `package.json:2` defines `"name": "@figma/my-make-file"` (starter template artifact).

#### Backend API (`backend/requirements.txt`, `backend/main.py`)
* **API Framework & Server:** Python 3.10+, FastAPI (`fastapi`), Uvicorn ASGI server (`uvicorn`), Pydantic v2 (`pydantic[email]`)
* **Database & ORM:** SQLAlchemy (`sqlalchemy` `^2.0.35`), SQLite (`sqlite:///./app.db` default), `psycopg2-binary` (PostgreSQL), `pymysql` (MySQL)
* **Authentication & Security:** `passlib[bcrypt]`, `PyJWT`, `OAuth2PasswordBearer` (FastAPI security scheme)
* **Communications:** `resend` (Resend API), `smtplib` (Gmail SMTP fallback in `backend/routers/users.py:223`)
* **Proxy Server:** Node.js HTTP proxy (`proxy.js`, routing port 9000 -> Vite frontend 5173 / FastAPI backend 8000)

#### AI & RAG Engine (`backend/routers/documents.py`, `backend/test_rag.py`)
* **Vector Store & Embeddings:** FAISS (`faiss-cpu`), HuggingFace SentenceTransformers `all-MiniLM-L6-v2` via `langchain-huggingface`
* **Document Chunking & Text Splitters:** LangChain `RecursiveCharacterTextSplitter` (supporting fixed, paragraph, line, sentence strategies)
* **PDF & Vision Processing:** `pdfplumber` (table extraction to Markdown tables), `PyMuPDF` (`fitz` image extraction), Google Gemini API (`gemini-2.5-flash` REST endpoint for OCR and visual chart/diagram analysis)

### 1.3 Codebase Architecture & File Map

#### Frontend File Structure (`src/`)
```
src/
├── main.tsx                           # Entry point: renders <App /> into DOM root
├── styles/
│   ├── index.css                      # Master stylesheet importing Tailwind & variables
│   ├── tailwind.css                   # Tailwind v4 configuration directives
│   ├── theme.css                      # CSS custom properties and color variables
│   └── fonts.css                      # Custom font imports
└── app/
    ├── App.tsx                        # App wrapper: <RouterProvider> & <Toaster>
    ├── routes.ts                      # React Router v7 browser router configuration (17 routes)
    ├── config/
    │   └── api.ts                     # Exports API_BASE_URL (checks VITE_API_BASE_URL)
    ├── components/
    │   ├── DashboardLayout.tsx        # Shell for protected routes (Sidebar, Header, Profile)
    │   ├── figma/
    │   │   └── ImageWithFallback.tsx  # Fallback image rendering wrapper
    │   └── ui/                        # Atomic Shadcn UI primitives (button, card, dialog, table...)
    └── pages/
        ├── LandingPage.tsx            # Public marketing landing page & GitHub OAuth callback handler
        ├── LoginPage.tsx              # User login page (Email/Password & GitHub OAuth)
        ├── SignupPage.tsx             # Tenant registration & invite token signup
        ├── ForgotPasswordPage.tsx     # 3-step OTP password reset page
        ├── EmailVerificationPage.tsx  # 6-digit email OTP verification page
        ├── admin/
        │   └── AdminPanel.tsx         # Platform admin panel [MOCKED UI]
        └── dashboard/
            ├── DashboardOverview.tsx  # Executive metrics & charts [MOCKED UI]
            ├── DatabasesPage.tsx      # DB connection management & table previewer [LIVE API]
            ├── KnowledgeBasePage.tsx  # RAG document listing & vector search [LIVE API]
            ├── UploadDocumentsPage.tsx# File upload & FAISS indexing [LIVE API]
            ├── AnalyticsPage.tsx      # Analytics & visualizations [MOCKED UI]
            ├── AIInsightsPage.tsx     # AI insights & recommendations [MOCKED UI]
            ├── ApiKeysPage.tsx        # API key management [LIVE API]
            ├── ChatbotWidgetPage.tsx  # Custom chatbot config & embed preview [LIVE API]
            ├── UsagePage.tsx          # Resource & query usage tracking [MOCKED UI]
            ├── LogsPage.tsx           # Query execution logs [MOCKED UI]
            └── SettingsPage.tsx       # Tenant profile settings [LIVE/PARTIAL]
```

#### Backend File Structure (`backend/`)
```
backend/
├── main.py                            # FastAPI app, CORS middleware, router registration
├── database.py                        # SQLAlchemy engine setup (SQLite default / PostgreSQL), SessionLocal
├── models.py                          # 10 SQLAlchemy ORM models (Tenant, User, ApiKey, Document...)
├── schemas.py                         # Pydantic request/response validation schemas
├── auth.py                            # bcrypt password hashing & PyJWT token utilities
├── dependencies.py                    # get_current_user JWT Bearer authentication dependency
├── requirements.txt                   # Python dependencies manifest
├── test_rag.py / test_backend_rag.py  # Diagnostic & test scripts for RAG pipeline
├── scratch/                           # 13 diagnostic/temporary scripts
└── routers/
    ├── users.py                       # /api/auth (register, login, github-login, OTP, verification)
    ├── tenants.py                     # /api/tenant (current tenant, member listing, invites)
    ├── databases.py                   # /api/databases (DB CRUD, schema introspection, 100-row preview)
    ├── api_keys.py                    # /api/keys (API key creation, list, revocation, deletion)
    ├── chatbot_config.py              # /api/chatbot-config (Get & update widget preferences)
    └── documents.py                   # /api/documents (Upload, PDF parsing, FAISS vector search)
```

### 1.4 Database Schemas & ORM Model Discrepancy
* **Enterprise SQL Schema (`Full_Project_Schemas.sql`):** Contains **35 tables** spanning 9 production modules (`tenants`, `tenant_settings`, `users`, `roles`, `permissions`, `memberships`, `database_connections`, `secrets`, `database_schemas`, `table_metadata`, `column_metadata`, `chatbot_configs`, `conversations`, `messages`, `intents`, `query_templates`, `executed_queries`, `query_safety_logs`, `documents`, `document_chunks`, `collections`, `vector_records`, `generated_insights`, `recommendations`, `dashboards`, `widgets`, `subscriptions`, `invoices`, `payments`, `metered_usage`, `api_keys`, `rate_limits`, `security_policies`, `audit_logs`, `system_metrics`).
* **Python ORM Implementation (`backend/models.py`):** Defines only **10 MVP models**:
  1. `Tenant` (`tenants`)
  2. `User` (`users`)
  3. `UserDatabaseAccess` (`user_database_access`)
  4. `TenantInvite` (`tenant_invites`)
  5. `DatabaseConnection` (`database_connections`)
  6. `ApiKey` (`api_keys`)
  7. `ChatbotConfig` (`chatbot_configs`)
  8. `Document` (`documents`)
  9. `DocumentChunk` (`document_chunks`)
  10. `PasswordResetOTP` (`password_reset_otps`)
* **Finding:** 25 out of 35 enterprise database tables defined in the project schema are currently unbuilt in the backend Python ORM.

### 1.5 Detailed Code Observations & Bugs

1. **Python Function Overwriting Defect in SQLite Inspection (`backend/routers/databases.py`):**
   * Lines 13-20 define `get_connection_url(db_conn)` with SQLite support.
   * Lines 92-97 redefine `get_connection_url(db_conn)` without SQLite support, overwriting the initial function definition.
   * *Verbatim code (lines 92-97):*
     ```python
     def get_connection_url(db_conn: models.DatabaseConnection):
         if db_conn.db_type == "postgresql":
             return f"postgresql://{db_conn.username}:{db_conn.password}@{db_conn.host}/{db_conn.database}"
         elif db_conn.db_type == "mysql" or db_conn.db_type == "mariadb":
             return f"mysql+pymysql://{db_conn.username}:{db_conn.password}@{db_conn.host}/{db_conn.database}"
         return None
     ```
   * *Impact:* Any SQLite connection fails `get_connection_url`, returning `None` and falling back to mock data.

2. **API Contract Bug in Chatbot Config Update (`backend/routers/chatbot_config.py`):**
   * UI (`ChatbotWidgetPage.tsx:59-73`) sends payload: `{ theme_color, greeting_message, position, welcome_delay, max_history, widget_title, sound_enabled }`.
   * Backend endpoint (`chatbot_config.py:43-47`) only updates:
     ```python
     config.theme_color = config_update.theme_color
     config.greeting_message = config_update.greeting_message
     config.position = config_update.position
     config.welcome_delay = config_update.welcome_delay
     config.max_history = config_update.max_history
     ```
   * *Impact:* `widget_title` and `sound_enabled` are silently dropped during backend saves.

3. **SQL Injection Vulnerability (`backend/routers/databases.py:152`):**
   * Direct string interpolation used in query execution:
     ```python
     result = conn.execute(text(f"SELECT * FROM {table_name} LIMIT 100"))
     ```
   * *Impact:* Malicious `table_name` parameters allow arbitrary SQL injection.

4. **Plaintext Password Storage (`backend/models.py:64`):**
   * `DatabaseConnection` stores external database passwords in plain text column `password = Column(String, nullable=False)`.

5. **Hardcoded OAuth Secrets in Source Code (`backend/routers/users.py:130`):**
   * `client_secret = os.getenv("GITHUB_CLIENT_SECRET", "067e59b3c050792898954f727be0dbdbfc5c590a")`.

6. **Environment Variable Configuration Mismatch:**
   * `.env.example` declares `VITE_API_URL=http://localhost:8000`.
   * Frontend code (`src/app/config/api.ts:1`) reads `import.meta.env.VITE_API_BASE_URL`.

---

## 2. Logic Chain

1. **Premise 1 (Codebase Inspection):** Inspecting `package.json`, `requirements.txt`, `src/app/routes.ts`, and `backend/main.py` provides exact technological dependencies, file locations, routing maps, and endpoint specifications for DataSpeakAI.
2. **Premise 2 (Database Schema Analysis):** Comparing `Full_Project_Schemas.sql` (35 tables) with `backend/models.py` (10 ORM models) demonstrates that the core database schema is only partially implemented in code.
3. **Premise 3 (Backend Code & Router Review):** Line-by-line inspection of `backend/routers/databases.py`, `chatbot_config.py`, `users.py`, and `documents.py` revealed specific implementation bugs (function overwrite, dropped update fields, unhandled SQL parameterization, hardcoded secrets).
4. **Premise 4 (Requirements Synthesis for AGENTS.md):** Consolidating these observations yields all necessary technical data required to construct a comprehensive `AGENTS.md` file:
   * Executive Summary & Purpose
   * Frontend/Backend/AI/Database Tech Stack Breakdown
   * Component & Router Architecture Map
   * Engineering Rules & Security Guidelines
   * Instructions for AI Coding Tools (Antigravity, Cursor, Copilot)

---

## 3. Caveats

* **Unexecuted Live External DB Connections:** Database connection testing to live remote PostgreSQL/MySQL instances was not executed during this read-only investigation.
* **Unexecuted Production Build:** Vite build (`npm run build`) was not invoked during this read-only exploration phase.
* **No File Mutations Executed:** As specified in the read-only exploration constraint, no code or project files outside `.agents/explorer_m1_3` were modified or moved.

---

## 4. Conclusion

DataSpeakAI is a well-structured hybrid SaaS application with functional authentication, team invite, DB connection preview, RAG document vector search, API key, and chatbot configuration modules. However, clear architectural debt, functional gaps, and backend bugs exist:
1. **Frontend-Backend Synchronization:** 6 out of 11 dashboard views render static mock data.
2. **Backend Bugs:** Function overwriting in `databases.py`, dropped payload fields in `chatbot_config.py`, and SQL injection risks in dynamic query execution.
3. **Missing ORM Models:** 25 of 35 tables in `Full_Project_Schemas.sql` require Python ORM model implementation.
4. **Environment Drift:** `.env.example` must be updated to align `VITE_API_BASE_URL` and document all 8 backend environment variables.

All findings, file maps, tech stack versions, and coding rules are fully documented in this report to serve as the blueprint for drafting `AGENTS.md` in Milestone 2.

---

## 5. Verification Method

To independently verify the observations in this handoff report:

1. **Verify Tech Stack & Frontend Routes:**
   * View `package.json` to confirm React `18.3.1`, Vite `6.3.5`, Tailwind CSS `4.1.12`.
   * View `src/app/routes.ts` to inspect the 17 defined React Router v7 routes.

2. **Verify Backend Routers & Overwriting Defect:**
   * View `backend/routers/databases.py` at lines 13-20 and lines 92-97 to confirm `get_connection_url` double definition.
   * View `backend/routers/databases.py` at line 152 to confirm dynamic SQL string interpolation (`conn.execute(text(f"SELECT * FROM {table_name} LIMIT 100"))`).

3. **Verify API Contract Bug:**
   * View `src/app/pages/dashboard/ChatbotWidgetPage.tsx` lines 59-73 and compare with `backend/routers/chatbot_config.py` lines 43-47 to confirm `widget_title` and `sound_enabled` omission.

4. **Verify Database Model Gap:**
   * Count table definitions in `Full_Project_Schemas.sql` (35 tables) and compare with classes in `backend/models.py` (10 SQLAlchemy models).

5. **Verify Environment Variable Mismatch:**
   * Compare `.env.example` line 1 (`VITE_API_URL`) with `src/app/config/api.ts` line 1 (`VITE_API_BASE_URL`).
