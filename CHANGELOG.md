# DataSpeakAI Changelog

All notable changes to the DataSpeakAI project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## Session Logging Guidelines

To maintain seamless multi-developer and AI agent collaboration:
1. **Work Session Logs**: For any major session, architectural change, or multi-agent handoff, create a session log file under `docs/sessions/` using the naming format `YYYY-MM-DD_<topic>.md` (see `docs/sessions/README.md` for standard structure).
2. **Updating `CHANGELOG.md`**: When completing features, bug fixes, or structural changes, add a summary under the `[Unreleased]` section of this file. When releasing a milestone, summarize all unreleased items under a new version header (e.g. `[v0.3.0] - YYYY-MM-DD`).
3. **Traceability**: Reference specific session logs in `docs/sessions/` or handoff reports in `.agents/` when logging major updates.

---

## [Unreleased]

- **Phase 7: Next-Generation AI Intelligence Architecture & Roadmap Established (`docs/architecture/ai_features_phase7_implementation_plan.md`, `todo.md`)**:
  - **Added (Comprehensive Architecture Audit & Roadmap Formulation):** Formulated an 8-sub-phase (7A–7H, 28 engineering tasks) implementation roadmap establishing the transition of DataSpeakAI from MVP to an enterprise-grade AI analytics and intelligence platform.
  - **Phase 7A (Unified LLM Gateway & Hardening - P0):** Consolidated LLM generation services into a unified gateway with thread-safe multi-key rotation (Gemini + Groq), true token-level SSE streaming (<500ms TTFT), conversation sliding-window memory with auto-summarization, and per-dialect statement timeout guards (PostgreSQL, MySQL, SQLite).
  - **Phase 7D (Real-Time Bidirectional Chat & RLHF Feedback - P0):** Architected `/ws/chat/{conversation_id}` WebSocket channel for live token streaming and mid-stream cancellation, lightweight dynamic title generation, and user feedback datastore (`MessageFeedback`).
  - **Phase 7B (Advanced RAG 2.0 & Hierarchical Intelligence - P1):** Designed context-aware semantic boundary chunking, hierarchical parent-child document modeling (`DocumentNode`), multi-vector retrieval with contextual compression, dual-index embedding upgrade (`BAAI/bge-m3`), and verifiable citation provenance.
  - **Phase 7C (Agentic NL-to-SQL 2.0 & Multi-Turn Refinement - P1):** Designed self-correcting SQL execution agent with AST safety guards and `EXPLAIN` query plan dry-runs, contextual schema starter suggestions, and plain English SQL explanations.
  - **Phase 7E (Predictive Analytics & Anomaly Detection - P2):** Formulated multi-model time-series forecasting (MAPE-driven auto-selection), real-time statistical anomaly detection, and automated scheduled intelligence sweeps.
  - **Phase 7F (AI-Powered Data Quality & Governance - P2):** Designed automated 0–100 Data Quality Index (DQI) profiler, actionable SQL cleaning recommendations, and end-to-end column lineage graphing.
  - **Phase 7G (Multimodal Analytics & Voice Interface - P3):** Designed Gemini Vision chart screenshot analysis, natural language to Recharts configuration generator, and Whisper voice query transcription.
  - **Phase 7H (Embeddable Copilot SDK & Plugins - P3):** Designed public REST API query endpoint (`POST /api/v1/query`), asynchronous webhook event dispatcher, and dynamic AI model plugin registry.

- **Phase 5: Entity-Relationship Diagram (ERD) & Schema Relationships (`backend/routers/erd.py`, `backend/services/erd_service.py`, `backend/models.py`, `backend/schemas.py`, `backend/services/db_migration.py`, `src/app/pages/dashboard/DatabaseErdPage.tsx`, `src/app/components/erd/TableNode.tsx`, `src/app/components/erd/TableDetailsDrawer.tsx`, `src/app/utils/erdTransform.ts`, `src/app/utils/erdLayout.ts`, `tests/test_phase5_erd_backend.py`, `src/app/utils/erdTransformAndLayout.test.ts`)**:
  - **Added (Catalog-First ERD Endpoint & Bulk Reflection - D1, D2, D3):** Implemented `GET /api/databases/{id}/erd` in `backend/routers/erd.py` and `backend/services/erd_service.py`. Reflects schemas via SQLAlchemy 2.0 bulk inspection (`get_multi_columns`, `get_multi_pk_constraint`, `get_multi_foreign_keys`) with per-table fallback. Caches reflected metadata and constraint-level foreign keys in `DatabaseSchema`, `TableMetadata`, `ColumnMetadata`, and `TableRelationship` in a single atomic transaction.
  - **Added (Heuristic Relationship Inference):** Implemented name-based foreign key inference (`include_inferred=true`) matching single-column primary keys with confidence scores and explainable rationale, skipping ambiguous matches and generic column names.
  - **Added (React Flow Interactive ERD Canvas - D8):** Implemented interactive diagram visualization at `/dashboard/databases/:id/erd` using `@xyflow/react` v12 and `@dagrejs/dagre`, loaded via React Router v7 `lazy`. Features custom `TableNode` components, inspection side drawer (`TableDetailsDrawer`), live table search with viewport centering, PK/FK column filter, layout direction switching (LR/TB), auto-layout reset, and `localStorage` position persistence.
  - **Added (Large Schema Performance Optimization):** Integrated automatic viewport virtualization (`onlyRenderVisibleElements={true}`) and compact node headers for schemas exceeding 60 tables, maintaining 60+ FPS panning.
  - **Security (SSRF Prevention & Host Blocklist - D5):** Enforced IP validation on database connection hostnames, blocking loopback (`127.0.0.0/8`), link-local (`169.254.0.0/16`), and private RFC 1918 ranges unless `ALLOW_PRIVATE_DB_HOSTS=true`. Converted SQLite path resolution to strictly confined checks rejecting traversal tokens (`..`).
  - **Security (Tenant Scoping & DoS Refresh Cooldown - D6, D7):** Database access is tenant-isolated with HTTP 404 on cross-tenant access. Added per-tenant, per-database refresh rate limiting (`ERD_REFRESH_COOLDOWN_SECONDS`, default 30s) returning HTTP 429 with `Retry-After`.
  - **Security (Credential Redaction & Dialect Enforcement - D4):** Sanitized reflection exceptions to prevent leakage of connection strings, hosts, usernames, or passwords. Rejects non-relational document databases (MongoDB, Firebase) with HTTP 400.
  - **Added (Comprehensive Test Suites):** Authored 16 backend test cases in `tests/test_phase5_erd_backend.py` covering composite/self/dangling FKs, SQL injection-style table names, host blocklists, bracketed IPv6 SSRF protection, URL password encoding, inferred hardening, tenant isolation, and mocked PostgreSQL/MySQL reflection ("no live server used"). Added 9 frontend Vitest unit tests in `src/app/utils/erdTransformAndLayout.test.ts`.
  - **Fixed (QA Hardening & Robustness Package):**
    - Blocked SSRF loopback bypass via bracketed IPv6 literals (e.g. `[::1]`) in `validate_db_host_security`.
    - Protected `build_erd_connection_url` against connection string crashes on passwords/usernames containing `@`, `:`, or `#` using `urllib.parse.quote_plus`.
    - Hardened heuristic relationship inference in `detect_inferred_relationships` with robust English plural suffix rules and strict `_id` / camelCase `Id` boundaries, eliminating false positive matches (such as `invoices.paid` -> `pass.id`) while correctly resolving `users.address_id` -> `addresses.id`.
    - Resolved cache miss on empty databases in `load_erd_from_catalog` so schemas with 0 tables are served as `source="catalog"`.
    - Preserved canvas pan/zoom state across filter toggles ("PK/FK Only", "Inferred", layout options) by gating `fitView` to initial load and explicit layout resets.
    - Added vertical handle routing (`sourceHandle="bottom"`, `targetHandle="top"`) for Top-to-Bottom ("TB") layout direction in `erdTransform.ts` and `TableNode.tsx`.

- **Phase 4 QA Remediation Package (`backend/services/sql_engine.py`, `backend/models.py`, `backend/schemas.py`, `backend/services/db_migration.py`, `backend/routers/query.py`, `backend/routers/users.py`, `docs/database/Full_Project_Schemas.sql`, `tests/test_phase4_enterprise_schema_regression.py`)**:
  - **Fixed (ISSUE-01 Catalog Re-sync Column Multiplication):** Resolved SQLite orphaned column accumulation by explicitly purging child `ColumnMetadata` rows prior to deleting `TableMetadata` and calling `db_session.expunge_all()`.
  - **Fixed (ISSUE-02 Persistent Relational Context Loss):** Extended `ColumnMetadata` and `ColumnMetadataResponse` with `is_primary_key`, `is_foreign_key`, and `foreign_key_target`. Populated them in `sync_database_catalog()` and formatted `[PRIMARY KEY]`, `[FOREIGN KEY -> target.col]`, and `[PII]` in persistent schema prompt context in `get_db_schema_context()`, eliminating relational context stripping when querying via cached schema.
  - **Fixed (ISSUE-03 Canonical SQL & Migration Parity):** Unified `executed_queries` in `Full_Project_Schemas.sql` to include `tenant_id`, `user_id`, `database_id`, `raw_query`, `status`, `error_message`, and `executed_at`, plus canonical timestamps across Phase 4 tables. Added automated zero-dependency migrations in `db_migration.py` ensuring pre-existing databases auto-migrate without `OperationalError`.
  - **Fixed (ISSUE-04 Structured Telemetry Exception Logging):** Added `logger.exception()` in `backend/routers/query.py` inside `log_query()` to prevent silent suppression of query audit persistence failures.
  - **Fixed (ISSUE-05 User Registration RBAC Lifecycle):** Updated `register_user()` in `backend/routers/users.py` to auto-initialize default `TenantSettings` and `Membership` (`is_owner=True`) records linked to the matching `Role` upon new tenant creation.
  - **Added (ISSUE-06 Real Cascade Deletion & Hardened Regression Tests):** Expanded `test_phase4_enterprise_schema_regression.py` to 6 comprehensive tests, including true ORM cascade deletion across tenants, roles, collections, dashboards, and subscriptions, catalog re-sync deduplication, and user registration RBAC lifecycle.
  - **Fixed (ISSUE-07 Documentation & Handoff Alignment):** Corrected documentation and handoff discrepancies regarding the 1-to-many `Permission.role_id` foreign key and canonical table count (45 total registered tables).

