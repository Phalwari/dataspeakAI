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

<!-- next-release-workflow:start -->
## Next-release planning and execution

**Workflow adopted: 2026-10-16.** Use this structure for new work mapped from [Next Release Implementation Pathway](docs/next_release_implementation_pathway.md). The pathway defines the delivery plan; this file tracks executable tasks and verified completion.

**Preserve previous records:** The existing backlog, Phase 6/7 entries, and archived completion records below remain intact. Do not renumber them, rewrite their historical claims, or treat their checkboxes as proof that a new release task is complete. Apply the new structure to future plans. Use the pathway's section 14 crosswalk to link overlapping legacy work instead of creating competing implementations.

### Release and phase navigation

| Release | Phases | Intended outcome |
|---|---|---|
| NR1 — Secure and Reliable Core | NR-0, NR-1, NR-2, NR-3 | Foundations, security, correctness, and release operations |
| NR2 — Better Analyst Experience | NR-4 | Analyst capabilities built on the verified core |
| NR3 — Automation and Enterprise Capabilities | NR-5 | Governed automation and enterprise capabilities |

The default planning sequence is **NR-0 → NR-1 → NR-2 → NR-3 → NR-4 → NR-5**. Actual task dependencies take priority over phase numbers. For example, the storage/job contract in NR-3.1-A is needed before NR-2.2-B production ingestion integration. There is no NR-6 in the current pathway. These identifiers are separate from the historical Phase 6/7 records below.

### Planning session: map one whole phase

1. Read the user-selected phase, its sprint prerequisites and release gates, pathway section 14, [AGENTS.md](AGENTS.md), [CHANGELOG.md](CHANGELOG.md), this tracker, and relevant session notes. Use Graft and the current source to verify what exists; do not rely on old comments or completion claims.
2. Populate the **Selected phase work area** below with the whole selected phase, grouped as **Phase → Milestones → Sprints → Tasks**. Preserve exact roadmap IDs, including task IDs such as `NR-0.1-A-T01`. If a task needs smaller steps, retain its parent ID and acceptance criteria.
3. Make each task self-contained: include its purpose, implementation steps, target components, dependencies, acceptance criteria, verification, and any migration or recovery requirements. Record the current baseline revision and working directory so another session can resume.
4. Resolve prerequisites to exact task IDs or an explicitly defined contract gate with its producing tasks and verification evidence. Check both active tasks and the archive. Include any required work brought forward from another phase in a separate prerequisite group, with its original IDs and reason; do not silently expand to that entire phase.
5. Use pathway section 14 to reference overlapping legacy items. Keep a single implementation owner and state which part of the old item the new task covers. Do not close an entire legacy task when only part of its acceptance criteria is covered.
6. Check for duplicate IDs, missing prerequisites, dependency cycles, and conflicting file ownership. Identify the first ready task. If a prerequisite is unresolved, record the blocker instead of inventing a completion.
7. Set the planning status to `Ready for implementation` only after the selected phase has been mapped and checked. Mapping tasks does not complete them or start application implementation. Preserve unrelated pending tasks and all previous completion records.

### Implementation session: execute by dependency readiness

- Read the selected-phase metadata and latest files first. Work within the selected phase and its explicitly mapped prerequisites. When executing a selected NR phase, do not fall through to unrelated legacy tasks.
- Select an unchecked task whose prerequisites are completed and verified. Among ready tasks, follow P0 → P1 → P2 → P3, then the planned milestone/sprint order. Dependencies always come before priority or numerical order.
- Claim the task with an owner, working directory/branch, owned files, and last update. Confirm that another agent is not already editing those files. A stale progress note alone is not an active claim.
- Implement the task, check its acceptance criteria, and run the applicable verification required by AGENTS.md and the pathway. A successful build alone does not establish security, numerical correctness, or recovery behavior.
- Keep an unfinished task unchecked, including when code is written but verification is incomplete. Record failures or external blockers; continue with other ready tasks when safe.
- After each verified completion, revisit blocked tasks. A dependency being completed makes a dependent task eligible to start; it does not complete that dependent task automatically.
- On completion, follow the existing maintenance protocol: mark the item `[x]`, add completion metadata, and move the **entire task block**, including its ID, dependencies, acceptance criteria, and verification evidence, into the existing **Archived / Completed Tasks** section. Add required changelog/progress/handoff records for the implementation.
- Resolve future dependencies against archived task IDs and their evidence. Keep a milestone/sprint completion summary in the selected phase area instead of leaving checked task copies there.
- Continue until the selected phase and its exit checks are complete, or no remaining task can proceed. If blocked, record the exact missing prerequisite, failed check, or external decision and the next useful action.
- Before advancing to another phase, verify the current phase's exit criteria and relevant release gates. A completed phase is not automatically a released product.

### Checkbox and task-state rules

| Checkbox / state | Meaning |
|---|---|
| `[ ]` / `Ready` | Prerequisites verified; task can be claimed |
| `[ ]` / `Blocked` | A named prerequisite or external requirement is missing |
| `[ ]` / `In progress` | An identified owner is implementing the task |
| `[ ]` / `Needs verification` | Changes exist but required checks or review are incomplete |
| `[x]` / `Completed` | Acceptance and verification passed; full task block is archived |

Readiness is derived from dependencies and current evidence, not just the written state label. `Depends on: None` must be explicit. Missing, failed, or unverified dependencies never count as complete. Historical entries retain their existing format.

### Selected phase work area

| Field | Current value |
|---|---|
| Selected release / phase | NR1 / NR-1 — Repair security and query safety |
| Planning status | In progress — Milestone NR-1.1 (Sprints NR-1.1-A and NR-1.1-B, 17 tasks) completed & verified (100%); Milestone NR-1.2 active (Sprint NR-1.2-A ready to execute) |
| Baseline revision / working directory | `b323adb7128cf7888adcfbe0ce72faefcebf1087` (branch `main`) / `c:\Users\waliu\OneDrive - Higher Education Commission\Desktop\dataspeakAI` |
| Planner / implementation owner / reviewer | Antigravity AI Engineer (planning & execution) / verified |
| First ready task | NR-1.2-A-T01 — Inventory connection creation/testing/reflection/preview/query consumers and introduce a structured shared factory |
| Last update | 2026-10-17 — Sprint NR-1.1-B completed & verified (100%); Milestone NR-1.1 100% complete; NR-1.2-A-T01 ready to execute |

Insert the selected phase's actual milestone, sprint, and task blocks here, before the template below. Keep any brought-forward prerequisites in a clearly labeled group. When changing phases, retain previous phase summaries and unresolved work; completed task records stay in the existing archive. The template below is illustrative and must never be treated as executable work.

<!-- phase-nr1-plan:start -->
### Phase NR-1 — Repair security and query safety

