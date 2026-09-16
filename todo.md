# DataSpeakAI — Master Engineering Roadmap & Task Tracker (`todo.md`)

This document is the **single authoritative backlog and task tracking standard** for all human developers and AI coding agents (Antigravity, Cursor, Copilot, Claude Code) working on the **DataSpeakAI** codebase.

All agents must strictly follow the **Agent Execution & Maintenance Protocol** below when claiming, executing, and closing tasks.

---

## 📋 Agent Execution & Maintenance Protocol (MANDATORY)

Every AI agent working on this repository **MUST** adhere to this 4-step workflow:

1. **Task Selection & Verification**:
   - Inspect this file (`todo.md`) and select the next uncompleted task (`- [ ]`) in priority order (P0 → P1 → P2 → P3) or the task explicitly requested by the user.
   - Review target files and dependencies using `view_file` before making any code modifications.
   - Strictly follow engineering rules in [`AGENTS.md`](file:///d:/dataspeak/AGENTS.md) (SQL parameterization, minimal changes, no hardcoded secrets).

2. **Implementation & Testing**:
   - Write clean, production-grade code with zero placeholder mocks.
   - Execute verification:
     - Frontend: `cmd.exe /c "npm run build"` must pass with 0 errors.
     - Backend: Ensure Python modules import cleanly and router endpoints return valid Pydantic schemas.

3. **Task Completion & Archiving**:
   - When a task is completed, **do NOT leave it in the active phase list**.
   - Mark the checkbox with `[x]`.
   - Add completion metadata: `[Completed: YYYY-MM-DD | Agent/Role | Short Summary]`.
   - **Move the completed task item** from the active phase section into the [## 📦 Archived / Completed Tasks](#-archived--completed-tasks) section at the bottom of this file.

4. **Changelog & Documentation Update**:
   - Update [`CHANGELOG.md`](file:///d:/dataspeak/CHANGELOG.md) under `## [Unreleased]` with a clear, descriptive bullet point under the proper category (`Added`, `Changed`, `Fixed`, `Security`).
   - If architectural changes or new schemas were introduced, update corresponding docs in `docs/` and [`AGENTS.md`](file:///d:/dataspeak/AGENTS.md).

---

## 🚀 Active Engineering Roadmap

---

### Phase 1: Live Frontend-to-Backend Dashboard Wiring
**Priority: P0 (Immediate Quick Win) | Estimated Effort: 2-3 sessions**  
**Goal:** Connect all frontend dashboard views to the existing backend endpoints in [`backend/routers/analytics.py`](file:///d:/dataspeak/backend/routers/analytics.py) and remove hardcoded static mock arrays.

- [ ] **Task 1.1 — Wire Overview Dashboard to Live Analytics API**
  - **Target Files:** [`src/app/pages/dashboard/DashboardOverview.tsx`](file:///d:/dataspeak/src/app/pages/dashboard/DashboardOverview.tsx), [`backend/routers/analytics.py`](file:///d:/dataspeak/backend/routers/analytics.py)
  - **Details:** Replace static mock constants (`stats`, `queryData`, `databaseActivity`, `recentQueries`) with live data fetched from `GET /api/analytics/overview`. Add loading skeletons and error states with Sonner toast feedback.
  - **Acceptance Criteria:** Real-time KPI counts (queries, databases, documents, API calls), 7-day query timeline chart, and recent query table render live tenant data.

- [ ] **Task 1.2 — Wire Analytics & Visualization Page to Live Trends API**
  - **Target Files:** [`src/app/pages/dashboard/AnalyticsPage.tsx`](file:///d:/dataspeak/src/app/pages/dashboard/AnalyticsPage.tsx), [`backend/routers/analytics.py`](file:///d:/dataspeak/backend/routers/analytics.py)
  - **Details:** Replace static arrays (`queryTrendsData`, `topTablesData`, `databaseDistribution`, `dataGrowthData`) with `GET /api/analytics/trends`. Connect database filter dropdown and date range selector to backend query params.
  - **Acceptance Criteria:** Recharts graphs display live query trends, top queried tables, database type distribution, latency, and success rates.

- [ ] **Task 1.3 — Wire Query Logs Page with Pagination, Search & Filtering**
  - **Target Files:** [`src/app/pages/dashboard/LogsPage.tsx`](file:///d:/dataspeak/src/app/pages/dashboard/LogsPage.tsx), [`backend/routers/analytics.py`](file:///d:/dataspeak/backend/routers/analytics.py)
  - **Details:** Connect log table to `GET /api/logs`. Wire search input, status filter dropdown (`All`, `Success`, `Failed`), database selector, and pagination controls (`page`, `limit`).
  - **Acceptance Criteria:** Live query logs render with exact execution time in ms, rows returned, error messages (if failed), and timestamp. Export CSV button downloads live log data.

- [ ] **Task 1.4 — Wire Usage & Metering Page to Live Usage API**
  - **Target Files:** [`src/app/pages/dashboard/UsagePage.tsx`](file:///d:/dataspeak/src/app/pages/dashboard/UsagePage.tsx), [`backend/routers/analytics.py`](file:///d:/dataspeak/backend/routers/analytics.py)
  - **Details:** Replace static arrays (`usageData`, `databaseTypeData`, `hourlyData`) with `GET /api/usage`.
  - **Acceptance Criteria:** Meter cards display actual tokens used vs. limit (500k), daily token usage charts, database breakdown pie chart, and hourly query patterns.

- [ ] **Task 1.5 — Wire Admin Panel to Live System & Tenant APIs**
  - **Target Files:** [`src/app/pages/admin/AdminPanel.tsx`](file:///d:/dataspeak/src/app/pages/admin/AdminPanel.tsx), [`backend/routers/analytics.py`](file:///d:/dataspeak/backend/routers/analytics.py)
  - **Details:** Connect admin dashboard to `GET /api/admin/stats` and `GET /api/admin/tenants`. Enforce Admin role gate.
  - **Acceptance Criteria:** Superadmin sees true platform-wide tenant counts, query volumes, active database counts, system health metrics, and tenant management table with real user counts.

---

### Phase 2: Embeddable Standalone Chatbot Widget
**Priority: P1 (Core SaaS Capability) | Estimated Effort: 3-4 sessions**  
**Goal:** Enable SaaS tenants to embed the AI chatbot on external websites via a single `<script>` tag.

- [ ] **Task 2.1 — Build Public Tenant-Authenticated Widget Chat API**
  - **Target Files:** [`backend/routers/chat.py`](file:///d:/dataspeak/backend/routers/chat.py), [`backend/routers/api_keys.py`](file:///d:/dataspeak/backend/routers/api_keys.py)
  - **Details:** Create endpoint `POST /api/chat/widget` that authenticates via `X-API-Key` or tenant public token (without requiring user login cookies/JWT). Apply rate-limiting and query logging.
  - **Acceptance Criteria:** External applications can execute conversational RAG/SQL queries safely using a valid tenant API key.

- [ ] **Task 2.2 — Compile Standalone Embeddable Script (`widget.js`)**
  - **Target Files:** `src/widget/` or `public/widget.js`, `vite.config.ts`
  - **Details:** Build a lightweight, zero-dependency vanilla JS/preact bundle that injects a floating chat button, expandable iframe/modal, respects tenant branding (`theme_color`, `widget_title`, `greeting_message` from `/api/chatbot-config`), and connects to `/api/chat/widget`.
  - **Acceptance Criteria:** Loading `<script src=".../widget.js" data-tenant-key="..."></script>` on an arbitrary HTML page renders a responsive, branded chat bubble that chats with tenant documents and databases.

- [ ] **Task 2.3 — Live Widget Preview & Embed Snippet Verification**
  - **Target Files:** [`src/app/pages/dashboard/ChatbotWidgetPage.tsx`](file:///d:/dataspeak/src/app/pages/dashboard/ChatbotWidgetPage.tsx)
  - **Details:** Ensure the live preview sandbox matches the production `widget.js` bundle exactly, and the generated copyable HTML snippet contains the correct host URL and active API key.
  - **Acceptance Criteria:** Users can copy the embed code directly from the UI and paste it into any external site with instant functionality.

---

### Phase 3: Dynamic AI Insights & Recommendation Engine
**Priority: P1 (Core BI Value) | Estimated Effort: 3 sessions**  
**Goal:** Transform [`AIInsightsPage.tsx`](file:///d:/dataspeak/src/app/pages/dashboard/AIInsightsPage.tsx) from static mock cards into an AI-powered business anomaly and recommendation engine.

- [ ] **Task 3.1 — Create Database Models for Insights & Recommendations**
  - **Target Files:** [`backend/models.py`](file:///d:/dataspeak/backend/models.py), [`backend/schemas.py`](file:///d:/dataspeak/backend/schemas.py)
  - **Details:** Implement `GeneratedInsight` and `Recommendation` SQLAlchemy models matching [`Full_Project_Schemas.sql`](file:///d:/dataspeak/docs/database/Full_Project_Schemas.sql) lines 216-231.
  - **Acceptance Criteria:** Tables created in SQLite/PostgreSQL with foreign key links to `tenants.id`.

- [ ] **Task 3.2 — Build AI Insights Generator Worker & Router**
  - **Target Files:** `backend/services/insights_engine.py`, `backend/routers/insights.py`, [`backend/main.py`](file:///d:/dataspeak/backend/main.py)
  - **Details:** Develop an analytics worker that analyzes tenant query patterns, table row growth, execution errors, and database metrics using Gemini 2.5 Flash to identify anomalies, trends, and action items. Expose `GET /api/insights` and `POST /api/insights/refresh`.
  - **Acceptance Criteria:** Backend generates structured insights (`warning`, `alert`, `opportunity`, `critical`) with confidence scores and action recommendations.

- [ ] **Task 3.3 — Connect AI Insights UI to Live Backend**
  - **Target Files:** [`src/app/pages/dashboard/AIInsightsPage.tsx`](file:///d:/dataspeak/src/app/pages/dashboard/AIInsightsPage.tsx)
  - **Details:** Fetch live insights from `GET /api/insights`. Add a "⚡ Refresh AI Insights" trigger button with loading animation and toast notifications.
  - **Acceptance Criteria:** Real anomalies and recommendations render with interactive action triggers and category filtering (`All`, `Revenue`, `Performance`, `Customer Success`).

---

### Phase 4: Enterprise Database Schema Expansion
**Priority: P2 (Architecture & Scalability) | Estimated Effort: 4 sessions**  
**Goal:** Expand [`backend/models.py`](file:///d:/dataspeak/backend/models.py) to implement the 22 unbuilt enterprise tables from [`Full_Project_Schemas.sql`](file:///d:/dataspeak/docs/database/Full_Project_Schemas.sql).

- [ ] **Task 4.1 — Granular RBAC Models (`roles`, `permissions`, `memberships`)**
  - **Target Files:** [`backend/models.py`](file:///d:/dataspeak/backend/models.py), [`backend/schemas.py`](file:///d:/dataspeak/backend/schemas.py)
  - **Details:** Implement enterprise role-based access control models replacing simple string roles.

- [ ] **Task 4.2 — Persistent Schema Catalog (`database_schemas`, `table_metadata`, `column_metadata`)**
  - **Target Files:** [`backend/models.py`](file:///d:/dataspeak/backend/models.py), [`backend/services/sql_engine.py`](file:///d:/dataspeak/backend/services/sql_engine.py)
  - **Details:** Persist introspected database schemas and column PII flags to avoid re-introspecting live databases on every query.

- [ ] **Task 4.3 — Fine-Grained Query Auditing (`query_templates`, `executed_queries`, `query_safety_logs`, `intents`)**
  - **Target Files:** [`backend/models.py`](file:///d:/dataspeak/backend/models.py), [`backend/routers/query.py`](file:///d:/dataspeak/backend/routers/query.py)
  - **Details:** Log detailed validation results, violation details, and intent classification scores for security compliance.

- [ ] **Task 4.4 — Multi-Collection Vector Registry (`collections`, `vector_records`)**
  - **Target Files:** [`backend/models.py`](file:///d:/dataspeak/backend/models.py), [`backend/routers/documents.py`](file:///d:/dataspeak/backend/routers/documents.py)
  - **Details:** Support grouping documents into separate searchable knowledge collections per tenant.

- [ ] **Task 4.5 — Custom Dashboards & Drag-and-Drop Widgets (`dashboards`, `widgets`)**
  - **Target Files:** [`backend/models.py`](file:///d:/dataspeak/backend/models.py), [`backend/schemas.py`](file:///d:/dataspeak/backend/schemas.py)
  - **Details:** Persist user-customized dashboard layouts and chart widget configurations.

- [ ] **Task 4.6 — Billing & Metering Infrastructure (`subscriptions`, `invoices`, `payments`, `metered_usage`)**
  - **Target Files:** [`backend/models.py`](file:///d:/dataspeak/backend/models.py), [`backend/schemas.py`](file:///d:/dataspeak/backend/schemas.py)
  - **Details:** Implement Stripe customer IDs, plan tiers, billing cycles, and feature metering models.

- [ ] **Task 4.7 — Security Policies & System Metrics (`rate_limits`, `security_policies`, `audit_logs`, `system_metrics`)**
  - **Target Files:** [`backend/models.py`](file:///d:/dataspeak/backend/models.py), [`backend/schemas.py`](file:///d:/dataspeak/backend/schemas.py)
  - **Details:** Store 2FA enforcement flags, IP whitelists, rate limit thresholds, and cluster health metrics.

---

### Phase 5: Interactive Visual Database ERD Generator
**Priority: P2 (Visual BI Feature) | Estimated Effort: 2-3 sessions**  
**Goal:** Allow users to visualize relationships between database tables visually.

- [ ] **Task 5.1 — Database Foreign Key Graph Introspection API**
  - **Target Files:** `backend/routers/erd.py`, [`backend/services/sql_engine.py`](file:///d:/dataspeak/backend/services/sql_engine.py)
  - **Details:** Build endpoint `GET /api/databases/{id}/erd` returning nodes (tables, column types, PKs) and edges (foreign key relations) formatted for diagram rendering.
  - **Acceptance Criteria:** Endpoint returns complete relationship graph for SQLite, PostgreSQL, and MySQL.

- [ ] **Task 5.2 — Interactive ERD Canvas Component in React**
  - **Target Files:** `src/app/pages/dashboard/DatabaseErdPage.tsx` or modal in [`DatabasesPage.tsx`](file:///d:/dataspeak/src/app/pages/dashboard/DatabasesPage.tsx)
  - **Details:** Render interactive zoomable/pannable ERD diagram (using React Flow or Mermaid) with table details on click.
  - **Acceptance Criteria:** Users can visually inspect table relationships and foreign keys with zoom, pan, and table search.

---

### Phase 6: Production Hardening, Billing & DevOps
**Priority: P3 (Production Readiness) | Estimated Effort: 2 sessions**  
**Goal:** Prepare DataSpeakAI for commercial production deployment.

- [ ] **Task 6.1 — Stripe Billing & Subscription Webhooks**
  - **Target Files:** `backend/routers/billing.py`, `backend/services/stripe_service.py`
  - **Details:** Implement checkout session creation, webhook listener for subscription updates/cancellations, and customer portal redirection.
  - **Acceptance Criteria:** Users can upgrade plans from Starter to Pro/Enterprise with live subscription status reflected in UI.

- [ ] **Task 6.2 — Dockerfile & Docker Compose Multi-Container Setup**
  - **Target Files:** `Dockerfile`, `docker-compose.yml`, `.dockerignore`
  - **Details:** Containerize FastAPI backend, Redis broker, Celery worker, React SPA (Nginx), and PostgreSQL into a single reproducible stack.
  - **Acceptance Criteria:** `docker-compose up --build` launches the entire platform locally with verified service communication.

- [ ] **Task 6.3 — Production Security Hardening Checklist**
  - **Target Files:** [`backend/main.py`](file:///d:/dataspeak/backend/main.py), [`src/app/pages/LoginPage.tsx`](file:///d:/dataspeak/src/app/pages/LoginPage.tsx), `.env.example`
  - **Details:** Gate `seed_superadmin()` behind `ENVIRONMENT != "production"`. Remove default admin quick-fill card on login page for production builds. Rotate default admin credentials.
  - **Acceptance Criteria:** Zero hardcoded credentials or debug shortcuts exposed in production mode.

---

## 📦 Archived / Completed Tasks

*(When completing a task from the roadmap above, mark with `[x]`, append completion metadata, and move here.)*

- [x] **Conversational AI Assistant Workspace & Unified Chat Engine**
  - *Completed:* 2026-08-08 | Antigravity AI Orchestrator
  - *Summary:* Built responsive 3-panel chat interface in [`ChatPage.tsx`](file:///d:/dataspeak/src/app/pages/dashboard/ChatPage.tsx), unified multi-turn chat router [`chat.py`](file:///d:/dataspeak/backend/routers/chat.py), `Conversation`/`Message` models, auto-DB router [`query_router.py`](file:///d:/dataspeak/backend/services/query_router.py), and safe NL-to-SQL engine [`sql_engine.py`](file:///d:/dataspeak/backend/services/sql_engine.py).

- [x] **Multimodal Document RAG Pipeline & Hybrid Search**
  - *Completed:* 2026-08-07 | Antigravity AI Specialist
  - *Summary:* Built multi-format file parser (`backend/ingestion/`), Gemini 2.5 Flash VLM OCR, LangChain chunking, FAISS + BM25Okapi hybrid search with Reciprocal Rank Fusion and Cross-Encoder re-ranking in [`hybrid.py`](file:///d:/dataspeak/backend/search/hybrid.py), and dual progress tracking in [`UploadDocumentsPage.tsx`](file:///d:/dataspeak/src/app/pages/dashboard/UploadDocumentsPage.tsx).

- [x] **Backend Analytics & Execution Logs API Layer**
  - *Completed:* 2026-08-06 | Antigravity AI Implementer
  - *Summary:* Built [`backend/routers/analytics.py`](file:///d:/dataspeak/backend/routers/analytics.py) exposing `/api/analytics/overview`, `/api/analytics/trends`, `/api/logs`, `/api/usage`, and `/api/admin/*` backed by `QueryLog` database model.

- [x] **Multi-Tenant Authentication, OTP & GitHub OAuth**
  - *Completed:* 2026-07-20 | Project Team
  - *Summary:* Implemented JWT authentication, bcrypt hashing, 6-digit email OTP verification, 3-step password recovery, GitHub OAuth 2.0 sign-in, tenant invitation tokens, and dev superadmin seed in [`users.py`](file:///d:/dataspeak/backend/routers/users.py).

- [x] **External Database Connection Management & Safe 100-Row Preview**
  - *Completed:* 2026-07-15 | Project Team
  - *Summary:* Built CRUD endpoints for PostgreSQL, MySQL, MariaDB, and SQLite in [`databases.py`](file:///d:/dataspeak/backend/routers/databases.py), Fernet symmetric password encryption in [`crypto.py`](file:///d:/dataspeak/backend/crypto.py), and table explorer in [`DatabasesPage.tsx`](file:///d:/dataspeak/src/app/pages/dashboard/DatabasesPage.tsx).
