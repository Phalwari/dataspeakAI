# DataSpeakAI: Technical Analysis, Architectural Inventory & Development Roadmap

**Date:** 2026-08-04  
**Project:** DataSpeakAI (AI-Driven Database Query, Visualization, and Analytics Platform)  
**Location:** `d:\dataspeak`  
**Author:** Project Orchestrator

---

## Executive Summary

DataSpeakAI is an AI-driven SaaS platform designed for database querying, schema visualization, knowledge base retrieval-augmented generation (RAG), and analytics. A comprehensive codebase audit across the frontend (`src/`), backend (`backend/`), database DDL (`Full_Project_Schemas.sql`, `Database_ERD.md`), and configuration documentation (`SETUP_GUIDE*.md`, `WORKFLOW.md`) reveals a **well-architected hybrid platform**.

Core foundational features—including multi-tenant authentication, database connection management, interactive table data preview, document vector indexing (FAISS + Gemini OCR), API key lifecycle management, and custom chatbot configuration—are **fully functional and connected to live backend APIs**.

However, technical debt, functional gaps, integration bugs, and security vulnerabilities exist:
1. **Core AI & Query Features Unbuilt**: The primary Natural Language to SQL (NL-to-SQL) translation engine, ERD visualizer generator, dynamic dashboard builder, and export services do not exist in the backend. 6 major UI dashboard views render 100% hardcoded static mock data.
2. **Database Schema Discrepancy**: Python SQLAlchemy ORM (`backend/models.py`) implements only **10 MVP tables**, leaving **25 of 35 enterprise tables** defined in `Full_Project_Schemas.sql` unbuilt.
3. **API Integration Contract Bug**: The Chatbot Config update UI sends `widget_title` and `sound_enabled`, but the backend handler drops both fields during the database update.
4. **Backend Bugs & Security Risks**: A Python function overwriting defect in `backend/routers/databases.py` breaks SQLite inspection; SQL string interpolation creates SQL injection risks; database credentials are stored in plaintext; and hardcoded GitHub OAuth secrets exist in backend source code.
5. **Configuration & Documentation Drift**: Mismatched environment variable names (`VITE_API_URL` vs `VITE_API_BASE_URL`) and 8 undocumented backend environment variables cause deployment friction.

---

## 1. R1: Repository & Architectural Analysis

### 1.1 Tech Stack Overview

| Layer | Technologies & Frameworks | Version / Package Details |
|---|---|---|
| **Frontend UI** | React, Vite, React Router v7 | React `^18.3.1`, Vite `^6.3.5`, `react-router` `^7.13.0` |
| **Styling & Components** | Tailwind CSS v4, Shadcn UI / Radix, Recharts, Lucide Icons, Sonner | `@tailwindcss/vite` `4.1.12`, `@radix-ui/react-*`, `recharts` `^2.15.1` |
| **Backend API** | Python, FastAPI, Uvicorn, Pydantic | FastAPI `^0.115.0`, Uvicorn `^0.32.0`, Pydantic `^2.9.0` |
| **Database & ORM** | PostgreSQL, SQLite, SQLAlchemy, PyMySQL, psycopg2-binary | SQLAlchemy `^2.0.35`, SQLite (default `sqlite:///./app.db`) |
| **AI / RAG Pipeline** | LangChain, HuggingFace Embeddings, FAISS, PyMuPDF, pdfplumber, Google Gemini API | `langchain` `^0.3.0`, `faiss-cpu` `^1.8.0`, `all-MiniLM-L6-v2`, Gemini 2.5 Flash |
| **Auth & Security** | Passlib (bcrypt), PyJWT, OAuth2 Bearer Tokens | `passlib[bcrypt]` `^1.7.4`, `pyjwt` `^2.9.0` |
| **Reverse Proxy & Config** | Node.js reverse proxy (`proxy.js`), Render Cloud Config (`render.yaml`) | Port 9000 -> Frontend 5173 / Backend 8000 |

---

### 1.2 Frontend Architecture & Navigation Map (`src/`)