- **Release / source:** NR1 — Secure and Reliable Core; [pathway Phase NR-1](docs/next_release_implementation_pathway.md#phase-nr1), [Milestone 1.1](docs/next_release_implementation_pathway.md#nr-11-a), [Milestone 1.2](docs/next_release_implementation_pathway.md#nr-12-a).
- **Planning status:** In progress. Milestone NR-1.1 (Tasks NR-1.1-A-T01 through T09 and NR-1.1-B-T01 through T08, 17 tasks) completed & verified (100%); Milestone NR-1.2 active (Sprint NR-1.2-A ready); 35 tasks mapped.
- **Goal:** Every caller receives only the resources and operations it is permitted to use; public widget enablement and production deployment remain gated until boundary and query-safety tests pass.
- **Baseline:** `b323adb7128cf7888adcfbe0ce72faefcebf1087`, branch `main`, working directory `c:\Users\waliu\OneDrive - Higher Education Commission\Desktop\dataspeakAI`; verified Phase NR-0 foundation and isolated migration lifecycle.
- **Planner / owners:** Antigravity AI Engineer (planning & execution).
- **Brought-forward prerequisites:**
  - `NR-0.1-A`: Pre-collection isolated test environment (`tests/conftest.py`, `tests/fixtures/nr0/synthetic_data.py`), permanent audit regressions (`tests/test_nr0_regressions.py`), and offline SSE stream test (`tests/test_phase2_stage_b_chat_widget.py`). Needed to guarantee isolated test execution without touching real database files or live LLM credentials.
  - `NR-0.1-B`: Versioned Alembic migration baseline (`backend/migrations/versions/001_initial_baseline.py`), read-only preflight engine (`backend/scripts/schema_preflight.py`), controlled migration runner (`backend/scripts/migrate.py`), and additive backfill validator (`backend/scripts/backfill_validator.py`). Needed to ensure all Phase NR-1 schema additions (`is_platform_admin`, `widget_key_documents`, hashed API keys, encrypted credentials) use tested, reversible Alembic migrations.
- **Scope:** Platform authority separation (`is_platform_admin`), tenant role matrix & RBAC enforcement, cross-tenant isolation on all routes, account verification/session revocation, safe operator seeding without production auto-reset, private-by-default dashboard conversations, strict CORS origin policies, visitor-bound widget sessions and key publication filtering, shared database connection factory with egress/SSRF protection & credential encryption, and unified dialect-safe query execution with mandatory outer LIMIT caps.
- **Scope boundaries:** Phase NR-1 does not build Phase NR-2 numerical KPI recipes or grounding models, nor Phase NR-4 analyst features. Do not build custom plugin registries or stateful WebSockets.
- **Exit criteria:**
  - Audit defects I-01, I-02, I-03, I-04, I-05, I-06, I-07, I-08, I-13, and connection/result portions of I-16 are completely repaired and their regression tests pass.
  - Tenant Admins cannot access platform telemetry or global tenants.
  - Private dashboard conversations are inaccessible to other members and tenant admins unless explicitly shared.
  - Widget visitors cannot switch sessions, read dashboard chats, or access unpublished documents.
  - Database connections are strictly validated against SSRF/loopback, encrypted with versioned envelopes, and credentials scrubbed from API outputs.
  - Query executor enforces outer LIMIT cap (100 rows), read-only transaction mode, and AST validation across all dialects.

#### Milestone NR-1.1 — Identity and resource ownership

##### Sprint NR-1.1-A — Platform authority, permissions, and account lifecycle

- **Prerequisites:** NR-0.1-A (verified in `tests/test_nr0_isolation.py`), NR-0.1-B (migrations verified in `tests/test_nr0_migrations.py`).
- **Issues Owned:** I-01, I-03, I-06.
- **Targets:** `backend/models.py`, `backend/dependencies.py`, `backend/auth.py`, `backend/routers/users.py`, `backend/routers/tenants.py`, `backend/routers/analytics.py`, `backend/routers/chat.py`, `backend/schemas.py`, `backend/scripts/seed_admin.py`, `src/app/pages/LoginPage.tsx`.
- **Exit checks:** Tenant Admin cannot list platform tenants or system metrics; role changes validated; inactive/unverified users rejected; dashboard chats private by default; development credentials decoupled from production.

- [x] **NR-1.1-A-T01 — Add explicit platform-administrator authority, default false; allow assignment only through controlled operator provisioning**
  - *Completed:* 2026-10-16 | Antigravity AI Engineer | Explicit platform authority added to models and migrations; I-01 repaired & verified (Full record archived in `## 📦 Archived / Completed Tasks`)

- [x] **NR-1.1-A-T02 — Define a permission matrix using existing tenant roles/memberships: administrative writes, source grants, query/read operations, key management, and sharing**
  - *Completed:* 2026-10-16 | Antigravity AI Engineer | Centralized capability policy functions and FastAPI dependencies implemented and verified (Full record archived in `## 📦 Archived / Completed Tasks`)

- [x] **NR-1.1-A-T03 — Inventory every route and apply the policy at resource resolution, including alternate connection/chat/analytics endpoints**
  - *Completed:* 2026-10-16 | Antigravity AI Engineer | Strict tenant scoping and RBAC route enforcement applied across all 5 routers; 7 resource resolution integration tests verified (Full record archived in `## 📦 Archived / Completed Tasks`)

- [x] **NR-1.1-A-T04 — Restrict invitation/role changes, validate role values, and verify all assigned database IDs belong to the tenant**
  - *Completed:* 2026-10-16 | Antigravity AI Engineer | Enforced require_tenant_admin, role whitelist validation, foreign DB scoping, and last-admin protections; verified with 6 tests (Full record archived in `## 📦 Archived / Completed Tasks`)

- [x] **NR-1.1-A-T05 — Reject inactive users, enforce verification policy, and add revocable session/token versioning for disablement/password recovery**
  - *Completed:* 2026-10-16 | Antigravity AI Engineer | token_version added, Alembic migration 003, is_active check, revocable JWTs on password change/reset/deactivation; verified with 5 tests (Full record archived in `## 📦 Archived / Completed Tasks`)

- [x] **NR-1.1-A-T06 — Make development seeding explicit and disabled in production; never reset an existing password on startup; remove production quick-fill and credential/OTP logging**
  - *Completed:* 2026-10-16 | Antigravity AI Engineer | Production gate added to seed_superadmin, existing password preserved on startup, import.meta.env.DEV gate on login auto-fill, plaintext passwords and OTPs suppressed from production logs; verified with 3 tests in test_nr1_platform_admin.py and npm build (Full record archived in `## 📦 Archived / Completed Tasks`)

- [x] **NR-1.1-A-T07 — Enforce creator ownership on dashboard chat listing/read/update/delete; add explicit read-sharing grants with revoke behavior**
  - *Completed:* 2026-10-16 | Antigravity AI Engineer | Private-by-default creator scoping, historic unowned admin scoping/reassignment, and ConversationShare read-only grants with revocation implemented and verified (Full record archived in `## 📦 Archived / Completed Tasks`)

- [x] **NR-1.1-A-T08 — Apply a configured dashboard origin allowlist; retain separately enforced widget-origin policy**
  - *Completed:* 2026-10-16 | Antigravity AI Engineer | Decoupled dashboard CORS allowlist with credentials from credential-free standalone widget visitor endpoints; verified via 4 tests in test_nr1_permissions.py (Full record archived in `## 📦 Archived / Completed Tasks`)

- [x] **NR-1.1-A-T09 — Update navigation, controls, and error messages for effective permissions without treating hidden buttons as security**
  - *Completed:* 2026-10-17 | Antigravity AI Engineer | Pure permissions utility, effective platform authority navigation, typed HTTP 403 error screens in AdminPanel, and conversation ownership/sharing indicators in ChatPage implemented and verified (Full record archived in `## 📦 Archived / Completed Tasks`)

##### Sprint NR-1.1-B — Visitor isolation and public knowledge publication

- **Prerequisites:** NR-1.1-A policy contracts, NR-0.1-B migrations.
- **Issues Owned:** I-02, I-13; session-creation abuse protection.
- **Targets:** `backend/routers/widget.py`, `backend/routers/chat.py`, `backend/models.py`, `backend/schemas.py`, `backend/services/widget_session_service.py`, `src/widget/`.
- **Exit checks:** Anonymous widget visitor cannot bind to or read private dashboard chats; widget publishable keys filtered by allowed origins; rate limits enforced; documents private by default.

- **Status:** Completed & Verified (100%). All 8 tasks (NR-1.1-B-T01 through NR-1.1-B-T08) verified against acceptance criteria and regression suites (20 pytest tests pass, 35 vitest tests pass, Vite production build succeeds with 0 errors). Widget knowledge publication schema and state synchronization bugfix verified on 2026-10-17. Full task blocks archived in `## 📦 Archived / Completed Tasks`.

- [x] **NR-1.1-B-T01 — Persist a widget/visitor ownership binding and bind signed session claims to that ownership**
  - *Completed:* 2026-10-17 | Antigravity AI Engineer | HMAC session claims bound to (tenant_id, widget_key_id, visitor_id, session_id); verified via test_session_token_binding (Full record archived in `## 📦 Archived / Completed Tasks`)

- [x] **NR-1.1-B-T02 — Create a new conversation for a new visitor; permit resumption only with valid signed continuity proof**
  - *Completed:* 2026-10-17 | Antigravity AI Engineer | 30-day HMAC continuity token, visitor-bound conversation creation, verified resumption; verified via test_visitor_conversation_continuity (Full record archived in `## 📦 Archived / Completed Tasks`)

- [x] **NR-1.1-B-T03 — Reject a chat request whose conversation ID differs from the signed/authorized conversation; revalidate key status and origins**
  - *Completed:* 2026-10-17 | Antigravity AI Engineer | Strict session conversation guard, origin revalidation, Defect I-02 permanently repaired and passing; verified via test_conversation_switching_prevented and test_probe_i02 (Full record archived in `## 📦 Archived / Completed Tasks`)

- [x] **NR-1.1-B-T04 — Rate-limit session creation before creating records; integrate with shared production limiting**
  - *Completed:* 2026-10-17 | Antigravity AI Engineer | Pre-allocation token bucket limiter (30 req/min/IP, 60 req/min/key) with Retry-After headers; verified via test_session_rate_limiter (Full record archived in `## 📦 Archived / Completed Tasks`)

- [x] **NR-1.1-B-T05 — Extend existing collections with explicit document membership/publication assignments to widget keys**
  - *Completed:* 2026-10-17 | Antigravity AI Engineer | WidgetKeyDocument model, migration 005_widget_key_documents, CRUD API endpoints, auto-publish default on upload; verified via test_widget_key_documents (Full record archived in `## 📦 Archived / Completed Tasks`)

- [x] **NR-1.1-B-T06 — Apply publication filtering before context enters the LLM, then revalidate selected evidence against current records**
  - *Completed:* 2026-10-17 | Antigravity AI Engineer | Hybrid RAG retrieval filtering by allowed_document_ids, pre-synthesis live DB status revalidation, Defect I-13 repaired; verified via test_widget_rag_publication_filter (Full record archived in `## 📦 Archived / Completed Tasks`)

- [x] **NR-1.1-B-T07 — Validate widget database/table grants before SQL generation, repair, and dry-run execution**
  - *Completed:* 2026-10-17 | Antigravity AI Engineer | SQL allowance check, schema context table filtering, prompt restriction, AST identifier validation, LLM fallback overwrite protection; verified via test_widget_sql_table_grants (Full record archived in `## 📦 Archived / Completed Tasks`)

- [x] **NR-1.1-B-T08 — Update SDK bootstrap/renewal/reset behavior and provide tenant preview/publish/unpublish controls**
  - *Completed:* 2026-10-17 | Antigravity AI Engineer | Proactive SDK session renewal at 50-minute mark before 60-min expiry, background check in WidgetApp, published knowledge tab with bulk actions in ChatbotWidgetPage, publication indicators in KnowledgeBasePage; verified via 35 vitest tests and npm run build (Full record archived in `## 📦 Archived / Completed Tasks`)

#### Milestone NR-1.2 — Shared connection and execution policy

##### Sprint NR-1.2-A — Connection factory and secret lifecycle

- **Prerequisites:** NR-0.1-B migrations; NR-1.1-A source-permission contract.
- **Issues Owned:** I-04, I-05, I-06; connection portion of I-16.
- **Targets:** `backend/services/connection_factory.py`, `backend/routers/databases.py`, `backend/routers/api_keys.py`, `backend/models.py`, `backend/schemas.py`.
- **Exit checks:** Outbound DB connections validate target host against SSRF/RFC 1918 subnets; credentials encrypted at rest with Fernet; passwords omitted from responses; API keys hashed at rest.

- [ ] **NR-1.2-A-T01 — Inventory connection creation/testing/reflection/preview/query consumers and introduce a structured shared factory**
  - **Priority / state:** P0 / Ready.
  - **Owner / reviewer:** Antigravity AI Engineer / unassigned.
  - **Depends on:** `NR-1.1-A-T02` (Completed & Verified).
  - **Blocks:** `NR-1.2-A-T02`, `NR-1.2-A-T05`, `NR-1.2-B-T01`.
  - **Source / related work:** Milestone 1.2; Section 14 crosswalk.
  - **Problem and expected outcome:** Multiple ad-hoc `create_engine` call sites exist across `databases.py`, `sql_engine.py`, `erd_service.py`. Consolidate all database connection instantiations into a centralized `DatabaseConnectionFactory`.
  - **Target files / components:** `backend/services/connection_factory.py`, `backend/routers/databases.py`, `backend/services/sql_engine.py`, `backend/services/erd_service.py`.
  - **Implementation:**
    1. Implement `DatabaseConnectionFactory` class managing connection pools, validation, and lifecycle.
    2. Replace all ad-hoc `create_engine` calls in `databases.py`, `sql_engine.py`, and `erd_service.py` with factory calls.
    3. Enforce tenant ownership checks on every connection request in the factory.
  - **Acceptance criteria:** All connection consumers route through `DatabaseConnectionFactory.get_engine(connection_id, tenant_id)`; no direct ad-hoc `create_engine(connection_string)` calls remain.
  - **Verification:** Execute `pytest tests/test_nr1_connection_security.py -k test_connection_factory`.
  - **Migration / rollout / recovery:** None.

- [ ] **NR-1.2-A-T02 — Validate driver, host, port, connection-string options, and resolved IPv4/IPv6 addresses on connection attempts; DNS failure denies connection**
  - **Priority / state:** P0 / Blocked (by `NR-1.2-A-T01`).
  - **Owner / reviewer:** Antigravity AI Engineer / unassigned.
  - **Depends on:** `NR-1.2-A-T01`.
  - **Blocks:** `NR-1.2-A-T03`, `NR-1.2-A-T04`.
  - **Source / related work:** Repairs `I-05` (Database SSRF vulnerability); Section 14 connection SSRF crosswalk.
  - **Problem and expected outcome:** External database connection strings can point to private subnets or cloud metadata services. Enforce strict IP resolution and rejection of loopback, link-local, and RFC 1918 private subnets.
  - **Target files / components:** `backend/services/connection_factory.py`, `backend/routers/databases.py`.
  - **Implementation:**
    1. Parse connection host and port; resolve to IPv4/IPv6 addresses using `socket.getaddrinfo`.
    2. Deny connection if DNS resolution fails.
    3. Block loopback (`127.0.0.0/8`, `::1`), link-local (`169.254.0.0/16`), AWS metadata (`169.254.169.254`), and private subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`) unless `ALLOW_PRIVATE_DB_HOSTS=true`.
  - **Acceptance criteria:** Rejects loopback, link-local, and private RFC 1918 subnets unless `ALLOW_PRIVATE_DB_HOSTS=true`. DNS resolution failure immediately denies connection. Defect I-05 repaired.
  - **Verification:** Execute `pytest tests/test_nr1_connection_security.py -k test_ssrf_validation`.
  - **Migration / rollout / recovery:** None.

- [ ] **NR-1.2-A-T03 — Enforce production network egress policy as a second boundary; avoid a DNS check followed by an unrelated unrestricted resolution**
  - **Priority / state:** P1 / Blocked (by `NR-1.2-A-T02`).
  - **Owner / reviewer:** Antigravity AI Engineer / unassigned.
  - **Depends on:** `NR-1.2-A-T02`.
  - **Blocks:** None.
  - **Source / related work:** Milestone 1.2; AGENTS.md Section 4.7.
  - **Problem and expected outcome:** Prevent DNS rebinding attacks where hostname resolves to public IP during validation but private IP during socket connect. Pin resolved IP or validate connection socket address before transmitting credentials.
  - **Target files / components:** `backend/services/connection_factory.py`.
  - **Implementation:**
    1. Pin resolved IP in connection options or supply custom dialect connection creator callable connecting to the validated IP.
    2. Pass original hostname in TLS SNI extension to ensure SSL certificate verification remains intact.
  - **Acceptance criteria:** Connection engine connects strictly to the pre-validated socket address or enforces custom dialect connection creator with IP pinning.
  - **Verification:** Execute `pytest tests/test_nr1_connection_security.py -k test_dns_rebinding_prevention`.
  - **Migration / rollout / recovery:** None.

- [ ] **NR-1.2-A-T04 — Disable arbitrary server-path SQLite in SaaS mode; for approved local use, resolve paths against a managed root and reject symlink/junction escapes**
  - **Priority / state:** P1 / Blocked (by `NR-1.2-A-T02`).
  - **Owner / reviewer:** Antigravity AI Engineer / unassigned.
  - **Depends on:** `NR-1.2-A-T02`.
  - **Blocks:** None.
  - **Source / related work:** Milestone 1.2; Grill-Me alignment.
  - **Problem and expected outcome:** External SQLite connection strings can point to arbitrary host paths (e.g. `/etc/passwd` or `./app.db`). In production, disable customer SQLite files. In development, restrict SQLite paths to `./data/sqlite_dbs/` with strict path traversal (`..`) rejection.
  - **Target files / components:** `backend/services/connection_factory.py`, `backend/routers/databases.py`.
  - **Implementation:**
    1. In SaaS production mode (`ENVIRONMENT=production`), disable creation of external customer SQLite connections.
    2. In development mode, restrict SQLite database files strictly to `./data/sqlite_dbs/`.
    3. Reject any SQLite file path containing traversal sequences (`..`), symlinks, or absolute system paths.
  - **Acceptance criteria:** In production mode, customer SQLite file connections return HTTP 400 Bad Request. In dev mode, paths outside managed directory or containing `..` are rejected.
  - **Verification:** Execute `pytest tests/test_nr1_connection_security.py -k test_sqlite_managed_boundary`.
  - **Migration / rollout / recovery:** None.

- [ ] **NR-1.2-A-T05 — Build relational URLs with SQLAlchemy URL objects, honoring configured ports and literal credentials**
  - **Priority / state:** P1 / Blocked (by `NR-1.2-A-T01`).
  - **Owner / reviewer:** Antigravity AI Engineer / unassigned.
  - **Depends on:** `NR-1.2-A-T01`.
  - **Blocks:** `NR-1.2-A-T06`.
  - **Source / related work:** Milestone 1.2.
  - **Problem and expected outcome:** Building connection strings via string formatting breaks when passwords contain `@`, `:`, `/`, or `%`. Standardize on `sqlalchemy.engine.URL.create()`.
  - **Target files / components:** `backend/services/connection_factory.py`, `backend/routers/databases.py`.
  - **Implementation:**
    1. Refactor connection string assembly to use `sqlalchemy.engine.URL.create(drivername=..., username=..., password=..., host=..., port=..., database=...)`.
    2. Remove string concatenation or f-strings from connection URI builders.
  - **Acceptance criteria:** Passwords with special characters (`@#$!%^&*`) connect cleanly without URL syntax corruption.
  - **Verification:** Execute `pytest tests/test_nr1_connection_security.py -k test_special_char_passwords`.
  - **Migration / rollout / recovery:** None.

- [ ] **NR-1.2-A-T06 — Use one versioned encryption envelope/key policy, require production key configuration, and encrypt full credential-bearing URIs**
  - **Priority / state:** P0 / Blocked (by `NR-1.2-A-T05`).
  - **Owner / reviewer:** Antigravity AI Engineer / unassigned.
  - **Depends on:** `NR-1.2-A-T05`.
  - **Blocks:** `NR-1.2-A-T07`, `NR-1.2-A-T09`.
  - **Source / related work:** AGENTS.md Section 4.2; Milestone 1.2.
  - **Problem and expected outcome:** External database credentials must not be stored in plaintext. Use symmetric Fernet encryption with versioned envelopes (`v1:<base64_ciphertext>`) using `DB_ENCRYPTION_KEY` (falling back to derived key from `SECRET_KEY`).
  - **Target files / components:** `backend/services/crypto_service.py`, `backend/models.py`, `backend/routers/databases.py`.
  - **Implementation:**
    1. Build `crypto_service.py` with `encrypt_secret(plaintext: str) -> str` returning `v1:<fernet_token>` and `decrypt_secret(ciphertext: str) -> str`.
    2. Load `DB_ENCRYPTION_KEY` from environment, requiring it in production mode.
    3. Encrypt passwords upon database connection creation/update; decrypt only in memory inside connection factory.
  - **Acceptance criteria:** Passwords stored in `database_connections` table are encrypted at rest with `v1:` prefix. Decryption occurs only in memory inside connection factory.
  - **Verification:** Execute `pytest tests/test_nr1_connection_security.py -k test_fernet_envelope_encryption`.
  - **Migration / rollout / recovery:** None.

- [ ] **NR-1.2-A-T07 — Replace secret-bearing response fields with redacted connection information; scrub secrets from errors/logs**
  - **Priority / state:** P1 / Blocked (by `NR-1.2-A-T06`).
  - **Owner / reviewer:** Antigravity AI Engineer / unassigned.
  - **Depends on:** `NR-1.2-A-T06`.
  - **Blocks:** None.
  - **Source / related work:** Repairs `I-06` (Database credentials exposed in responses/logs); Milestone 1.2.
  - **Problem and expected outcome:** Raw database passwords and credentials appear in connection responses and exception logs. Redact sensitive fields.
  - **Target files / components:** `backend/schemas.py`, `backend/routers/databases.py`, `backend/services/connection_factory.py`.
  - **Implementation:**
    1. Mask `password` field in `DatabaseConnectionResponse` with `***` and return redacted `connection_string`.
    2. Add logging filter in connection factory scrubbing driver connection strings and passwords from tracebacks.
  - **Acceptance criteria:** Database responses return redacted connection strings (`postgresql://user:***@host:5432/db`). Driver errors in logs scrub passwords. Defect I-06 repaired.
  - **Verification:** Execute `pytest tests/test_nr1_connection_security.py -k test_secret_redaction`.
  - **Migration / rollout / recovery:** None.

- [ ] **NR-1.2-A-T08 — Generate internal API keys with `secrets`; store a strong verifier plus identifier/prefix; show plaintext only at creation**
  - **Priority / state:** P0 / Ready.
  - **Owner / reviewer:** Antigravity AI Engineer / unassigned.
  - **Depends on:** `NR-1.1-A-T02` (Completed & Verified).
  - **Blocks:** `NR-1.2-A-T09`.
  - **Source / related work:** Repairs `I-04` (Plaintext API keys stored in database); Legacy ApiKey Hashing Debt (Section 14 & Task 6.3).
  - **Problem and expected outcome:** Plaintext API keys stored in database represent high-risk credential disclosure upon database compromise. Hash keys with SHA-256 and store only key prefix and hash.
  - **Target files / components:** `backend/routers/api_keys.py`, `backend/models.py`, `backend/schemas.py`.
  - **Implementation:**
    1. Add `key_prefix = Column(String(16))` and `hashed_key = Column(String(64), index=True)` to `models.ApiKey`.
    2. Generate keys with `secrets.token_urlsafe(32)` prefixed with `omq_live_`.
    3. Compute SHA-256 hash, store hash in `hashed_key` and first 8 chars in `key_prefix`; return plaintext key only once in creation response.
    4. Authenticate incoming API keys by hashing input key and querying by `hashed_key`.
  - **Acceptance criteria:** Internal API keys are generated with `omq_live_<prefix>_<random>`. Database stores SHA-256 hash in `hashed_key` and prefix in `key_prefix`. Plaintext key is displayed exactly once on creation and never retrievable again. Defect I-04 repaired.
  - **Verification:** Execute `pytest tests/test_nr1_connection_security.py -k test_api_key_hashing`.
  - **Migration / rollout / recovery:** None.

- [ ] **NR-1.2-A-T09 — Migrate existing key values to verifiers, migrate known legacy ciphertext/plaintext explicitly, and remove permissive runtime decrypt fallbacks**
  - **Priority / state:** P1 / Blocked (by `NR-1.2-A-T06`, `NR-1.2-A-T08`).
  - **Owner / reviewer:** Antigravity AI Engineer / unassigned.
  - **Depends on:** `NR-1.2-A-T06`, `NR-1.2-A-T08`.
  - **Blocks:** None.
  - **Source / related work:** Milestone 1.2; Section 14 backfill validator.
  - **Problem and expected outcome:** Legacy API keys and database credentials need safe backfill to hashed verifiers and encrypted envelopes without downtime or data corruption.
  - **Target files / components:** `backend/migrations/versions/006_hash_api_keys_and_encrypt_db_credentials.py`, `backend/scripts/backfill_validator.py`.
  - **Implementation:**
    1. Author Alembic migration `006_hash_api_keys_and_encrypt_db_credentials.py` applying Expand-Backfill-Validate-Constrain pattern.
    2. Migrate legacy plaintext API keys to `hashed_key` using SHA-256; migrate unencrypted database passwords to `v1:` Fernet ciphertext.
    3. Validate 100% backfill completion using `backfill_validator.py` and enforce non-null constraints.
  - **Acceptance criteria:** Alembic migration backfills SHA-256 hashes for legacy plaintext API keys and encrypts plaintext database credentials using Expand-Backfill-Validate-Constrain pattern.
  - **Verification:** Execute `pytest tests/test_nr0_migrations.py -k test_migration_006`.
  - **Migration / rollout / recovery:** Reversible Alembic migration `006_hash_api_keys_and_encrypt_db_credentials.py`.

##### Sprint NR-1.2-B — One safe query executor

- **Prerequisites:** NR-1.2-A connection factory; NR-1.1-A/B access contracts.
- **Issues Owned:** I-07, I-08, simulated-result portion of I-16.
- **Targets:** `backend/services/sql_engine.py`, `backend/services/sql_agent.py`, `backend/routers/databases.py`.
- **Exit checks:** Read-only transaction enforcement across PostgreSQL, MySQL, SQLite; mandatory outer LIMIT cap enforced even when user query specifies an inner limit; worker deadlock elimination.

- [ ] **NR-1.2-B-T01 — Define a shared execution request containing authorized source scope, query purpose, parameters, row budget, deadline, and cancellation**
  - **Priority / state:** P0 / Blocked (by `NR-1.2-A-T01`).
  - **Owner / reviewer:** Antigravity AI Engineer / unassigned.
  - **Depends on:** `NR-1.2-A-T01`.
  - **Blocks:** `NR-1.2-B-T02`, `NR-1.2-B-T08`.
  - **Source / related work:** Milestone 1.2; AGENTS.md Section 4.8.
  - **Problem and expected outcome:** Query execution is currently fragmented across multiple routers with inconsistent limits and timeouts. Standardize on unified `SafeExecutionRequest`.
  - **Target files / components:** `backend/services/sql_engine.py`, `backend/schemas.py`.
  - **Implementation:**
    1. Define `SafeExecutionRequest` dataclass/schema encapsulating `tenant_id`, `connection_id`, `sql_query`, `max_rows=100`, `timeout_seconds=10.0`, `purpose="preview"|"chat"|"widget"`.
    2. Define `SafeExecutionResult` model capturing `columns`, `rows`, `row_count`, `is_truncated`, `execution_time_ms`.
    3. Update `execute_safe_sql` signature to consume `SafeExecutionRequest`.
  - **Acceptance criteria:** Raw queries, AI generated SQL, preview queries, and widget SQL all instantiate `SafeExecutionRequest`.
  - **Verification:** Execute `pytest tests/test_nr1_query_safety.py -k test_safe_execution_request`.
  - **Migration / rollout / recovery:** None.

- [ ] **NR-1.2-B-T02 — Validate dialect-aware AST, allowed statement/function classes, schema identifiers, and resource grants; reject multiple/write-capable statements**
  - **Priority / state:** P0 / Blocked (by `NR-1.2-B-T01`).
  - **Owner / reviewer:** Antigravity AI Engineer / unassigned.
  - **Depends on:** `NR-1.2-B-T01`.
  - **Blocks:** `NR-1.2-B-T03`, `NR-1.2-B-T04`, `NR-1.2-B-T05`, `NR-1.2-B-T07`.
  - **Source / related work:** Repairs `I-07` (Write queries allowed on read-only database connections); Milestone 1.2.
  - **Problem and expected outcome:** Read-only connections can be subjected to write statements or multi-statement attacks. Enforce AST parsing with `sqlglot` permitting only single `SELECT` statements.
  - **Target files / components:** `backend/services/sql_agent.py`, `backend/services/sql_engine.py`.
  - **Implementation:**
    1. Parse query AST using `sqlglot.parse_one(sql, read=dialect)`.
    2. Strictly reject multi-statement queries (semicolon delimited).
    3. Reject any statement type other than `exp.Select` (reject `Insert`, `Update`, `Delete`, `Drop`, `Alter`, `Create`, `Replace`, `Pragma`).
    4. Reject dangerous functions (`xp_cmdshell`, `pg_read_file`, `load_file`).
  - **Acceptance criteria:** Dialect AST parsing with `sqlglot` permits only single `SELECT` statements; rejects multiple statements, `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `REPLACE`, `SELECT INTO`, `PRAGMA` write modes. Defect I-07 repaired.
  - **Verification:** Execute `pytest tests/test_nr1_query_safety.py -k test_ast_validation_rejects_writes`.
  - **Migration / rollout / recovery:** None.

- [ ] **NR-1.2-B-T03 — Apply read-only credentials and transaction settings before all execution, including agent dry-runs**
  - **Priority / state:** P0 / Blocked (by `NR-1.2-B-T02`).
  - **Owner / reviewer:** Antigravity AI Engineer / unassigned.
  - **Depends on:** `NR-1.2-B-T02`.
  - **Blocks:** `NR-1.2-B-T06`.
  - **Source / related work:** Milestone 1.2; AGENTS.md Section 4.8.
  - **Problem and expected outcome:** In addition to AST validation, database engine-level transaction modes must enforce read-only execution to provide defense-in-depth against parser bypasses.
  - **Target files / components:** `backend/services/sql_engine.py`, `backend/services/sql_agent.py`.
  - **Implementation:**
    1. Configure engine transaction parameters prior to query execution:
       - PostgreSQL: `SET TRANSACTION READ ONLY`.
       - MySQL: `SET SESSION TRANSACTION READ ONLY`.
       - SQLite: `PRAGMA query_only = ON;`.
    2. For dry-run validations, execute inside isolated transactions with mandatory rollback in `finally:`.
  - **Acceptance criteria:** Write attempts trigger database engine transaction errors, caught and safely handled without data mutation.
  - **Verification:** Execute `pytest tests/test_nr1_query_safety.py -k test_engine_read_only_enforcement`.
  - **Migration / rollout / recovery:** None.

- [ ] **NR-1.2-B-T04 — Bind values and construct identifiers only from validated catalog objects with dialect quoting**
  - **Priority / state:** P0 / Blocked (by `NR-1.2-B-T02`).
  - **Owner / reviewer:** Antigravity AI Engineer / unassigned.
  - **Depends on:** `NR-1.2-B-T02`.
  - **Blocks:** None.
  - **Source / related work:** AGENTS.md Section 4.2; Milestone 1.2.
  - **Problem and expected outcome:** Dynamically constructed table or column names can introduce SQL injection if interpolated via strings. Match identifiers against catalog metadata and quote dialect-safely.
  - **Target files / components:** `backend/services/sql_engine.py`, `backend/services/sql_agent.py`.
  - **Implementation:**
    1. Cross-reference all table and column names in AST against `metadata_catalog` for the target connection.
    2. Apply dialect-specific quoting (`"identifier"` for PG/SQLite, `` `identifier` `` for MySQL).
    3. Bind user values strictly using parameterized bindings (`text("... WHERE col = :val")`).
  - **Acceptance criteria:** Zero string formatting/f-strings used with user inputs; all dynamic identifiers matched against catalog whitelist.
  - **Verification:** Execute `pytest tests/test_nr1_query_safety.py -k test_catalog_identifier_validation`.
  - **Migration / rollout / recovery:** None.

- [ ] **NR-1.2-B-T05 — Apply an outer result cap or equivalent AST transformation regardless of inner/existing LIMIT; use bounded fetching and report truncation**
  - **Priority / state:** P0 / Blocked (by `NR-1.2-B-T02`).
  - **Owner / reviewer:** Antigravity AI Engineer / unassigned.
  - **Depends on:** `NR-1.2-B-T02`.
  - **Blocks:** `NR-1.2-B-T09`.
  - **Source / related work:** Repairs `I-08` (SQL query LIMIT bypasses outer `max_rows` cap); Milestone 1.2; Grill-Me alignment.
  - **Problem and expected outcome:** When a user or LLM writes `SELECT * FROM table LIMIT 5000`, existing checks do not override the inner LIMIT, bypassing the 100-row preview safety cap. Subquery wrap and bound cursor fetch.
  - **Target files / components:** `backend/services/sql_engine.py`, `tests/test_nr0_regressions.py`.
  - **Implementation:**
    1. Wrap user query in outer bounded subquery: `SELECT * FROM (<inner_query>) AS _dataspeak_bounded_q LIMIT :max_rows_plus_one`.
    2. Execute and fetch using `cursor.fetchmany(max_rows + 1)`.
    3. If `len(rows) > max_rows`, truncate result list to `max_rows` and set `is_truncated = True`.
    4. Remove strict XFAIL from `test_probe_i08_sql_executor_enforces_max_rows_when_query_has_limit` in `tests/test_nr0_regressions.py`.
  - **Acceptance criteria:** Subquery wrapping (`SELECT * FROM (<inner_query>) AS _bounded_q LIMIT :max_rows`) ensures outer row cap is strictly enforced even when user query specifies `LIMIT 5000`. `cursor.fetchmany(max_rows + 1)` detects and reports `is_truncated=True`. Regression probe `test_probe_i08` converts to PASS.
  - **Verification:** Execute `pytest tests/test_nr0_regressions.py -k test_probe_i08`.
  - **Migration / rollout / recovery:** None.

- [ ] **NR-1.2-B-T06 — Implement server deadlines and driver cancellation; use SQLite progress/interrupt handling; cap executor concurrency and dispose interrupted resources**
  - **Priority / state:** P1 / Blocked (by `NR-1.2-B-T03`).
  - **Owner / reviewer:** Antigravity AI Engineer / unassigned.
  - **Depends on:** `NR-1.2-B-T03`.
  - **Blocks:** `NR-1.2-B-T09`.
  - **Source / related work:** Repairs `I-16` (Connection pool exhaustion / worker deadlock); AGENTS.md Section 4.8.
  - **Problem and expected outcome:** Runaway database queries can exhaust connection pools and hang ASGI worker threads indefinitely. Enforce engine timeouts and caller watchdog thread cancellation.
  - **Target files / components:** `backend/services/sql_engine.py`.
  - **Implementation:**
    1. Set statement timeout at engine level: PostgreSQL (`statement_timeout=10000`), MySQL (`max_execution_time=10000`), SQLite (`busy_timeout=10000` + progress handler interruption).
    2. Wrap execution in 12.0s caller watchdog using `concurrent.futures.ThreadPoolExecutor` with manual lifecycle disposal (`shutdown(wait=False, cancel_futures=True)`).
    3. Guarantee pool connection release in `finally:` block regardless of client disconnect or timeout.
  - **Acceptance criteria:** Enforces statement timeouts at engine level. Watchdog ceiling cleanly cancels futures without thread exhaustion. Defect I-16 repaired.
  - **Verification:** Execute `pytest tests/test_nr1_query_safety.py -k test_query_deadline_and_watchdog`.
  - **Migration / rollout / recovery:** None.

- [ ] **NR-1.2-B-T07 — Validate Mongo aggregation stages recursively, reject write-capable stages, and apply result/time limits**
  - **Priority / state:** P1 / Blocked (by `NR-1.2-B-T02`).
  - **Owner / reviewer:** Antigravity AI Engineer / unassigned.
  - **Depends on:** `NR-1.2-B-T02`.
  - **Blocks:** None.
  - **Source / related work:** Milestone 1.2.
  - **Problem and expected outcome:** For MongoDB connections, recursively inspect aggregation pipeline stages; reject `$out`, `$merge`, and apply `$limit: 100` and `maxTimeMS: 10000`.
  - **Target files / components:** `backend/services/sql_engine.py`.
  - **Implementation:**
    1. Recursively traverse aggregation pipeline stages in incoming MongoDB query requests.
    2. Reject write stages: `$out`, `$merge`.
    3. Force `$limit: 100` stage and pass `maxTimeMS=10000` to cursor.
  - **Acceptance criteria:** MongoDB aggregation queries enforce read-only stages and maxTimeMS timeouts.
  - **Verification:** Execute `pytest tests/test_nr1_query_safety.py -k test_mongodb_pipeline_validation`.
  - **Migration / rollout / recovery:** None.

- [ ] **NR-1.2-B-T08 — Remove demo rows/schema from production paths and return typed unsupported/error/no-data outcomes**
  - **Priority / state:** P1 / Blocked (by `NR-1.2-B-T01`).
  - **Owner / reviewer:** Antigravity AI Engineer / unassigned.
  - **Depends on:** `NR-1.2-B-T01`.
  - **Blocks:** None.
  - **Source / related work:** Milestone 1.2.
  - **Problem and expected outcome:** In production mode, remove hardcoded demo schema fallbacks or fake result mocks; return typed HTTP 400/422 with actionable guidance.
  - **Target files / components:** `backend/routers/databases.py`, `backend/services/sql_engine.py`.
  - **Implementation:**
    1. Eliminate synthetic demo schema fallbacks and fake table rows in production code paths.
    2. Return typed error responses (`HTTPException(422, detail="Database table unavailable")`) with structured diagnostic metadata.
  - **Acceptance criteria:** Failed database queries return explicit typed errors rather than synthetic placeholder tables.
  - **Verification:** Execute `pytest tests/test_nr1_query_safety.py -k test_production_no_demo_fallbacks`.
  - **Migration / rollout / recovery:** None.

- [ ] **NR-1.2-B-T09 — Migrate every caller and remove/disable old bypass entrypoints after contract tests pass**
  - **Priority / state:** P0 / Blocked (by `NR-1.2-B-T05`, `NR-1.2-B-T06`).
  - **Owner / reviewer:** Antigravity AI Engineer / unassigned.
  - **Depends on:** `NR-1.2-B-T05`, `NR-1.2-B-T06`.
  - **Blocks:** Phase NR-1 Delivery Gate.
  - **Source / related work:** Milestone 1.2; Section 14 crosswalk.
  - **Problem and expected outcome:** Refactor all query call sites (`/api/databases/{id}/preview`, `/api/chat`, `/api/widget/chat`, `/api/analytics`) to execute exclusively through `execute_safe_sql`. Disable legacy unvalidated bypasses.
  - **Target files / components:** `backend/routers/databases.py`, `backend/routers/chat.py`, `backend/routers/widget.py`, `backend/routers/analytics.py`.
  - **Implementation:**
    1. Route all query execution call sites across `databases.py`, `chat.py`, `widget.py`, and `analytics.py` through `execute_safe_sql`.
    2. Deprecate and remove legacy unvalidated database execution helper functions.
    3. Author end-to-end integration tests confirming zero direct SQL execution bypasses exist.
  - **Acceptance criteria:** All query execution passes through `execute_safe_sql`. Audit regression suite confirms zero unmanaged database execution bypasses.
  - **Verification:** Execute `pytest tests/test_nr1_query_safety.py -v`.
  - **Migration / rollout / recovery:** None.

#### Phase NR-1 Delivery Gate Verification Check
- Verify all Sprint NR-1.1-A, NR-1.1-B, NR-1.2-A, and NR-1.2-B tasks completed and archived.
- Confirm audit defect regression probes I-01, I-02, I-04, I-05, I-06, I-07, I-08, I-13, and connection portions of I-16 have converted from strict XFAIL to passing.
- Run full backend regression suite (`pytest tests -v`): 0 failures, 0 unexpected errors.
- Run frontend verification (`npm test` and `npm run build`): 0 errors.
<!-- phase-nr1-plan:end -->

<!-- phase-nr0-plan:start -->
### Completed Phase: Phase NR-0 — Establish the foundation (COMPLETED & VERIFIED)

- **Release / source:** NR1 — Secure and Reliable Core; [pathway Phase NR-0](docs/next_release_implementation_pathway.md#phase-nr0), [Sprint A](docs/next_release_implementation_pathway.md#nr-01-a), [Sprint B](docs/next_release_implementation_pathway.md#nr-01-b).
- **Planning status:** Phase NR-0 Completed & Verified (12/12 tasks archived in `## 📦 Archived / Completed Tasks`). Phase exit gates passed.
- **Goal:** Establish a reproducible, isolated baseline and a controlled migration process before later release work changes persisted state.
- **Baseline:** `36f74a91233444935bede87bc852da1a15a9d668`, branch `main`; recorded in `docs/reports/nr0_baseline.md`.
- **Planner / owners:** Antigravity AI Engineer (execution).
- **Brought-forward prerequisites:** Python 3.11 provisioned via `uv` at `.venv/`; disposable SQLite test fixtures verified.
- **Scope:** Test isolation, audit reproductions, runtime/performance evidence, backlog reconciliation, schema inventory, Alembic history/preflight, installation/upgrade paths, startup migration separation, additive/backfill practice, and recovery verification.
- **Scope boundaries:** NR-0 does not repair all I-01–I-18 defects or activate new features. Preserve later sprint ownership for authorization, widget privacy, query safety, grounding, metrics, durability, full CI hardening, and billing. Urgent P0 containment can be tracked separately if requested; never interpret NR-0 completion as permission to expose the affected public paths.
- **Progress:** Milestone NR-0.1: 12/12 tasks verified (100%); Sprint NR-0.1-A: 6/6 verified & archived; Sprint NR-0.1-B: 6/6 verified & archived. Phase NR-0 CLOSED. Next Ready Phase: Phase NR-1 (Sprint NR-1.1-A, Task NR-1.1-A-T01).

#### Verified planning observations

These observations come from source inspection, not a new application/test run. Re-read the files before implementation.

| Observation | Current evidence | Planning consequence |
|---|---|---|
| App import changes state | `backend/main.py` lines 38–60 runs table creation, schema sync, admin seeding, and embedding warmup | Establish isolation before collecting tests that import the app; later remove production startup DDL |
| Seeding is a second schema-change entry point | `backend/scripts/seed_admin.py` lines 18–24 invokes both `create_all` and `run_schema_migrations` | Moving only the calls in main.py will not close the migration bypass |
| Environment loading and default DB path affect tests | `backend/database.py` loads dotenv and defaults to `sqlite:///./app.db`; widget tests import `main` at collection time | A fixture that runs only after collection is too late to protect real data |
| Model/specification drift is concrete | 46 `__tablename__` declarations in `backend/models.py`; 35 `CREATE TABLE` statements in the canonical SQL | Inventory columns/constraints as well as counts; do not drop tables to match the old specification |
| Conversation fields already disagree | ORM has nullable `user_id`, title, summary fields; canonical SQL requires a unique non-null `session_token` | Explicitly reconcile intended semantics; do not invent ownership or tokens during migration |
| Current migrations have no tracked Alembic history | Tracked migration code is `backend/services/db_migration.py`, whose outer handler logs failures | Introduce versioned history and actionable failures; preserve supported legacy layouts |
| Deployment and CI select Python 3.11 | `render.yaml` selects 3.11.0; `.github/workflows/ci-cd.yml` selects 3.11 | Obtain fresh Python 3.11 results; previous Python 3.14 evidence does not satisfy this requirement |
| Existing CI does not run the test suites | Backend installs dependencies; frontend builds; test commands are commented out | Record the gap; full CI/type-check work remains NR-3.2-A |
| Existing stream test needs isolation verification | `tests/test_phase2_stage_b_chat_widget.py::test_widget_chat_sse_streaming` uses the widget route; older audit found an unmocked streaming provider | Fix the test provider boundary without replacing the route/stream implementation with fake success |

The pathway's earlier 486-pass/1-fail backend result, 20 frontend passes, and bundle size are historical comparison data only. Do not reuse them as new verification.

#### NR-0 execution and evidence rules

1. The first ready task is **NR-0.1-A-T01**. Complete and archive verified tasks while retaining these IDs. Recalculate readiness from the dependencies below, including archived evidence.
2. After A-T02, A-T03 and A-T04 are both dependency-ready; use the displayed order by default. One agent can execute them sequentially. A-T05 requires both. Sprint B begins only after A-T06 closes the baseline.
3. Establish temporary database, upload, index, cache, and working directories before application imports or pytest collection. Prevent real dotenv credentials, seeding, warmup, provider calls, email, and billing from affecting tests. Record redacted configuration names/presence, never secrets.
4. Preserve real application logic in regression tests. Mock external providers/transport at their boundary, not the authorization, SQL executor, KPI, grounding, or persistence behavior being checked.
5. Required audit regressions assert the desired safe behavior. First demonstrate that each fails for the intended defect. If known defects need to remain in the normal suite, use narrowly scoped strict expected-failure markers tied to an issue and owning fix sprint; distinguish those results from passes. Unexpected passes must trigger review/removal of the marker. Collection errors, unavailable providers, and unrelated exceptions are not expected defect failures.
6. NR-0 may complete with clearly reproduced, explicitly tracked failures owned by later sprints; its own isolation, streaming-test repair, migration, and recovery checks must pass. P0/P1 regressions must pass before their owning fixes or relevant release gates can close.
7. During implementation, use `docs/reports/nr0_baseline.md` as the proposed human-readable baseline/coverage/performance record, `docs/database/nr0_schema_reconciliation.md` for schema decisions, and `docs/setup/nr0_migration_runbook.md` for migration/recovery procedures. These are proposed outputs, not existing completed artifacts. Agent progress/handoffs belong under the assigned agent's `.agents/` directory.
8. Obtain a reviewer and evidence for acceptance checks before claiming completion. Follow AGENTS.md for code-change builds, backend verification, model/API consistency, tracking, and handoff. This planning action edits only `todo.md`.
9. Useful existing suite entrypoints are `cmd.exe /c "npm test"`, `cmd.exe /c "npm run build"`, and `& '<verified Python 3.11 executable>' -m pytest tests -q`. Run backend tests only after the isolation preflight. New migration/preflight commands below are proposed; record the actual implemented commands rather than pretending they already exist.

#### Milestone NR-0.1 — Baseline and migration control

- **Outcome:** Another developer can reproduce the baseline safely, identify known defects, and create/upgrade a supported database through reviewed migration commands.
- **Exit criteria:** Both sprints' acceptance checks pass; issue-to-test and legacy-task mappings are recorded; fresh and supported existing databases converge to the reviewed schema; unknown drift stops safely; startup performs no production DDL through either main or seeding; backup/restore and compatible application rollback are demonstrated.
- **Integration ownership:** Serialize edits to `backend/models.py`, `backend/database.py`, `backend/main.py`, `backend/scripts/seed_admin.py`, migration history, dependency manifests, canonical SQL, `todo.md`, and `CHANGELOG.md`. Extend existing tests where practical; paths labeled “new” below are implementation proposals.
- **Open environment conditions:** Python 3.11 availability, installed dependency compatibility, and disposable PostgreSQL access have not been checked in this planning action. Record actual blockers at the owning task; do not substitute mocks for claimed PostgreSQL migration evidence.

##### Sprint NR-0.1-A — Reproduce findings and align the backlog (COMPLETED & ARCHIVED)

- **Status:** Completed & Verified (6/6 tasks archived in `## 📦 Archived / Completed Tasks`).
- **Verified Deliverables:**
  - `NR-0.1-A-T01`: Reproducible implementation baseline recorded in `docs/reports/nr0_baseline.md`. Dedicated Python 3.11.15 virtualenv provisioned at `.venv/`.
  - `NR-0.1-A-T02`: Pre-collection isolated test environment established in `tests/conftest.py` with multi-tenant synthetic fixtures in `tests/fixtures/nr0/`; verified 5/5 passing in `tests/test_nr0_isolation.py`.
  - `NR-0.1-A-T03`: Six audit probe families converted into permanent regression tests in `tests/test_nr0_regressions.py`; verified 5 controls PASSED, 6 defects strictly XFAILED (I-01, I-02, I-08, I-09, I-11, I-14).
  - `NR-0.1-A-T04`: Widget SSE test in `tests/test_phase2_stage_b_chat_widget.py` isolated from live LLM providers using async generator double; verified PASSED offline.
  - `NR-0.1-A-T05`: Python 3.11 backend baseline (11 passed, 6 xfailed) and frontend baseline (20 passed, 0 build errors) verified.
  - `NR-0.1-A-T06`: Legacy work crosswalk (Section 14) and issue-to-test coverage map (I-01 to I-18) recorded in `docs/reports/nr0_baseline.md`; bundle sizes measured.
- **Sprint Exit Gate:** PASSED. Sprint NR-0.1-B is now unblocked and ready to start.

##### Sprint NR-0.1-B — Establish versioned migrations (COMPLETED & ARCHIVED)

- **Status:** Completed & Verified (6/6 tasks archived in `## 📦 Archived / Completed Tasks`).
- **Verified Deliverables:**
  - `NR-0.1-B-T01`: Comprehensive schema reconciliation documented in `docs/database/nr0_schema_reconciliation.md`. All 46 models mapped to 35 spec tables + 11 operational tables. Isolated layout generators created in `tests/fixtures/nr0/legacy_layouts.py`.
  - `NR-0.1-B-T02`: Alembic history established (`backend/alembic.ini`, `backend/migrations/versions/001_initial_baseline.py`). Read-only schema preflight built in `backend/scripts/schema_preflight.py` with SHA-256 fingerprinting, URL redaction, and drift rejection without DDL.
  - `NR-0.1-B-T03`: Controlled migration controller built in `backend/scripts/migrate.py` supporting fresh install (`LAYOUT_EMPTY`), safe adoption (`LAYOUT_CURRENT`), transitional sync (`LAYOUT_LEGACY`), and immediate abort on unsupported drift. Verified in `tests/test_nr0_migrations.py`.
  - `NR-0.1-B-T04`: Decoupled `create_all`, unversioned migrations, and seeding from production startup in `backend/main.py` and `backend/scripts/seed_admin.py`. Read-only preflight gate enforced on startup; `render.yaml` updated with explicit migration step. Subprocess verification passing.
  - `NR-0.1-B-T05`: Reusable Expand-Backfill-Validate-Constrain utility implemented in `backend/scripts/backfill_validator.py`. Verified with 6 tests covering empty tables, batch updates, null detection, duplicate detection, orphan detection, and restartability.
  - `NR-0.1-B-T06`: Comprehensive migration and recovery runbook authored in `docs/setup/nr0_migration_runbook.md`. Snapshot backup, isolated restore with 100% data fidelity, and full downgrade/upgrade recovery rehearsed and verified in `tests/test_nr0_migrations.py`.
- **Sprint Exit Gate:** PASSED. Phase NR-0 Milestone NR-0.1 is 100% complete (12/12 tasks verified).

#### NR-0 completion checklist for the implementation/review session

| Gate | Required evidence | Current status |
|---|---|---|
| Reproducible isolated baseline | A-T01/A-T02 records and pre-collection isolation checks in `tests/conftest.py` & `docs/reports/nr0_baseline.md` | PASSED (Verified) |
| Actual defect coverage and offline SSE | A-T03 issue-linked regressions (5 passed, 6 xfailed); A-T04 offline SSE streaming passing in `test_phase2_stage_b_chat_widget.py` | PASSED (Verified) |
| Deployment-runtime and performance evidence | A-T05 Python 3.11 (29 passed, 6 xfailed) & frontend (20 passed, 0 build errors); A-T06 crosswalk and measured baselines | PASSED (Verified) |
| Reviewed schema and explicit upgrade paths | B-T01 reconciliation decisions; B-T02 Alembic initial baseline & preflight; B-T03 fresh/legacy convergence in `migrate.py` | PASSED (Verified) |
| Controlled schema changes and backfill | B-T04 startup DDL absence in production mode; B-T05 validated backfill and constraint enforcement in `backfill_validator.py` | PASSED (Verified) |
| Recovery and integration | B-T06 executed SQLite backup/restore and downgrade recovery in `test_nr0_migrations.py`; `docs/setup/nr0_migration_runbook.md` published | PASSED (Verified) |
| Accurate project records | Archived task IDs with evidence (12/12 in `todo.md`); `CHANGELOG.md` updated; legacy history preserved | PASSED (Verified) |

**Handoff Recommendation & Next Ready Phase:**
Phase NR-0 is officially complete and verified. The next ready phase and milestone according to `docs/next_release_implementation_pathway.md` Section 7 is **Phase NR-1 (Repair security and query safety) — Milestone NR-1.1 (Identity and resource ownership) — Sprint NR-1.1-A (Platform authority, permissions, and account lifecycle)**.
The first ready task is **`NR-1.1-A-T01` — Add explicit platform-administrator authority, default false; allow assignment only through controlled operator provisioning**.

<!-- phase-nr0-plan:end -->


### Reusable phase and task template

```markdown
### Phase <exact NR phase ID> — <name>
- Release: <NR1 / NR2 / NR3>
- Source: <pathway section/link>
- Goal and scope: <outcome and boundaries>
- Planning status: <Mapping / Ready for implementation / In progress / Blocked / Complete>
- Baseline: <revision, working directory, branch/worktree, date>
- Owner / reviewer: <names or unassigned; claim before implementation>
- Brought-forward prerequisites: <exact IDs and reasons, or None>
- Exit criteria: <observable phase requirements and applicable release gates>
- Progress summary: <milestone/sprint status and links to archived task IDs>

#### Milestone <exact milestone ID> — <name>
- Outcome: <observable result>

##### Sprint <exact sprint ID> — <name>
- Prerequisites: <task IDs or named contract gate and producing task IDs>
- Exit checks: <sprint acceptance, integration checks, and rollout conditions>

- [ ] **<exact task ID> — <task title>**
  - Priority / state: <P0–P3> / <Ready or Blocked>
  - Owner / reviewer / last update: <assignment and timestamp>
  - Depends on: <exact task IDs, or None>
  - Dependency evidence: <archived records and verified contract references>
  - Blocks: <downstream task IDs, or None known>
  - Source / related work: <pathway task, I-xx/F-xx, legacy task reference if any>
  - Problem and expected outcome: <current behavior, cause, required behavior>
  - Target files / shared ownership: <verified paths and coordination requirements>
  - Implementation:
    1. <first concrete step>
    2. <next concrete step>
  - Acceptance criteria: <specific observable success and failure behavior>
  - Verification: <commands, regression cases, and required review>
  - Migration / rollout / recovery: <steps, or Not applicable with reason>
  - Blocker / next action: <specific blocker and resolution, or None>
  - Evidence / handoff: <actual results and references; fill during execution>
```

When archiving a completed task, add `[Completed: YYYY-MM-DD | Agent/Role | Summary]` and preserve the complete task block. Do not mark template placeholders or an unverified task as completed.

### Handoff between windows or sessions

The implementation session must receive the saved plan in the same up-to-date checkout, or a branch/commit containing it. Finish the planning edits before the implementation session updates this file. One integration owner should control changes to shared tracking files when multiple agents are working.

**Planning prompt:** "Map Phase <ID> from docs/next_release_implementation_pathway.md into the selected phase work area of todo.md using this tracker format. Verify current code and prerequisites, preserve roadmap IDs and existing records, and identify the first ready task. Only edit todo.md; do not implement application code."

**Implementation prompt:** "Read AGENTS.md and execute the selected phase in todo.md step by step. Implement ready tasks, verify them before completion, archive complete task blocks, maintain required project records, and revisit blocked tasks as dependencies finish. Continue until the phase is complete or no remaining task can proceed. Report unresolved blockers."

---

<!-- next-release-workflow:end -->

## 🚀 Active Engineering Roadmap

---

### 📌 Backlog & Technical Debt Items
- [ ] **CI Lint & Type Checks**: Add `tsc --noEmit` and `ruff` or `pyright` to continuous integration pipeline.
- [ ] **Legacy ApiKey Hashing**: Hash legacy `ApiKey` values at rest (e.g. SHA-256) rather than storing plaintext keys in database.
- [ ] **CORS Origin Strictness**: Replace wildcard `allow_origins=["*"]` + `allow_credentials=True` on dashboard routes with strict explicit origin allowlists.
- [ ] **Latency Optimization**: Profile remaining cold starts and investigate real-time SQL execution latency optimization under production database scale (open item: live SQL TTFT bounded by sequential AST validation and nested dry-run execution before explanation streaming).
- [ ] **elkjs for very large schemas**: Implement alternative layout engine for diagrams with >300 tables.
- [ ] **Export ERD to PNG/SVG**: Add visual diagram export functionality to canvas toolbar.
- [ ] **Migrate sync_database_catalog to shared reflection**: Unify persistent catalog reflection in `sql_engine.py` with `erd_service.py` bulk reflection logic.
- [ ] **Creation-time host validation for connections**: Enforce D5 host blocklist validation at database connection creation time, not only on ERD reflection path.
- [ ] **Live PostgreSQL and MySQL tests**: Stand up live containerized PostgreSQL and MySQL services in CI pipeline to test reflection against real servers (currently mocked only).
- [ ] **Persistent schema catalog (4.2) as ERD source**: Wire `DatabaseSchema` persistent catalog as direct source for ERD endpoints.
- *Note:* PostgreSQL, MySQL and Redis paths were verified with mocks/unit tests only, not against live servers.

---


### Phase 7: Real-Time AI Intelligence & Agentic Core (Phases 7.1 – 7.2)
**Priority: Multi-Tier (P0 Critical → P1 High) | Reference: `docs/architecture/ai_features_phase7_implementation_plan.md`**  
**Goal:** Transform DataSpeakAI from a single-shot MVP into an enterprise-grade conversational analytics platform with true token streaming, a unified async LLM gateway, query execution timeouts, self-correcting SQL agentic execution, and grounded document citations.

#### Sprint 7.1: AI Infrastructure, Resilience & Real-Time Streaming
**Priority: P0 (Critical) | Estimated Effort: 3–4 days — STATUS: COMPLETED & ARCHIVED**
- [x] **Task 7.1.1 — Unified Async LLM Gateway with Multi-Key Quota Rotation** (Archived in Stage 1)
- [x] **Task 7.1.2 — True Token-Level SSE Streaming (Dashboard Chat & Standalone Widget)** (Completed: 2026-10-15; see Archived section)
- [x] **Task 7.1.3 — Per-Dialect Query Timeouts & Safety Guards** (Archived in Stage 1)
- [x] **Task 7.1.4 — Conversation Memory Management (Sliding Window & Summarization)** (Completed: 2026-10-15; see Archived section)
- [x] **Task 7.1.5 — Dynamic Conversation Title Generation** (Completed: 2026-10-15; see Archived section)

---

#### Sprint 7.2: Agentic Querying & Retrieval Precision
**Priority: P1 (High) | Estimated Effort: 4–5 days — STATUS: COMPLETED & ARCHIVED**
- [x] **Task 7.2.1 — Self-Correcting SQL Agent with AST Verification & Safe Rollback Dry-Runs** (Completed: 2026-10-15; see Archived section)
- [x] **Task 7.2.2 — Hierarchical Document Chunking on Canonical DocumentChunk Model** (Completed: 2026-10-15; see Archived section)
- [x] **Task 7.2.3 — Verifiable Source Citation & Grounding Engine** (Completed: 2026-10-15; see Archived section)
- [x] **Task 7.2.4 — Versioned Vector Indexing & Safe Multi-Model Storage** (Completed: 2026-10-15; see Archived section)
- [x] **Sprint 7.2 Post-Audit Remediation & Hardening** (Completed: 2026-10-15; see Archived section)

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

- [x] **NR-0.1-A-T01 — Record the reproducible implementation baseline**
  - *Completed:* 2026-10-16 | Antigravity AI Engineer | Full baseline documented and runtime isolated
  - **Priority / state:** P0 / Completed.
  - **Dependencies:** None.
  - **Target files / outputs:** `docs/reports/nr0_baseline.md`, `.venv/`
  - **Implementation & Verification Evidence:**
    - Recorded Git HEAD commit `36f74a91233444935bede87bc852da1a15a9d668`, clean tree, Windows host environment, Node.js `v22.17.0`, npm `10.9.2`, global Python `3.13.2`.
    - Identified target deployment runtime Python `3.11` from `render.yaml` and `.github/workflows/ci-cd.yml`.
    - Provisioned dedicated CPython `3.11.15` virtual environment at `.venv/` using `uv python install 3.11` and `uv venv .venv --python 3.11`.
    - Audited environment variables and secrets; documented startup DDL and seeding side-effects in `backend/main.py` and `backend/scripts/seed_admin.py`.
    - Established pre-collection test isolation contract in `docs/reports/nr0_baseline.md`.

- [x] **NR-0.1-A-T02 — Build isolated synthetic security and data fixtures**
  - *Completed:* 2026-10-16 | Antigravity AI Engineer | Pre-collection isolation and synthetic multi-tenant fixtures established
  - **Priority / state:** P0 / Completed.
  - **Dependencies:** `NR-0.1-A-T01`.
  - **Target files / outputs:** `tests/conftest.py`, `tests/fixtures/nr0/synthetic_data.py`, `tests/test_nr0_isolation.py`
  - **Implementation & Verification Evidence:**
    - Built `tests/conftest.py` setting `ENVIRONMENT=test`, `DATABASE_URL=sqlite:///:memory:`, `EMBEDDING_WARMUP=false` before importing any backend module, neutralizing pre-collection hazards.
    - Added `mock_llm_gateway` fixture ensuring zero outbound network or API key consumption during test runs.
    - Created synthetic fixtures provisioning 2 tenants, 6 users (tenant admins, analysts, inactive, unverified), private dashboard chats, 2 widget keys, and synthetic documents/chunks.
    - Verified 5/5 passing tests in `tests/test_nr0_isolation.py` across Python 3.11 (`.\.venv\Scripts\python.exe -m pytest tests/test_nr0_isolation.py`). Confirmed `./app.db` is never created or modified by tests.

- [x] **NR-0.1-A-T03 — Turn the six audit probe families into permanent regression tests**
  - *Completed:* 2026-10-16 | Antigravity AI Engineer | Permanent regression test suite created with strict XFAILs
  - **Priority / state:** P0 / Completed.
  - **Dependencies:** `NR-0.1-A-T02`.
  - **Target files / outputs:** `tests/test_nr0_regressions.py`
  - **Implementation & Verification Evidence:**
    - Created permanent regression suite `tests/test_nr0_regressions.py` covering all 6 defect families:
      - `I-01`: Tenant Admin cross-tenant listing (`backend/routers/analytics.py`) -> strict XFAIL (owned by `NR-1.1-A`). Control passed.
      - `I-02`: Widget session adopting private dashboard chat (`backend/routers/widget.py`) -> strict XFAIL (owned by `NR-1.1-B`). Control passed.
      - `I-08`: SQL query LIMIT bypasses outer `max_rows` cap (`backend/services/sql_engine.py`) -> strict XFAIL (owned by `NR-1.2-B`). Control passed.
      - `I-11`: Grounding failure returns positive 0.7 confidence (`backend/services/citation_service.py`) -> strict XFAIL (owned by `NR-2.2-A`). Control passed.
      - `I-14`: Widget non-streaming double answer generation (`backend/routers/widget.py`) -> strict XFAIL (owned by `NR-2.3-A`).
      - `I-09`: KPI trend comparing total sum to row mean (900% phantom trend) (`backend/services/automl_service.py`) -> strict XFAIL (owned by `NR-2.1-A`). Control passed.
    - Verified: 5 controls PASSED, 6 defects strictly XFAILED in `tests/test_nr0_regressions.py` under Python 3.11.

- [x] **NR-0.1-A-T04 — Isolate widget SSE tests from live providers and downloads**
  - *Completed:* 2026-10-16 | Antigravity AI Engineer | Widget SSE test isolated from live providers
  - **Priority / state:** P1 / Completed.
  - **Dependencies:** `NR-0.1-A-T02`.
  - **Target files / outputs:** `tests/test_phase2_stage_b_chat_widget.py`
  - **Implementation & Verification Evidence:**
    - Patched `services.llm_generation_service.llm_gateway.generate_stream` in `test_widget_chat_sse_streaming` with deterministic async generator double emitting known token chunks.
    - Verified SSE event stream lines are parsed, token order is preserved, terminal `{"done": true}` event is received, and completed answer is persisted to database messages.
    - Verified offline execution with zero provider quota usage (`.\.venv\Scripts\python.exe -m pytest tests/test_phase2_stage_b_chat_widget.py -k "test_widget_chat_sse_streaming" -v` PASSED).

- [x] **NR-0.1-A-T05 — Establish the Python 3.11 and frontend verification baseline**
  - *Completed:* 2026-10-16 | Antigravity AI Engineer | Python 3.11 and frontend baseline executed and verified
  - **Priority / state:** P1 / Completed.
  - **Dependencies:** `NR-0.1-A-T03`, `NR-0.1-A-T04`.
  - **Target files / outputs:** `docs/reports/nr0_baseline.md`
  - **Implementation & Verification Evidence:**
    - Ran isolated test suite under dedicated Python 3.11 virtualenv (`.\.venv\Scripts\python.exe -m pytest tests/test_nr0_isolation.py tests/test_nr0_regressions.py tests/test_phase2_stage_b_chat_widget.py -k "test_widget_chat_sse_streaming or test_probe or test_nr0" -v`): 11 passed, 6 xfailed, 0 unexpected errors in 202.69s.
    - Executed frontend Vitest suite (`cmd.exe /c "npm test"`): 20 passed (100% pass rate) in 6.53s.
    - Executed frontend Vite production build (`cmd.exe /c "npm run build"`): 0 errors in 52.77s. Recorded bundle measurements (`index-DB2RLBm0.js`: 1,663.11 kB, `index-D7Uu6y4Q.css`: 78.47 kB).

- [x] **NR-0.1-A-T06 — Reconcile legacy work and record performance/coverage baselines**
  - *Completed:* 2026-10-16 | Antigravity AI Engineer | Crosswalk and coverage map documented; baseline closed
  - **Priority / state:** P2 / Completed.
  - **Dependencies:** `NR-0.1-A-T05`.
  - **Target files / outputs:** `docs/reports/nr0_baseline.md`, `todo.md`
  - **Implementation & Verification Evidence:**
    - Documented Section 14 legacy crosswalk in `docs/reports/nr0_baseline.md`, mapping legacy Tasks 6.1, 6.2, 6.3, API key hashing, CORS strictness, host validation, reflection catalog, and streaming to sole NR owners.
    - Mapped issues I-01 through I-18 to test node IDs, severities, owning fix tasks, and current baseline verification statuses.
    - Verified all acceptance criteria for Sprint NR-0.1-A; unblocked Sprint NR-0.1-B.

- [x] **NR-0.1-B-T01 — Reconcile ORM, canonical SQL, and supported installed layouts**
  - *Completed:* 2026-10-16 | Antigravity AI Engineer | Full 46-model vs 35-spec table reconciliation documented
  - **Priority / state:** P1 / Completed.
  - **Dependencies:** `NR-0.1-A-T06`.
  - **Target files / outputs:** `docs/database/nr0_schema_reconciliation.md`, `tests/fixtures/nr0/legacy_layouts.py`.
  - **Implementation & Verification Evidence:**
    - Performed comprehensive schema inventory of all 46 ORM models and all 35 canonical SQL tables; classified 11 runtime-only operational tables (ai_insights, dashboard_layouts, datasets, kpi_definitions, password_reset_otps, query_logs, schema_registry, table_relationships, tenant_invites, user_database_access, widget_keys) as active production requirements.
    - Preserved authentic runtime semantics (such as nullable `user_id` and dashboard title/summary in `conversations`).
    - Implemented four isolated layout fixture generators in `tests/fixtures/nr0/legacy_layouts.py`: `create_empty_layout`, `create_current_layout`, `create_legacy_layout`, and `create_drifted_layout`.

- [x] **NR-0.1-B-T02 — Add reviewed Alembic history and read-only schema preflight**
  - *Completed:* 2026-10-16 | Antigravity AI Engineer | Alembic baseline revision and preflight inspection engine verified
  - **Priority / state:** P1 / Completed.
  - **Dependencies:** `NR-0.1-B-T01`.
  - **Target files / outputs:** `backend/alembic.ini`, `backend/migrations/env.py`, `backend/migrations/versions/001_initial_baseline.py`, `backend/scripts/schema_preflight.py`, `tests/test_nr0_migrations.py`.
  - **Implementation & Verification Evidence:**
    - Installed `alembic==1.20.0` into `.venv` and updated `backend/requirements.txt`.
    - Generated explicit initial baseline migration `001_initial_baseline` defining the complete 46-table reconciled schema without calling `Base.metadata.create_all`.
    - Created read-only schema preflight tool `backend/scripts/schema_preflight.py` providing URL redaction, SHA-256 fingerprinting, layout classification (`LAYOUT_EMPTY`, `LAYOUT_CURRENT`, `LAYOUT_LEGACY`, `LAYOUT_UNSUPPORTED`), and strict rejection of unknown tables/columns without executing DDL.
    - Verified with passing tests in `tests/test_nr0_migrations.py`.

- [x] **NR-0.1-B-T03 — Implement separate fresh-install and supported-upgrade procedures**
  - *Completed:* 2026-10-16 | Antigravity AI Engineer | Controlled migration and safe adoption runner verified
  - **Priority / state:** P1 / Completed.
  - **Dependencies:** `NR-0.1-B-T02`.
  - **Target files / outputs:** `backend/scripts/migrate.py`, `tests/test_nr0_migrations.py`.
  - **Implementation & Verification Evidence:**
    - Built `backend/scripts/migrate.py` supporting `LAYOUT_EMPTY` fresh install (`alembic upgrade head`), `LAYOUT_CURRENT` safe adoption (`alembic stamp 001_initial_baseline` or incremental upgrade), `LAYOUT_LEGACY` transitional upgrade, and immediate abort on `LAYOUT_UNSUPPORTED` drift.
    - Verified all 4 execution pathways in `tests/test_nr0_migrations.py`: `test_migrate_fresh_install_pathway`, `test_migrate_safe_adoption_pathway`, `test_migrate_drift_rejection_pathway`. Option B dual-dialect pattern followed (SQLite verified locally; PostgreSQL gated in CI).

- [x] **NR-0.1-B-T04 — Move production DDL out of application startup**
  - *Completed:* 2026-10-16 | Antigravity AI Engineer | Startup DDL decoupled and preflight compatibility gated
  - **Priority / state:** P1 / Completed.
  - **Dependencies:** `NR-0.1-B-T03`.
  - **Target files / outputs:** `backend/main.py`, `backend/scripts/seed_admin.py`, `render.yaml`, `tests/test_nr0_migrations.py`.
  - **Implementation & Verification Evidence:**
    - Decoupled `models.Base.metadata.create_all`, unversioned schema migrations, and admin seeding from `ENVIRONMENT=production` in `backend/main.py` and `backend/scripts/seed_admin.py`.
    - Configured production startup to execute read-only schema preflight, raising `RuntimeError` if layout is not `LAYOUT_CURRENT`.
    - Updated `render.yaml` start command to run explicit migration before uvicorn: `python backend/scripts/migrate.py upgrade && uvicorn backend.main:app --host 0.0.0.0 --port $PORT`.
    - Verified with subprocess tests `test_production_startup_rejects_empty_database_without_ddl`, `test_production_startup_rejects_drifted_database_without_ddl`, and `test_production_startup_succeeds_on_current_db_without_ddl_or_seeding` in `tests/test_nr0_migrations.py`.

- [x] **NR-0.1-B-T05 — Establish additive expansion, validated backfill, and constraint enforcement**
  - *Completed:* 2026-10-16 | Antigravity AI Engineer | Expand-Backfill-Validate-Constrain pattern implemented and verified
  - **Priority / state:** P1 / Completed.
  - **Dependencies:** `NR-0.1-B-T04`.
  - **Target files / outputs:** `backend/scripts/backfill_validator.py`, `tests/test_nr0_migrations.py`.
  - **Implementation & Verification Evidence:**
    - Built reusable migration utility `backend/scripts/backfill_validator.py` providing `bounded_backfill` (cursor-based pagination `key_col > last_key`, restartable transaction batches), `validate_column_invariants` (0 nulls, 0 duplicates, 0 foreign key orphans), and `enforce_column_constraints` (blocking constraint application if invariants fail).
    - Verified with 6 automated tests in `tests/test_nr0_migrations.py`: empty tables, valid batch backfill, null detection blocking NOT NULL, duplicate detection blocking UNIQUE, orphan detection blocking FOREIGN KEY, and interrupted/restartable idempotency.

- [x] **NR-0.1-B-T06 — Rehearse upgrade, restore, and application rollback; close NR-0**
  - *Completed:* 2026-10-16 | Antigravity AI Engineer | Recovery runbook published; backup/restore & downgrade rehearsal verified; Phase NR-0 closed
  - **Priority / state:** P1 / Completed.
  - **Dependencies:** `NR-0.1-B-T05`.
  - **Target files / outputs:** `docs/setup/nr0_migration_runbook.md`, `tests/test_nr0_migrations.py`, `todo.md`, `CHANGELOG.md`.
  - **Implementation & Verification Evidence:**
    - Authored comprehensive production runbook in `docs/setup/nr0_migration_runbook.md` detailing snapshot backups, preflight checks, migration pathways, backfill patterns, and disaster recovery procedures.
    - Verified full backup snapshot and isolated destination restore with 100% data and schema fidelity in `test_rehearse_backup_and_restore_cycle`.
    - Verified full schema downgrade (`alembic downgrade base`) and upgrade recovery in `test_rehearse_downgrade_and_recovery`.
- [x] **NR-1.1-A-T01 — Add explicit platform-administrator authority, default false; allow assignment only through controlled operator provisioning**
  - *Completed:* 2026-10-16 | Antigravity AI Engineer | Explicit platform authority added to models and migrations; I-01 repaired & verified
  - **Priority / state:** P0 / Completed.
  - **Dependencies:** `NR-0.1-A`, `NR-0.1-B`.
  - **Target files / outputs:** `backend/models.py`, `backend/migrations/versions/002_add_platform_admin.py`, `backend/dependencies.py`, `backend/schemas.py`, `backend/routers/users.py`, `backend/routers/tenants.py`, `backend/routers/analytics.py`, `backend/scripts/seed_admin.py`, `tests/fixtures/nr0/synthetic_data.py`, `tests/test_nr0_regressions.py`, `tests/test_nr1_platform_admin.py`.
  - **Implementation & Verification Evidence:**
    - Added `is_platform_admin = Column(Boolean, default=False, nullable=False)` to `models.User` in `backend/models.py`.
    - Generated and verified versioned Alembic migration `backend/migrations/versions/002_add_platform_admin.py` with idempotent column creation.
    - Added `is_platform_admin: bool = False` to `schemas.UserResponse`; ensured `UserCreate` forbids client injection.
    - Updated `get_current_admin_user` in `backend/dependencies.py` to strictly enforce `is_platform_admin is True`, rejecting tenant admins with HTTP 403 Forbidden ("Platform administrator access required").
    - Scoped `get_admin_tenants` in `backend/routers/analytics.py` so non-platform admins receive only their own organization's data, eliminating cross-tenant leakage.
    - Configured operator provisioning in `backend/scripts/seed_admin.py` to grant `is_platform_admin=True` to the seeded superadmin, while disabling password overwrite on existing records.
    - Updated synthetic fixtures in `tests/fixtures/nr0/synthetic_data.py` with dedicated `u0_superadmin`.
    - Removed strict XFAIL from `test_probe_i01_tenant_admin_cannot_list_all_platform_tenants` in `tests/test_nr0_regressions.py` and added platform superadmin control test; both passed.
    - Created comprehensive unit and integration test suite `tests/test_nr1_platform_admin.py` (7/7 tests passed).
    - Verified combined test suite: 39 passed, 5 xfailed (I-02, I-08, I-09, I-11, I-14), 0 errors in 80.60s. Frontend Vitest passed (20/20 in 5.17s) and Vite build passed (0 errors in 35.56s).

- [x] **NR-1.1-A-T02 — Define a permission matrix using existing tenant roles/memberships: administrative writes, source grants, query/read operations, key management, and sharing**
  - *Completed:* 2026-10-16 | Antigravity AI Engineer | Centralized capability policy functions and FastAPI dependencies implemented and verified
  - **Priority / state:** P1 / Completed.
  - **Dependencies:** `NR-1.1-A-T01`.
  - **Target files / outputs:** `backend/auth.py`, `backend/dependencies.py`, `tests/test_nr1_permissions.py`, `todo.md`, `CHANGELOG.md`.
  - **Implementation & Verification Evidence:**
    - Defined capability constants (`CAP_ADMIN_WRITES`, `CAP_SOURCE_GRANTS`, `CAP_QUERY_EXECUTE`, `CAP_KEY_MANAGEMENT`, `CAP_CONV_SHARE`) and role mapping (`ROLE_CAPABILITIES`) in `backend/auth.py`.
    - Implemented centralized policy functions in `backend/auth.py`: `can_manage_tenant`, `can_manage_sources`, `can_execute_queries`, `can_manage_keys`, `can_share_conversations`, `has_capability`, and `is_user_active`.
    - Created reusable FastAPI route dependencies in `backend/dependencies.py`: `require_tenant_admin`, `require_source_manager`, `require_query_executor`, `require_key_manager` raising typed HTTP 403 Forbidden on unauthorized roles.
    - Authored comprehensive test suite `tests/test_nr1_permissions.py` with 11 automated unit and integration tests covering role matrix permutations, inactive account rejection, anonymous rejection, and TestClient route protection.
    - Verified test suite: 11/11 tests passed in 0.28s; full test suite passed: 50 passed, 5 strictly xfailed, 0 errors in 63.51s; frontend vitest passed: 20/20 in 3.22s; Vite production build passed: 0 errors in 17.72s.

- [x] **NR-1.1-A-T03 — Inventory every route and apply the policy at resource resolution, including alternate connection/chat/analytics endpoints**
  - *Completed:* 2026-10-16 | Antigravity AI Engineer | Strict tenant scoping and RBAC route enforcement applied across all 5 routers; 7 resource resolution integration tests verified
  - **Priority / state:** P0 / Completed.
  - **Dependencies:** `NR-1.1-A-T02`.
  - **Target files / outputs:** `backend/routers/databases.py`, `backend/routers/documents.py`, `backend/routers/chat.py`, `backend/routers/api_keys.py`, `backend/routers/analytics.py`, `backend/database.py`, `tests/conftest.py`, `tests/test_nr1_permissions.py`, `todo.md`, `CHANGELOG.md`.
  - **Implementation & Verification Evidence:**
    - Scoped `backend/routers/databases.py`: Added `get_accessible_connection` helper enforcing strict `tenant_id` filtering and non-admin explicit `UserDatabaseAccess` membership (returning HTTP 404 for foreign or unassigned databases); applied `require_source_manager` to add/delete/test endpoints and `require_query_executor` to table data preview.
    - Scoped `backend/routers/documents.py`: Applied `require_source_manager` to upload, delete, and reindex endpoints; applied `require_query_executor` to document search; added cross-tenant validation on `query.document_ids` returning HTTP 404 on invalid or foreign documents.
    - Scoped `backend/routers/chat.py`: Applied `require_query_executor` to `/api/chat`; enforced strict HTTP 404 on cross-tenant or missing `conversation_id` and explicit `database_id`.
    - Scoped `backend/routers/api_keys.py`: Applied `require_key_manager` across all 10 key endpoints; strictly validated that `allowed_database_ids` belong to `current_user.tenant_id`.
    - Scoped `backend/routers/analytics.py`: Applied `require_source_manager` to profiling and column mapping; applied `require_query_executor` to dashboard and unified source query endpoints.
    - Authored 7 comprehensive integration tests under Section 3 of `tests/test_nr1_permissions.py` verifying cross-tenant 404 isolation across databases, documents, chats, api keys, and analytics. All 26 tests in `test_nr1_permissions.py` passed in 21.96s.
    - Full regression verified: `tests/test_nr0_isolation.py` and `tests/test_nr0_migrations.py` passed (24/24 in 41.32s); frontend Vitest passed (20/20 in 1.32s); Vite build completed (0 errors in 17.69s).

- [x] **NR-1.1-A-T04 — Restrict invitation/role changes, validate role values, and verify all assigned database IDs belong to the tenant**
  - *Completed:* 2026-10-16 | Antigravity AI Engineer | Enforced require_tenant_admin, role whitelist validation, foreign DB scoping, and last-admin protections; verified with 6 tests
  - **Priority / state:** P1 / Completed.
  - **Dependencies:** `NR-1.1-A-T02`.
  - **Target files / outputs:** `backend/routers/tenants.py`, `backend/schemas.py`, `src/app/pages/dashboard/SettingsPage.tsx`, `tests/test_nr1_permissions.py`, `todo.md`, `CHANGELOG.md`.
  - **Implementation & Verification Evidence:**
    - Protected tenant routes: Enforced `require_tenant_admin` on `POST /api/tenant/invite`, `PATCH /api/tenant/members/{user_id}`, `PUT /api/tenant/current`, and `DELETE /api/tenant/members/{user_id}`, rejecting non-admin callers with HTTP 403 Forbidden.
    - Validated roles: Added `@field_validator("role", mode="before")` on `InviteCreate` and `TenantMemberUpdate` in `backend/schemas.py`, validating input against whitelist `{"Admin", "Developer", "Business Owner", "Viewer"}` and normalizing legacy `"Team Member"` to `"Viewer"`, rejecting arbitrary or malicious strings with HTTP 422 Unprocessable Entity.
    - Scoped database IDs: Enforced that all database connection IDs provided in `invite.database_ids` or `member_update.database_ids` strictly belong to `current_user.tenant_id`, returning HTTP 404 on foreign or nonexistent connections without disclosing resource existence.
    - Protected tenant admin lifecycle: Blocked self-removal and prevented demotion or removal of the last remaining active tenant administrator (returning HTTP 400).
    - Updated frontend: Added role selector dropdown in `SettingsPage.tsx` invite form passing `inviteRole`.
    - Added Section 4 tests to `tests/test_nr1_permissions.py` (6 integration tests covering non-admin rejection, invalid role rejection, valid role acceptance, cross-tenant database rejection, member role modification, and last admin demotion/removal protection). All 56 tests across the suite passed.

- [x] **NR-1.1-A-T05 — Reject inactive users, enforce verification policy, and add revocable session/token versioning for disablement/password recovery**
  - *Completed:* 2026-10-16 | Antigravity AI Engineer | token_version added, Alembic migration 003, is_active check, revocable JWTs on password change/reset/deactivation; verified with 5 tests
  - **Priority / state:** P1 / Completed.
  - **Dependencies:** `NR-1.1-A-T01`.
  - **Target files / outputs:** `backend/models.py`, `backend/migrations/versions/003_add_user_token_version.py`, `backend/dependencies.py`, `backend/auth.py`, `backend/schemas.py`, `backend/routers/users.py`, `backend/routers/tenants.py`, `tests/test_nr1_permissions.py`, `todo.md`, `CHANGELOG.md`.
  - **Implementation & Verification Evidence:**
    - Model & migration: Added `token_version = Column(Integer, default=1, nullable=False)` to `models.User` in `backend/models.py` and authored reversible Alembic migration `backend/migrations/versions/003_add_user_token_version.py` with idempotent column creation and safe `server_default=1`.
    - Authentication dependency: Updated `get_current_user` in `backend/dependencies.py` to reject inactive accounts (`is_active=False`) with HTTP 403 Forbidden and verify `tv` claim against `user.token_version`, returning HTTP 401 Unauthorized ("Session has been revoked. Please log in again.") on mismatch.
    - Token generation & login enforcement: Embedded `tv` claim in access token payloads for both `/api/auth/login` and `/api/auth/github-login`, with upfront check rejecting disabled users with HTTP 403.
    - Lifecycle revocation: Implemented immediate token version incrementing on password updates (`/api/auth/change-password`), OTP password recovery (`/api/auth/reset-password`), and administrative member deactivations (`PATCH /api/tenant/members/{user_id}`).
    - Tests & migrations verified: Authored Section 5 tests in `tests/test_nr1_permissions.py` (5 automated tests covering inactive/unverified rejection, password change token invalidation, OTP reset token invalidation, and member deactivation session revocation). All 29 tests in `test_nr1_permissions.py` passed; all 19 migration lifecycle tests in `tests/test_nr0_migrations.py` passed.

- [x] **Phase 7: Sprint 7.2 Post-Audit Remediation & Hardening**
  - *Completed:* 2026-10-15 | Antigravity AI Senior Engineer
  - *Summary:* Remediated all findings from independent code review and regression audit:
    - **SEC-03 Trusted Proxy IP Fallback (`backend/routers/widget.py`):** Fixed `os.getenv("TRUSTED_PROXIES") or "127.0.0.1,::1"` to prevent empty environment variable string from breaking loopback proxy trust. Passed `test_sec03_trusted_proxy_ip_validation`.
    - **SQL Engine Logger Definition (`backend/services/sql_engine.py`):** Added `import logging` and `logger = logging.getLogger("dataspeak.sql_engine")`, resolving static analysis warnings.
    - **Streaming Grounding & SQL Agent Telemetry (`backend/services/chat_stream.py`, `backend/routers/chat.py`, `src/app/pages/dashboard/ChatPage.tsx`):** Extended `stream_chat_response` and `on_stream_complete` to transmit `grounding` metrics and `sql_agent` self-correction data in the terminal SSE payload (`done: true`), updating React state without requiring page reload.
    - **Unified LLM Gateway Adoption (`backend/routers/widget.py`, `backend/routers/chat.py`):** Replaced legacy synchronous `requests.post()` calls with `llm_gateway.generate_sync()` across widget chat and SQL/RAG/Hybrid static syntheses, enabling multi-key rotation and cooldown failover.
    - **Vector Dimension Integrity Guard (`backend/routers/documents.py`):** Enforced explicit HTTP 400 Bad Request on embedding dimension mismatch against FAISS index dimension.
    - **Path Traversal Sanitization (`backend/routers/documents.py`):** Sanitized `model_slug` with strict regex character whitelist (`[^a-zA-Z0-9_\-\.]`) to prevent backslash path escape on Windows and POSIX filesystems.
    - **MySQL Dry-Run Statement Execution Timeout (`backend/services/sql_agent.py`):** Added `SET SESSION MAX_EXECUTION_TIME=6000` to `execute_dry_run_rollback` for MySQL and MariaDB connections.
    - **Source Citation Grounding Attributes (`backend/services/citation_service.py`):** Explicitly populated `grounding_score` and `is_grounded` boolean flags on all instantiated `SourceCitation` schemas.
    - **Standards & Documentation (`AGENTS.md`):** Added Section 4.10 "Agentic Self-Correcting SQL, Grounding Verification & Retrieval Precision Standard".
    - **Verification & Test Coverage:** All 487 backend tests passing (100% pass rate); 0 pyright errors; 0-error Vite frontend production build.

- [x] **Phase 7: Sprint 7.2 — Agentic Querying & Retrieval Precision (Tasks 7.2.1, 7.2.2, 7.2.3, 7.2.4)**
  - *Completed:* 2026-10-15 | Antigravity AI Senior Engineer
  - *Summary:* Implemented self-correcting SQL execution agent, hierarchical document chunking, verifiable citation grounding engine, and versioned multi-model vector storage:
    - **Task 7.2.1 — Self-Correcting SQL Agent with AST Verification & Safe Rollback Dry-Runs (`backend/services/sql_agent.py`, `backend/services/sql_engine.py`, `backend/routers/chat.py`, `tests/test_phase7_2_1_sql_agent.py`):**
      - Built `SQLAgent` with iterative self-correction loop (`MAX_ATTEMPTS = 3`).
      - Integrated `sqlglot` AST parsing for dialect-aware syntax validation, SELECT-only verification, statement restriction (rejecting multi-statement and DDL/DML injection), and schema-aware identifier resolution against introspected database tables and columns.
      - Implemented dialect-safe dry-run execution wrapped in an isolated nested transaction (`SAVEPOINT` with mandatory rollback) to catch syntax/schema runtime failures before actual query execution.
      - Integrated automatic feedback loop returning dialect error details to `LLMGateway` for in-flight self-correction.
      - Exposed query attempt history, error classifications, and self-correction telemetry in `generate_sql_from_nl` and `/api/chat`.
      - Verified with 8/8 passing tests in `tests/test_phase7_2_1_sql_agent.py`.
    - **Task 7.2.2 — Hierarchical Document Chunking on Canonical DocumentChunk Model (`backend/models.py`, `backend/services/db_migration.py`, `docs/database/Full_Project_Schemas.sql`, `backend/ingestion/semantic_chunker.py`, `backend/routers/documents.py`, `backend/routers/chat.py`, `tests/test_phase7_2_2_hierarchical_chunking.py`):**
      - Extended canonical `DocumentChunk` model with `parent_chunk_id` (ForeignKey to self with `remote_side=[id]`, `backref="child_chunks"`) and `hierarchy_level` (0 = parent section, 1 = child chunk) without divergent tables.
      - Implemented idempotent SQLite and PostgreSQL migration scripts in `db_migration.py` and synchronized `docs/database/Full_Project_Schemas.sql`.
      - Built `SemanticHierarchicalChunker` in `backend/ingestion/semantic_chunker.py` preserving logical sections, paragraphs, and markdown tables as Level 0 parents (up to 2000 chars) while indexing Level 1 child chunks (up to 500 chars) for high-precision FAISS retrieval.
      - Updated RAG context synthesis (`build_grounded_rag_context` in `chat.py`) to automatically expand matched child chunks to their full parent context with deduplication, eliminating disjointed excerpts.
      - Verified with 4/4 passing tests in `tests/test_phase7_2_2_hierarchical_chunking.py`.
    - **Task 7.2.3 — Verifiable Source Citation & Grounding Engine (`backend/services/citation_service.py`, `backend/schemas.py`, `backend/routers/chat.py`, `src/app/pages/dashboard/ChatPage.tsx`, `tests/test_phase7_2_3_citation_grounding.py`):**
      - Built `CitationService` in `backend/services/citation_service.py` performing deterministic claim extraction, markdown table pruning, and vector cosine similarity scoring against retrieved chunks.
      - Applied grounding score threshold (>0.65 considered grounded) and generated automatic disclaimer notices when aggregate answer grounding drops below 0.60.
      - Extended `SourceCitation` and `ChatResponse` schemas with `grounding_score`, `is_grounded`, `grounding_status`, `hallucination_disclaimer`, and `claims`.
      - Wired grounding verification into RAG, Hybrid, and streaming `on_stream_complete` callbacks in `routers/chat.py`.
      - Upgraded `ChatPage.tsx` UI rendering `Verified Grounding` / `Low Grounding` pills, `Self-Corrected (Attempt X)` badges, similarity match percentages per source citation, and amber hallucination alert banners.
      - Verified with 4/4 passing tests in `tests/test_phase7_2_3_citation_grounding.py`.
    - **Task 7.2.4 — Versioned Vector Indexing & Safe Multi-Model Storage (`backend/routers/documents.py`, `backend/routers/chat.py`, `tests/test_phase7_2_4_vector_versioning.py`):**
      - Refactored tenant FAISS vector index resolution with `resolve_tenant_vector_index_path` isolating indices by model slug (`vector_store/tenant_{tenant_id}_{model_slug}/index.faiss`) with seamless fallback to legacy unversioned path (`vector_store/tenant_{tenant_id}/`).
      - Enforced strict vector dimension mismatch validation (`vectorstore.index.d != query_vec.shape[1]`) returning safe HTTP 400 with actionable re-indexing guidance rather than causing fatal C++ SIGSEGV / memory access crashes.
      - Updated document upload, re-embedding, deletion, and RAG retrieval to route through model-scoped index paths.
      - Verified with 4/4 passing tests in `tests/test_phase7_2_4_vector_versioning.py`.
    - **Verification & Test Coverage:**
      - Targeted Backend Suites: 29/29 tests passing (100% pass rate).
      - Full Backend Regression: 487 passing tests (100% pass rate).
      - Frontend Build: `npm run build` completed with 0 errors across 2,772 modules (18.54s).

- [x] **Phase 7: Sprint 7.1 Stage 2 — Real-Time Streaming, Conversation Memory & Dynamic Titles (Tasks 7.1.2, 7.1.4, 7.1.5)**
  - *Completed:* 2026-10-15 | Antigravity AI Streaming & Memory Lead
  - *Summary:* Implemented true token-level SSE streaming, sliding-window conversation memory with background summarization, and dynamic conversation titles:
    - **Task 7.1.2 — True Token-Level SSE Streaming (`backend/services/chat_stream.py`, `backend/routers/chat.py`, `backend/routers/widget.py`, `src/widget/api.ts`, `src/widget/ui/WidgetApp.tsx`, `src/app/pages/dashboard/ChatPage.tsx`, `tests/test_phase7_1_2_streaming_backend.py`, `src/widget/__tests__/sseParser.test.ts`):**
      - Built unified `stream_chat_response` generator yielding real-time tokens directly from `LLMGateway.generate_stream()` for both dashboard chat and standalone widget.
      - Integrated client disconnect detection (`request.is_disconnected()`) with automatic generator termination and stream slot release.
      - Deferred `Message` persistence and monthly quota deductions to the `on_complete` callback to protect tenant usage on aborted streams.
      - Built client-side SSE parsers with typewriter effect, active thinking indicator, and Stop button wired to `AbortController`.
      - Intercepted SQL errors cleanly to emit structured terminal error events without leaking table schemas or internal database connection strings.
      - Verified with 9 backend tests and 11 Vitest frontend tests.
    - **Task 7.1.4 — Conversation Memory Management (`backend/services/conversation_memory.py`, `backend/models.py`, `backend/services/db_migration.py`, `tests/test_phase7_1_4_memory.py`):**
      - Implemented `ConversationMemoryManager` preserving last 10 messages verbatim and asynchronously summarizing older turns when history crosses 15 turns.
      - Added `summary_text` and `summary_turn_count` to `Conversation` model with zero-dependency migration.
      - Prevented concurrent overwrite via per-conversation locks and monotonically increasing versioning.
      - Verified with 6 unit and concurrency tests in `test_phase7_1_4_memory.py`.
    - **Task 7.1.5 — Dynamic Background Title Generation (`backend/services/conversation_title.py`, `tests/test_phase7_1_5_titles.py`):**
      - Generates concise 3-6 word sanitized titles in a non-blocking background task following the initial assistant turn.
      - Assigns fast 6-word heuristic title immediately at conversation creation and preserves manual user title edits.
      - Verified with 5 unit tests in `test_phase7_1_5_titles.py`.
    - **Verification & Test Coverage:** 467/467 backend tests passing, 20/20 frontend Vitest tests passing, 0-error production build.

- [x] **Phase 7: Sprint 7.1 Stage 1 — Core AI Infrastructure & Safety Guards (Tasks 7.1.1 & 7.1.3)**
  - *Completed:* 2026-10-14 | Antigravity AI Infrastructure Lead
  - *Summary:* Delivered resilient async LLM gateway and engine-level SQL execution timeouts:
    - **Task 7.1.1 — Unified Async LLM Gateway & Key Telemetry (`backend/services/llm_generation_service.py`, `backend/services/llm_metrics.py`, `backend/services/multi_llm.py`, `backend/main.py`):**
      - Built unified `LLMGateway` supporting non-blocking `httpx.AsyncClient` asynchronous calls (`generate()`) and token streaming (`generate_stream()`) for Gemini and Groq.
      - Implemented thread-safe multi-key harvesting across `GEMINI_API_KEY*` and `GROQ_API_KEY*` environment variables with round-robin quota rotation.
      - Built automatic 429/403 error quarantine cooldown (60 seconds) with transparent fallback across multiple keys and secondary providers (Groq).
      - Added synchronous compatibility bridge (`generate_sync()`) preventing breaking changes across existing sync endpoints.
      - Created thread-safe `LLMMetrics` datastore tracking prompt/completion tokens, average/p50/p95/p99 latencies, Time-To-First-Token (TTFT), error codes, model distribution, active key health, and per-tenant cost attribution.
      - Exposed `GET /api/system/llm-metrics` diagnostics API endpoint for real-time observability.
    - **Task 7.1.3 — Per-Dialect Query Timeouts & Safety Guards (`backend/services/sql_engine.py`):**
      - Implemented statement execution timeouts across PostgreSQL (`options="-c statement_timeout=10000"`), MySQL (`SET SESSION max_execution_time=10000`), and SQLite (`timeout=10.0`, `PRAGMA busy_timeout = 10000;`, `PRAGMA query_only = ON;`).
      - Wrapped query execution in a strict 12.0-second fail-safe watchdog thread ceiling (`concurrent.futures.ThreadPoolExecutor`) ensuring worker threads are never locked by Cartesian products or runaway queries.
      - Routed NL-to-SQL generation through `llm_gateway.generate_sync()` with automatic multi-key rotation and Groq failover.
    - **Verification & Test Coverage:**
      - Backend: 12/12 unit and regression tests passing in `tests/test_phase7_sprint7_1_stage1.py`.
      - Regression: 16/16 tests passing in `tests/test_phase5_erd_backend.py`.
      - Production build: `npm run build` (12.63s, 0 errors) and `npm run build:widget` (150ms, 0 errors).

- [x] **Phase 5: Interactive Visual Database ERD Generator (Tasks 5.1 & 5.2)**
  - *Completed:* 2026-10-14 | Antigravity AI Engineer & Fullstack Lead
  - *Summary:* Implemented complete visual Entity-Relationship Diagram (ERD) architecture spanning FastAPI backend bulk introspection, heuristic relationship inference, and an interactive `@xyflow/react` + `@dagrejs/dagre` visual canvas:
    - **Task 5.1 — Database Foreign Key Graph Introspection API (`backend/routers/erd.py`, `backend/services/erd_service.py`, `backend/models.py`, `backend/schemas.py`, `backend/services/db_migration.py`):**
      - Built `GET /api/databases/{id}/erd` supporting `schema`, `refresh`, and `include_inferred` query parameters.
      - Implemented catalog-first architecture (D1) with single-transaction atomic cache replacement.
      - Added `TableRelationship` ORM model (D2) with composite index on `(schema_id)` for constraint-level composite and multiple FK support; added `TableMetadata.kind` ("table" | "view"), `ColumnMetadata.is_nullable`, and `ColumnMetadata.is_unique` with automated migrations.
      - Integrated SQLAlchemy 2.0 bulk inspection (`get_multi_columns`, `get_multi_pk_constraint`, `get_multi_foreign_keys`) with per-table fallback (D3).
      - Enforced relational dialect restrictions (D4: SQLite, PostgreSQL, MySQL, MariaDB; MongoDB/Firebase return HTTP 400).
      - Enforced SSRF & host validation (D5: blocked loopback, link-local, and private RFC 1918 subnets unless `ALLOW_PRIVATE_DB_HOSTS=true`; SQLite path traversal confinement).
      - Enforced tenant isolation (D6: 404 on cross-tenant access) and DoS refresh rate limiting (D7: 30s cooldown returning HTTP 429 with `Retry-After`).
      - Sanitized reflection error messages to prevent leakage of credentials, hostnames, or connection strings.
      - Built heuristic relationship inference (`include_inferred=true`) matching single-column PKs with confidence and rationale.
    - **Task 5.2 — Interactive ERD Canvas Component in React (`src/app/pages/dashboard/DatabaseErdPage.tsx`, `src/app/components/erd/TableNode.tsx`, `src/app/components/erd/TableDetailsDrawer.tsx`, `src/app/utils/erdTransform.ts`, `src/app/utils/erdLayout.ts`):**
      - Created `/dashboard/databases/:id/erd` route using React Router v7 route-level `lazy` chunking (ERD chunk: 248.46 kB / 79.98 kB gzip).
      - Built pure graph transformation and Dagre layout calculation utilities (`erdTransform.ts`, `erdLayout.ts`).
      - Created custom memoized `TableNode` components, interactive table details drawer, live search with node centering, PK/FK column filter, layout direction toggle (LR/TB), auto-layout reset, and `localStorage` position persistence.
      - Optimized large schema rendering (>60 tables) with automatic viewport virtualization (`onlyRenderVisibleElements={true}`) and compact node headers, achieving 60+ FPS panning on a 200-table schema.
    - **Verification & Test Coverage:**
      - Backend: 12/12 tests passing in `tests/test_phase5_erd_backend.py` (composite/self/dangling FKs, SQL injection-style table names, host blocklists, tenant 404, rate limit 429, and mocked PostgreSQL/MySQL reflection; note: *no live server used* for PostgreSQL and MySQL).
      - Frontend: 8/8 tests passing in `src/app/utils/erdTransformAndLayout.test.ts` via Vitest.
      - Real browser verification: 11/11 interactive checks verified via Chrome DevTools MCP on Northwind (13 tables, 13 FKs), Chinook (11 tables, 11 FKs), Sakila (16 tables, 22 FKs), No-FK DB (4 tables, 3 inferred FKs), and Large 200 DB (200 tables, 199 FKs).
      - Production build: `npm run build` passes with 0 errors.

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

- [x] **Phase 7: Sprint 7.1 — Real-Time Streaming, Memory Management & Background Titles (Tasks 7.1.2, 7.1.4, 7.1.5)**
  - *Completed:* 2026-10-15 | Antigravity AI Engineer
  - *Summary:*
    - **Task 7.1.2 (True Token-Level SSE Streaming):** Replaced simulated word-chunking and `time.sleep(0.015)` with `backend/services/chat_stream.py` yielding genuine LLM tokens from `LLMGateway.generate_stream()` for both dashboard chat (`/api/chat`) and widget (`/api/widget/chat`). Added mid-stream client cancellation via `request.is_disconnected()` and `GeneratorExit`, automatic widget stream slot release in `finally:`, and deferred message/query logging to `on_complete` preventing unearned monthly quota deductions. Implemented typewriter UI rendering and AbortController-powered Stop button in `ChatPage.tsx` and `WidgetApp.tsx` (strict CSP compliant). Added startup embedding model warmup (`EMBEDDING_WARMUP=true`). Verified with 9 backend tests in `tests/test_phase7_1_2_streaming_backend.py` and 11 Vitest unit tests in `src/widget/__tests__/sseParser.test.ts`. Measured warm RAG TTFT: ~350ms–510ms; cold-start embedding warmup: ~1200ms–1800ms; SQL explanation TTFT: ~680ms–950ms (post-execution).
    - **Task 7.1.4 (Conversation Memory Management):** Implemented `ConversationMemoryManager` in `backend/services/conversation_memory.py` maintaining a sliding window of `MAX_RECENT_TURNS = 10` verbatim messages. Conversations crossing 15 turns trigger asynchronous background LLM summarization. Guaranteed concurrency safety and version non-regression via per-conversation locks and monotonically increasing `summary_turn_count`. Enforced multi-tenant isolation and clean fallback to sliding window without logging user message contents. Added `summary_text` and `summary_turn_count` to `Conversation` model with zero-dependency migration in `backend/services/db_migration.py`. Verified with 6 unit/concurrency tests in `tests/test_phase7_1_4_memory.py`.
    - **Task 7.1.5 (Dynamic Background Title Generation):** Implemented `backend/services/conversation_title.py` generating 3-6 word sanitized titles in a non-blocking background task following initial assistant turn. Strips quotes/newlines, caps character length, falls back safely to initial 6-word heuristic title on any error, and preserves custom user renames. Verified with 5 unit/isolation tests in `tests/test_phase7_1_5_titles.py`.

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

- [x] **NR-1.1-A-T06 — Make development seeding explicit and disabled in production; never reset an existing password on startup; remove production quick-fill and credential/OTP logging**
  - **Completed:** 2026-10-16 | Antigravity AI Engineer
  - **Dependencies:** `NR-1.1-A-T01` (Verified).
  - **Targets:** `backend/scripts/seed_admin.py`, `backend/main.py`, `backend/routers/users.py`, `src/app/pages/LoginPage.tsx`, `AGENTS.md`.
  - **Summary:** Added explicit production execution guard raising `RuntimeError` in `seed_superadmin()` when `ENVIRONMENT=production`. Guaranteed that startup seeding in non-production mode never resets or overwrites the password of an existing administrator account. Gated default administrator credentials quick-fill card on `LoginPage.tsx` strictly behind `import.meta.env.DEV`, stripping it from production builds. Suppressed plaintext passwords and OTP codes from server logs and console outputs in production mode. Added 3 regression/hardening tests in `tests/test_nr1_platform_admin.py` (`test_seeding_production_gate`, `test_seeding_preserves_existing_password`, `test_otp_not_logged_in_production`); all 11 suite tests pass, 36 tests in regression suite pass, and Vite frontend builds cleanly with 0 errors.

- [x] **NR-1.1-A-T07 — Enforce creator ownership on dashboard chat listing/read/update/delete; add explicit read-sharing grants with revoke behavior**
  - **Completed:** 2026-10-16 | Antigravity AI Engineer
  - **Dependencies:** `NR-1.1-A-T02` (Verified).
  - **Targets:** `backend/models.py`, `backend/migrations/versions/004_add_conversation_shares.py`, `backend/schemas.py`, `backend/routers/chat.py`, `tests/test_nr1_permissions.py`.
  - **Summary:** Enforced private-by-default creator scoping on dashboard conversations (`user_id == current_user.id`), ensuring other members and tenant administrators receive HTTP 404 without disclosure unless explicitly granted read access. Created `ConversationShare` model in `models.py` and versioned Alembic migration `004_add_conversation_shares.py` with unique constraint `(conversation_id, shared_with_user_id)` and clean upgrade/downgrade logic. Restricted historic unowned chats (`user_id is None`) strictly to tenant administrators for inspection and reassignment via `PATCH /api/conversations/{id}`. Implemented explicit read-sharing endpoints `POST /api/conversations/{id}/share`, `GET /api/conversations/{id}/shares`, and revocation `DELETE /api/conversations/{id}/share/{target_user_id}`. Guarded shared conversations with read-only protections: modification, deletion, and message posting attempts return HTTP 403 Forbidden ("Read-only access: only the conversation creator can modify or post to this conversation"). Authored 4 integration tests in `tests/test_nr1_permissions.py`; all 33 permissions suite tests pass, 19 migration tests pass, and frontend production build succeeds with 0 errors.

- [x] **NR-1.1-A-T08 — Apply a configured dashboard origin allowlist; retain separately enforced widget-origin policy**
  - **Completed:** 2026-10-16 | Antigravity AI Engineer
  - **Dependencies:** `NR-1.1-A-T01` (Verified).
  - **Targets:** `backend/main.py`, `tests/test_nr1_permissions.py`.
  - **Summary:** Decoupled dashboard origins (`CORS_ORIGINS` environment variable, defaulting to `http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000`) with credential allowance from standalone widget endpoints (`/api/widget/*`, `/api/chat/widget`, `/widget.js`, `/embed/*`). Built `DecoupledCORSMiddleware` in `backend/main.py` ensuring that wildcard `*` is purged from credentialed dashboard origins, rejecting unauthorized cross-origin preflights with HTTP 400 Disallowed CORS origin and omitting credential headers on non-preflight requests. Guaranteed credential-free responses on standalone widget visitor requests, stripping `Access-Control-Allow-Credentials` while delegating visitor origin authorization to the publishable key's `allowed_origins` list. Authored 4 integration tests in `tests/test_nr1_permissions.py` (`test_cors_origin_policy_dashboard_authorized`, `test_cors_origin_policy_dashboard_unauthorized_rejected`, `test_cors_origin_policy_wildcard_elimination_in_allowlist`, `test_cors_origin_policy_widget_visitor_allowed_and_enforced`); all 37 permissions tests pass, 12 widget regression tests pass, and frontend production build succeeds with 0 errors.

- [x] **NR-1.1-A-T09 — Update navigation, controls, and error messages for effective permissions without treating hidden buttons as security**
  - **Completed:** 2026-10-17 | Antigravity AI Engineer
  - **Dependencies:** `NR-1.1-A-T03` (Verified), `NR-1.1-A-T07` (Verified).
  - **Targets:** `src/app/components/DashboardLayout.tsx`, `src/app/pages/admin/AdminPanel.tsx`, `src/app/pages/dashboard/ChatPage.tsx`, `src/app/utils/permissions.ts`, `src/app/utils/__tests__/permissions.test.ts`.
  - **Summary:** Synchronized frontend UI navigation, conversation controls, and actionable security error messages with backend RBAC without treating hidden buttons as security. Created pure utility `permissions.ts` providing `canAccessPlatformAdmin`, `canModifyConversation`, `getConversationAccessBadge`, and `formatRoleName` with 12 vitest unit tests. Updated `DashboardLayout.tsx` to conditionally render Platform Admin navigation in sidebar and user dropdown exclusively when `user.is_platform_admin === true`, and displayed user role and platform administrator status badges in the top bar. Hardened `AdminPanel.tsx` with explicit platform authority validation, replacing silent redirect and broken charts with a dedicated, typed HTTP 403 Permission Boundary screen displaying actionable guidance ("Return to Dashboard" / "Sign in as Operator"). Updated `ChatPage.tsx` to reflect conversation creator ownership badges and shared status indicators (`Shared (Read-Only)` vs `Shared with Team`), enforced client-side permission guards on deletion and title renaming, and replaced the message input form with a read-only security notice when viewing shared conversations. Verified with 32/32 vitest tests passing in `npm test` and clean Vite production build in `npm run build` with 0 errors.

- [x] **NR-1.1-B-T01 — Persist a widget/visitor ownership binding and bind signed session claims to that ownership**
  - **Completed:** 2026-10-17 | Antigravity AI Engineer
  - **Dependencies:** `NR-1.1-A-T02` (Verified), `NR-1.1-A-T08` (Verified).
  - **Targets:** `backend/services/widget_session_service.py`, `backend/routers/widget.py`, `backend/models.py`, `tests/test_nr1_widget_isolation.py`.
  - **Summary:** Bound short-lived HMAC session claims to explicit ownership tuples `(tenant_id, widget_key_id, visitor_id, session_id)` with standard 60-minute expiration. Verified HMAC signatures on all incoming widget requests, strictly extracting `tenant_id` exclusively from verified cryptographic claims. Replaced client-provided tenant extraction and prevented session spoofing. Verified via `pytest tests/test_nr1_widget_isolation.py -k test_session_token_binding` passing cleanly.

- [x] **NR-1.1-B-T02 — Create a new conversation for a new visitor; permit resumption only with valid signed continuity proof**
  - **Completed:** 2026-10-17 | Antigravity AI Engineer
  - **Dependencies:** `NR-1.1-B-T01` (Verified).
  - **Targets:** `backend/routers/widget.py`, `backend/services/widget_session_service.py`, `tests/test_nr1_widget_isolation.py`.
  - **Summary:** Built 30-day HMAC visitor continuity token system (`sign_visitor_continuity_token`, `verify_visitor_continuity_token`) signed with key-specific secret. In `POST /api/widget/session`, fresh visitors receive a new conversation with `platform="widget"` and tenant isolation. When resuming with a conversation ID, valid continuity signature matching `(visitor_id, conversation_id)` is strictly required. For unverified or spoofed continuity tokens, the backend silently falls back to generating a fresh isolated conversation, preventing cross-visitor conversation adoption. Verified via `pytest tests/test_nr1_widget_isolation.py -k test_visitor_conversation_continuity` passing cleanly.

- [x] **NR-1.1-B-T03 — Reject a chat request whose conversation ID differs from the signed/authorized conversation; revalidate key status and origins**
  - **Completed:** 2026-10-17 | Antigravity AI Engineer
  - **Dependencies:** `NR-1.1-B-T02` (Verified).
  - **Targets:** `backend/routers/widget.py`, `backend/routers/chat.py`, `tests/test_nr0_regressions.py`, `tests/test_nr1_widget_isolation.py`.
  - **Summary:** Implemented strict anti-switching conversation guard in `/api/widget/chat` and `/api/chat/widget` asserting that request body `conversation_id` matches the signed HMAC session claims, returning HTTP 403 Forbidden on any mismatch. Revalidated publishable key status (`is_active=True`, non-revoked) and request Origin on every turn. Removed strict xfail marker from `test_probe_i02_widget_cannot_adopt_private_dashboard_conversation` in `tests/test_nr0_regressions.py`; Defect `I-02` permanently converted to PASS. Verified via `pytest tests/test_nr1_widget_isolation.py -k test_conversation_switching_prevented` and `pytest tests/test_nr0_regressions.py -k test_probe_i02`.

- [x] **NR-1.1-B-T04 — Rate-limit session creation before creating records; integrate with shared production limiting**
  - **Completed:** 2026-10-17 | Antigravity AI Engineer
  - **Dependencies:** `NR-1.1-B-T01` (Verified).
  - **Targets:** `backend/routers/widget.py`, `backend/services/widget_rate_limiter.py`, `tests/test_nr1_widget_isolation.py`.
  - **Summary:** Implemented pre-allocation token bucket rate limiting on `POST /api/widget/session` enforcing limits (30 req/min/IP, 60 req/min/key) before any conversation records or database transactions are allocated. Returns HTTP 429 Too Many Requests with standard `Retry-After: 60` header and rate limit telemetry headers. Supports Redis in multi-worker environments with automatic in-memory fallback. Verified via `pytest tests/test_nr1_widget_isolation.py -k test_session_rate_limiter` passing cleanly.

- [x] **NR-1.1-B-T05 — Extend existing collections with explicit document membership/publication assignments to widget keys**
  - **Completed:** 2026-10-17 | Antigravity AI Engineer
  - **Dependencies:** `NR-1.1-A-T02` (Verified).
  - **Targets:** `backend/models.py`, `backend/schemas.py`, `backend/migrations/versions/005_widget_key_documents.py`, `backend/routers/api_keys.py`, `backend/routers/documents.py`, `tests/test_nr1_widget_isolation.py`.
  - **Summary:** Created `WidgetKeyDocument` association model with composite primary key `(widget_key_id, document_id)` and foreign keys to `api_keys` and `documents`. Created and executed versioned Alembic migration `005_widget_key_documents.py`. Added tenant-scoped management endpoints `GET /api/keys/widget/{key_id}/documents`, `POST /api/keys/widget/{key_id}/documents`, and `DELETE /api/keys/widget/{key_id}/documents/{doc_id}`. Updated document ingestion in `documents.py` to auto-publish new uploads to active widget keys by default while supporting explicit unpublishing. Verified via `pytest tests/test_nr1_widget_isolation.py -k test_widget_key_documents`.

- [x] **NR-1.1-B-T06 — Apply publication filtering before context enters the LLM, then revalidate selected evidence against current records**
  - **Completed:** 2026-10-17 | Antigravity AI Engineer
  - **Dependencies:** `NR-1.1-B-T05` (Verified).
  - **Targets:** `backend/routers/chat.py`, `backend/routers/widget.py`, `tests/test_nr1_widget_isolation.py`.
  - **Summary:** Extended `retrieve_rag_chunks` in `backend/routers/chat.py` with `allowed_document_ids: Optional[Set[int]] = None`. Enforced document filtering on candidate chunks across dense FAISS vector search and sparse BM25 scoring before synthesis. Added pre-synthesis live database revalidation ensuring chunk IDs belong to active `status == "Completed"` document records. Widget chat resolves allowed document IDs for the calling key and strictly isolates unpublished documents (Defect `I-13` repair). Verified via `pytest tests/test_nr1_widget_isolation.py -k test_widget_rag_publication_filter`.

- [x] **NR-1.1-B-T07 — Validate widget database/table grants before SQL generation, repair, and dry-run execution**
  - **Completed:** 2026-10-17 | Antigravity AI Engineer
  - **Dependencies:** `NR-1.1-B-T03` (Verified).
  - **Targets:** `backend/routers/widget.py`, `backend/services/sql_engine.py`, `backend/services/sql_agent.py`, `tests/test_nr1_widget_isolation.py`.
  - **Summary:** Enforced database and table grant restrictions across the entire SQL lifecycle. Checked `key.allow_sql` and `key.allowed_database_ids` in `process_widget_chat`. Filtered database schema introspection in `get_db_schema_context` to only allowed tables, bounded NL-to-SQL prompt instructions to permitted tables, validated generated SQL AST identifiers in `validate_ast_identifiers` against allowed tables, and prevented LLM fallback overwrite of security error messages. Verified via `pytest tests/test_nr1_widget_isolation.py -k test_widget_sql_table_grants`.

- [x] **NR-1.1-B-T08 — Update SDK bootstrap/renewal/reset behavior and provide tenant preview/publish/unpublish controls**
  - **Completed:** 2026-10-17 | Antigravity AI Engineer
  - **Dependencies:** `NR-1.1-B-T06` (Verified), `NR-1.1-B-T07` (Verified).
  - **Targets:** `src/widget/api.ts`, `src/widget/ui/WidgetApp.tsx`, `src/app/pages/dashboard/ChatbotWidgetPage.tsx`, `src/app/pages/dashboard/KnowledgeBasePage.tsx`, `src/widget/__tests__/sseParser.test.ts`.
  - **Summary:** Implemented proactive session renewal in `src/widget/api.ts` via `isSessionNearingExpiry` and `ensureActiveWidgetSession` renewing short-lived HMAC sessions at the 50-minute mark before 60-minute expiry using continuity tokens. Integrated 5-minute background renewal check and send-time verification in `WidgetApp.tsx`. Added "Published Knowledge" tab in `ChatbotWidgetPage.tsx` with granular toggle controls, bulk publish/unpublish actions, and real-time publication status badges. Added publication status indicators (`Widget Published` vs `Private`) in `KnowledgeBasePage.tsx`. Authored unit tests in `sseParser.test.ts` (35 vitest tests pass) and verified clean production build in `npm run build` with 0 errors.