- **Phase 4: Enterprise Database Schema Expansion (`backend/models.py`, `backend/schemas.py`, `backend/services/sql_engine.py`, `backend/routers/query.py`, `backend/scripts/seed_admin.py`, `backend/services/db_migration.py`, `tests/test_phase4_stage_a_regression.py`, `tests/test_phase4_stage_b_regression.py`, `tests/test_phase4_enterprise_schema_regression.py`)**:
  - **Added (Canonical Schema Parity & 24 Enterprise ORM Models):** Expanded backend architecture to 100% parity with `Full_Project_Schemas.sql` (all 35 canonical enterprise tables):
    - *Stage 4A (RBAC & Persistent Schema Catalog):* `TenantSettings`, `Role`, `Permission`, `role_permissions` (M2M association), `Membership`, `Secret`, `DatabaseSchema`, `TableMetadata`, `ColumnMetadata`. Added relationships on `Tenant`, `User`, and `DatabaseConnection`.
    - *Stage 4B (Query Safety & Vector Registry):* `QueryTemplate`, `ExecutedQuery` (expanded with `message_id`, `was_successful`, safety relationships), `QuerySafetyLog`, `Intent`, `Collection`, and `VectorRecord`.
    - *Stage 4C (Custom Dashboards, Billing & Security):* `Dashboard`, `Widget`, `Subscription`, `Invoice`, `Payment`, `MeteredUsage`, `RateLimit`, `SecurityPolicy`, `AuditLog`, and `SystemMetric`.
  - **Added (Pydantic V2 Contract Schemas):** Added Pydantic V2 models (`ConfigDict(from_attributes=True)`) in `backend/schemas.py` for all 24 new entities spanning role management, membership assignment, secrets, schema catalog, query safety, collections, dashboard widgets, billing/invoices, and security policies.
  - **Added (Persistent Schema Catalog Caching & Automated PII Detection):** Built `sync_database_catalog()` in `backend/services/sql_engine.py` introspecting database tables, column types, and foreign keys into `DatabaseSchema`, `TableMetadata`, and `ColumnMetadata`. Integrated automatic regex PII detection (`is_pii=True`) on sensitive patterns (`email`, `ssn`, `password`, `phone`, `card`, `address`, `dob`). Wired persistent catalog caching into `get_db_schema_context()` eliminating redundant live introspection overhead.
  - **Added (Query Execution & AST Safety Logging):** Wired `ExecutedQuery` and `QuerySafetyLog` persistence into `POST /api/query` in `backend/routers/query.py`, logging query latency, rows returned, error messages, and security violation details.
  - **Added (Startup RBAC Seeding):** Enhanced `backend/scripts/seed_admin.py` to auto-seed default `TenantSettings`, 4 standard roles (`Admin`, `Developer`, `Business Owner`, `Viewer`) with granular action permissions, and link superadmin membership on startup with full idempotency.
  - **Architecture (Strict Backward Compatibility):** Preserved legacy columns `User.role` and `User.tenant_id` to guarantee zero breaking changes across existing authentication, permissions, and frontend dashboard views.
  - **Added (Automated Regression Test Suites):** Authored 14 comprehensive tests across `tests/test_phase4_stage_a_regression.py` (6 tests), `tests/test_phase4_stage_b_regression.py` (4 tests), and `tests/test_phase4_enterprise_schema_regression.py` (4 tests), verifying full 35-table SQLite schema creation, foreign key cascade lifecycles, catalog caching, and RBAC memberships. Frontend production build passes with 0 errors (2,772 modules).

- **Phase 3 QA & Security Hardening: AI Insights Remediation (`backend/routers/insights.py`, `backend/services/insights_engine.py`, `backend/schemas.py`, `src/app/pages/dashboard/AIInsightsPage.tsx`, `src/app/pages/dashboard/LogsPage.tsx`, `tests/test_phase3_ai_insights_regression.py`)**:
  - **Security (SEC-01 Cross-Tenant Database IDOR Remediation):** Added strict tenant verification (`models.DatabaseConnection.tenant_id == current_user.tenant_id`) for `database_id` query filters and refresh targets in `GET /api/insights` and `POST /api/insights/refresh`, returning `404 Not Found` if a database belongs to a different tenant. Resolved N+1 query overhead using eager relationship loading (`joinedload`, `selectinload`).
  - **Security (SEC-02 Recommendation ID Enumeration Defense):** Replaced divergent 403 Forbidden vs 404 Not Found responses in `PUT /api/insights/recommendations/{id}/status` with uniform `404 Not Found` across missing and cross-tenant recommendations via strict join on `models.GeneratedInsight.tenant_id == current_user.tenant_id`.
  - **Fixed (BUG-01 Child Recommendation Orphan Purging):** Fixed accumulation of orphaned `Recommendation` rows during insight refreshes in SQLite by explicitly purging child recommendations prior to deleting parent `GeneratedInsight` entities, eliminating SQLAlchemy stale identity warnings and subsequent 500 `AttributeError` on status mutation.
  - **Fixed (BUG-02 Resilient LLM Score Parsing):** Implemented `_safe_float()` helper in `backend/services/insights_engine.py` converting percentage strings (e.g., `"92%"`), invalid string bounds, and non-numeric representations safely, while filtering out non-dict responses from LLM JSON outputs. Added exception handling around insight refresh persistence with deterministic zero-hallucination fallback.
  - **Fixed (UI-01 Pending Actions KPI Synchronization):** Updated `handleToggleRecommendation` in `AIInsightsPage.tsx` to optimistically increment or decrement the executive `summary.pending_actions_count` KPI immediately upon completing or reopening a recommendation task.
  - **Fixed (INT-01 Logs Deep-Link Query Parameter Recognition):** Integrated `useSearchParams` in `LogsPage.tsx` to read the initial `?status=` parameter from the URL, enabling direct deep-linking from AI Insights (e.g. `/dashboard/logs?status=failed`) to automatically filter to failed audit logs.
  - **Refactored (NIT-01 Pydantic V2 Config Migration):** Upgraded `RecommendationItem` and `GeneratedInsightItem` in `backend/schemas.py` from deprecated class-based `Config` to Pydantic V2 `model_config = ConfigDict(from_attributes=True)`.
  - **Added (Extended Regression Tests):** Expanded `tests/test_phase3_ai_insights_regression.py` to 12 comprehensive test cases, covering orphaned recommendation cascades, malformed LLM scores, cross-tenant database filters, and uniform 404 security boundaries. Verified 100% full regression pass rate across the entire test suite (**382/382 passed, 0 failures**).

- **Phase 3: Dynamic AI Insights & Recommendation Engine (`backend/models.py`, `backend/schemas.py`, `backend/services/db_migration.py`, `backend/services/insights_engine.py`, `backend/routers/insights.py`, `src/app/pages/dashboard/AIInsightsPage.tsx`, `tests/test_phase3_ai_insights_regression.py`)**:
  - **Added (ORM Models & Migrations):** Implemented `GeneratedInsight` and `Recommendation` SQLAlchemy models in `backend/models.py` with foreign key links to `tenants.id` and `database_connections.id`, cascade deletion, severity classifications (`critical`, `warning`, `alert`, `opportunity`), confidence scoring, and interactive status tracking (`active`, `dismissed`, `actioned`, `pending`, `completed`). Registered idempotent auto-migrations in `backend/services/db_migration.py` ensuring cross-database schema synchronization across SQLite and PostgreSQL on startup.
  - **Added (Pydantic Contracts):** Defined structured schemas in `backend/schemas.py` (`RecommendationItem`, `RecommendationStatusUpdate`, `GeneratedInsightItem`, `GeneratedInsightStatusUpdate`, `AIInsightsOverviewResponse`, `AIInsightsRefreshResponse`).
  - **Added (Insights Engine Worker):** Created `InsightsEngine` in `backend/services/insights_engine.py` collecting genuine telemetry (query counts, error rates, average latency, slowest queries, top failure errors, introspected tables, and indexed documents), detecting deterministic statistical anomalies (error rate spikes, latency bottlenecks, unprofiled databases, empty knowledge base), and synthesizing structured business insights using Google Gemini 2.5 Flash via `llm_generation_service` with Groq failover and deterministic zero-hallucination fallback.
  - **Added (REST Router Endpoints):** Mounted Phase 3 routes on `backend/routers/insights.py` including `GET /api/insights` (overview KPIs, category filtering, severity filtering, database scoping, dismissed visibility), `POST /api/insights/refresh` (synchronous analysis and atomic persistence), `PUT /api/insights/{id}/status` (insight dismissal/restoration), and `PUT /api/insights/recommendations/{id}/status` (recommendation task completion) with strict tenant ownership validation.
  - **Changed (AI Insights Command Center UI):** Fully overhauled `AIInsightsPage.tsx` from static prototypes into a live interactive command center featuring an executive KPI strip (Active Insights, Critical/Warnings, Growth Opportunities, Pending Actions), category tabs (`All`, `Revenue`, `Performance`, `Customer Success`, `Operational`), severity badges, interactive task completion toggles with visual strikethrough, insight dismissal/restore controls, contextual navigation deep-links (`/dashboard/logs`, `/dashboard/databases`), database scoping dropdown, and truthful cold-start onboarding states.
  - **Added (Automated Regression Testing):** Authored 10 dedicated regression tests in `tests/test_phase3_ai_insights_regression.py` validating schema cascades, telemetry calculations, anomaly rules, fallback synthesis, API endpoints, status mutations, and strict multi-tenant isolation. Full automated test suite reaches **380/380 passing tests (0 failures)** with a 0-error Vite frontend production build (2,772 modules).

- **Phase 2: Embeddable Standalone Chatbot Widget & Security QA Hardening**:
  - **Added:**
    - Embeddable widget standalone Preact IIFE bundle (`dist/widget.js`, 32.92 kB uncompressed, 12.10 kB gzipped) mounted strictly inside an open Shadow DOM root with pixel-pinned styles.
    - Publishable keys architecture (`pk_live_...`) with origin allowlisting, 24-hour key rotation grace periods, and per-key monthly message caps.
    - Browser HMAC sessions via `POST /api/widget/session` returning short-lived HMAC-SHA256 session tokens binding `tenant_id`, `origin`, and `conversation_id`.
    - Script serving endpoint `GET /widget.js` with priority resolution (`dist/` → `public/` → `backend/static/`) and fallback iframe embed routes `GET /embed/{public_key}`.
    - Shadow DOM UI with accessible keyboard controls, 56×56 px launcher button, escape key listener, auto-focus management, and screen-reader `aria-hidden` attributes.
    - Dashboard key management in `src/app/pages/dashboard/ChatbotWidgetPage.tsx` with live preview, origin allowlist editing, key rotation, revocation/disabling, and key deletion with confirmation modals and Sonner toasts.
  - **Security:**
    - Strict origin allowlist enforcement on handshake and subsequent chat requests.
    - Fail-closed SQL validation using `sqlglot` AST parsing, completely eliminating regex fallbacks on the widget path.
    - Exact schema-qualified table allowlist matching (removed `tbl.split('.')[-1]` matching) preventing unauthorized schema bypasses.
    - `TRUSTED_PROXIES` allowlist enforcement for client IP resolution; untrusted client `X-Forwarded-For` spoofing rejected.
    - Fail-closed dialect guardrails per database engine: PostgreSQL uses connect options (`-c default_transaction_read_only=on -c statement_timeout=10000`), MySQL uses session read-only and query limits, and SQLite uses dedicated connections with `NullPool` preventing `PRAGMA query_only = ON` leakage.
    - Strict origin regex validation (`^https?://[A-Za-z0-9.-]+(?::[0-9]{1,5})?$`) on key creation and update; frame-ancestors header suppressed if any stored origin fails validation.
    - Per-key monthly message cap enforcement with `widget_key_id` tracking in `QueryLog` and composite database index `(widget_key_id, created_at)`.
    - CSP-safe styling using `shadowRoot.adoptedStyleSheets` with `CSSStyleSheet.replaceSync()` and CSSOM `element.style.setProperty()`, allowing full operation under strict CSP without `style-src 'unsafe-inline'`.
    - Concurrency stream slot TTL (120s) with refresh, plus disconnect/exception cleanup handlers preventing slot exhaustion.
    - Idle rate-limiter bucket eviction (`cleanup_idle_buckets(ttl_seconds=600)`) preventing memory leaks.
  - **Streaming & Verification Notes:**
    - *SSE Implementation Note:* Current SSE streaming sends the answer in chunks after full generation (post-generation chunking; TTFT approximates total generation latency). True token-level LLM streaming is tracked as a separate backlog item.
    - *Verification Scope Note:* PostgreSQL, MySQL and Redis paths were verified with mocks/unit tests only, not against live servers. Full test suite: 375 passed, 45 warnings on `.\backend\venv\Scripts\pytest.exe tests/`.