The React application uses React Router v7 defined in `src/app/routes.ts`. It contains **17 page components** organized into public marketing, authentication, protected dashboard routes (wrapped in `DashboardLayout`), and an admin panel.

```
Public Marketing & Auth
 ├── /                               -> LandingPage.tsx (Marketing & GitHub OAuth handler)
 ├── /login                          -> LoginPage.tsx (Email/Pass & GitHub OAuth)
 ├── /signup                         -> SignupPage.tsx (Tenant reg & Invite token)
 ├── /forgot-password                -> ForgotPasswordPage.tsx (3-step OTP recovery)
 └── /verify-email                   -> EmailVerificationPage.tsx (6-digit OTP verification)

Protected Tenant Dashboard (/dashboard -> DashboardLayout.tsx)
 ├── /dashboard (index)              -> DashboardOverview.tsx [MOCKED]
 ├── /dashboard/databases            -> DatabasesPage.tsx [LIVE API]
 ├── /dashboard/knowledge-base       -> KnowledgeBasePage.tsx [LIVE API]
 ├── /dashboard/upload-documents     -> UploadDocumentsPage.tsx [LIVE API]
 ├── /dashboard/analytics            -> AnalyticsPage.tsx [MOCKED]
 ├── /dashboard/ai-insights          -> AIInsightsPage.tsx [MOCKED]
 ├── /dashboard/api-keys             -> ApiKeysPage.tsx [LIVE API]
 ├── /dashboard/chatbot              -> ChatbotWidgetPage.tsx [LIVE API]
 ├── /dashboard/usage                -> UsagePage.tsx [MOCKED]
 ├── /dashboard/logs                 -> LogsPage.tsx [MOCKED]
 └── /dashboard/settings             -> SettingsPage.tsx [PARTIAL MOCKED]

Platform Administration
 └── /admin                          -> AdminPanel.tsx [MOCKED]
```

---

### 1.3 Backend API Endpoint Inventory (`backend/`)

The Python backend exposes **35 total API endpoints** (1 root endpoint in `main.py` + 34 endpoints across 6 router modules in `backend/routers/`):

| Router Module | HTTP Method | Endpoint Path | Functionality | Auth Level |
|---|---|---|---|---|
| `main.py` | `GET` | `/` | Health check / Root greeting | Public |
| **`users.py`** | `POST` | `/api/auth/register` | Register user & tenant | Public |
| | `POST` | `/api/auth/login` | Email/password login | Public (Verified) |
| | `POST` | `/api/auth/github-login` | GitHub OAuth code exchange | Public |
| | `POST` | `/api/auth/change-password` | Password update | Bearer Auth |
| | `GET` | `/api/auth/me` | Fetch current user profile | Bearer Auth |
| | `POST` | `/api/auth/forgot-password` | Request password reset OTP | Public |
| | `POST` | `/api/auth/verify-otp` | Validate password OTP | Public |
| | `POST` | `/api/auth/reset-password` | Reset password with OTP | Public |
| | `POST` | `/api/auth/verify-email` | Verify email with OTP | Public |
| | `POST` | `/api/auth/resend-verification` | Resend verification email | Public |
| **`tenants.py`** | `GET` | `/api/tenant/current` | Get organization details | Bearer Auth |
| | `PUT` | `/api/tenant/current` | Update organization details | Bearer Auth |
| | `GET` | `/api/tenant/members` | List organization team members | Bearer Auth |
| | `POST` | `/api/tenant/invite` | Invite user to organization | Bearer Auth |
| | `DELETE` | `/api/tenant/members/{user_id}` | Remove member from tenant | Admin Only |
| **`databases.py`** | `GET` | `/api/databases` | List database connections | Bearer Auth |
| | `POST` | `/api/databases` | Add new database connection | Bearer Auth |
| | `DELETE` | `/api/databases/{db_id}` | Delete database connection | Bearer Auth |
| | `GET` | `/api/databases/{db_id}/tables` | Introspect database tables | Bearer Auth |
| | `GET` | `/api/databases/{db_id}/tables/{table}/data` | Preview 100 rows table data | Bearer Auth |
| | `GET` | `/api/databases/{db_id}/stats` | Get DB table count & stats | Bearer Auth |
| | `GET` | `/api/databases/{db_id}/tables/{table}/stats` | Get table row/col count | Bearer Auth |
| | `POST` | `/api/databases/test` | Test DB host connection | Bearer Auth |
| **`api_keys.py`** | `GET` | `/api/keys` | List tenant API keys | Bearer Auth |
| | `POST` | `/api/keys` | Generate new API key | Bearer Auth |
| | `PUT` | `/api/keys/{key_id}/revoke` | Revoke active API key | Bearer Auth |
| | `DELETE` | `/api/keys/{key_id}` | Delete API key record | Bearer Auth |
| **`chatbot_config.py`** | `GET` | `/api/chatbot-config` | Fetch chatbot widget settings | Bearer Auth |
| | `PUT` | `/api/chatbot-config` | Update chatbot settings | Bearer Auth |
| **`documents.py`** | `GET` | `/api/documents` | List uploaded RAG documents | Bearer Auth |
| | `POST` | `/api/documents/upload` | Upload PDF/TXT & build FAISS index | Bearer Auth |
| | `DELETE` | `/api/documents/{document_id}` | Delete document & vector index | Bearer Auth |
| | `GET` | `/api/documents/{document_id}/chunks` | View extracted text chunks | Bearer Auth |
| | `POST` | `/api/documents/search` | Execute FAISS vector search | Bearer Auth |

