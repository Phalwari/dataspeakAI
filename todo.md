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

### 📌 Backlog & Technical Debt Items
- [ ] **Real Token Streaming**: Current SSE sends the answer in chunks after full generation (TTFT ~ total latency); implement true token-level streaming directly from Gemini / LLM engine.
- [ ] **CI Lint & Type Checks**: Add `tsc --noEmit` and `ruff` or `pyright` to continuous integration pipeline.
- [ ] **Legacy ApiKey Hashing**: Hash legacy `ApiKey` values at rest (e.g. SHA-256) rather than storing plaintext keys in database.
- [ ] **CORS Origin Strictness**: Replace wildcard `allow_origins=["*"]` + `allow_credentials=True` on dashboard routes with strict explicit origin allowlists.
- [ ] **Latency Optimization**: Embedding cold start and TTFT latency profiling and caching.
- *Note:* PostgreSQL, MySQL and Redis paths were verified with mocks/unit tests only, not against live servers.

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
  - **Target Files:** [`backend/main.py`](file:///d:/dataspeak/backend/main.py), [`backend/models.py`](file:///d:/dataspeak/backend/models.py), [`backend/routers/api_keys.py`](file:///d:/dataspeak/backend/routers/api_keys.py), [`src/app/pages/LoginPage.tsx`](file:///d:/dataspeak/src/app/pages/LoginPage.tsx), `.env.example`
  - **Details:** 
    - Gate `seed_superadmin()` behind `ENVIRONMENT != "production"`. Remove default admin quick-fill card on login page for production builds. Rotate default admin credentials.
    - Hash legacy `ApiKey` values at rest (e.g. SHA-256) rather than storing plain text keys; review and modernize the legacy `omq_` prefix.
    - Replace global CORS `allow_origins=["*"]` + `allow_credentials=True` on dashboard routes with an explicit origin allowlist (e.g. `CORS_ORIGINS` env var) to eliminate browser credential reflection risks.
  - **Acceptance Criteria:** Zero hardcoded credentials or debug shortcuts exposed in production mode; legacy API keys hashed at rest; CORS origins explicitly constrained for credentialed requests.

---

## 📦 Archived / Completed Tasks

- [x] **Phase 4: Enterprise Database Schema Expansion & QA Remediation (Tasks 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7)**
  - *Completed:* 2026-10-13 | Antigravity AI Engineer & QA Lead
  - *Summary:* Expanded backend ORM architecture from 10 MVP models to full 35-table enterprise coverage achieving 100% parity with `Full_Project_Schemas.sql` and remediated all 7 post-expansion QA review findings:
    - **Task 4.1 (Granular RBAC Models & Lifecycle):** Implemented `TenantSettings`, `Role`, `Permission` (1-to-many via `role_id`), and `Membership` in `backend/models.py`. Seeded 4 standard roles (`Admin`, `Developer`, `Business Owner`, `Viewer`) with granular action permissions in `seed_admin.py`. Wired automatic initialization of `TenantSettings` and `Membership(is_owner=True)` into `register_user()` in `routers/users.py`. Preserved legacy `User.role` and `User.tenant_id` for backward compatibility. Added `Secret` model for encrypted credential storage.
    - **Task 4.2 (Persistent Schema Catalog & Relational Context Preservation):** Created `DatabaseSchema`, `TableMetadata`, and `ColumnMetadata` models with `is_primary_key`, `is_foreign_key`, and `foreign_key_target`. Built `sync_database_catalog()` in `sql_engine.py` with automatic PII column pattern tagging (`is_pii=True`) and explicit child `ColumnMetadata` purging to eliminate SQLite column multiplication on re-sync. Formatted `[PRIMARY KEY]`, `[FOREIGN KEY -> target.col]`, and `[PII]` in persistent schema prompt context in `get_db_schema_context()`, matching live introspection with 100% fidelity.
    - **Task 4.3 (Fine-Grained Query Auditing & Observable Telemetry):** Created `QueryTemplate`, `ExecutedQuery`, `QuerySafetyLog`, and `Intent` models. Integrated query execution telemetry and AST safety violation logging into `POST /api/query` in `routers/query.py` with structured `logger.exception()` failure logging. Unified `executed_queries` columns with `Full_Project_Schemas.sql` and added zero-dependency auto-migrations in `services/db_migration.py`.
    - **Task 4.4 (Multi-Collection Vector Registry):** Built `Collection` and `VectorRecord` models for partitioned tenant knowledge bases.
    - **Task 4.5 (Custom Dashboards & Widgets):** Implemented `Dashboard` and `Widget` models with layout configurations and cascade deletion.
    - **Task 4.6 (Billing & Metering Infrastructure):** Added `Subscription`, `Invoice`, `Payment`, and `MeteredUsage` models storing Stripe identifiers, billing cycles, payment statuses, and consumable usage units.
    - **Task 4.7 (Security Policies & System Metrics):** Created `RateLimit`, `SecurityPolicy`, `AuditLog`, and `SystemMetric` models.
    - **Pydantic V2 Schemas:** Added complete `from_attributes=True` schemas in `backend/schemas.py` for all new models.
    - **Regression & Behavioral Testing:** Expanded regression suite to 16 tests across `test_phase4_stage_a_regression.py` (6 tests), `test_phase4_stage_b_regression.py` (4 tests), and `test_phase4_enterprise_schema_regression.py` (6 tests, including real ORM cascade deletions and registration RBAC lifecycle). Verified 100% schema integrity, behavioral suite passing, and 0-error Vite frontend production build (2,772 modules).

- [x] **Phase 3.1: AI Insights Engine Security & Behavioral Hardening (Post-QA Remediation Package)**
  - *Completed:* 2026-10-13 | Antigravity QA Engineer
  - *Summary:* Remediated 7 issues identified during independent code review and behavioral QA on Phase 3:
    - **SEC-01 (Cross-Tenant Database IDOR):** Enforced tenant verification (`DatabaseConnection.tenant_id == current_user.tenant_id`) on `GET /api/insights` and `POST /api/insights/refresh`, returning 404 on cross-tenant or missing databases. Eliminated N+1 query overhead using eager relationship loading (`joinedload`, `selectinload`).
    - **SEC-02 (Recommendation ID Enumeration Defense):** Replaced divergent 403 Forbidden vs 404 Not Found responses in `PUT /api/insights/recommendations/{id}/status` with uniform 404 responses across non-existent and foreign-tenant recommendations.
    - **BUG-01 (Child Recommendation Orphan Purging):** Resolved SQLite orphaned recommendation accumulation on refresh by explicitly deleting child `Recommendation` entities before deleting parent `GeneratedInsight` instances, eliminating `SAWarning` and 500 `AttributeError` on subsequent status mutations.
    - **BUG-02 (Resilient LLM Score Parsing):** Implemented `_safe_float()` helper in `insights_engine.py` with percentage string parsing and clamp bounds; filtered non-dict items; added try-except fallback on persistence failure.
    - **UI-01 (Pending Actions KPI Sync):** Updated `handleToggleRecommendation` in `AIInsightsPage.tsx` to optimistically increment/decrement `summary.pending_actions_count` when toggling task completion.
    - **INT-01 (Logs Deep-Link Parameter Binding):** Wired `useSearchParams` in `LogsPage.tsx` to read `?status=failed` on initialization and pre-select the query logs filter.
    - **NIT-01 (Pydantic V2 Migration):** Migrated `RecommendationItem` and `GeneratedInsightItem` to `model_config = ConfigDict(from_attributes=True)`.
    - **Regression Suite:** Expanded `tests/test_phase3_ai_insights_regression.py` to 12 tests; 382/382 full test suite passing (0 failures); 0-error Vite frontend build.

- [x] **Phase 3: Dynamic AI Insights & Recommendation Engine (Tasks 3.1, 3.2, 3.3)**
  - *Completed:* 2026-10-13 | Antigravity AI Engineer
  - *Summary:* Built dynamic AI Insights & Recommendation Engine spanning backend ORM, telemetry aggregation worker, router endpoints, and React UI. Created `GeneratedInsight` and `Recommendation` models in `backend/models.py` with foreign key links to `tenants.id`, cascade deletion, zero-dependency migrations in `backend/services/db_migration.py`, and Pydantic validation schemas in `backend/schemas.py`. Built `InsightsEngine` worker in `backend/services/insights_engine.py` collecting genuine telemetry (query volume, error spikes, average execution latency, top error messages, introspected tables, and vector knowledge base documents), detecting deterministic statistical anomalies, and synthesizing structured business insights using Gemini 2.5 Flash via `llm_generation_service` (with Groq and deterministic zero-hallucination fallback). Added endpoints in `backend/routers/insights.py` (`GET /api/insights`, `POST /api/insights/refresh`, `PUT /api/insights/{id}/status`, `PUT /api/insights/recommendations/{id}/status`) with category, severity, status, and database scoping. Overhauled `AIInsightsPage.tsx` with live data fetching, executive KPI strip, category filtering pills (`All`, `Revenue`, `Performance`, `Customer Success`, `Operational`), severity badges, interactive recommendation completion toggles, insight dismiss/restore actions, contextual deep-links (`/dashboard/logs`, `/dashboard/databases`), and truthful cold-start onboarding states. Authored 10 regression tests in `tests/test_phase3_ai_insights_regression.py` reaching 380/380 passing tests (0 failures) and verified 0-error Vite frontend production build (2,772 modules).

- [x] **Task 2.1 — Standalone Widget Key Architecture, HMAC Handshake & Rate Limiting**
  - *Completed:* 2026-10-13 | Antigravity AI Security Engineer
  - *Summary:* Implemented `WidgetKey` publishable key model (`pk_live_...`) with origin allowlisting, rotation grace period, and per-key monthly message caps. Built `POST /api/widget/session` HMAC session handshake binding origin and conversation. Implemented multi-tier token bucket rate limiting (per key, IP, session) and concurrent stream capping.
  - *Note:* PostgreSQL, MySQL and Redis paths were verified with mocks/unit tests only, not against live servers.

- [x] **Task 2.2 — Standalone IIFE Widget Script Bundle & Shadow DOM Sandbox**
  - *Completed:* 2026-10-13 | Antigravity AI Engineer
  - *Summary:* Compiled standalone Preact IIFE bundle (`dist/widget.js`, 32.92 kB uncompressed, 12.10 kB gzipped) mounted strictly inside open Shadow DOM with CSSOM `adoptedStyleSheets` and `element.style.setProperty()` for strict CSP compliance. Built `GET /widget.js` priority serving, public-safe `GET /api/widget/config`, and accessible keyboard/focus management.

- [x] **Task 2.3 — Embeddable Standalone Chatbot Widget Security QA Hardening**
  - *Completed:* 2026-10-13 | Antigravity AI Security Engineer
  - *Summary:* Remediated all independent QA security findings (includes live widget preview + embed snippet, dashboard key management): SEC-01 exact table allowlist matching without split bypass; SEC-02 fail-closed AST parsing without regex fallback; SEC-03 trusted proxy IP extraction; SEC-04 per-key monthly cap with QueryLog migration and composite index; SEC-07 strict origin regex validation + frame-ancestors safety; SEC-09 fail-closed dialect guardrails and SQLite NullPool isolation; SEC-06 Redis stream counter 120s TTL and slot release on disconnect; SEC-05 idle rate limit bucket eviction; SEC-08 Dashboard UI key revoke/disable and delete with confirmation; SEC-10 unified rate limit values; Finding F non-destructive test isolation; Finding G strict CSP compatibility. Full test suite verification: **375 passed, 45 warnings in 195.88s (0:03:15)** on `.\backend\venv\Scripts\pytest.exe tests/`.
  - *Note:* PostgreSQL, MySQL and Redis paths were verified with mocks/unit tests only, not against live servers.

- [x] **Phase 1: Live Frontend-to-Backend Dashboard Wiring & QA Hardening (Tasks 1.1, 1.3, 1.4, 1.5 & Backend API Layer)**
  - *Completed:* 2026-10-12 | Antigravity AI Engineer
  - *Summary:* Restored and hardened Phase 1 analytics endpoints in `backend/routers/analytics.py` and `backend/main.py` (`GET /api/analytics/overview`, `GET /api/overview` alias, `GET /api/logs`, `GET /api/logs/export`, `GET /api/usage`, `GET /api/admin/stats`, `GET /api/admin/tenants`) with Pydantic response models in `backend/schemas.py`. Hardened CSV log exports against formula injection (`_sanitize_csv_cell`) and implemented true chunked generator streaming (`yield_per(500)`). Optimized 90d tenant usage via single SQL `func.date(created_at)` grouping and bounded hourly distributions. Mounted `/overview` on `core_router` eliminating OpenAPI duplicate operation ID warnings. Added `plan` column to `Tenant` model with zero-dependency migration in `services/db_migration.py`. Wired `DashboardOverview.tsx` to live analytics overview API with animated skeleton loading, truthful empty-state onboarding banners, and live 7-day query timeline. Wired `LogsPage.tsx` to live query logs API with search, status filtering, database filtering, pagination controls, delayed blob URL revocation to prevent download aborts, and server-side CSV streaming export. Wired `UsagePage.tsx` to live usage API with period selector (`24h`, `7d`, `30d`, `90d`), token consumption meter, database breakdown pie chart, and hourly activity pattern chart. Wired `AdminPanel.tsx` to live system health, week-over-week trends, 7-day platform activity curve (`platform_activity`), and registered tenant roster with search filtering and Admin role gating. Added 9 comprehensive automated regression tests in `tests/test_phase1_dashboard_wiring_regression.py` bringing test suite to 336/336 passing tests (0 failures) and verified 0-error Vite frontend production build.

- [x] **Recent Commits Remediation & Codebase Hygiene Hardening (8-Issue Fix Package)**
  - *Completed:* 2026-10-08 | Antigravity AI Engineer
  - *Summary:* Fixed critical test regression by re-mounting `analytics.router` in `backend/main.py` restoring all 29 broken endpoints and bringing test suite to 100% pass rate. Added missing `scikit-learn` and `xgboost` to `backend/requirements.txt` preventing deployment crash on `automl_service.py`. Scrubbed 23 occurrences of "NexaBI" branding contamination across 14 backend and frontend files, standardizing on DataSpeakAI (`DataSpeakDashboard`, `DATASPEAK_THEME`, `DataSpeakAI Analytics Hub`, `dataspeak.*` loggers). Added missing `description` column to `DatabaseConnection` in `backend/models.py` aligning ORM with `db_migration.py`, and completed wire-up across `add_database()` in `backend/routers/databases.py` and listing/get/update responses in `backend/routers/connections.py`. Harmonized `GEMINI_MODEL` environment variable support in `backend/services/llm_generation_service.py`, fixing model prioritization and deduplication. Pruned 4 dead/orphan service files (`pipeline_service.py`, `file_service.py`, `relationship_detector.py`, `security_service.py`) removing 581 lines of dead code. Relocated root sample CSV `covid19_healthcare_hospital_analytics.csv` to `tests/fixtures/`. Generalized `scripts/run_audit_mongo_business.py` with CLI arguments (`--data-path`, `--output-dir`), safe optional `mongomock` import, and proper error exit codes. Added 7 automated regression tests in `tests/test_fix_commit_issues_regression.py` reaching 327/327 passing tests (0 failures) and verified 0-error Vite frontend build.

- [x] **Phase 1.6 & 1.6.1: Source-Aware Discovery, Adaptive Visualizations Studio & Tabular Introspection Hardening**
  - *Completed:* 2026-10-02 | Antigravity AI Orchestrator & Visualization Specialist
  - *Summary:* Discovered database and document source archetypes (relational time-series, categorical SQL, tabular spreadsheets, document knowledge bases); built automated source profiler in `source_profiler.py` and adaptive recommendation engine in `adaptive_chart_recommender.py` (Line/Area for time-series, Donut/Bar for categorical data, Scatter for multi-metric correlations, density/modality charts for documents); added unified endpoints `GET /api/analytics/sources`, `GET /sources/{type}/{id}/discover`, `GET /sources/{type}/{id}/dashboard`, `POST /sources/{type}/{id}/query` in `analytics.py`; upgraded `AnalyticsHeader.tsx` with grouped sources; created `SourceArchetypeBanner.tsx` with referral pills; wired `LiveExplorerCanvas.tsx` with recommendation star indicators. Resolved HTML table chunk parsing in `source_profiler.py` via BeautifulSoup, accurately detecting 18 measures, 4 dimensions, and 4 time axes on `client_data.csv`. Hardened `LiveExplorerCanvas.tsx` to render an elegant glass empty state instead of collapsing to `null`. Added "Auto" mode to `AISynthesizedGrid.tsx` preserving diverse chart types (Bar, Donut, Line). Added unit tests in `test_source_profiler.py` and `test_adaptive_chart_recommender.py`; full regression reached 320 passing tests with 0 failures and frontend build passed with 0 errors across 2,763 modules.

- [x] **Task 1.2 — Analytics & Visualization Page: Full Frontend Overhaul & Domain Mapping Wizard**
  - *Completed:* 2026-09-24 | Antigravity AI Engineer
  - *Summary:* Removed all static mock arrays (`queryTrendsData`, `topTablesData`, `databaseDistribution`, `dataGrowthData`). Decomposed 863-line AnalyticsPage.tsx monolith into 9 focused components: `ChartRenderer`, `AnalyticsHeader`, `KpiSummaryStrip`, `LiveExplorerCanvas`, `AISynthesizedGrid`, `DomainSetupBanner`, `SchemaHealthPanel`, `AIInsightsSummaryCard`, `DomainMappingWizard`. Added 3-step guided Domain Mapping Wizard surfacing `/domains`, `/suggest-mapping`, `/apply-mapping` endpoints. Added inline AI Insights card and Schema Health panel. Build: ✓ 2762 modules, 0 errors.

- [x] **Phase 2F & 2F.1: Deterministic Dashboard Layout & Composition Engine**
  - *Completed:* 2026-09-23 | Antigravity AI Engineer
  - *Summary:* Built deterministic layout and composition engine in `dashboard_layout_engine.py` composing `MetricRecipe[]`, `ChartRecommendation[]`, and `Mapping[metric_id, FilterRecommendationResult]` into 12-column grid `DashboardLayoutPlan` (KPI card span=3, chart span=6); strictly enforced single-table composition boundary rejecting multi-table and cross-table references; added Phase 2F.1 defense-in-depth guard strictly rejecting non-KPI chart recommendations for derived recipes (`RatioMetricRecipe`, `DifferenceMetricRecipe`); added 34 unit and safety tests in `test_phase2f_dashboard_layout_engine.py`; full regression reached 309 passing tests with 0 failures and 0 Pyright errors.

- [x] **Phase 2E: Deterministic Filter Recommendation Engine**
  - *Completed:* 2026-09-23 | Antigravity AI Engineer
  - *Summary:* Built deterministic, execution-free filter recommendation engine in `filter_recommender.py` recommending `date_range` and `select` (IN) filters based on SchemaRegistry metadata and confirmed column references; enabled filter support for derived recipes (AOV, Gross Profit); enforced identifier protection and cardinality boundaries (2..50); added 30 tests in `test_phase2e_filter_recommender.py`; full regression reached 275 passing tests with 0 failures and 0 Pyright errors.

- [x] **Phase 2D: Deterministic Chart Recommendation Engine**
  - *Completed:* 2026-09-23 | Antigravity AI Engineer
  - *Summary:* Built deterministic, execution-free chart recommendation engine in `chart_recommender.py` recommending `KPI`, `Line`, and `Bar` charts based on confirmed grouping context and SchemaRegistry; enforced scalar-only `KPI` for derived recipes (Ratio/Difference); rejected cross-table and unqualified groupings; added 27 tests in `test_phase2d_chart_recommender.py`; full regression reached 245 passing tests with 0 failures and 0 Pyright errors.

- [x] **Phase 2C.1: Derived Execution Boundary Hardening**
  - *Completed:* 2026-09-23 | Antigravity AI Engineer
  - *Summary:* Hardened `derived_metric_executor.py` against cross-table runtime filters (`customers.region` on `orders` recipes) and unqualified filters; enforced strict finite numeric checks (`math.isfinite()`) and arithmetic overflow protection preventing `NaN`/`+inf`/`-inf` from composition; added 15 focused tests in `test_phase2c1_execution_boundary.py`; full regression reached 218 passing tests with 0 failures and 0 Pyright errors.

- [x] **Phase 2C: Deterministic Metric Recipe Executor**
  - *Completed:* 2026-09-23 | Antigravity AI Engineer
  - *Summary:* Built `execute_metric_recipe()` in `derived_metric_executor.py` executing Atomic, Ratio, and Difference recipes strictly via `MetricExecutor` with zero raw SQL, joins, or eval; safe ratio division (`status="undefined", value=None` on zero denominator) and missing data handling without fabricating zero; added 29 tests in `test_phase2c_derived_metric_executor.py`.

- [x] **Phase 2B.2: Template Formula Fidelity Guard**
  - *Completed:* 2026-09-23 | Antigravity AI Engineer
  - *Summary:* Enforced 3-way metadata agreement between `formula_template`, `aggregation`, and `required_variables`; implemented `_SIMPLE_ATOMIC_FORMULA_RE` to reject formulas with filters, arithmetic, or multiple variables; converted mismatched/deferred formulas into structured `SkippedMetric` instances; verified 174/174 tests passing.

- [x] **Phase 2B.1: Semantic Substitution Removal & Domain Template Alignment**
  - *Completed:* 2026-09-23 | Antigravity AI Engineer
  - *Summary:* Purged all concept substitution fallbacks (`mrr -> revenue`); aligned atomic KPI rules directly with `domain_templates.py`; preserved canonical `aov` metric ID; added filter-required guard skipping `active_subscriptions`; verified 159/159 tests passing.

- [x] **Phase 2B: Deterministic KPI Metric Recipe Generator**
  - *Completed:* 2026-09-23 | Antigravity AI Engineer
  - *Summary:* Created `metric_recipe_generator.py` converting confirmed semantic mappings into typed MetricRecipes via deterministic rules with zero LLM dependence; enforced zero column inference and zero fuzzy matching; integrated Phase 2A schema validation; verified 147/147 tests passing.

- [x] **Phase 2A: Typed Metric Recipe Contract**
  - *Completed:* 2026-09-23 | Antigravity AI Engineer
  - *Summary:* Defined typed Pydantic contracts for Atomic, Ratio, and Difference metric recipes in `metric_recipes.py` rejecting arbitrary SQL/formula fields; enforced canonical aggregation whitelist; added schema-aware and connection-aware validation helpers; verified 126/126 tests passing.

- [x] **Phase 1.5D.2: Atomic Regeneration Safety & Dimension Enforcement**
  - *Completed:* 2026-09-23 | Antigravity AI Engineer
  - *Summary:* Fixed zero-valid regeneration dashboard wipeout risk by validating in-memory before deletion; unified KPI + layout replacement in a single atomic transaction with rollback; rejected cross-table dimensions pending relationship engine; enforced tenant connection ownership defense; verified 105/105 tests passing.


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