- **Phase 1: Live Frontend-to-Backend Dashboard Wiring & QA Hardening (`backend/routers/analytics.py`, `backend/schemas.py`, `backend/models.py`, `backend/services/db_migration.py`, `backend/main.py`, `src/app/pages/dashboard/DashboardOverview.tsx`, `src/app/pages/dashboard/LogsPage.tsx`, `src/app/pages/dashboard/UsagePage.tsx`, `src/app/pages/admin/AdminPanel.tsx`, `tests/test_phase1_dashboard_wiring_regression.py`)**:
  - **Added (P0 Backend Core Dashboard Endpoints):** Restored and hardened 6 essential dashboard endpoints in [`backend/routers/analytics.py`](file:///d:/dataspeak/backend/routers/analytics.py) and mounted via dual route registration on `router` and `core_router` in [`backend/main.py`](file:///d:/dataspeak/backend/main.py):
    - `GET /api/analytics/overview` (and `/api/overview` alias): Real-time tenant KPI counts, 7-day query timeline, connected database activity summary, and recent query execution logs.
    - `GET /api/logs`: Query audit logs with pagination (`page`, `limit`), status filtering (`success`, `failed`, `all`), database selector, search query matching, and aggregate statistics (`success_rate`, `avg_response_time_ms`).
    - `GET /api/logs/export`: Server-side streaming endpoint streaming filtered query logs directly as a chunked CSV attachment (`yield_per(500)`) with formula injection defense.
    - `GET /api/usage`: Tenant token consumption meters, period-selected timelines (`24h`, `7d`, `30d`, `90d`) optimized with single SQL `func.date()` grouping, database type distribution, and bounded hourly query patterns.
    - `GET /api/admin/stats` & `GET /api/admin/tenants`: Platform-wide tenant metrics with week-over-week growth calculations, 7-day platform query timeline, database counts, real admin emails, and tenant administration table reading persisted subscription plans.
  - **Security (CSV Formula Injection Sanitization):** Neutralized spreadsheet formula execution triggers (`=`, `+`, `-`, `@`, `\t`, `\r`) in query log CSV export by prepending a single quote (`'`), preventing formula execution in Microsoft Excel and LibreOffice Calc.
  - **Performance (Usage Aggregation & Streaming):** Replaced 90-iteration Python querying loop in `get_tenant_usage` with a single SQL `GROUP BY func.date(created_at)` query; bounded hourly query distribution by period cutoff; converted CSV export from monolithic in-memory string accumulation to generator chunked streaming (`yield_per(500)`).
  - **Architecture & Route Aliasing:** Fixed FastAPI duplicate operation ID warning by mounting `/overview` on `core_router` as a clean alias to `/api/analytics/overview`.
  - **Data Integrity & Schema Sync:** Added `plan` column to `Tenant` model in [`backend/models.py`](file:///d:/dataspeak/backend/models.py) and updated [`backend/services/db_migration.py`](file:///d:/dataspeak/backend/services/db_migration.py) to automatically apply schema sync across SQLite and PostgreSQL on startup.
  - **Added (P0 Pydantic Contracts):** Defined structured Pydantic schemas in [`backend/schemas.py`](file:///d:/dataspeak/backend/schemas.py) (`AnalyticsOverviewResponse`, `QueryLogsResponse`, `QueryLogItem`, `TenantUsageResponse`, `AdminStatsResponse`, `AdminTenantItem`) enforcing response validation.
  - **Changed (P0 Dashboard Overview Wiring):** Replaced hardcoded static mock constants in [`DashboardOverview.tsx`](file:///d:/dataspeak/src/app/pages/dashboard/DashboardOverview.tsx) with live API state, animated skeleton loaders, Sonner toast feedback, and truthful empty-state onboarding banners with actionable CTAs (`Connect Database`, `Upload Document`, `Start First Chat`).
  - **Changed (P0 Query Logs Wiring):** Connected [`LogsPage.tsx`](file:///d:/dataspeak/src/app/pages/dashboard/LogsPage.tsx) to live logs API, wiring search inputs, status filters, database dropdowns, pagination controls, delayed blob URL revocation to prevent download aborts, and one-click authenticated CSV export.
  - **Changed (P0 Usage & Metering Wiring):** Connected [`UsagePage.tsx`](file:///d:/dataspeak/src/app/pages/dashboard/UsagePage.tsx) to live usage API, supporting period switching (`24h`, `7d`, `30d`, `90d`), token limits meter, database type breakdown pie chart, and hourly activity pattern chart.
  - **Changed (P0 Admin Panel Wiring):** Connected [`AdminPanel.tsx`](file:///d:/dataspeak/src/app/pages/admin/AdminPanel.tsx) to live admin stats, 7-day platform activity curve (`platform_activity`), system health indicators, and registered tenant roster with search filtering and enforced Admin role gating.
  - **Added (Tests):** Authored 9 automated regression tests in [`tests/test_phase1_dashboard_wiring_regression.py`](file:///d:/dataspeak/tests/test_phase1_dashboard_wiring_regression.py) verifying overview metrics, log pagination, status/search filtering, CSV streaming, formula injection defense, route aliasing, admin platform activity, usage timelines, role gating, and tenant data isolation; test suite reached 336/336 passing tests (0 failures) and verified 0-error Vite frontend build.


- **Recent Commits Remediation & Codebase Hygiene Hardening (`backend/main.py`, `backend/requirements.txt`, `backend/models.py`, `backend/services/`, `src/app/`, `scripts/run_audit_mongo_business.py`, `tests/`)**:
  - **Fixed (P0 Router Regression):** Re-mounted `analytics.router` on the FastAPI application in [`backend/main.py`](file:///d:/dataspeak/backend/main.py), immediately resolving 29 broken `/api/analytics/*` test failures and restoring all 17 analytics routes.
  - **Added (P0 Dependencies):** Added `scikit-learn` and `xgboost` to [`backend/requirements.txt`](file:///d:/dataspeak/backend/requirements.txt), eliminating build/import crashes in `backend/services/automl_service.py` on fresh environments.
  - **Fixed (P1 Branding Hygiene):** Thoroughly purged 23 occurrences of ported "NexaBI" branding across 14 backend and frontend files: standardized logger names to `dataspeak.*`, updated LLM prompt personas to DataSpeakAI, renamed React component to `DataSpeakDashboard` and theme to `DATASPEAK_THEME` in `ECommerceTemplate.tsx`, and updated UI labels in `CsvAnalyticsPage.tsx` and `BusinessInsightsPage.tsx`. Verified with automated regex scan.
  - **Fixed (P1 ORM Schema Alignment & Route Wire-Up):** Added missing `description` column to `DatabaseConnection` in [`backend/models.py`](file:///d:/dataspeak/backend/models.py), aligning ORM definition with `services/db_migration.py` and `schemas.py`. Hardened [`backend/routers/databases.py`](file:///d:/dataspeak/backend/routers/databases.py) to persist `description`, `port`, and `connection_string` in `add_database()`, and included `description` in connection listing, detail, and update payloads in [`backend/routers/connections.py`](file:///d:/dataspeak/backend/routers/connections.py).
  - **Fixed (P1 LLM Model Configuration):** Harmonized `GEMINI_MODEL` environment variable support in [`backend/services/llm_generation_service.py`](file:///d:/dataspeak/backend/services/llm_generation_service.py), fixing prioritization logic so models existing in default lists are promoted to the front, deduplicating fallback chains, and respecting `GEMINI_MODEL` in multimodal generation.
  - **Removed (P1 Dead Code):** Deleted 4 orphan service files with 0 callers across the repository (`pipeline_service.py`, `file_service.py`, `relationship_detector.py`, `security_service.py`), eliminating ~581 lines of unreferenced code.
  - **Changed (P2 Repository Structure):** Relocated root sample CSV `covid19_healthcare_hospital_analytics.csv` into `tests/fixtures/`.
  - **Changed (P2 Script Portability & Robustness):** Generalized [`scripts/run_audit_mongo_business.py`](file:///d:/dataspeak/scripts/run_audit_mongo_business.py) with CLI argument parsing (`--data-path`, `--output-dir`), eliminating hardcoded user paths, adding safe fallback for optional `mongomock` dependency, and returning non-zero exit codes on fatal missing-dataset or missing-dependency errors.
  - **Added (Tests):** Authored comprehensive automated regression test suite in [`tests/test_fix_commit_issues_regression.py`](file:///d:/dataspeak/tests/test_fix_commit_issues_regression.py) testing all 8 remediation areas; full test suite now reaches 327/327 passing tests (0 failures).

- **MongoDB Drill-Down Record Inspector & Live Document Streaming Fix (`backend/services/database_connection_service.py`, `backend/routers/connections.py`)**:
  - **Connection String & Host Dual-Fallback:** Fixed route handler in `/api/connections/{id}/preview` to decrypt connection strings and seamlessly fall back to `c.host` when Atlas URIs (`mongodb+srv://...`) are stored in host fields.
  - **Dynamic Mongo Filter & Slice Support:** Connected frontend drill-down filters (e.g. `Filter: US` or `Filter: All`) to MongoDB `find(mongo_filter)` queries with regex support for month dates.
  - **Recursive BSON & Datetime Serialization:** Upgraded `_serialize_row` and `_serialize_value` to convert `ObjectId`, nested subdocuments, lists, UUIDs, Decimals, and datetimes to standard JSON-serializable structures, eliminating the "No matching records found for this slice (0 records retrieved)" drawer bug.

- **MongoDB Chart Expansion & Intelligent Pushdown Sampling (`backend/services/db_pipeline_service.py`)**:
  - **6 Rich Analytical Charts:** Expanded MongoDB chart generation from 2 hardcoded dimension charts to 6 diverse, high-value visualizations: Activity Trend Over Time (Area Chart across 24 monthly periods), Distribution by Country ISO2 (Bar), Distribution by Country ISO3 (Donut), Top Territories by Name (Bar), Top Entities by Population (Bar), and Top Entities by Confirmed Cases (Donut).
  - **Pushdown Sampling for Multi-Million Document Datasets:** Added statistical `$sample: 25000` pushdown aggregation for collections exceeding 50,000 documents (such as `global_and_us` with 4,151,376 documents), achieving sub-second aggregation response without Atlas memory limit errors or timeout bottlenecks.

- **LLM Multi-Key Token Exhaustion Auto-Shifting & Provider Optimization (`backend/services/llm_generation_service.py`, `backend/services/multi_llm.py`)**:
  - **Instant Key Shift on Token Exhaustion (429/403):** Implemented proactive token/quota exhaustion detection. When any API key encounters rate limits or quota exhaustion, it is placed on a 60-second cooldown and the system immediately shifts to the next available key in the pool without retrying dead models or falling back to raw error text.
  - **Multi-Key & Comma-Separated Key Harvesting:** Added support for comma-separated API keys in `.env` (`GEMINI_API_KEY=key1,key2...`, `GEMINI_API_KEYS`, `GROQ_API_KEYS`, `GROQ_API_KEY_1..15`).
  - **DeepSeek Removal:** Removed DeepSeek from the provider fallback chains (`_build_provider_order`, `multi_llm.py`), streamlining generation to Gemini and Groq.
  - **Model Endpoint Modernization:** Updated active model lists to live supported endpoints (`gemini-flash-lite-latest`, `gemma-4-26b-a4b-it`, `qwen/qwen3.8-27b`, `openai/gpt-oss-120b`).

- **MongoDB Native Analytics Pipeline & Schema Introspection Fix (`backend/services/database_connection_service.py`, `backend/services/db_pipeline_service.py`)**:
  - **Collection Introspection Sanitization:** Filtered out internal `system.` collections (e.g. `system.views`) in `get_mongodb_schema` to prevent Unauthorized errors on read-only MongoDB Atlas clusters, and formatted schema entries directly to collection mapping.
  - **Connection String & Host Field Dual-Binding:** Handled MongoDB connections where Atlas URIs (`mongodb+srv://...`) are stored in either `host` or `connection_string`.
  - **Native Aggregation Pushdown:** Implemented native MongoDB aggregation pipelines (`$match`, `$group`, `$sum`, `$avg`, `estimated_document_count`) for document databases, yielding real KPIs and distribution charts instead of raw SQL failures.

- **Cloud Databases Live Connectivity & Schema Audit (`Cloud_Databases_Postgres_Mongo_Firebase/`, `backend/services/database_connection_service.py`, `backend/services/document_db_profiler.py`)**:
  - **Live Online PostgreSQL:** Connected to European Bioinformatics Institute (RNAcentral, UK) PostgreSQL 16.11 server (`postgresql://reader:NWDMCE5xdipIjRrp@hh-pgsql-public.ebi.ac.uk:5432/pfmegrnargs`) with 1.35s latency and executed live SQL queries.
  - **Live Online MongoDB Atlas:** Connected to official MongoDB COVID-19 open data replica set cluster (`mongodb+srv://readonly:readonly@covid-19.hip2i.mongodb.net/covid19`) in 3.02s. Introspected 9 collections, verified document retrieval across `countries_summary` (~229,743 docs) and `global` (~331,470 docs), and verified nested document dot-notation flattening.
  - **Firebase / Firestore Engine:** Tested Firestore Project ID and Service Account Certificate validation schemes and collection schema introspection (`users`, `orders`, `products`).
  - **Desktop Verification Artifacts:** Generated `test_results.md`, `test_results.json`, and `run_audit_cloud_dbs.py` in `Desktop/Database_Verification_Audits/Cloud_Databases_Postgres_Mongo_Firebase/`.

- **Database Verification & Ground-Truth Reconciliation Audit 3 of 5: Sakila Media & Movie Rentals (`Database_3_Sakila/`, `backend/services/db_pipeline_service.py`)**:
  - **Online Source Ingestion:** Downloaded `sakila.db` from DuckDB SQLite scanner repository (16 tables, 16,049 payments, 16,044 rentals, 1,000 films, 599 customers).
  - **Relational Domain Traversal & Intelligence (`backend/services/db_pipeline_service.py`):**
    - Expanded domain topology detection to automatically identify `payment` and `rental` facts, `film` catalog, and `member`/`customer` entities.
    - Implemented multi-hop geographic dimension traversal (`payment.customer_id -> customer.address_id -> address.city_id -> city.country_id -> country.country`) to resolve geographic sales breakdown when no country column exists on the fact table.
    - Added relational many-to-many bridge joining (`film -> film_category -> category`) for taxonomy distribution and genre sales share donuts.
    - Enhanced customer spend ranking to automatically resolve customer names (`Karl Seal`, `Eleanor Hunt`) instead of surrogate IDs.
  - **100% Ground-Truth Mathematical Reconciliation (0.00 Variance):**
    - Total Revenue: **$67,416.51** vs SQL `SUM(amount)`: **$67,416.51** (Exact Match)
    - Total Orders: **16,049** vs SQL `COUNT(*)`: **16,049** (Exact Match)
    - Average Order Value: **$4.20** vs SQL `AVG(amount)`: **$4.20** (Exact Match)
    - Active Customers: **599** vs SQL `COUNT(*)`: **599** (Exact Match)
    - Customer Lifetime Value (CLV): **$112.55** vs SQL: **$112.55** (Exact Match)
    - Total Units Sold / Rented: **16,044** vs SQL `COUNT(*)` from `rental`: **16,044** (Exact Match)
    - Catalog Size: **1,000** vs SQL `COUNT(*)` from `film`: **1,000** (Exact Match)
    - Top Market: **India ($6,630.27)** vs SQL multi-join: **India ($6,630.27)** (Exact Match)
    - Monthly Velocity trajectory across 5 months sum = **$67,416.51** (Exact Match)
  - **Desktop Verification Artifacts:** Saved `sakila.db`, `run_audit_db3.py`, `test_results.json`, and `test_results.md` to `Desktop/Database_Verification_Audits/Database_3_Sakila/`. Verified regression on Chinook (DB 1) and Northwind (DB 2) with 100% pass rates.

- **Phase 1.7: Multi-Domain Enterprise Accuracy Hardening & IDE Type Health (`backend/services/db_pipeline_service.py`, `backend/ingestion/extractors.py`, `backend/services/metric_recipes.py`, `tests/`, `src/app/components/templates/ECommerceTemplate.tsx`)**:
  - **Monetary Measure Prioritization (`backend/services/db_pipeline_service.py`):** Fixed revenue misattribution bug where `unit_price` was mistakenly selected as total revenue. Implemented `sort_monetary_columns_by_priority` and `is_unit_price_column` to prioritize genuine transaction totals (`net_revenue`, `gross_revenue`, `total_amount`) and automatically formulate `SUM(unit_price * quantity)` when only unit rates exist.
  - **Truthful Lifecycle Status Accounting:** Eliminated misleading "completed transactions" subtitle. Built lifecycle analyzer detecting delivered, shipped, cancelled, and returned records, displaying truthful volume distributions.
  - **Same-Period-Last-Year (SPLY) Time Series Engine:** Replaced naive full-year vs. partial-year comparisons (-80.5% distortion) with true SPLY windowing (Jan 1–Mar 11 2026 vs Jan 1–Mar 11 2025: -0.6%), returning `None` if insufficient historical intervals exist.
  - **Zero Fabricated Constants & Domain-Agnostic Charts:** Removed all hardcoded constants (`5.8`, `3.4`, `11.2`, `4.8`, `6.5`, `5.0`, `6.8`, `3.2`, `3,503`) and replaced Chinook music schema queries (`TrackId`, `Genre`, `Album`, `MediaType`) with multi-domain introspected dimensions, generating all 6 charts dynamically on any schema.
  - **IDE & Pyright Type Error Remediation:** Fixed all 8 reported static typing errors across `backend/ingestion/extractors.py` (explicit `str` typing for PyMuPDF `get_text`, safe PPTX `shape.text_frame` reflection), `backend/services/metric_recipes.py` (discriminated union base class override), `tests/test_phase2a_metric_recipe_contract.py`, and `tests/test_phase2c_derived_metric_executor.py`. Restored `backend/routers/analytics.py`.
  - **Full Automated Verification:** Golden test `scratch/test_golden_ecommerce.py` verified with 5/5 `[PASS]`, backend test suites verified with 81 passed, and frontend production build verified (`npm run build` → ✓ 2755 modules transformed, 0 errors).

- **Phase 1.6.1: Tabular Document Introspection & Multi-Chart Layout Hardening (`backend/services/source_profiler.py`, `backend/services/adaptive_chart_recommender.py`, `src/app/components/analytics/LiveExplorerCanvas.tsx`, `AISynthesizedGrid.tsx`, `tests/test_source_profiler.py`)**:
  - **HTML Table Extraction Parser (`backend/services/source_profiler.py`):** Built `_parse_html_table` using BeautifulSoup to introspect HTML tables (`<table border='1' class='extracted-table'>`) generated during document ingestion (e.g. `client_data.csv`). Resolved an issue where tabular documents showed 0 Measures, 0 Dimensions, and 0 Time Axes. Accurately extracted 18 numeric measures, 4 categorical dimensions, and 4 date/time axes.
  - **Live Explorer Layout Geometry Defense (`src/app/components/analytics/LiveExplorerCanvas.tsx`):** Replaced `if (availableTables.length === 0) return null` with a styled glass empty-state component featuring `Table2` icon and informative guidance. Ensures the 3-column studio grid geometry never collapses or leaves blank column voids on non-tabular sources.
  - **Auto View Mode for AI Grid (`src/app/components/analytics/AISynthesizedGrid.tsx`):** Added `"Auto"` as the default view mode in `GLOBAL_CHART_TYPES`. Each card in the AI Synthesized Dashboard now renders in its distinctive recommended format (Bar for comparative breakdown, Donut for category share, Line for chronological trajectories) while still allowing users to force a specific chart type across all cards via the View tabs.
  - **Live Spreadsheet Metric Aggregations (`backend/services/adaptive_chart_recommender.py`):** Computed real-time top-5 category sums for Bar recommendations, category frequency counts for Donut recommendations, and chronological progressions for Line recommendations directly from parsed spreadsheet rows.
  - **Automated Verification:** Added `test_parse_html_table` to `tests/test_source_profiler.py`. Full test suite passed (320 passed, 0 failures). Frontend production build passed cleanly (`npm run build` → ✓ 2763 modules transformed, 0 errors).

- **Phase 1.6: Source-Aware Discovery & Adaptive Analytics Visualizations (`backend/services/source_profiler.py`, `backend/services/adaptive_chart_recommender.py`, `backend/routers/analytics.py`, `src/app/components/analytics/SourceArchetypeBanner.tsx`, `AnalyticsHeader.tsx`, `LiveExplorerCanvas.tsx`, `AnalyticsPage.tsx`)**:
  - **Automated Source Archetype Discovery (`backend/services/source_profiler.py`):** Built source classifier introspecting connected SQL databases (PostgreSQL, MySQL, SQLite) and uploaded document sources (CSVs, Excel sheets, and document knowledge bases). Classifies sources into `relational_timeseries`, `relational_categorical`, `tabular_spreadsheet`, and `document_knowledge` by analyzing temporal axes, measure/dimension ratios, cardinalities, and extracted table chunks. Includes markdown table chunk parser (`_parse_markdown_table`).
  - **Adaptive Chart Recommendation Engine (`backend/services/adaptive_chart_recommender.py`):** Developed rule-based and semantic recommendation engine generating visualization recommendations tailored to data shapes and modalities:
    - *Relational Time-Series:* Recommends velocity trend Line charts, cumulative volume Area charts, categorical breakdown Bar charts, and headline KPI cards.
    - *Relational Categorical:* Recommends proportional share Donut charts, ranked Bar charts, bivariate correlation Scatter plots (when 2+ continuous numeric measures exist), and average KPI cards.
    - *Tabular Spreadsheets:* Recommends direct column Bar charts, row composition Donut charts, horizontal ranking Bar charts, and total KPI cards.
    - *Document Knowledge Base:* Recommends modality breakdown Donut charts (text vs table vs image), page content density Area curves, extraction yield Bar charts, and indexed chunk KPI cards.
  - **Unified Backend Analytics API (`backend/routers/analytics.py`):**
    - Added `GET /api/analytics/sources`: Unified source catalog returning all database connections and documents with detected archetypes.
    - Added `GET /api/analytics/sources/{type}/{id}/discover`: On-demand source archetype discovery and adaptive visualization recommendations.
    - Added `GET /api/analytics/sources/{type}/{id}/dashboard`: Unified dashboard endpoint serving both SQL database metrics and document knowledge/tabular metrics.
    - Added `POST /api/analytics/sources/{type}/{id}/query`: Unified query runner supporting SQL queries and structured document table aggregations (SUM, AVG, MAX, MIN, COUNT).
    - Preserved 100% backward compatibility for existing `/dashboard/{connection_id}` and `/connections/{connection_id}/profile` endpoints.
  - **Database Models & Auto-Migration (`backend/models.py`, `backend/services/db_migration.py`):** Added `source_type`, `source_archetype`, and `document_id` columns to `DashboardLayout` with idempotent auto-migration across SQLite and PostgreSQL.
  - **Discovered Source Archetype Banner (`src/app/components/analytics/SourceArchetypeBanner.tsx`):** Created glassmorphic banner rendering discovered archetype identity, archetype descriptions, structural badges (tables, measures, dimensions, time axis), and interactive recommendation referral pills.
  - **Grouped Source Selector (`src/app/components/analytics/AnalyticsHeader.tsx`):** Enhanced header dropdown to categorize sources into "Relational Databases" and "Document Data Sources" with distinct modality icons, plus a pulsing Discovered Archetype badge in the header bar.
  - **Interactive Referral Wiring (`src/app/components/analytics/LiveExplorerCanvas.tsx`, `AnalyticsPage.tsx`):** Wired chart buttons in the Live Explorer to highlight recommended chart types with glowing star indicators (`⭐ Recommended`). Clicking recommendation referral pills in the archetype banner instantly switches and visualizes the recommended chart in the explorer.
  - **Automated Verification:** Added 10 unit tests in `tests/test_source_profiler.py` and `tests/test_adaptive_chart_recommender.py`. Full regression suite reached 319 passing tests with 0 failures. Frontend production build compiled cleanly (`npm run build` → ✓ 2763 modules transformed, 0 errors).

- **Analytics Page Full Frontend Overhaul — Task 1.2 (`src/app/pages/dashboard/AnalyticsPage.tsx`, `src/app/components/analytics/`)**:
  - **Monolith Decomposition:** Rewrote 863-line `AnalyticsPage.tsx` into a ~250-line orchestrator composing 9 focused child components. All original data-fetch logic (`fetchDatabases`, `fetchDashboardData`, `runInteractiveQuery`, `handleTriggerProfile`) preserved 100% unchanged.
  - **Mock Data Removal (Task 1.2):** Eliminated all static mock arrays (`queryTrendsData`, `topTablesData`, `databaseDistribution`, `dataGrowthData`). Page now derives all display data from live backend API responses.
  - **ChartRenderer (`components/analytics/ChartRenderer.tsx`):** Unified Recharts wrapper eliminating all repeated chart JSX. Supports `bar`, `line`, `area`, `donut`, `scatter`, `horizontal_bar` with dark-mode tooltip styling.
  - **AnalyticsHeader (`components/analytics/AnalyticsHeader.tsx`):** Premium dark header bar with `business_domain` badge, `used_fallback` amber warning, profiling status, DB selector, date range picker, Re-profile button, and "Setup Domain ⚡" wizard trigger.
  - **KpiSummaryStrip (`components/analytics/KpiSummaryStrip.tsx`):** Glassmorphic animated 4-KPI row (Total, Average, Max, Count) with mini sparklines, per-card color glow, and Framer Motion stagger entrance.
  - **LiveExplorerCanvas (`components/analytics/LiveExplorerCanvas.tsx`):** Redesigned dark glass explorer panel with SQL chip preview, chart type pill toggles, copy-to-clipboard, and `AnimatePresence` chart transitions.
  - **AISynthesizedGrid (`components/analytics/AISynthesizedGrid.tsx`):** AI chart grid with per-card chart type toggle (Bar/Line/Area), validation warning accordion, fallback badge, scalar KPI card rendering, and error state display (`error_code`).
  - **DomainSetupBanner (`components/analytics/DomainSetupBanner.tsx`):** Full-width gradient CTA banner shown when `kpis.length === 0`, guides users to the wizard.
  - **SchemaHealthPanel (`components/analytics/SchemaHealthPanel.tsx`):** Collapsible schema accordion surfacing `schema_summary` data (never visualized before) — null% color bars, cardinality pills, data type badges, role dots (Measure/Dimension/Time), filter tabs.
  - **AIInsightsSummaryCard (`components/analytics/AIInsightsSummaryCard.tsx`):** Inline Gemini AI Insights card calling existing `GET/POST /api/analytics/connections/{id}/ai-insights` endpoints with 429 cooldown timer, collapsible expanded view, and key metrics grid.
  - **DomainMappingWizard (`components/analytics/DomainMappingWizard.tsx`):** ⭐ 3-step guided setup drawer surfacing previously unused backend APIs (`GET /domains` → `POST /suggest-mapping` → `POST /apply-mapping`) — domain card grid, mapping confidence badges (Auto/Review/Manual), per-row column override dropdowns, "Accept All High-Confidence" bulk action, confirm panel with animated success state.
  - **CSS Tokens:** Added analytics palette variables (`--analytics-blue`, `--analytics-violet`, etc.) and glass surface tokens to `src/styles/theme.css`.
  - **Build Verification:** `npm run build` → ✓ 2762 modules transformed, 0 errors, exit code 0.
  - **Backend:** Zero backend files modified.

- **Phase 2F & 2F.1: Deterministic Dashboard Layout & Composition Engine (`backend/services/dashboard_layout_engine.py`, `tests/test_phase2f_dashboard_layout_engine.py`)**:
  - **Deterministic 12-Column Grid Composition:** Created `compose_dashboard_layout()` deterministically aggregating `MetricRecipe[]`, `ChartRecommendation[]`, and `Mapping[metric_id, FilterRecommendationResult]` into a typed `DashboardLayoutPlan` without SQL execution, customer DB queries, MetricExecutor/DerivedMetricExecutor invocations, LLMs, persistence, ORM mutations, or frontend changes.
  - **Single-Table Composition Boundary:** Strictly enforced that all recipes, charts, and filter recommendations entering one dashboard layout must resolve to the exact same source table. Multi-table mixes fail fast with `DashboardLayoutError("Phase 2 dashboard composition supports exactly one source table. Multi-table composition requires Phase 3.")`.
  - **Derived Metric Chart Capability Guard (Phase 2F.1):** Enforced that `RatioMetricRecipe` and `DifferenceMetricRecipe` strictly require `chart.chart_type == "KPI"`. Grouped chart recommendations (`Line`, `Bar`) for derived recipes fail fast with `DashboardLayoutError("Derived metrics currently support scalar KPI placement only.")`.
  - **KPI Card & Chart Placement Rules:** Every `MetricRecipe` receives exactly one `KpiCardPlacement` (`col_span=3`, 4 per row) preserving input order. Metrics with `chart_type="KPI"` do not produce a duplicate chart placement; metrics with `Line` (`grouping_kind="time"`) or `Bar` (`grouping_kind="dimension"`) produce a separate `ChartPlacement` (`col_span=6`, 2 per row).
  - **Chart Completeness & Cross-Table Grouping Guard:** Requires exactly one chart recommendation per metric with matching title. Grouping column references must belong to the verified source table; cross-table groupings fail fast with `DashboardLayoutError("Cross-table chart placement requires a validated relationship path.")`.
  - **Provenance-Preserving Filter Results & Global Deduplication:** Accepted `Mapping[str, FilterRecommendationResult]` ensuring unambiguous metric attribution. Flattened and deduplicated identical filters with deterministic sorting (priority first: date range priority 1 before select priority 2; then discovery order). Conflicting filter IDs or conflicting same-column configurations fail fast. Cross-table filter references are rejected.
  - **Comprehensive Test Suite:** Added 34 comprehensive test cases covering grid constants, recipe order preservation, ratio/difference KPI card isolation, derived Line/Bar rejections, chart/filter cross-table rejections, filter deduplication, conflicting definition rejection, and proof of zero SQL/LLM/executor execution. Total regression suite reached 309 passing tests with 0 failures and 0 Pyright errors.



- **Phase 2E: Deterministic Filter Recommendation Engine (`backend/services/filter_recommender.py`, `tests/test_phase2e_filter_recommender.py`)**:
  - **Deterministic Execution-Free Filter Recommendations:** Created `recommend_filters()` recommending structured `DateRangeFilterRecommendation` (`>=` start, `<=` end) and `SelectFilterRecommendation` (`operator="IN"`) directly from SchemaRegistry metadata and confirmed column references without executing SQL, calling LLMs, or querying customer DB values.
  - **Derived Metric Filter Support:** Enabled filter recommendations for `RatioMetricRecipe` and `DifferenceMetricRecipe` (e.g. AOV and Gross Profit with `orders.status` or `orders.created_at`), fully aligned with Phase 2C runtime filter propagation across all atomic operands.
  - **Cardinality & Identifier Guards:** Automatically skips identifier-like columns (`is_primary_key=True` or `semantic_type in {"ID", "UUID", "IDENTIFIER", "PRIMARY_KEY"}`), columns with missing cardinality, or non-informative cardinality (< 2 distinct values). Recommends bounded `select` dropdowns for cardinality between 2 and 50; defers cardinality > 50 for future searchable filters.
  - **Strict Same-Table Boundary:** Enforces qualified `table.column` references and rejects cross-table filter references (`FilterRecommendationError("Cross-table filter recommendation requires a validated relationship path.")`) with zero join guessing.
  - **Deterministic Ordering & Deduplication:** Ensures time filter appears first, followed by dimensions in supplied order, deduplicating repeated columns and suppressing duplicate dimensional filters when a time filter is already active on the same column.
  - **Comprehensive Test Suite:** Added 30 unit and security tests in `tests/test_phase2e_filter_recommender.py` covering atomic and derived recipes, boundary thresholds (cardinality 0, 1, 2, 50, 51, None), identifier safety, cross-table rejection, and proof of zero option-value fetching or SQL/LLM invocation. Total regression suite reached 275 passing tests with 0 failures and 0 Pyright errors.


- **Phase 2D: Deterministic Chart Recommendation Engine (`backend/services/chart_recommender.py`, `tests/test_phase2d_chart_recommender.py`)**:
  - **Deterministic Rule-Based Recommender:** Created `recommend_chart()` synthesizing typed `MetricRecipe` inputs, SchemaRegistry metadata, and explicit confirmed grouping references into typed `ChartRecommendation` instances without LLM calls, DB queries, SQL generation, or persistence.
  - **Conservative 3-Chart Topology:** Restricted supported chart types strictly to `KPI`, `Line`, and `Bar`. Deferred advanced visualizations (Pie, Donut, Scatter, Area, Heatmap, etc.) pending cardinality and visualization suitability rules.
  - **Derived Metric Scalar Isolation:** Enforced that `RatioMetricRecipe` and `DifferenceMetricRecipe` (e.g. AOV, Gross Profit) strictly recommend `chart_type="KPI"` with `grouping_kind="none"` and `group_by_ref=None`, even if grouping context is passed, because Phase 2C derived execution is scalar-only.
  - **Deterministic Atomic Mapping Rules:** Atomic recipes with explicit same-table `time_ref` map to `Line` (`grouping_kind="time"`); with explicit same-table `dimension_ref` map to `Bar` (`grouping_kind="dimension"`); if both are passed, `time_ref` deterministically takes precedence; without grouping maps to `KPI` (`grouping_kind="none"`).
  - **Strict Grouping Reference Validation:** Enforced qualified `table.column` syntax, existence in verified `SchemaRegistry`, and single-table containment. Cross-table references fail fast with `ChartRecommendationError("Cross-table chart grouping requires a validated relationship path.")`. Zero column-name substring guessing (`if "date" in col`).
  - **Comprehensive Test Suite:** Added 27 unit and security tests in `tests/test_phase2d_chart_recommender.py` covering scalar KPIs, line charts, bar charts, time precedence, derived recipe scalar confinement, cross-table and unqualified rejection, and verification of zero SQL/LLM invocation. Total regression suite reached 245 passing tests with 0 failures and 0 Pyright errors.


- **Phase 2C.1: Derived Execution Boundary Hardening (`backend/services/derived_metric_executor.py`, `tests/test_phase2c1_execution_boundary.py`)**:
  - **Single-Table Runtime Filter Boundary Enforcement:** Added `_get_recipe_table()` and `_validate_runtime_filters()` to strictly enforce that external `MetricFilter` criteria supplied to `execute_metric_recipe()` are qualified (`table.column`) and target the exact single source table of the recipe. Cross-table filters (e.g., `customers.region` on an `orders` recipe) raise `DerivedMetricExecutionError("Cross-table runtime filters require a validated relationship path.")` before any database queries or `MetricExecutor` calls are made.
  - **Unqualified Filter Guard:** Unqualified filter column references (e.g. `status = "completed"`) fail fast with `DerivedMetricExecutionError("Runtime metric filters must use qualified table.column references.")`.
  - **Non-Finite Numeric Guard:** Hardened `_ensure_numeric()` to reject non-finite float values (`NaN`, `+inf`, `-inf`) via `math.isfinite()`, raising `DerivedMetricExecutionError("Derived metric component '<role>' returned a non-finite numeric value.")`. Added post-arithmetic finite guards on division and difference operations. Non-finite values are never converted to 0, `None`, or sentinel values.
  - **Preserved Core Invariants:** Preserved strict `None` vs real zero (`0`, `0.0`) semantics, `status="undefined", value=None` for zero denominator, no raw SQL, no joins, no eval/exec, and zero rounding in the calculation layer.
  - **Comprehensive Test Suite:** Added 15 focused execution boundary, numeric safety, and overflow result tests in `tests/test_phase2c1_execution_boundary.py`. Full regression test suite passed cleanly with 218 tests passing, 0 failures, and 0 Pyright errors.


- **Phase 2C: Deterministic Metric Recipe Executor (`backend/services/derived_metric_executor.py`, `tests/test_phase2c_derived_metric_executor.py`)**:
  - **MetricExecutor Sole Calculation Authority:** Built `execute_metric_recipe()` executing Atomic, Ratio, and Difference metric recipes without raw SQL generation, joins, eval, or formula string execution. All database interactions delegate strictly to `MetricExecutor.execute()` per atomic operand.
  - **Safe Ratio & Difference Composition:** Executes numerator and denominator (or left and right) independently through `MetricExecutor`. Division by zero evaluates strictly to `status="undefined", value=None` without defaulting to 1; missing operand data evaluates to `status="no_data", value=None` without fabricating zeros. Legitimate numeric zeros (`0`, `0.0`) are strictly preserved.
  - **Zero Rounding in Calculation Layer:** Maximum floating point precision is retained (e.g. `1000.0 / 3 = 333.3333333333333`) leaving formatting to the presentation layer.
  - **Strict Defense-in-Depth:** Enforces tenant ownership checks (`db_conn.tenant_id == tenant_id`, `db_conn.id == connection_id`), connection-boundary revalidation (`validate_recipe_for_connection`), scalar output checks, and numeric type validation (explicitly rejecting booleans, dates, and text).
  - **Runtime Filter Propagation:** Propagates external `MetricFilter` criteria consistently to all atomic operands of derived recipes.
  - **Comprehensive Test Suite:** Added 29 focused unit and security tests in `tests/test_phase2c_derived_metric_executor.py` verifying exact AOV (`250.0`), Gross Profit (`450.0`), filtered values (`150.0` and `140.0`), call counts, and zero/null semantics. Full test suite reached 203 passing tests with 0 failures and 0 Pyright errors.

- **Phase 2B.2: Template Formula Fidelity Guard (`backend/services/metric_recipe_generator.py`, `tests/test_phase2b2_formula_fidelity.py`)**:
  - **Strict Atomic Formula Grammar:** Implemented `_SIMPLE_ATOMIC_FORMULA_RE` to parse only exact single-variable atomic aggregations (`SUM`, `AVG`, `MIN`, `MAX`, `COUNT`, `COUNT_DISTINCT`) over a single placeholder `{variable}`. Rejects multi-variable, division, subtraction, `WHERE` predicates, and `CASE` expressions.
  - **3-Way Metadata Agreement Verification:** Enforced that `formula_template`, declared `aggregation`, and `required_variables` must strictly agree in count, operation, and variable name. Any divergence produces a structured `DeferredRecipeRule`.
  - **Decoupled from Private Registry:** Replaced import of private `_DOMAIN_REGISTRY` with canonical public `get_domain_template()` helper, safely handling generic fallbacks and unknown domains.
  - **Deferred Metric Lifecycle:** Added `DeferredRecipeRule` to `RecipeRule` union. Generator converts deferred rules into structured `SkippedMetric` instances with explanatory reasons instead of silently dropping unsupported template semantics.
  - **Formula Fidelity Test Suite:** Added 15 focused tests in `tests/test_phase2b2_formula_fidelity.py`, verifying simple formula acceptance, whitespace tolerance, mismatch deferral, multi-variable/division/subtraction/filter rejection, and public template retrieval. Full test suite reached 174 passing tests with 0 failures and 0 Pyright errors.

- **Phase 2B.1: Semantic Substitution Removal & Domain Template Alignment (`backend/services/metric_recipe_generator.py`, `tests/test_phase2b1_recipe_semantics.py`)**:
  - **Eliminated Concept Substitution & Mapping Fallbacks:** Purged all `fallback_mapping_keys` (`mrr -> revenue`, `appointment_id -> encounter_id`, `amount -> transaction_amount`). If an explicitly requested business variable is missing in the confirmed mapping, the metric is cleanly skipped (`MissingMappingError`) with zero silent semantic guessing.
  - **Single Source of Truth via Domain Templates:** Refactored `metric_recipe_generator.py` to source atomic KPI rules (`title`, `required_variables`, `aggregation`, `format`, `description`) directly from `domain_templates.py` via `build_domain_recipe_rules()`. Eliminated manual duplication and prevented catalog drift.
  - **Canonical Metric ID Preservation:** Fixed Average Order Value to preserve its canonical domain template ID `metric_id="aov"` instead of `average_order_value`.
  - **Active Subscriptions Filter Guard:** Added `FILTER_REQUIRED_METRIC_IDS = {"active_subscriptions"}` to explicitly skip `active_subscriptions` with a structured reason until filter-aware recipes are supported in the recipe contract, preventing misleading `COUNT_DISTINCT(subscription_id)` metrics.
  - **Narrowed Exception Handling:** Removed bare `ValueError` from the rule generation catch block. Only expected contract errors (`ValidationError`, `MetricRecipeValidationError`, `MissingMappingError`) are converted to `SkippedMetric`; programmer bugs propagate and fail tests loudly.
  - **API Hardening:** Removed `rules` parameter from public `generate_metric_recipes()` function signature, exposing `_generate_metric_recipes_from_rules()` internally for test fixtures.
  - **Regression & Semantic Test Suites:** Added 12 focused semantic regression tests in `tests/test_phase2b1_recipe_semantics.py`. Full test suite reached 159 passing tests across Phase 1.5, Phase 2A, Phase 2B, and Phase 2B.1 with 0 failures and 0 Pyright errors.

- **Phase 2B: Deterministic KPI Metric Recipe Generator (`backend/services/metric_recipe_generator.py`, `tests/test_phase2b_metric_recipe_generator.py`)**:
  - **Deterministic Recipe Synthesis:** Built `generate_metric_recipes()` transforming explicitly confirmed semantic mappings into typed, validated `MetricRecipe` instances (Atomic, Ratio, Difference) using structured domain recipe rules without LLM dependencies.
  - **Zero Inference & Zero Fuzzy Matching:** Operates strictly on confirmed mapping keys. Missing dependencies cleanly skip metrics with descriptive, structured reasons (`SkippedMetric`) rather than inventing columns or falling back to generic/demo defaults.
  - **Domain Isolation:** Unknown or generic domains never fall back to e-commerce; generic telemetry data generates zero hallucinated business metrics.
  - **Phase 2A Registry Validation Integration:** Every candidate recipe is validated against `SchemaRegistry` and canonical semantic guards (blocking arithmetic on IDs, blocking `SUM` on percentages, rejecting cross-table derived operands).
  - **Comprehensive Test Suite:** Added 21 focused unit and regression tests in `tests/test_phase2b_metric_recipe_generator.py`, verifying deterministic ordering, stability across repeated runs, absence of arbitrary `sql`/`formula` fields, and alignment between `AggregationType` and `ALLOWED_AGGREGATIONS`. Total regression suite reached 147 passing tests with 0 failures.

- **Phase 2A: Typed Metric Recipe Contract (`backend/services/metric_recipes.py`, `tests/test_phase2a_metric_recipe_contract.py`)**:
  - **Deterministic Metric Recipe Language:** Created typed Pydantic models for Atomic, Ratio, and Difference metric recipes (`StrictRecipeModel` with `extra="forbid"`) that reject arbitrary executable formulas, free-form strings, Python eval, and raw SQL.
  - **Canonical Aggregation Alignment:** Strictly enforces canonical aggregation whitelist (`SUM`, `AVG`, `MIN`, `MAX`, `COUNT`, `COUNT_DISTINCT`) reused directly from `services.metric_semantics.ALLOWED_AGGREGATIONS`, with wildcards constrained to `COUNT`.
  - **Safe Ratio & Difference Semantics:** Mandates explicit `zero_division: Literal["null"]` for ratios and enforces single-table boundary across operands until Phase 3 relationship engine.
  - **Schema-Aware & Connection-Aware Validation:** Implemented `validate_recipe_against_registry` and `validate_recipe_for_connection` leveraging `parse_column_ref()` and `validate_metric_aggregation()` to enforce identifier guards and percentage/rate non-additive guards prior to future execution.
  - **Deterministic JSON Round-Trip:** Provided stable serialization functions `metric_recipe_to_dict` and `metric_recipe_to_json` with sorted keys.
  - **Test Suite:** Added 21 comprehensive contract and validation tests in `tests/test_phase2a_metric_recipe_contract.py`, bringing the total regression suite to 126 passing tests with zero regressions.

- **Phase 1.5D.2: Atomic Regeneration Safety & Dimension Enforcement (`backend/routers/analytics.py`, `tests/test_phase1_5d2_atomic_regeneration.py`)**:
  - **Preserve Working Dashboard on Zero-Valid Regeneration:** Validates all candidate agent KPI specifications in memory prior to issuing any database statements. If zero valid KPIs remain, aborts replacement cleanly without deleting existing `KpiDefinition` records or altering `DashboardLayout`.
  - **Atomic KPI + DashboardLayout Replacement:** Unified deletion of obsolete definitions, insertion of new definitions, and creation/update of `DashboardLayout` inside a single transactional block with a single `db.commit()` and `db.rollback()` on error. Cache invalidation executes strictly after successful commit.
  - **Reject Cross-Table Dimensions:** Enforced that optional secondary/dimension columns must belong to the exact same table as the primary metric. Cross-table dimensions (`orders.total_amount` by `customers.region`) are omitted (`dimension_column=None`) with a structured warning until the Phase 3 relationship engine exists, preserving the primary metric without inventing joins.
  - **Tenant Connection Ownership Defense:** Verified `connection_id` belongs to `tenant_id` via `DatabaseConnection` before accessing `SchemaRegistry` during agent persistence.
  - **Documented SQLite Nullable Mismatch:** Cataloged SQLite's physical DDL (`aggregation_function` nullable) vs SQLAlchemy ORM (`nullable=False`) as migration debt for the production Alembic baseline while application writers enforce non-null values.
  - **Comprehensive Test Suite:** Added 11 focused atomic regeneration tests in `tests/test_phase1_5d2_atomic_regeneration.py`, with 105/105 tests passing cleanly across the entire suite.

- **Phase 1.5D.1: Complete Removal of Silent KPI Fallbacks (`backend/routers/analytics.py`, `tests/test_phase1_5d1_silent_fallback_removal.py`)**:
  - **Eliminated Silent Aggregation Fallback:** Hardened `run_agent_pipeline_sync` to read `aggregation_function` explicitly. Any missing, empty, or unsupported aggregation (`GROWTH`, `DIFFERENCE`, `COMPUTED`, `RATIO`, `PERCENT_CHANGE`) is strictly dropped with a structured log warning instead of silently converting to `COUNT` or `SUM`.
  - **Eliminated Fake Target Column Fallbacks:** Removed all fallback logic defaulting missing tables or columns to `"orders.total_amount"`. Enforced strict `SchemaRegistry` whitelisting for both table and column names before KPI construction.
  - **Zero Valid KPIs Handling:** If all agent KPI specifications fail validation, the system cleanly logs a warning, deletes obsolete definitions, and persists zero KPIs without fabricating demo data or silently invoking an unrelated business-domain fallback.
  - **Comprehensive Test Suite:** Added 20 new tests in `tests/test_phase1_5d1_silent_fallback_removal.py` bringing the total regression suite to 94 passing tests.

- **Phase 1.5D: Contract Alignment, Legacy Cleanup & Production Readiness Gate (`backend/routers/analytics.py`, `backend/services/metric_adapter.py`, `backend/services/metric_executor.py`, `backend/services/ai_insights_service.py`, `backend/services/db_migration.py`, `src/app/pages/dashboard/AIInsightsPage.tsx`, `src/app/pages/dashboard/AnalyticsPage.tsx`, `tests/test_phase1_5d_readiness_gate.py`)**:
  - **AI Insights Contract Realignment:** Separated into `POST /api/analytics/connections/{id}/ai-insights/generate` (explicit synthesis, tenant-authorized, cached in `cache_service`) and `GET /api/analytics/connections/{id}/ai-insights` (read-only cached retrieval; returns `status: "not_generated"` if not run, never silently calls LLM).
  - **Hypothetical Field Removal:** Purged dead compatibility logic in `metric_adapter.py` checking speculative attributes (`source_table`, `table_name`).
  - **Strict Filter Contract:** Hardened `MetricExecutor` so `operator="IN"` strictly requires a collection (`list`/`tuple`/`set`) while scalar operators reject collections. Empty `IN` clauses compile cleanly to `1 = 0`.
  - **Semantic Frontend Stat Labels:** Dynamically updated summary cards in `AnalyticsPage.tsx` to render mathematically accurate labels (`Total Records` for `*`, `Distinct Count` for `COUNT_DISTINCT`, `Non-null Count` for `COUNT(col)`, `Sample Count` for numeric measures).
  - **Schema Parity Migration:** Synchronized 11 missing columns for `documents` and `document_chunks` in `db_migration.py` and executed non-destructive schema migrations across both SQLite databases.

- **Master Engineering Roadmap & Task Tracker ([`todo.md`](file:///d:/dataspeak/todo.md))**:
  - Established canonical project-wide backlog organized into sequential prioritized phases (P0 to P3): Phase 1 (Frontend Analytics Wiring), Phase 2 (Embeddable Widget), Phase 3 (AI Insights Engine), Phase 4 (Enterprise Database Schemas), Phase 5 (Interactive ERD Generator), and Phase 6 (Production & Billing Hardening).
  - Defined mandatory 4-step task lifecycle protocol for AI agents and human developers.
  - Added dedicated Archived / Completed Tasks tracking section.
- **AI Agent Protocol & Instruction Standardization ([`AGENTS.md`](file:///d:/dataspeak/AGENTS.md), [`Guidelines.md`](file:///d:/dataspeak/docs/setup/Guidelines.md), [`AI_TASK_TEMPLATE.md`](file:///d:/dataspeak/docs/templates/AI_TASK_TEMPLATE.md))**:
  - Codified Section 5.5 in `AGENTS.md`: Mandatory rules requiring agents to mark tasks as `[x]`, append completion metadata, move completed items to the Archived section in `todo.md`, and log updates under `## [Unreleased]` in `CHANGELOG.md`.
  - Updated `Guidelines.md` and `AI_TASK_TEMPLATE.md` to enforce `todo.md` and `CHANGELOG.md` synchronization across all delegated agent tasks.

- **Pyright / Pylance Static Typing Hardening & Test Isolation (`backend/routers/analytics.py`, `backend/services/document_db_profiler.py`, `backend/services/metric_adapter.py`, `backend/services/cache_service.py`, `tests/`, `scratch/`)**:
  - **Analytics Router Typing:** Explicitly cast `current_user.tenant_id` (`Column[int]`) to integer `t_id` across `trigger_schema_profile`, `get_profile_status`, `get_dashboard_data`, `execute_dashboard_query`, `invalidate_dashboard_cache`, `get_connection_ai_insights`, `get_suggested_mappings`, and `apply_user_confirmed_mapping`, eliminating all Pyright type mismatch errors on `get_owned_connection` and `MetricRequest`.
  - **Document DB Profiler Type Fixes:** In `backend/services/document_db_profiler.py`, resolved `Column[int]` passes by casting connection IDs to `int`, correctly stringified Mongo/Firestore host and database arguments, typed client handles, and removed redundant `str()` calls in `flatten_document`.
  - **Metric Adapter Typing:** Cast `kpi.connection_id` and `kpi.tenant_id` in `MetricRequest` initialization.
  - **Cache Isolation in Integration Tests:** Added `clear()` method to `InMemoryCacheService` and invoked it inside `c_integration_setup` fixtures to eliminate cross-test cache contamination between test modules.
  - **Scratch Scripts Typing:** Converted `int(col)` calls to `cast(int, col)` across scratch diagnostics and hardening scripts.

- **Phase 1.5C: Live Dashboard & Ad-Hoc Analytics Migration to Canonical MetricExecutor (`backend/services/metric_adapter.py`, `backend/routers/analytics.py`, `tests/test_phase1_5c_dashboard_executor_integration.py`)**:
  - **Metric Adapter Layer (`services/metric_adapter.py`):** Created dedicated bridge converting persisted `KpiDefinition` models into canonical `MetricRequest` objects. Normalizes `orders.all` to `orders.*` and resolves bare row-count `"all"` targets deterministically from verified contextual anchors (`dimension_column`, `time_column`, single-table `domain_mapping`, or single-table schemas). Raises `LegacyKpiIncompatibleError` without guessing on ambiguous multi-table datasets.
  - **Live Dashboard Migration (`routers/analytics.py`):** Refactored `GET /dashboard/{connection_id}` to compute all KPI and live chart values through `MetricExecutor.execute()`. Removed legacy hand-rolled SQL loop that previously hardcoded `SUM(...)` on all measures regardless of aggregation type.
  - **Ad-Hoc Query Migration (`routers/analytics.py`):** Refactored `POST /dashboard/{connection_id}/query` to execute chart series and summary statistics (`total`, `average`, `max`, `min`, `count`) through `MetricExecutor`.
  - **Strict Semantic Protection:** Enforced HTTP 400 rejection for non-whitelisted aggregations (`MEDIAN`), identifier aggregations (`SUM(order_id)`), cross-table metric combinations, and unknown schema elements.
  - **Frontend Contract Preservation:** Kept 100% backward compatibility for all keys consumed by `AnalyticsPage.tsx`.
  - **Comprehensive Integration Suite (`tests/test_phase1_5c_dashboard_executor_integration.py`):** Verified 13/13 tests covering exact numbers (`SUM=1000.0`, `AVG=250.0`, `COUNT=4`, `COUNT_DISTINCT=3`, status breakdown `completed=300.0`, `shipped=300.0`, `cancelled=400.0`), legacy `"all"` deterministic resolution, isolation from legacy calculation functions, and cross-tenant protection.

  - **Universal Schema Profiler Enhancement (`services/schema_profiler.py`):** Added primary key inspection (`get_pk_constraint`), foreign key tracking (`get_foreign_keys`), and normalized semantic typing (`ID`, `UUID`, `DATE`, `DATETIME`, `NUMERIC_MEASURE`, `CURRENCY/AMOUNT`, `CATEGORY`, `TEXT`, `BOOLEAN`, `UNKNOWN`).
  - **Extensible Domain Template Registry (`services/domain_templates.py`):** Created optimization templates for E-Commerce, SaaS, Healthcare, Logistics, and Finance, plus an extensible registry enabling runtime domain registration without core engine alterations.
  - **Robust Generic / Custom Fallback:** Built an architecture supporting arbitrary business datasets and unknown relational schemas. Conservative inference selects additive measures, timestamps, and low-cardinality dimensions without inventing hallucinated concepts or assuming numeric columns represent revenue.
  - **Type-Aware Mapping Matcher (`services/mapping_matcher.py`):** Developed heuristic column-to-variable matching with ID/UUID protection, unit-price vs. total revenue penalization, cardinality checks, confidence scoring (0.0 to 1.0), and plain-English reasoning.
  - **Guided Reliability API Endpoints (`backend/routers/analytics.py`):** Added `GET /api/analytics/domains`, `POST /api/analytics/connections/{id}/suggest-mapping`, and `POST /api/analytics/connections/{id}/apply-mapping`. Validates columns against SchemaRegistry and produces deterministic `KpiDefinition` and `DashboardLayout` records with zero fabricated data.
  - **Comprehensive Verification Suite (`scratch/test_guided_mapping_engine.py`):** Validated semantic types, domain suggestions, unit price guards, FK detection, unknown custom dataset generic fallback, column rejection, and deterministic KPI generation.

- **Default Superadmin Seed & Auto-Initialization (`backend/scripts/seed_admin.py`, `backend/main.py`, `LoginPage.tsx`)**:

  - Implemented automatic database seeding on startup ensuring a default verified Superadmin user (`admin@dataspeak.ai` / `AdminPassword123!`) and default tenant exist out-of-the-box.
  - Added an interactive **"⚡ Auto-fill Default Admin"** shortcut button on the frontend login page for fast multi-developer testing without re-registering.
  - *Production Hardening Note:* For production release, see [`AGENTS.md` Section 4.5](file:///d:/dataspeak/AGENTS.md) for instructions to disable auto-seeding in `main.py`, remove the login autofill card, and rotate the credentials.
- **Conversational Data Layer & Models (`backend/models.py`, `backend/schemas.py`)**:
  - Implemented `Conversation` (sessions, auto-generated titles, timestamps) and `Message` (turns, roles, query_type, metadata_json) SQLAlchemy models and Pydantic schemas.
- **Intelligent Query Router & Auto Database Selection (`backend/services/query_router.py`)**:
  - Developed multi-stage query intent classifier supporting heuristic keyword checks, schema metadata introspection, user preference overrides (`auto`, `documents`, `database`), and Google Gemini 2.5 Flash fallback.
  - Implemented automatic database connection selection (Option C) matching user queries to relevant database schemas.
- **Unified Chat API Endpoint (`backend/routers/chat.py`)**:
  - Built `POST /api/chat` supporting multi-turn conversational context windows (up to 8 turns), grounded RAG hybrid retrieval (FAISS + BM25 + RRF + Cross-Encoder re-ranking), safe NL-to-SQL execution, and multi-source Hybrid synthesis.
  - Added full conversation session management endpoints (`GET /api/conversations`, `GET /api/conversations/{id}`, `PATCH /api/conversations/{id}`, `DELETE /api/conversations/{id}`).
- **Conversational AI Assistant Workspace (`src/app/pages/dashboard/ChatPage.tsx`)**:
  - Built responsive 3-panel chat interface with conversation history sidebar, search filter, inline rename/delete, prompt suggestions, and engine switcher.
  - Added rich response rendering with engine status badges, syntax-highlighted SQL data tables, collapsible source citation cards, and modal chunk inspection.
  - Registered `/dashboard/chat` in router and updated navigation in `DashboardLayout.tsx`.
- **Architectural Documentation (`docs/architecture/`)**:
  - [`docs/architecture/RAG_SYSTEM_ARCHITECTURE.md`](file:///d:/dataspeak/docs/architecture/RAG_SYSTEM_ARCHITECTURE.md): Complete technical breakdown of multi-modal ingestion, table matrix preservation, recursive chunking, dual FAISS/BM25 indexing, intelligent query routing, and 5-stage hybrid retrieval.
  - [`docs/architecture/conversational_retrieval_architecture.md`](file:///d:/dataspeak/docs/architecture/conversational_retrieval_architecture.md): Conversational AI Assistant workflow and data flow specification.

### Added — Phase 1 & 2: Extraction Engine & Hybrid Search
- **Multimodal Document Extraction Pipeline & Structure-Aware Router (`backend/ingestion/`)**:
  - Implemented structure-aware pre-flight evaluation routing digital text pages to fast CPU text parsers and escalating scanned/image pages to Google Gemini 2.5 Flash VLM OCR.
  - Added native multi-format support for `.pdf`, `.docx`, `.xlsx`, `.pptx`, `.csv`, `.html`, `.md`, and `.txt` files.
  - Implemented streaming file upload handling in `backend/routers/documents.py` with 100MB chunked disk writing and post-processing file cleanup.
  - Created HTML table matrix generation with placeholder anchoring (`[[TABLE_REF_001]]`) inside narrative text streams.
- **Hybrid Dense-Sparse RAG Search & Reciprocal Rank Fusion (`backend/search/`)**:
  - Created BM25Okapi sparse keyword index manager (`backend/search/bm25_index.py`) per tenant.
  - Implemented Reciprocal Rank Fusion (`backend/search/hybrid.py`) combining dense FAISS embeddings with sparse BM25 scores.
  - Added metadata pre-filtering (document IDs, content types, page numbers) to `/api/documents/search`.
- **Extended Database Models & Pydantic Schemas**:
  - Added `progress`, `error_message`, `total_pages`, `pages_processed`, `visual_pages` to `Document` model.
  - Added `page_number`, `content_type`, `section_heading`, `reference_id` to `DocumentChunk` model.

### Added — Phase 3: Frontend Progress & Search Filters
- **Per-File Progress Tracking & Dual Progress Bars (`UploadDocumentsPage.tsx`)**:
  - Replaced global single-jump progress state with `FileUploadState` tracking per-file HTTP upload progress via `XMLHttpRequest` and backend processing progress via 3-second polling.
  - Added dual progress bars (blue for HTTP upload, green for backend processing).
  - Added VLM vision badge (`🔍 {visualPages} pages sent to AI vision`) when visual pages are extracted.
  - Added individual file error banners with `Retry` action buttons.
  - Replaced embedding model dropdown with static label: `Sentence Transformers (all-MiniLM-L6-v2)`.
- **Granular Search Filters & Progress Visualization (`KnowledgeBasePage.tsx`)**:
  - Added search filter panel inside Test AI Query dialog: document multi-select, content type toggles (Text 📄, Table 📊, Image 🖼️), page range inputs, Hybrid vs. Semantic search mode switch.
  - Added inline progress bar for documents with `Processing` status in the main table.
  - Wired `Re-index` context menu button to `POST /api/documents/{id}/reindex` with Sonner toast notifications.
  - Added red error message subtitles for documents in `Failed` status.

### Added — Phase 4: Scalability & Hardening
- **Celery Task Queue & Async Processing (`backend/celery_app.py`, `backend/ingestion/task_queue.py`)**:
  - Configured Celery with Redis broker/backend and `BackgroundTasks` fallback when Redis unavailable.
  - Wrapped document ingestion and reindexing into retriable Celery tasks with isolated DB sessions.
  - Added `celery_task_id` and `embedding_model` fields to `Document` model.
- **Document Reindexing Endpoint (`backend/routers/documents.py`)**:
  - Added `POST /api/documents/{id}/reindex` for on-demand re-embedding from stored chunks.
- **Search Mode Control & Cross-Encoder Re-Ranking (`backend/search/hybrid.py`)**:
  - Added `search_mode` ("hybrid"/"semantic") and `re_rank` flags to `SearchQuery` schema.
  - Implemented MS-MARCO Cross-Encoder re-ranking for improved retrieval precision.
- **Embedding Model Migration Tool (`backend/scripts/migrate_embeddings.py`)**:
  - CLI script to re-embed all tenant chunks with target model (default: `BAAI/bge-small-en-v1.5`), rebuild FAISS & BM25 indices, with `--dry-run` mode.

### Planned / In Progress
- Implementation of remaining 25 enterprise database schema tables into `backend/models.py`.
- Dynamic SQL query generator with advanced schema-aware guardrails and parameterization.
- Live backend integration for Analytics, AI Insights, Usage metering, and Audit Logs pages.
- Embedded chat widget JS bundle compilation for external SaaS tenant websites.

---

## [v0.2.0] - 2026-08-05

### Added
- **AI Agent Context Standard (`AGENTS.md`)**: Single source of truth context file at project root providing technical stack breakdown, directory architecture maps, security guidelines, parameterization requirements, and pre-task context protocols for AI coding tools (Google Antigravity, Cursor, Copilot, Claude Code).
- **Consolidated Documentation Tree (`docs/`)**: Reorganized project documentation into structured subdirectories:
  - `docs/architecture/`: System design, workflow diagrams, and FYP roadmap plans.
  - `docs/database/`: Enterprise SQL schemas (`Full_Project_Schemas.sql`), ERDs, and visual EERD diagrams.
  - `docs/setup/`: System setup guides, guidelines, and environment setup instructions.
  - `docs/reports/`: Technical reports, module implementation walkthroughs, and mockup analysis documents.
  - `docs/sessions/`: Dedicated work session logs for developers and AI tools.
  - `docs/templates/`: AI task prompt delegation templates (`AI_TASK_TEMPLATE.md`).
- **Multi-Developer Context Tracking**:
  - `CHANGELOG.md`: Standardized version history and change log tracking.
  - `docs/sessions/README.md`: Session logging guidelines and standard format specifications.
  - `docs/templates/AI_TASK_TEMPLATE.md`: Standardized prompt template for team members delegating tasks to AI agents.

### Changed
- Relocated 20+ root documentation markdown files, SQL scripts, and diagram images into `docs/` subdirectories to establish a disciplined, clean root directory structure.
- Standardized API base URL environment variable on `VITE_API_BASE_URL` across frontend config (`src/app/config/api.ts`).

### Fixed
- Eliminated root directory clutter while retaining mandatory build and runtime configuration files (`package.json`, `vite.config.ts`, `index.html`, `postcss.config.mjs`, `proxy.js`, `.env.example`, `README.md`, `AGENTS.md`, `CHANGELOG.md`).

---

## [v0.1.0] - 2026-07-15

### Added
- **Natural Language to SQL (NL-to-SQL) Core Engine**:
  - Automated database schema introspection for SQLite, PostgreSQL, and MySQL.
  - FastAPI `/api/databases` router supporting connection creation, listing, deletion, schema inspection, connection testing, and 100-row table preview.
- **RAG & Vector Knowledge Base Engine**:
  - FAISS local vector index integrated with HuggingFace `SentenceTransformer` (`all-MiniLM-L6-v2`) embeddings.
  - LangChain `RecursiveCharacterTextSplitter` supporting fixed-size, paragraph, line, and sentence chunking strategies.
  - FastAPI `/api/documents` router for PDF upload, processing, vector indexing, and semantic similarity search.
- **Multi-Modal Document & Vision Extraction**:
  - Structured markdown table extraction via `pdfplumber`.
  - Image extraction using `PyMuPDF` (`fitz`).
  - Google Gemini 2.5 Flash API integration for visual OCR, chart interpretation, and diagram comprehension.
- **Multi-Tenant & User Management Backend**:
  - FastAPI microservice architecture (`backend/main.py`) using SQLAlchemy ORM and Pydantic v2 validation.
  - User authentication router (`/api/auth`) supporting registration, email/password login, bcrypt password hashing, and PyJWT token generation.
  - 6-digit email OTP verification and 3-step password recovery workflow.
  - GitHub OAuth 2.0 authentication integration.
  - Multi-tenant tenant configuration (`/api/tenant`) with team member invites and role management.
  - API key generation and management router (`/api/keys`) with key revocation.
  - Customizable chatbot widget configuration endpoint (`/api/chatbot-config`).
- **React Frontend Single-Page Application**:
  - React 18.3 + Vite 6 client built with TypeScript.
  - React Router v7 setup featuring 17 routes across landing, auth, admin, and dashboard modules.
  - Styling system powered by Tailwind CSS v4, MUI v7, Radix UI primitives, Framer Motion v12, and custom design tokens.
  - Data visualization dashboard with Recharts charts and Sonner toast feedback.
  - Dedicated pages for Databases, Knowledge Base, Document Upload, API Keys, Chatbot Customization, and Tenant Settings connected to live backend APIs.
- **Database Architecture & Specs**:
  - 10 core SQLAlchemy models (`Tenant`, `User`, `UserDatabaseAccess`, `TenantInvite`, `DatabaseConnection`, `ApiKey`, `ChatbotConfig`, `Document`, `DocumentChunk`, `PasswordResetOTP`) defined in `backend/models.py`.
  - Comprehensive 35-table enterprise SQL schema specification defined in `docs/database/Full_Project_Schemas.sql`.