---

### 1.4 Database Models vs Enterprise SQL Schemas

- **`Full_Project_Schemas.sql`**: Defines **35 tables** across 9 enterprise modules:
  `tenants`, `tenant_settings`, `users`, `roles`, `permissions`, `memberships`, `database_connections`, `secrets`, `database_schemas`, `table_metadata`, `column_metadata`, `chatbot_configs`, `conversations`, `messages`, `intents`, `query_templates`, `executed_queries`, `query_safety_logs`, `documents`, `document_chunks`, `collections`, `vector_records`, `generated_insights`, `recommendations`, `dashboards`, `widgets`, `subscriptions`, `invoices`, `payments`, `metered_usage`, `api_keys`, `rate_limits`, `security_policies`, `audit_logs`, `system_metrics`.
- **`backend/models.py`**: Defines **10 SQLAlchemy ORM models** (matching `Database_ERD.md` 1:1):
  `Tenant`, `User`, `UserDatabaseAccess`, `TenantInvite`, `DatabaseConnection`, `ApiKey`, `ChatbotConfig`, `Document`, `DocumentChunk`, `PasswordResetOTP`.
- **Missing Enterprise Tables**: **25 of 35 tables** are completely unbuilt in Python ORM code.

---

## 2. R2: System Verification & Functional Gap Analysis

