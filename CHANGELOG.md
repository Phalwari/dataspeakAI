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

- **Bug Fixes & Hardening (Widget Document Publication & Persistence - 2026-10-17)**:
  - **Payload & Schema Interoperability:** Resolved payload schema mismatch where frontend toggle sent singular `{ document_id: int }` while backend expected `{ document_ids: List[int] }` resulting in HTTP 422. Extended `WidgetKeyDocumentAssignRequest` in `backend/schemas.py` and `backend/routers/api_keys.py` to transparently accept both singular `document_id` and plural `document_ids`.
  - **State Persistence & Badge Synchronization:** Fixed response parsing of `published_document_ids` in `src/app/pages/dashboard/ChatbotWidgetPage.tsx` and `src/app/pages/dashboard/KnowledgeBasePage.tsx` so publication toggle state and `Widget Published` table badges remain accurate and persist upon navigation or page reload.
  - **Atomic Bulk Operations:** Added fast atomic bulk unpublish endpoint `DELETE /api/keys/widget/{key_id}/documents` in `backend/routers/api_keys.py` and connected it to "Unpublish All" in the dashboard.
  - **Verification:** Verified via targeted test suite `tests/test_nr1_widget_isolation.py::test_widget_key_documents` (both singular and plural payloads and bulk unpublish), 35 vitest unit tests, and production Vite build.