### 2.1 Active vs Mocked Component Verification Matrix

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            DATASPEAKAI PLATFORM                             │
├──────────────────────────────────────┬──────────────────────────────────────┤
│       LIVE INTEGRATED MODULES        │       MOCKED / UNBUILT MODULES       │
├──────────────────────────────────────┼──────────────────────────────────────┤
│  ✓ User Auth & Email Verification    │  ✗ NL-to-SQL Query Translation Engine│
│  ✓ Tenant & Team Member Invites      │  ✗ ERD / Schema Visualizer Tool      │
│  ✓ DB Connections & Table Explorer   │  ✗ Overview & Analytics Dashboards   │
│  ✓ RAG Document Upload & FAISS Index │  ✗ AI Insights & Recommendations     │
│  ✓ API Key Generation & Revocation   │  ✗ Usage Metrics & Token Tracking    │
│  ✓ Chatbot Config Customization      │  ✗ Query Logs & Data Exporting       │
│  ✓ Security Password Change          │  ✗ Platform Administrator Panel      │
└──────────────────────────────────────┴──────────────────────────────────────┘
```

---

### 2.2 API Integration Contract Inspection

A detailed inspection of frontend API payloads (`src/`) against backend Pydantic schemas (`backend/schemas.py`) and router update handlers (`backend/routers/`) confirmed the following:

- **Verified Integration Contract Bug (Chatbot Config Field Drop)**:
  - UI (`ChatbotWidgetPage.tsx:59-73`) sends `PUT /api/chatbot-config` with payload `{ theme_color, greeting_message, position, welcome_delay, max_history, widget_title, sound_enabled }`.
  - Backend handler (`chatbot_config.py:43-47`) accepts `ChatbotConfigCreate` but updates only `theme_color`, `greeting_message`, `position`, `welcome_delay`, `max_history`. It **drops `widget_title` and `sound_enabled`** during the database update.
  - *Result*: Custom widget title and sound toggles are lost on reload.

- **Verified Correct Contracts**:
  - *Password Reset*: UI (`ForgotPasswordPage.tsx:137`) passes `otp_code: otp.join("")` alongside `email` and `new_password`, matching `ResetPasswordRequest` in `schemas.py:158`.
  - *Tenant Settings*: UI (`SettingsPage.tsx:96-100`) sends `website`, `industry`, `address`, matching `TenantUpdate` in `schemas.py:17`.
  - *API Key Creation*: UI (`ApiKeysPage.tsx:70`) sends `name` and `description`, matching `ApiKeyCreate` in `schemas.py:89`.

---

### 2.3 Critical Backend Bugs & Security Vulnerabilities

1. **Python Function Overwriting Defect (SQLite Inspection Bug)**:
   - `backend/routers/databases.py` defines `def get_connection_url(db_conn)` twice (lines 13-20 and 92-97). The second definition overwrites the first and omits `sqlite`.
   - *Impact*: Any SQLite database connection evaluates `get_connection_url` to `None`, silently falling through to mock table data.
2. **SQL Injection Vulnerability**:
   - `backend/routers/databases.py:150` executes `conn.execute(text(f"SELECT * FROM {table_name} LIMIT 100"))`.
   - *Impact*: Malicious table names can execute arbitrary SQL injection queries.
3. **Plaintext Database Passwords**:
   - `backend/models.py:65` stores external database credentials in plaintext column `password VARCHAR`.
   - *Impact*: Exposure of application database leaks all connected customer database passwords.
4. **Database Engine Connection Leak**:
   - `backend/routers/databases.py` calls `create_engine()` inside `get_table_data` without `engine.dispose()`.
   - *Impact*: High query volume will exhaust host socket handles and connection pools.
5. **Hardcoded Credentials in Source Code**:
   - `backend/routers/users.py:129-130` hardcodes fallback GitHub client secret `"067e59b3c050792898954f727be0dbdbfc5c590a"`.
   - *Impact*: High security vulnerability if committed to public repositories.
6. **RAG Vector Search Incomplete Pipeline**:
   - `backend/routers/documents.py:165` (`/api/documents/search`) queries FAISS vector store and returns raw context chunks without running an LLM synthesis step to generate a natural language answer.

---

### 2.4 Environment & Configuration Audit

- **Environment Name Mismatch**: `.env.example` defines `VITE_API_URL=http://localhost:8000`, but `src/app/config/api.ts` checks `import.meta.env.VITE_API_BASE_URL`.
- **8 Undocumented Backend Environment Variables**:
  - `GEMINI_API_KEY`: Required for PDF image OCR and vision processing (`documents.py:85`).
  - `EMAIL_USER`, `EMAIL_PASS`, `EMAIL_HOST`, `EMAIL_PORT`, `RESEND_API_KEY`: Required for email OTP delivery (`users.py:226-257`).
  - `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`: Required for GitHub OAuth (`users.py:129-130`).
- **Legacy Branding Artifacts**: `ChatbotWidgetPage.tsx` and `ApiKeysPage.tsx` contain embedded code snippets referencing `omniquery.ai` URLs.

---

## 3. R3: Priority Roadmap & Action Items

To transition DataSpeakAI from a partial MVP into a production-ready enterprise platform, execution is structured into 4 sequential phases:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            DEVELOPMENT ROADMAP                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  PHASE 1: Security Hardening & Environment Clean-Up (Immediate)            │
│  PHASE 2: API Contract Repair & Backend Defect Remediation                   │
│  PHASE 3: Core AI Engine Implementation (NL-to-SQL, ERD, Analytics, Export) │
│  PHASE 4: Enterprise Schema Expansion & UI Mock Replacement                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Phase 1: Security Hardening & Environment Clean-Up (Priority: IMMEDIATE)
- [ ] Remove hardcoded GitHub client secret from `backend/routers/users.py:130` and bind to `os.getenv("GITHUB_CLIENT_SECRET")`.
- [ ] Fix environment variable alignment: update `.env.example` to define `VITE_API_BASE_URL` and add all 8 missing backend variables (`GEMINI_API_KEY`, `EMAIL_*`, `RESEND_API_KEY`, `GITHUB_*`).
- [ ] Implement parameter sanitization or identifier quoting in `backend/routers/databases.py` to eliminate SQL injection in table previews.
- [ ] Add AES-256 encryption/decryption for stored database connection passwords in `models.py` / `databases.py`.

### Phase 2: API Contract Repair & Backend Defect Remediation (Priority: HIGH)
- [ ] Remove duplicate `get_connection_url` definition in `backend/routers/databases.py` to restore live SQLite database inspection.
- [ ] Add `engine.dispose()` calls to `databases.py` table inspection endpoints to prevent socket/connection leaks.
- [ ] Fix Chatbot Config update contract in `backend/routers/chatbot_config.py`: include `widget_title` and `sound_enabled` in SQL update logic.
- [ ] Fix frontend `UploadDocumentsPage.tsx` payload to append `embeddingModel` and `autoIndex` to upload `FormData`.

### Phase 3: Core AI Engine & Missing Service Implementation (Priority: HIGH)
- [ ] Build **NL-to-SQL Translation Service** (`backend/services/sql_engine.py` & `backend/routers/query.py`):
  - Implement schema grounding (fetch table metadata -> construct prompt -> call LLM).
  - Add SQL syntax validation & execution safety guardrails (`SELECT` only).
  - Build UI Query Bar / Natural Language Chat interface component in React.
- [ ] Build **ERD Visualizer Service** (`backend/routers/erd.py`):
  - Introspect foreign key relationships from database connections and return Mermaid/D3 JSON graphs.
  - Build interactive ERD Visualizer page in React.
- [ ] Complete **RAG LLM Synthesis Step**:
  - Update `POST /api/documents/search` to pass retrieved FAISS chunks to Gemini Flash LLM for synthesized answer generation.

### Phase 4: Enterprise Schema Expansion & UI Mock Replacement (Priority: MEDIUM)
- [ ] Implement Python SQLAlchemy ORM models for remaining 25 enterprise tables from `Full_Project_Schemas.sql` (RBAC `roles`/`permissions`/`memberships`, `dashboards`, `widgets`, `audit_logs`, `subscriptions`).
- [ ] Replace static mock arrays in UI components (`DashboardOverview`, `AnalyticsPage`, `AIInsightsPage`, `UsagePage`, `LogsPage`, `AdminPanel`) with live backend API endpoints.
- [ ] Clean up residual legacy branding references (`omniquery.ai`) across embed snippets.
- [ ] Create `Dockerfile` and `docker-compose.yml` for unified local/production containerized deployment.

---

## 4. Verification & Audit Trail

All findings in this report have been verified against source files in `d:\dataspeak`:
- Database & ORM Analysis: `d:\dataspeak\.agents\explorer_database_docs\handoff.md`
- Frontend UI Analysis: `d:\dataspeak\.agents\explorer_frontend\handoff.md`
- Backend API Analysis: `d:\dataspeak\.agents\explorer_backend\handoff.md`
- Integration Gap Analysis: `d:\dataspeak\.agents\explorer_integration_gaps\handoff.md`
- Victory Audit Feedback & Remediation: `d:\dataspeak\.agents\victory_auditor\audit_report.md`

*Report compiled and updated by Project Orchestrator.*