- **Phase NR-1: Sprint NR-1.1-B — Visitor Isolation & Public Knowledge Publication (`backend/models.py`, `backend/schemas.py`, `backend/services/widget_session_service.py`, `backend/services/widget_rate_limiter.py`, `backend/services/sql_engine.py`, `backend/services/sql_agent.py`, `backend/routers/widget.py`, `backend/routers/api_keys.py`, `backend/routers/documents.py`, `backend/routers/chat.py`, `backend/migrations/versions/005_widget_key_documents.py`, `src/widget/api.ts`, `src/widget/ui/WidgetApp.tsx`, `src/app/pages/dashboard/ChatbotWidgetPage.tsx`, `src/app/pages/dashboard/KnowledgeBasePage.tsx`, `src/widget/__tests__/sseParser.test.ts`, `tests/test_nr1_widget_isolation.py`, `tests/test_nr0_regressions.py`, `todo.md`)**:
  - **Security & Authorization (Visitor HMAC Session Binding & Continuity Resumption - NR-1.1-B-T01, T02, T03):**
    - Bound short-lived HMAC session claims in `backend/services/widget_session_service.py` to explicit ownership tuples `(tenant_id, widget_key_id, visitor_id, session_id)` with standard 60-minute expiration. Verified HMAC signatures on all widget chat and session requests, strictly extracting `tenant_id` exclusively from verified cryptographic claims.
    - Implemented 30-day HMAC visitor continuity token system (`sign_visitor_continuity_token`, `verify_visitor_continuity_token`) allowing legitimate visitors to resume their prior conversations while preventing cross-visitor conversation adoption. Unverified continuity proofs fall back silently to generating fresh isolated conversations.
    - Added strict anti-switching conversation guard in `POST /api/widget/chat` and `POST /api/chat/widget` asserting that request body `conversation_id` matches the signed HMAC session claims, rejecting mismatches with HTTP 403 Forbidden. Removed xfail marker from `test_probe_i02_widget_cannot_adopt_private_dashboard_conversation` in `tests/test_nr0_regressions.py`; Defect `I-02` permanently repaired and passing.
  - **Security & Rate Limiting (Pre-Allocation Session Limiting - NR-1.1-B-T04):**
    - Implemented pre-allocation token bucket rate limiting on `POST /api/widget/session` in `backend/services/widget_rate_limiter.py` enforcing thresholds of 30 req/min/IP and 60 req/min/key before any database records or conversation transactions are created.
    - Exceeded limits return HTTP 429 Too Many Requests with standard `Retry-After: 60` header and telemetry headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`). Added Redis cluster support with graceful in-memory fallback.
  - **Security & Knowledge Isolation (Document Membership & Publication Filtering - NR-1.1-B-T05, T06):**
    - Created `WidgetKeyDocument` association model in `backend/models.py` with composite primary key `(widget_key_id, document_id)` and foreign keys to `api_keys` and `documents`.
    - Generated versioned Alembic migration `backend/migrations/versions/005_widget_key_documents.py` executed cleanly on both development and test databases.
    - Added REST endpoints in `backend/routers/api_keys.py`: `GET /api/keys/widget/{key_id}/documents`, `POST /api/keys/widget/{key_id}/documents`, and `DELETE /api/keys/widget/{key_id}/documents/{doc_id}` with strict tenant validation. Newly uploaded documents in `backend/routers/documents.py` auto-publish to active widget keys while allowing explicit revocation.
    - Extended `retrieve_rag_chunks` in `backend/routers/chat.py` with `allowed_document_ids` filtering on dense FAISS vector search and sparse BM25 scoring before synthesis. Added pre-synthesis live DB status revalidation ensuring chunk IDs belong to active `status == "Completed"` document records, repairing Defect `I-13`.
  - **Security & SQL Table Grants Guardrails (NR-1.1-B-T07):**
    - Enforced database connection restrictions (`allowed_database_ids`) and table allowlists across the full SQL execution lifecycle for widget requests.
    - Bounded schema introspection in `get_db_schema_context` to only permitted tables, restricted NL-to-SQL prompt instructions, and validated AST identifiers in `validate_ast_identifiers` against allowed tables.
    - Protected existing security error messages in `process_widget_chat` from LLM fallback overwrite.
  - **Frontend UI & Widget SDK Renewal (NR-1.1-B-T08):**
    - Implemented proactive session renewal in `src/widget/api.ts` via `isSessionNearingExpiry` and `ensureActiveWidgetSession` renewing short-lived HMAC sessions at the 50-minute mark before 60-minute expiry using continuity tokens.
    - Integrated 5-minute background renewal check and send-time verification in `WidgetApp.tsx`.
    - Added dedicated "Published Knowledge" tab in `src/app/pages/dashboard/ChatbotWidgetPage.tsx` with granular toggle switches, bulk publish/unpublish actions, and real-time publication status badges.
    - Added publication status badges (`Widget Published` vs `Private`) in `src/app/pages/dashboard/KnowledgeBasePage.tsx`.
    - Authored unit tests in `src/widget/__tests__/sseParser.test.ts` (35 vitest tests pass) and verified clean production build in `npm run build` with 0 errors.

- **Phase NR-1: Sprint NR-1.1-A — Platform Authority, Permissions & Account Lifecycle (`backend/models.py`, `backend/migrations/versions/002_add_platform_admin.py`, `backend/migrations/versions/003_add_user_token_version.py`, `backend/migrations/versions/004_add_conversation_shares.py`, `backend/dependencies.py`, `backend/auth.py`, `backend/schemas.py`, `backend/main.py`, `backend/routers/users.py`, `backend/routers/tenants.py`, `backend/routers/chat.py`, `backend/routers/analytics.py`, `backend/scripts/seed_admin.py`, `src/app/pages/LoginPage.tsx`, `src/app/pages/dashboard/SettingsPage.tsx`, `src/app/components/DashboardLayout.tsx`, `src/app/pages/admin/AdminPanel.tsx`, `src/app/pages/dashboard/ChatPage.tsx`, `src/app/utils/permissions.ts`, `src/app/utils/__tests__/permissions.test.ts`, `tests/fixtures/nr0/synthetic_data.py`, `tests/test_nr0_regressions.py`, `tests/test_nr1_platform_admin.py`, `tests/test_nr1_permissions.py`, `tests/test_phase2_widget_keys_sessions.py`, `todo.md`)**:
  - **Security & Authorization (Effective Permissions UI, Platform Navigation & Non-Leaking Error Banners - NR-1.1-A-T09):**
    - Created pure permissions utility [`src/app/utils/permissions.ts`](file:///c:/Users/waliu/OneDrive%20-%20Higher%20Education%20Commission/Desktop/dataspeakAI/src/app/utils/permissions.ts) providing `canAccessPlatformAdmin`, `canModifyConversation`, `getConversationAccessBadge`, and `formatRoleName`, tested with 12 vitest unit tests in [`src/app/utils/__tests__/permissions.test.ts`](file:///c:/Users/waliu/OneDrive%20-%20Higher%20Education%20Commission/Desktop/dataspeakAI/src/app/utils/__tests__/permissions.test.ts).
    - Updated [`src/app/components/DashboardLayout.tsx`](file:///c:/Users/waliu/OneDrive%20-%20Higher%20Education%20Commission/Desktop/dataspeakAI/src/app/components/DashboardLayout.tsx) to conditionally render Platform Admin navigation in the sidebar and user avatar dropdown exclusively when `user.is_platform_admin === true`, and displayed role badges alongside platform admin status pills in the top bar.
    - Hardened [`src/app/pages/admin/AdminPanel.tsx`](file:///c:/Users/waliu/OneDrive%20-%20Higher%20Education%20Commission/Desktop/dataspeakAI/src/app/pages/admin/AdminPanel.tsx) with explicit platform authority checks and HTTP 403 response interceptors, replacing silent redirects and broken charts with a dedicated, typed HTTP 403 Permission Boundary screen displaying actionable navigation options ("Return to Dashboard", "Sign in as Operator").
    - Updated [`src/app/pages/dashboard/ChatPage.tsx`](file:///c:/Users/waliu/OneDrive%20-%20Higher%20Education%20Commission/Desktop/dataspeakAI/src/app/pages/dashboard/ChatPage.tsx) to reflect conversation creator ownership badges and shared status indicators (`Shared (Read-Only)` vs `Shared with Team`), enforced client-side permission guards on deletion and renaming, and rendered a clean read-only security banner replacing the chat input form for non-owners.
    - Verified all 32 vitest unit tests pass in `npm test`, Vite TypeScript production build succeeds with 0 errors, and backend pytest regression suites continue passing cleanly.
  - **Security & Authorization (Configured Dashboard Origin Allowlist & Decoupled Standalone Widget CORS - NR-1.1-A-T08):**
    - Implemented `get_dashboard_cors_origins()` and `DecoupledCORSMiddleware` in `backend/main.py`.
    - Decoupled dashboard origins (`CORS_ORIGINS` environment variable, defaulting to `http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000`) with credentials allowance from standalone widget endpoints (`/api/widget/*`, `/api/chat/widget`, `/widget.js`, `/embed/*`).
    - Eliminated wildcard `*` from credentialed dashboard origins; enforced runtime exception in production if invalid or wildcard-only origins are supplied.
    - Guaranteed credential-free responses on standalone widget visitor requests, stripping `Access-Control-Allow-Credentials` while retaining per-key origin authorization (`widget_key.allowed_origins`).
    - Authored 4 automated tests in `tests/test_nr1_permissions.py` (`test_cors_origin_policy_dashboard_authorized`, `test_cors_origin_policy_dashboard_unauthorized_rejected`, `test_cors_origin_policy_wildcard_elimination_in_allowlist`, `test_cors_origin_policy_widget_visitor_allowed_and_enforced`). All 37 permissions tests, 12 widget regression tests, and frontend production build pass cleanly.
  - **Security & Authorization (Dashboard Conversation Creator Privacy & Explicit Sharing - NR-1.1-A-T07):**
    - Added `ConversationShare` model in `backend/models.py` with foreign keys to `conversations`, `users` (`shared_with_user_id`, `granted_by_user_id`), and unique constraint on `(conversation_id, shared_with_user_id)`.
    - Created additive Alembic migration `backend/migrations/versions/004_add_conversation_shares.py` with clean upgrade and downgrade steps.
    - Added `ConversationShareRequest`, `ConversationShareResponse`, and updated `ConversationResponse`, `ConversationListItem`, and `ConversationUpdate` in `backend/schemas.py`.
    - Enforced private-by-default creator scoping in `backend/routers/chat.py`: dashboard conversations are accessible strictly to their creator (`user_id == current_user.id`) or explicitly shared users. Cross-tenant or unshared requests return HTTP 404 without disclosure (tenant admins do not automatically see member conversations).
    - Restricted unowned historic conversations (`user_id is None`) exclusively to tenant admins for inspection and reassignment via `PATCH /api/conversations/{id}`.
    - Implemented explicit read-sharing grant and revocation endpoints: `POST /api/conversations/{id}/share`, `GET /api/conversations/{id}/shares`, and `DELETE /api/conversations/{id}/share/{target_user_id}`.
    - Enforced read-only guardrails on shared conversations: shared members receive read access, while update, delete, and chat message posting attempts are rejected with HTTP 403 Forbidden.
    - Authored Section 6 tests in `tests/test_nr1_permissions.py` (4 comprehensive integration tests covering privacy by default, historic unowned admin access/reassignment, sharing lifecycle with 403 write protections and revocation, and input validation). All 33 permissions tests, 19 migration tests, and Vite production build passed cleanly.
  - **Security & Authorization (Production Seeding Decoupling & Credential Safeguards - NR-1.1-A-T06):**
    - Enforced strict production gate in `backend/scripts/seed_admin.py` raising `RuntimeError("Development seeding is strictly disabled when ENVIRONMENT=production.")` on any invocation in production mode.
    - Verified in `backend/main.py` that startup database seeding and DDL creation are strictly gated behind `ENVIRONMENT != "production"`.
    - Hardened `seed_superadmin()` in `backend/scripts/seed_admin.py` to preserve existing administrator accounts without resetting or modifying their passwords, while ensuring active, verified, and platform administrator flags.
    - Removed plaintext password print from `backend/scripts/seed_admin.py` console output.
    - Suppressed plaintext OTP codes in `backend/routers/users.py` from production server logs when no external email delivery provider is configured.
    - Conditionally gated the default administrator credentials quick-fill card on `src/app/pages/LoginPage.tsx` behind `import.meta.env.DEV`, stripping it completely from production bundles.
    - Documented production hardening checklist and safeguards in `AGENTS.md` Section 4.5.
    - Authored 3 unit/integration tests in `tests/test_nr1_platform_admin.py` (`test_seeding_production_gate`, `test_seeding_preserves_existing_password`, `test_otp_not_logged_in_production`); all 11 tests in the suite passed; 36 tests in regression suite passed with 0 failures; frontend production build succeeded with 0 errors.
  - **Security & Authorization (Account Status Enforcement & Token Versioning - NR-1.1-A-T05):**
    - Added `token_version = Column(Integer, default=1, nullable=False)` to `models.User` in `backend/models.py`.
    - Created versioned Alembic migration `backend/migrations/versions/003_add_user_token_version.py` with idempotent column creation and safe `1` server default.
    - Updated `get_current_user` in `backend/dependencies.py` to reject inactive accounts with HTTP 403 Forbidden and verify `tv` claim against `user.token_version`, raising HTTP 401 Unauthorized ("Session has been revoked. Please log in again.") on token mismatch.
    - Embedded `tv` claim in JWT access token payloads generated during `/api/auth/login` and `/api/auth/github-login`, with strict `is_active` validation rejecting disabled users.
    - Implemented immediate session revocation by bumping `user.token_version` on password changes (`/api/auth/change-password`), OTP password resets (`/api/auth/reset-password`), and administrative member deactivations (`PATCH /api/tenant/members/{user_id}`).
    - Authored Section 5 tests in `tests/test_nr1_permissions.py` (5 integration tests verifying inactive/unverified rejection, password change token invalidation, OTP reset token invalidation, and member deactivation session revocation). All 29 tests passing. Verified all 19 migration tests in `tests/test_nr0_migrations.py`.
  - **Security & Authorization (Member Invitation & Role Modification Validation - NR-1.1-A-T04):**
    - Enforced `require_tenant_admin` on `POST /api/tenant/invite`, `PATCH /api/tenant/members/{user_id}`, `PUT /api/tenant/current`, and `DELETE /api/tenant/members/{user_id}`, rejecting non-admin callers with HTTP 403 Forbidden.
    - Added strict whitelist role validation in `backend/schemas.py` (`InviteCreate` and `TenantMemberUpdate`) validating roles against `{"Admin", "Developer", "Business Owner", "Viewer"}` and normalizing legacy `"Team Member"` to `"Viewer"`, rejecting arbitrary or malicious role strings with HTTP 422 Unprocessable Entity.
    - Enforced tenant database connection scoping on member invitation and member update endpoints: all provided `database_ids` must belong to `current_user.tenant_id`, returning HTTP 404 on foreign or nonexistent connections without disclosing resource existence.
    - Protected tenant admin lifecycle by preventing self-removal and preventing demotion or removal of the last remaining tenant administrator.
    - Updated `src/app/pages/dashboard/SettingsPage.tsx` with a role selector dropdown for invitations.
    - Authored Section 4 tests in `tests/test_nr1_permissions.py` (6 integration tests covering non-admin rejection, invalid role rejection, valid role acceptance, cross-tenant database rejection, member role modification, and last admin demotion/removal protection). All 56 tests across the suite passed.
  - **Security & Authorization (Resource Resolution Policy & Route Scoping - NR-1.1-A-T03):**
    - Scoped `backend/routers/databases.py`: Introduced `get_accessible_connection` helper enforcing strict `tenant_id` filtering and non-admin explicit `UserDatabaseAccess` membership (returning HTTP 404 for foreign or unassigned databases); applied `require_source_manager` to add/delete/test endpoints and `require_query_executor` to table data preview.
    - Scoped `backend/routers/documents.py`: Applied `require_source_manager` to upload, delete, and reindex endpoints; applied `require_query_executor` to document search; added cross-tenant validation on `query.document_ids` returning HTTP 404 on invalid or foreign documents.
    - Scoped `backend/routers/chat.py`: Applied `require_query_executor` to `/api/chat`; enforced strict HTTP 404 on cross-tenant or missing `conversation_id` and explicit `database_id`.
    - Scoped `backend/routers/api_keys.py`: Applied `require_key_manager` across all 10 key endpoints; strictly validated that `allowed_database_ids` belong to `current_user.tenant_id`.
    - Scoped `backend/routers/analytics.py`: Applied `require_source_manager` to profiling and column mapping; applied `require_query_executor` to dashboard and unified source query endpoints.
    - Authored 7 comprehensive integration tests under Section 3 of `tests/test_nr1_permissions.py` verifying cross-tenant 404 isolation across databases, documents, chats, api keys, and analytics (all 26 tests in suite passing).
  - **Security & Authorization (Centralized Permission Matrix & Policy Dependencies - NR-1.1-A-T02):**
    - Defined central capability constants (`CAP_ADMIN_WRITES`, `CAP_SOURCE_GRANTS`, `CAP_QUERY_EXECUTE`, `CAP_KEY_MANAGEMENT`, `CAP_CONV_SHARE`) and role mapping (`ROLE_CAPABILITIES`) in `backend/auth.py`.
    - Implemented centralized policy evaluation functions in `backend/auth.py`: `can_manage_tenant`, `can_manage_sources`, `can_execute_queries`, `can_manage_keys`, `can_share_conversations`, `has_capability`, and `is_user_active`.
    - Created reusable FastAPI route dependencies in `backend/dependencies.py`: `require_tenant_admin`, `require_source_manager`, `require_query_executor`, `require_key_manager` raising typed HTTP 403 Forbidden on unauthorized roles.
    - Authored comprehensive automated test suite `tests/test_nr1_permissions.py` (11/11 tests passed in 0.28s) covering all role capability permutations, inactive account rejection, and TestClient route protection.
    - Verified full regression test suite: 50 passed, 5 strictly xfailed, 0 errors in 63.51s; frontend Vitest passed (20/20 in 3.22s); Vite production build passed (0 errors in 17.72s).
  - **Security & Authorization (Explicit Platform Administrator Authority - NR-1.1-A-T01 / Issue I-01):**
    - Added `is_platform_admin = Column(Boolean, default=False, nullable=False)` to `models.User` in `backend/models.py`.
    - Created versioned Alembic migration `backend/migrations/versions/002_add_platform_admin.py` with idempotent column creation and safe `False` default.
    - Updated `get_current_admin_user` in `backend/dependencies.py` to strictly require `is_platform_admin is True`, returning HTTP 403 Forbidden ("Platform administrator access required") to tenant administrators with `role="Admin"`.

- **Phase NR-0: Sprint NR-0.1-B — Establish Versioned Migrations & Close Phase NR-0 (`backend/alembic.ini`, `backend/migrations/`, `backend/scripts/schema_preflight.py`, `backend/scripts/migrate.py`, `backend/scripts/backfill_validator.py`, `backend/main.py`, `backend/scripts/seed_admin.py`, `render.yaml`, `docs/database/nr0_schema_reconciliation.md`, `docs/setup/nr0_migration_runbook.md`, `tests/fixtures/nr0/legacy_layouts.py`, `tests/test_nr0_migrations.py`, `todo.md`)**:
  - **Added (Schema Reconciliation & Legacy Layout Fixtures - NR-0.1-B-T01):** Reconciled 46 ORM models in `backend/models.py` with 35 canonical tables in `docs/database/Full_Project_Schemas.sql`, confirming 0 spec tables missing and 11 active operational tables. Authored reconciliation matrix in `docs/database/nr0_schema_reconciliation.md`. Created synthetic legacy layout generators (`LAYOUT_EMPTY`, `LAYOUT_LEGACY`, `LAYOUT_CURRENT`, `LAYOUT_UNSUPPORTED`) in `tests/fixtures/nr0/legacy_layouts.py`.
  - **Added (Alembic Versioned Migration Baseline & Read-Only Preflight - NR-0.1-B-T02):** Installed `alembic==1.20.0` into `.venv/` and `backend/requirements.txt`. Initialized Alembic configuration in `backend/alembic.ini`, `backend/migrations/env.py`, and `backend/migrations/versions/001_initial_baseline.py` covering all 46 models. Built read-only preflight engine in `backend/scripts/schema_preflight.py` with SHA-256 schema fingerprinting, sensitive URL redaction, and strict drift detection without DDL execution.
  - **Added (Installation & Upgrade Migration Controller - NR-0.1-B-T03):** Built CLI migration controller in `backend/scripts/migrate.py` supporting fresh installs (`LAYOUT_EMPTY` -> `alembic upgrade head`), safe adoption (`LAYOUT_CURRENT` -> `alembic stamp 001_initial_baseline`), transitional sync (`LAYOUT_LEGACY` -> stamp), and immediate abort on unsupported drift. Verified via 4 end-to-end tests in `tests/test_nr0_migrations.py`.
  - **Changed (Decoupled Production Startup DDL & Startup Gate - NR-0.1-B-T04):** Decoupled `Base.metadata.create_all`, unversioned schema sync, and admin seeding from production startup in `backend/main.py` and `backend/scripts/seed_admin.py`. In production mode (`ENVIRONMENT=production`), startup executes read-only preflight and aborts if schema layout is not `LAYOUT_CURRENT`. Updated `render.yaml` `startCommand` to execute `python backend/scripts/migrate.py upgrade` prior to web worker initialization.
  - **Added (Validated Additive Expansion & Backfill Utility - NR-0.1-B-T05):** Implemented reusable Expand-Backfill-Validate-Constrain utility in `backend/scripts/backfill_validator.py` with cursor-based pagination (`WHERE {key_col} > :last_key`), batch commits, zero credential leakage, and validation checks. Verified with 6 unit tests in `tests/test_nr0_migrations.py`.
  - **Added (Migration Runbook, Backup/Restore & Recovery Rehearsal - NR-0.1-B-T06):** Authored operational migration and disaster recovery runbook in `docs/setup/nr0_migration_runbook.md`. Rehearsed atomic SQLite backup/restore with 100% data and schema fidelity, safe migration upgrades, and full rollback (`alembic downgrade base` -> re-upgrade). Verified all 19 tests in `tests/test_nr0_migrations.py` passing.
  - **Closed Phase NR-0:** Milestone NR-0.1 is 100% complete (12/12 tasks verified and archived in `todo.md`). All 7 phase exit gates passed.

- **Phase NR-0: Sprint NR-0.1-A — Reproduce Findings and Align Backlog (`docs/reports/nr0_baseline.md`, `tests/conftest.py`, `tests/fixtures/nr0/`, `tests/test_nr0_isolation.py`, `tests/test_nr0_regressions.py`, `tests/test_phase2_stage_b_chat_widget.py`, `todo.md`)**:
  - **Added (Reproducible Baseline & Isolation Protocol - NR-0.1-A-T01):** Recorded Git HEAD commit `36f74a91233444935bede87bc852da1a15a9d668`, clean tree, Windows host environment, Node.js `v22.17.0`, npm `10.9.2`, and provisioned dedicated CPython `3.11.15` virtual environment at `.venv/`. Documented pre-collection isolation contract in `docs/reports/nr0_baseline.md`.
  - **Added (Pre-Collection Environment Isolation & Multi-Tenant Fixtures - NR-0.1-A-T02):** Established `tests/conftest.py` setting `ENVIRONMENT=test`, `DATABASE_URL=sqlite:///:memory:`, and `EMBEDDING_WARMUP=false` before test collection, neutralizing startup DDL/seeding side effects on `./app.db`. Built synthetic fixtures (`tests/fixtures/nr0/synthetic_data.py`) provisioning 2 tenants, 6 users (admin, analyst, inactive, unverified), private chats, widget keys, and synthetic documents. Verified 5/5 passing tests in `tests/test_nr0_isolation.py`.
  - **Added (Permanent Regression Probes with Strict XFAILs - NR-0.1-A-T03):** Authored `tests/test_nr0_regressions.py` covering all 6 mandatory audit probe families with strict expected failure markers (`@pytest.mark.xfail(strict=True)`):
    - `I-01`: Tenant Admin cross-tenant listing (`backend/routers/analytics.py`) -> strict XFAIL (owned by `NR-1.1-A`). Control passed.
    - `I-02`: Widget session adopting private dashboard chat (`backend/routers/widget.py`) -> strict XFAIL (owned by `NR-1.1-B`). Control passed.
    - `I-08`: SQL query LIMIT bypassing outer `max_rows` cap (`backend/services/sql_engine.py`) -> strict XFAIL (owned by `NR-1.2-B`). Control passed.
    - `I-11`: Grounding failure returning positive 0.7 confidence (`backend/services/citation_service.py`) -> strict XFAIL (owned by `NR-2.2-A`). Control passed.
    - `I-14`: Widget non-streaming double answer generation (`backend/routers/widget.py`) -> strict XFAIL (owned by `NR-2.3-A`).
    - `I-09`: KPI trend comparing total sum to row mean (900% phantom trend) (`backend/services/automl_service.py`) -> strict XFAIL (owned by `NR-2.1-A`). Control passed.
    - Verified 5 controls passed, 6 defects strictly XFAILED under Python 3.11.
  - **Fixed (Widget SSE Streaming Test Provider Isolation - NR-0.1-A-T04):** Patched `services.llm_generation_service.llm_gateway.generate_stream` in `tests/test_phase2_stage_b_chat_widget.py` with deterministic async generator double emitting known chunks. Verified offline test pass with ordered SSE token chunk assertions, terminal `done: true` event, and database message persistence.
  - **Verified (Python 3.11 & Frontend Baseline Execution - NR-0.1-A-T05):** Executed backend suite under Python 3.11.15 in `.venv` (11 passed, 6 xfailed, 0 errors in 202.69s). Executed frontend Vitest suite (20 passed in 6.53s) and frontend Vite production build (0 errors in 52.77s; recorded `index-DB2RLBm0.js`: 1,663.11 kB).
  - **Added (Legacy Crosswalk & Issue Coverage Map - NR-0.1-A-T06):** Documented Section 14 legacy crosswalk and mapped all 18 pathway issue families (I-01 to I-18) in `docs/reports/nr0_baseline.md`. Archived Sprint NR-0.1-A tasks in `todo.md`.


- **Phase 7: Sprint 7.2 Post-Audit Remediation & Hardening (`backend/routers/widget.py`, `backend/services/sql_engine.py`, `backend/services/chat_stream.py`, `backend/routers/chat.py`, `backend/schemas.py`, `backend/routers/documents.py`, `backend/services/sql_agent.py`, `backend/services/citation_service.py`, `src/app/pages/dashboard/ChatPage.tsx`, `AGENTS.md`)**:
  - **Security (Trusted Proxy IP Fallback - SEC-03):** Fixed `TRUSTED_PROXIES` empty string handling in `backend/routers/widget.py:get_client_ip` via `os.getenv("TRUSTED_PROXIES") or "127.0.0.1,::1"`, ensuring loopback IPs remain trusted even when the environment variable is present but empty. Passed `test_sec03_trusted_proxy_ip_validation`.
  - **Fixed (SQL Engine Logger Definition):** Added missing `import logging` and `logger = logging.getLogger("dataspeak.sql_engine")` to `backend/services/sql_engine.py`, resolving static analysis warnings.
  - **Added (Real-Time Grounding & SQL Agent Streaming Telemetry):** Extended `stream_chat_response` and `on_stream_complete` in `backend/routers/chat.py` to transmit verified `grounding` metrics and `sql_agent` self-correction metadata directly in the terminal SSE payload. Updated `ChatPage.tsx` to preserve `grounding` and `sql_agent` in React state upon stream completion.
  - **Refactored (Unified LLM Gateway Adoption):** Replaced legacy synchronous `requests.post()` calls in `backend/routers/widget.py` (`call_gemini_api`) and `backend/routers/chat.py` (SQL, RAG, and Hybrid non-streaming synthesis) with unified `llm_gateway.generate_sync()`, gaining quota rotation and cooldown failover across all generation pathways.
  - **Security (Vector Dimension Integrity Guard):** Enforced explicit HTTP 400 Bad Request in `backend/routers/documents.py:search_documents` on vector dimension mismatch between query embeddings and FAISS index dimension.
  - **Security (Model Slug Path Traversal Sanitization):** Sanitized `model_slug` in `backend/routers/documents.py:resolve_tenant_vector_index_path` using strict character whitelisting (`[^a-zA-Z0-9_\-\.]`) to prevent backslash/path escape on Windows and POSIX file systems.
  - **Added (MySQL Statement Execution Timeout in SQL Agent):** Added `SET SESSION MAX_EXECUTION_TIME=6000` to `execute_dry_run_rollback` in `backend/services/sql_agent.py` for MySQL and MariaDB dry-run transactions.
  - **Fixed (Source Citation Grounding Attributes):** Explicitly populated `grounding_score` and `is_grounded` boolean flags on all `SourceCitation` schemas constructed in `backend/services/citation_service.py:verify_grounding`.
  - **Standards & Documentation:** Added Section 4.10 "Agentic Self-Correcting SQL, Grounding Verification & Retrieval Precision Standard" to `AGENTS.md`.
  - **Verified (Production Readiness):** Full regression test suite passed with 487/487 tests (100% pass rate); 0 pyright static analysis errors; completed 0-error frontend production build (`npm run build` in 19.06s).

- **Phase 7: Sprint 7.2 — Agentic Querying & Retrieval Precision (`backend/services/sql_agent.py`, `backend/services/sql_engine.py`, `backend/models.py`, `backend/services/db_migration.py`, `docs/database/Full_Project_Schemas.sql`, `backend/ingestion/semantic_chunker.py`, `backend/services/citation_service.py`, `backend/schemas.py`, `backend/routers/documents.py`, `backend/routers/chat.py`, `src/app/pages/dashboard/ChatPage.tsx`, `tests/test_phase7_2_1_sql_agent.py`, `tests/test_phase7_2_2_hierarchical_chunking.py`, `tests/test_phase7_2_3_citation_grounding.py`, `tests/test_phase7_2_4_vector_versioning.py`)**:
  - **Added (Self-Correcting SQL Agent - Task 7.2.1):** Built `SQLAgent` in `backend/services/sql_agent.py` orchestrating an autonomous correction loop with `MAX_ATTEMPTS = 3`. Uses `sqlglot` for dialect-aware AST parsing, strict SELECT statement enforcement (disallowing multi-statement, DDL, and DML injection), and schema-aware identifier validation against database tables/columns.
  - **Added (Dialect-Safe Rollback Dry-Runs):** Implemented transaction-isolated dry-run testing using `SAVEPOINT` nested transactions with mandatory immediate rollback, trapping dialect-specific execution errors prior to live execution.
  - **Added (In-Flight Error Feedback Loop):** Automatically routes dialect compilation and database execution errors back to `LLMGateway` for in-flight self-correction, returning full correction trace and telemetry in `generate_sql_from_nl` and `/api/chat`.
  - **Added (Hierarchical Document Chunking - Task 7.2.2):** Extended canonical `DocumentChunk` model with self-referencing `parent_chunk_id` and `hierarchy_level` (0 = parent section, 1 = child chunk) via automated zero-dependency migrations in `db_migration.py` and synchronized `Full_Project_Schemas.sql`.
  - **Added (Semantic Boundary Chunking):** Created `SemanticHierarchicalChunker` in `backend/ingestion/semantic_chunker.py` preserving logical sections, paragraphs, and markdown tables as Level 0 parents (up to 2000 chars) while indexing Level 1 child chunks (up to 500 chars) for high-precision FAISS retrieval.
  - **Added (Parent Context Expansion in RAG):** Refactored `build_grounded_rag_context` in `backend/routers/chat.py` to automatically expand matched child chunks to their full parent context with deduplication, eliminating fragmented prompt excerpts.
  - **Added (Verifiable Source Grounding & Citations - Task 7.2.3):** Built `CitationService` in `backend/services/citation_service.py` extracting atomic factual claims, cleaning markdown table formatting, and computing vector cosine similarity against retrieved chunks (>0.65 threshold).
  - **Added (Automated Hallucination Disclaimers):** Computes overall response grounding status and attaches amber hallucination disclaimer warnings when aggregate confidence drops below 0.60.
  - **Added (Interactive Grounding UI):** Upgraded `ChatPage.tsx` with `Verified Grounding` / `Low Grounding` pills, `Self-Corrected (Attempt X)` query badge, percentage similarity match per source citation, and disclaimer alert banners.
  - **Added (Versioned Multi-Model Vector Storage - Task 7.2.4):** Implemented `resolve_tenant_vector_index_path` isolating FAISS indices by model slug (`vector_store/tenant_{id}_{model_slug}/index.faiss`) with seamless fallback to legacy unversioned path (`vector_store/tenant_{id}/`).
  - **Security (FAISS Vector Dimension Mismatch Guard):** Added pre-execution vector dimension validation (`vectorstore.index.d != query_vec.shape[1]`) returning safe HTTP 400 with actionable re-indexing guidance instead of causing fatal C++ SIGSEGV crashes.
  - **Added (Comprehensive Test Suites):** Authored 29 targeted unit and integration tests across `test_phase7_2_1_sql_agent.py` (8 tests), `test_phase7_2_2_hierarchical_chunking.py` (4 tests), `test_phase7_2_3_citation_grounding.py` (4 tests), and `test_phase7_2_4_vector_versioning.py` (4 tests).
  - **Verified (Production Readiness):** Passed 29/29 Phase 7 tests, 486 regression tests across the backend, and completed 0-error frontend production build (`npm run build` in 18.54s).

- **Phase 7: Sprint 7.1 — Real-Time Streaming, Conversation Memory & Dynamic Titles (`backend/services/chat_stream.py`, `backend/services/conversation_memory.py`, `backend/services/conversation_title.py`, `backend/routers/chat.py`, `backend/routers/widget.py`, `src/widget/api.ts`, `src/widget/ui/WidgetApp.tsx`, `src/app/pages/dashboard/ChatPage.tsx`, `tests/test_phase7_1_2_streaming_backend.py`, `src/widget/__tests__/sseParser.test.ts`, `tests/test_phase7_1_4_memory.py`, `tests/test_phase7_1_5_titles.py`)**:
  - **Added (True Token-Level SSE Streaming - Task 7.1.2):** Replaced artificial word delays and sleeps with unified `stream_chat_response` service. Emits real-time tokens directly from `LLMGateway.generate_stream()` for dashboard and widget chat.
  - **Added (Stream Disconnect & Resource Cleanup):** Periodic `request.is_disconnected()` checking and `GeneratorExit` handling cleanly terminates upstream generation, unconditionally releases widget stream slots, and protects tenant monthly quotas by deferring `Message` and `QueryLog` deduction to the `on_complete` callback.
  - **Added (Frontend Streaming & Abort Support):** Updated `ChatPage.tsx` and `WidgetApp.tsx` with typewriter token-by-token rendering, active thinking indicators, and Stop button wired to `AbortController.abort()`. Widget adheres to strict CSP (zero inline scripts/styles). Added 11 Vitest unit tests in `src/widget/__tests__/sseParser.test.ts`.
  - **Added (Startup Embedding Warmup):** Added non-blocking model preloading (`EMBEDDING_WARMUP=true`, defaults to false during tests) eliminating initial RAG cold-start lag.
  - **Added (Conversation Memory Management - Task 7.1.4):** Implemented `ConversationMemoryManager` with a sliding window of `MAX_RECENT_TURNS = 10` messages. Automated background LLM summarization compresses turns older than 10 once conversations exceed 15 turns. Prevented regressions via per-conversation locks and monotonically increasing `summary_turn_count`. Falls back cleanly without logging user text. Idempotent schema migration added `summary_text` and `summary_turn_count` to `Conversation`.
  - **Added (Dynamic Background Title Generation - Task 7.1.5):** Generates 3-6 word sanitized titles in a non-blocking background task following the first assistant turn. Preserves manual user renames and falls back safely to initial 6-word heuristic title on any failure.
  - **Added (Comprehensive Test Suites):** Created 9 tests in `test_phase7_1_2_streaming_backend.py`, 11 Vitest tests in `sseParser.test.ts`, 6 tests in `test_phase7_1_4_memory.py`, and 5 tests in `test_phase7_1_5_titles.py`.
  - **Measured Latency (TTFT):** RAG Time-To-First-Token achieved ~350ms – 510ms warm. Cold-start embedding model warmup measured at ~1200ms – 1800ms. SQL path streams explanation post-execution (TTFT ~680ms – 950ms) maintaining ACID dry-run AST safety.
  - **Security (Diagnostics Endpoint RBAC Guard):** Restricted `GET /api/system/llm-metrics` with `get_current_admin_user` dependency in `backend/main.py`. Unauthenticated visitors receive 401 Unauthorized, and non-admin tenant members receive 403 Forbidden.
  - **Fixed (SQL Engine Watchdog Deadlock Elimination):** Replaced context-managed `with ThreadPoolExecutor(...)` in `execute_safe_sql` (`backend/services/sql_engine.py`) with manual lifecycle control: `executor.shutdown(wait=False, cancel_futures=True)` on `TimeoutError` and in `finally`. This eliminates caller thread blocking when underlying database driver calls hang.
  - **Fixed (All-Keys-Cooling Fallback):** Updated candidate key selection in `backend/services/llm_generation_service.py` to allow cooling keys to be attempted in priority order if and only if all keys are currently in cooldown, ensuring zero hard stops during quota spikes.
  - **Fixed (Async Client Regression Test Alignment):** Updated `tests/test_fix_commit_issues_regression.py` to patch `httpx.AsyncClient.post` with `AsyncMock` alongside synchronous `httpx.post`, maintaining 100% test suite compatibility with async gateway routing.
  - **Optimized (Watchdog Test Execution Speed):** Added configurable `timeout_ceiling` parameter to `execute_safe_sql` and refactored `test_execute_safe_sql_watchdog_timeout` in `tests/test_phase7_sprint7_1_stage1.py` to complete in ~0.2s instead of 13s, slashing test suite execution time from 17.0s to 3.94s.
  - **Verified (100% Test Suite Baseline):** All 439 tests across the entire test suite pass with 0 errors.

- **Phase 7: Sprint 7.1 Stage 1 — Core AI Infrastructure & Safety Guards (`backend/services/llm_generation_service.py`, `backend/services/llm_metrics.py`, `backend/services/multi_llm.py`, `backend/services/sql_engine.py`, `backend/main.py`, `tests/test_phase7_sprint7_1_stage1.py`)**:
  - **Added (Unified Async LLM Gateway - Task 7.1.1):** Built `LLMGateway` in `backend/services/llm_generation_service.py` using non-blocking `httpx.AsyncClient`. Implemented thread-safe multi-key harvesting across `GEMINI_API_KEY*` and `GROQ_API_KEY*` (1..15+), round-robin quota rotation, and instant 429/403 failover with a 60-second quarantine cooldown registry. Provided backward-compatible synchronous bridge (`generate_sync()`) preventing breaking changes across existing services.
  - **Added (Real-Time Observability & Key Telemetry):** Created thread-safe `LLMMetrics` datastore in `backend/services/llm_metrics.py` tracking token consumption (prompt/completion), latency percentiles (average, p50, p95, p99), Time-To-First-Token (TTFT), error codes, provider/model distribution, active key health, and per-tenant cost attribution.
  - **Added (Diagnostics API Endpoint):** Exposed `GET /api/system/llm-metrics` in `backend/main.py` serving aggregated gateway telemetry and active key health summaries.
  - **Added (Per-Dialect Query Timeouts & Safety Guards - Task 7.1.3):** Updated `execute_safe_sql` in `backend/services/sql_engine.py` with engine statement timeouts across PostgreSQL (`options="-c statement_timeout=10000"`), MySQL (`SET SESSION max_execution_time=10000`), and SQLite (`timeout=10.0`, `PRAGMA busy_timeout = 10000;`, `PRAGMA query_only = ON;`).
  - **Security (Query Execution Watchdog Ceiling):** Wrapped query execution in a strict 12.0s fail-safe watchdog thread ceiling (`concurrent.futures.ThreadPoolExecutor`) to eliminate worker thread lockups on accidental Cartesian joins or runaway unindexed queries.
  - **Changed (NL-to-SQL Gateway Integration):** Refactored `generate_sql_from_nl` in `backend/services/sql_engine.py` to route through `llm_gateway.generate_sync` with automatic multi-key rotation and Groq failover, eliminating raw `requests.post()` and single `GEMINI_API_KEY` fragility.
  - **Added (Comprehensive Test Suite):** Authored 12 automated unit and regression tests in `tests/test_phase7_sprint7_1_stage1.py` with 100% pass rate covering telemetry recording, percentiles, key cooldowns, round-robin rotation, async generation, 429 failover, SSE stream chunking, and database statement timeouts.

- **Phase 7: Real-Time AI Intelligence & Agentic Core Architecture Established (`docs/architecture/ai_features_phase7_implementation_plan.md`, `todo.md`)**:
  - **Audited (Senior AI Engineer Architectural Review):** Conducted independent engineering audit of initial Phase 7 proposals, eliminating scope sprawl (rejected stateful WebSockets, voice/Whisper, and ad-hoc plugin registries) in favor of high-leverage enterprise priorities scoped into two focused sprints:
  - **Sprint 7.1 (AI Infrastructure, Resilience & Real-Time Streaming - P0):** Consolidated LLM generation services into a unified async gateway (`LLMGateway`) with thread-safe multi-key rotation (Gemini + Groq), true token-level SSE streaming (<500ms TTFT with native `AbortController` cancellation), conversation sliding-window memory with auto-summarization, and per-dialect statement timeout guards (PostgreSQL, MySQL, SQLite).
  - **Sprint 7.2 (Agentic Querying & Retrieval Precision - P1):** Architected self-correcting SQL execution agent using `sqlglot` AST safety validation and isolated `SAVEPOINT` transaction rollback dry-runs, hierarchical document chunking extending canonical `DocumentChunk` (`parent_chunk_id`, `hierarchy_level`), verifiable source citations with semantic grounding scores, and versioned multi-model FAISS index storage (`faiss_{tenant_id}_{model}.bin`) preventing vector dimension collision crashes.

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
