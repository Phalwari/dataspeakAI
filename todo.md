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
| Selected release / phase | NR1 / NR-0 — Establish the foundation |
| Planning status | Ready for implementation — 12 tasks mapped; none implemented |
| Baseline revision / working directory | 36065f2107e30b499302bd68ea299d51fbb2dcf5 / D:\dataspeak / branch main; existing local planning changes retained |
| Planner / implementation owner / reviewer | Codex (mapping) / unassigned / unassigned |
| First ready task | NR-0.1-A-T01 — Record the reproducible implementation baseline |
| Last update | 2026-10-16 — NR-0 mapped; prior task and completion records preserved |

Insert the selected phase's actual milestone, sprint, and task blocks here, before the template below. Keep any brought-forward prerequisites in a clearly labeled group. When changing phases, retain previous phase summaries and unresolved work; completed task records stay in the existing archive. The template below is illustrative and must never be treated as executable work.

<!-- phase-nr0-plan:start -->
### Phase NR-0 — Establish the foundation

- **Release / source:** NR1 — Secure and Reliable Core; [pathway Phase NR-0](docs/next_release_implementation_pathway.md#phase-nr0), [Sprint A](docs/next_release_implementation_pathway.md#nr-01-a), [Sprint B](docs/next_release_implementation_pathway.md#nr-01-b).
- **Planning status:** Ready for implementation. This is a mapped plan; none of its tasks has been implemented or verified by this planning action.
- **Goal:** Establish a reproducible, isolated baseline and a controlled migration process before later release work changes persisted state.
- **Baseline:** `36065f2107e30b499302bd68ea299d51fbb2dcf5`, branch `main`, working directory `D:\dataspeak`; mapped 2026-10-16. Existing local changes at planning start: modified `todo.md`; untracked `docs/next_release_implementation_pathway.md` and `intructions_for_humans.md`. Preserve them. Record the actual implementation starting revision and uncommitted diff when work begins; this revision alone does not include these planning documents.
- **Planner / owners:** Codex prepared this mapping. Implementation owners and reviewers are unassigned. Suggested ownership: QA/backend for Sprint A, data/platform for Sprint B, release integrator for review and shared files. Claim before editing; no parallel agents are assigned by this document.
- **Brought-forward prerequisites:** None from other NR phases. Python 3.11 and disposable SQLite/PostgreSQL test environments are execution requirements to establish/verify, not reasons to implement the entire NR-3 platform phase early.
- **Scope:** Test isolation, audit reproductions, runtime/performance evidence, backlog reconciliation, schema inventory, Alembic history/preflight, installation/upgrade paths, startup migration separation, additive/backfill practice, and recovery verification.
- **Scope boundaries:** NR-0 does not repair all I-01–I-18 defects or activate new features. Preserve later sprint ownership for authorization, widget privacy, query safety, grounding, metrics, durability, full CI hardening, and billing. Urgent P0 containment can be tracked separately if requested; never interpret NR-0 completion as permission to expose the affected public paths.
- **Progress:** Milestone NR-0.1: 0/12 tasks verified; Sprint NR-0.1-A: 0/6; Sprint NR-0.1-B: 0/6. All implementation evidence is pending. No phase exit check has passed yet.

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

##### Sprint NR-0.1-A — Reproduce findings and align the backlog

- **Priority / owner:** P0 foundation; QA/backend implementer and release integrator reviewer, unassigned.
- **Prerequisites:** None outside this plan. Internal task dependencies are listed below.
- **Issues / legacy links:** I-18 baseline and coverage for I-01–I-17; preserve the historical Phase 6/debt and Phase 7 records and use pathway section 14 for the crosswalk.
- **Exit checks:** Reproducible environment record; reusable synthetic fixtures; six mandatory regression families; provider-free streaming tests; Python 3.11 and frontend baseline evidence; issue/backlog/performance mapping. Known defect failures are separated from environment failures and passes.
- **Compatibility / recovery:** Changes are limited to tests, baseline tooling, and implementation records. External integrations remain explicit opt-in checks; no live data is migrated in this sprint.

- [ ] **NR-0.1-A-T01 — Record the reproducible implementation baseline**
  - **Priority / state:** P0 / Ready.
  - **Owner / reviewer / last update:** Unassigned / release integrator to be assigned / 2026-10-16 (planning).
  - **Depends on:** None.
  - **Blocks:** NR-0.1-A-T02.
  - **Source / purpose:** Pathway A-T01, I-18. Existing test claims use different runtimes and do not specify a safe repeatable execution environment.
  - **Target files / outputs:** Read `package.json`, `package-lock.json`, `backend/requirements.txt`, `render.yaml`, `.github/workflows/ci-cd.yml`, startup/database configuration, and test entrypoints; create the baseline report proposed above during implementation.
  - **Implementation:**
    1. Record branch, full revision, dirty files, actual Python/Node/npm executables and versions, operating system, and intended deployment runtime; inventory installed package versions without upgrading them.
    2. Inventory environment-variable names, default paths, dotenv loading, test imports, startup DDL/seeding/warmup, and external service entrypoints; redact values that contain secrets.
    3. Record exact commands and working directories for the baseline, fixture bootstrap, tests, build, and later timings. Separate already observed evidence from commands not yet run.
    4. Define the isolation preflight that A-T02 must implement. Do not collect/import unsafe backend tests merely to gather version information.
  - **Acceptance criteria:** Another session can identify the baseline and prepare the same environment from the record; unsafe side effects and pending runtime/tool availability are explicitly documented.
  - **Verification:** Cross-check recorded versions using the named executables and package metadata; compare documented script names with manifests; verify no production credentials or data were captured.
  - **Migration / recovery:** No schema/data change; retain existing environment/dependency files and record any unavailable tools.
  - **Blocker / next action:** None known for read-only inventory; claim this task first.
  - **Evidence / handoff:** Pending execution; planning inspection is not task-completion evidence.

- [ ] **NR-0.1-A-T02 — Build isolated synthetic security and data fixtures**
  - **Priority / state:** P0 / Blocked.
  - **Owner / reviewer / last update:** Unassigned / release integrator to be assigned / 2026-10-16 (planning).
  - **Depends on:** NR-0.1-A-T01.
  - **Blocks:** NR-0.1-A-T03, NR-0.1-A-T04.
  - **Source / purpose:** Pathway A-T02; reusable regression setup for tenant, user, widget, and document boundaries.
  - **Target files / outputs:** Existing test fixtures in `tests/test_phase2_stage_b_chat_widget.py` and Phase 4/7 suites; proposed new `tests/conftest.py`, `tests/fixtures/nr0/`, and `tests/test_nr0_isolation.py`; extend the baseline report.
  - **Implementation:**
    1. Establish isolation before test-module imports: use an explicit bootstrap/environment setup or equivalent collection-safe mechanism, not only an autouse fixture that runs after collection.
    2. Use disposable SQLite sessions and temporary uploads/vector/cache directories; prevent real dotenv values, live network/provider/model downloads, and production database access.
    3. Create two tenants; multiple same-tenant users including tenant admin and restricted/inactive users; private dashboard chats; two visitors and widget keys; and documents/chunks with distinct synthetic source identities.
    4. Represent publication intent and expected visitor ownership in fixture expectations until the owning sprint supplies persisted fields. Do not invent production schema changes or authorize by replacing the real policy code.
    5. Provide deterministic external provider/embedding doubles and cleanup of dependency overrides, sessions, caches, and mocks. Restore fixture state between tests.
    6. Add isolation checks using disposable sentinel files/databases to prove startup/test collection cannot touch the real application's data or reset an existing real account.
  - **Acceptance criteria:** Fixtures are reusable, contain no real data/secrets, distinguish the intended permission cases, and cannot leak state between tests; pre-collection isolation is demonstrated.
  - **Verification:** Run the dedicated isolation checks in a subprocess and repeat fixture-dependent cases with different orders. Verify all database/file destinations stay under the disposable test root.
  - **Migration / recovery:** Test databases only; dispose sessions/engines and clean only owned temporary artifacts.
  - **Blocker / next action:** Await A-T01's startup/isolation inventory; then build fixtures before app-route probes.
  - **Evidence / handoff:** Pending; record fixture IDs and isolation command for consumers.

- [ ] **NR-0.1-A-T03 — Turn the six audit probe families into permanent regression tests**
  - **Priority / state:** P0 / Blocked.
  - **Owner / reviewer / last update:** Unassigned / release integrator to be assigned / 2026-10-16 (planning).
  - **Depends on:** NR-0.1-A-T02.
  - **Blocks:** NR-0.1-A-T05.
  - **Source / purpose:** Pathway A-T03; reproduce I-01, I-02, I-08, I-09, I-11, and I-14 using actual code behavior.
  - **Target files / outputs:** Proposed `tests/test_nr0_regressions.py` or clearly grouped additions to existing suites; inspect `backend/dependencies.py`, `backend/routers/analytics.py`, `backend/routers/widget.py`, `backend/services/sql_engine.py`, `backend/services/citation_service.py`, and `backend/services/automl_service.py`; extend the baseline coverage record.
  - **Implementation:**
    1. Assert tenant administrators cannot use global tenant/admin endpoints to obtain another tenant's data (I-01 → NR-1.1-A).
    2. Exercise widget handshake and chat with another visitor's, another key's, and a private dashboard conversation ID; inspect captured provider input to detect private-history leakage without mocking authorization (I-02 → NR-1.1-B).
    3. Execute synthetic SQLite queries with excessive outer LIMIT and nested LIMIT/CTE cases; assert the requested final cap is enforced by the real executor (I-08 → NR-1.2-B).
    4. Force embedding failure and assert the answer is unverified, with no positive verified/grounded claim (I-11 → NR-2.2-A).
    5. Count actual gateway invocations for widget response modes and verify one response does not generate its answer twice; use deterministic provider boundary doubles (I-14 → NR-2.3-A).
    6. Feed ten revenue rows of 100 through the real KPI computation: total must be 1,000 and no invented 900% trend may be presented without a valid comparison period (I-09 → NR-2.1-A).
    7. Verify each failing case reaches the intended behavior; add a legitimate positive/control case where applicable. Record the responsible fix sprint and apply the narrow known-failure policy above without changing product logic to force a pass.
  - **Acceptance criteria:** All six families have reproducible tests of desired behavior; failures identify actual defects, not missing keys/downloads or copied expected outputs. A later repair can turn each case into a real passing regression.
  - **Verification:** Run each family against the recorded baseline; capture actual assertions and control-case results. Report known failures/strict expected failures separately from passes.
  - **Migration / recovery:** Disposable fixtures only; these tests do not authorize production exploitation or feature fixes.
  - **Blocker / next action:** Await A-T02's collection-safe fixtures. Any unresolved defect outside these six is captured in A-T06's coverage map.
  - **Evidence / handoff:** Pending; store issue IDs, test node IDs, observed failures, and fix-owner references.

- [ ] **NR-0.1-A-T04 — Isolate widget SSE tests from live providers and downloads**
  - **Priority / state:** P1 / Blocked.
  - **Owner / reviewer / last update:** Unassigned / release integrator to be assigned / 2026-10-16 (planning).
  - **Depends on:** NR-0.1-A-T02.
  - **Blocks:** NR-0.1-A-T05.
  - **Source / purpose:** Pathway A-T04, I-18. The historical widget SSE failure crossed an unmocked streaming-provider boundary.
  - **Target files / outputs:** `tests/test_phase2_stage_b_chat_widget.py`, `tests/test_phase7_1_2_streaming_backend.py`, shared NR-0 test fixtures; inspect `backend/services/chat_stream.py` and the gateway call sites.
  - **Implementation:**
    1. Trace the stream route's actual gateway binding and mock `generate_stream` at the used reference with a real async iterator, plus consistent synthetic usage metadata.
    2. Stub any additional provider/embedding calls reached by the test without replacing the route, SSE encoder, persistence callback, or limiter behavior being verified.
    3. Parse SSE events and assert ordered content plus terminal success/error behavior instead of accepting any raw substring as proof of success.
    4. Reuse existing cancellation/error cases where suitable and verify missing external keys and empty model caches do not cause outbound requests or downloads in normal test execution.
  - **Acceptance criteria:** The previously provider-dependent widget SSE case passes offline for the correct reason. Tests still detect malformed streaming, missing completion, and relevant failures.
  - **Verification:** Run the isolated widget and existing streaming suites with provider credentials absent and outbound calls guarded; repeat without relying on a downloaded embedding model.
  - **Migration / recovery:** Test-only repair; maintain opt-in integration boundaries and preserve current stream contracts until their owning sprint changes them.
  - **Blocker / next action:** Await A-T02; may be completed independently of A-T03 once fixtures are verified.
  - **Evidence / handoff:** Pending; record patched call sites, exact commands, and actual case outcomes.

- [ ] **NR-0.1-A-T05 — Establish the Python 3.11 and frontend verification baseline**
  - **Priority / state:** P1 / Blocked.
  - **Owner / reviewer / last update:** Unassigned / release integrator to be assigned / 2026-10-16 (planning).
  - **Depends on:** NR-0.1-A-T03, NR-0.1-A-T04.
  - **Blocks:** NR-0.1-A-T06.
  - **Source / purpose:** Pathway A-T05, I-18. Current deployment/CI select Python 3.11; old audit results used Python 3.14.
  - **Target files / outputs:** Existing backend/frontend suites, `package.json`, `backend/requirements.txt`, CI/runtime settings as reference; baseline report and necessary isolated verification tooling.
  - **Implementation:**
    1. Locate or establish a dedicated Python 3.11 environment and record its exact patch/dependency versions. Do not silently use a different global Python or change the production runtime to avoid incompatibility.
    2. Run isolation preflight, backend collection/tests, and backend initialization checks against disposable data; use no live providers or secrets.
    3. Run frontend tests and Vite production build with the recorded Node/npm environment. Record widget-specific checks when relevant and avoid committing generated artifacts by accident.
    4. Classify every outcome as pass, known linked regression, unexpected code failure, skipped integration, or environment failure. Investigate unexpected failures; assign any out-of-scope repair explicitly rather than hiding it.
    5. Save commands, counts, timings, warnings, runtime details, and repeatability notes. Do not describe skipped live integrations or expected failures as passing behavior.
  - **Acceptance criteria:** Fresh Python 3.11 backend and frontend evidence exists; normal tests need no live credentials/downloads; unexpected failures are resolved or remain explicit blockers. Known linked product regressions follow the sprint policy.
  - **Verification:** Repeat targeted affected checks after any test-tooling adjustment; reviewer can reproduce the recorded commands. A missing Python 3.11 environment leaves this task unverified.
  - **Migration / recovery:** Disposable test environment only; full dependency pinning/type-check CI remains NR-3.2-A.
  - **Blocker / next action:** Await A-T03/A-T04; verify Python 3.11 availability at execution and record any actual environment blocker.
  - **Evidence / handoff:** Pending; do not copy the historical 486/1 or 20-test results.

- [ ] **NR-0.1-A-T06 — Reconcile legacy work and record performance/coverage baselines**
  - **Priority / state:** P2 / Blocked.
  - **Owner / reviewer / last update:** Unassigned / release integrator to be assigned / 2026-10-16 (planning).
  - **Depends on:** NR-0.1-A-T05.
  - **Blocks:** NR-0.1-B-T01.
  - **Source / purpose:** Pathway A-T06 and section 14; eliminate duplicate ownership and establish meaningful before/after measurements.
  - **Target files / outputs:** `todo.md`, baseline report, existing build output statistics and disposable request harness; read the pathway crosswalk and catalog/ERD implementation through Graft.
  - **Implementation:**
    1. Cross-reference Task 6.1 → NR-5.2-B, Task 6.2 → NR-3.1-A, and Task 6.3 → NR-1.1-A/NR-1.2-A; map legacy key hashing, CORS, host validation, reflection, CI/type checks, and latency debt to their existing pathway owners.
    2. Verify the “persistent catalog as ERD source” backlog claim against code before proposing any closure. Preserve ERD export/large-layout items as optional existing work and preserve every historical completion record.
    3. Record I-01 through I-18 in a coverage map with test node IDs or an explicit coverage gap, current status, and owning fix sprint. Link remaining cases to later work; do not declare untested issues resolved.
    4. Record fresh main/widget/ERD bundle sizes where produced, including compression and measurement method. Measure representative synthetic non-streaming/streaming requests and SQL/grounding paths with fixed data, warm/cold distinction, sample count, and latency/TTFT statistics.
    5. Label mocked-provider latency as application overhead, separate from live-provider latency. Save the repeatable workload and confirm one owner per overlap.
    6. Review Sprint A's evidence and record its exit decision, known-failure list, and unresolved operational limits.
  - **Acceptance criteria:** Legacy work has an explicit crosswalk with no duplicate implementation ownership; all audit IDs have a truthful coverage status; current bundle/request baselines are reproducible.
  - **Verification:** Reviewer checks mappings against pathway section 14 and recomputes representative measurements. Preserve legacy entries unless a separately verified completion is being recorded under the normal protocol.
  - **Migration / recovery:** No product migration or performance optimization; measurement fixtures remain synthetic.
  - **Blocker / next action:** Await A-T05 evidence, then close Sprint A and make B-T01 ready.
  - **Evidence / handoff:** Pending; this task's reviewed completion is the baseline gate consumed by Sprint B.

##### Sprint NR-0.1-B — Establish versioned migrations

- **Priority / owner:** P1 foundation; data/platform implementer and release integrator reviewer, unassigned.
- **Prerequisites:** Sprint A baseline, represented by verified NR-0.1-A-T06 and its transitive dependencies.
- **Issues / legacy links:** I-17 schema-change portion; migration foundation for later persisted changes. Durable production storage, Docker/Compose, and worker infrastructure remain NR-3.1-A.
- **Proposed outputs:** `backend/alembic.ini`, `backend/migrations/env.py`, `backend/migrations/versions/`, `backend/scripts/schema_preflight.py`, `tests/test_nr0_migrations.py`, schema reconciliation report, and migration runbook. Confirm naming during B-T01/B-T02 before introducing files; they do not exist merely because they are listed here.
- **Exit checks:** Fresh/known-legacy convergence, read-only preflight, unknown-drift rejection, explicit deployment migration command, no production startup DDL, repeatable validated backfill, and measured restore/application rollback.
- **Supported state versus query connectors:** This sprint governs the application's own state database. Verify SQLite and PostgreSQL compatibility. Support for querying customer MySQL/Mongo sources does not imply their schemas are owned or migrated by this application.

- [ ] **NR-0.1-B-T01 — Reconcile ORM, canonical SQL, and supported installed layouts**
  - **Priority / state:** P1 / Blocked.
  - **Owner / reviewer / last update:** Unassigned / data/platform reviewer to be assigned / 2026-10-16 (planning).
  - **Depends on:** NR-0.1-A-T06.
  - **Blocks:** NR-0.1-B-T02.
  - **Source / purpose:** Pathway B-T01, I-17. Table counts and concrete field/constraint meanings differ across the application and specification.
  - **Target files / outputs:** `backend/models.py`, `backend/schemas.py`, `backend/services/db_migration.py`, `docs/database/Full_Project_Schemas.sql`, `docs/database/Database_ERD.md`; proposed reconciliation report and synthetic legacy-layout fixture definitions.
  - **Implementation:**
    1. Inventory tables, columns/types/defaults/nullability, primary/foreign/unique constraints, indexes, relationships, and SQLite/PostgreSQL differences from source and isolated reflection.
    2. Compare the 46 declared ORM tables with the 35 SQL definitions; classify runtime-only tables, spec-only requirements, renamed fields, constraint differences, and historical migration additions.
    3. Review concrete examples including conversation ownership/session fields, `Message.metadata_json` versus SQL `metadata`, document fields, and hierarchical chunk relationships.
    4. Define the intended baseline schema and a finite set of supported installed layouts. Use synthetic/anonymized disposable copies; never access a real installation implicitly.
    5. Record decisions and unresolved ambiguities without deleting fields, inventing data, or rewriting historic claims. Identify what the canonical spec must change to reflect deliberately preserved runtime behavior.
  - **Acceptance criteria:** Reviewed table/column/constraint reconciliation and supported-layout matrix exist; unresolved mappings that affect migration block B-T02 until decided.
  - **Verification:** Compare static inventory with reflected synthetic layouts; reviewer verifies representative constraints and source consumers, not just table counts.
  - **Migration / recovery:** Inventory only; no DDL or stamping of an existing database.
  - **Blocker / next action:** Await A-T06 baseline; then resolve schema decisions before generating a revision.
  - **Evidence / handoff:** Pending; capture schema fingerprints and decision references for B-T02/B-T03.

- [ ] **NR-0.1-B-T02 — Add reviewed Alembic history and read-only schema preflight**
  - **Priority / state:** P1 / Blocked.
  - **Owner / reviewer / last update:** Unassigned / data/platform reviewer to be assigned / 2026-10-16 (planning).
  - **Depends on:** NR-0.1-B-T01.
  - **Blocks:** NR-0.1-B-T03.
  - **Source / purpose:** Pathway B-T02; replace unversioned schema mutation with an explicit, inspectable migration foundation.
  - **Target files / outputs:** Proposed Alembic/preflight files and migration tests above; `backend/requirements.txt`, `backend/database.py` only as needed for side-effect-free configuration; reviewed canonical SQL/docs.
  - **Implementation:**
    1. Add a Python-3.11-compatible Alembic dependency and configuration that loads model metadata without importing `main`, triggering seeding, or connecting to an unintended default database.
    2. Create a reviewed initial revision describing the reconciled schema. Do not call today's mutable `Base.metadata.create_all` inside a historic revision or accept autogenerated drops/renames without review.
    3. Implement read-only preflight reporting dialect, detected revision, schema fingerprint, drift, and whether the layout is empty, recognized legacy, current, or unsupported.
    4. Include indexes/constraints/type/default checks with deliberate dialect normalization; redact URLs and credentials. Unknown layouts fail with actionable details and no DDL/stamp.
    5. Update canonical specification and schema documentation to reflect reviewed baseline decisions; preserve compatibility rather than forcing the application into obsolete field names.
  - **Acceptance criteria:** The initial revision is reproducible; preflight identifies all declared fixture layouts and rejects unsupported drift without changing them; metadata discovery has no app-startup side effects.
  - **Verification:** Test preflight against empty, known, current, malformed, and unknown-extra-column layouts; compare schema/data and revision markers before/after read-only checks. Review generated migration operations.
  - **Migration / recovery:** Run only on disposable databases now; backup/restore policy must be documented before deployment. Full installation/adoption behavior is B-T03.
  - **Blocker / next action:** Await B-T01's reviewed schema decisions.
  - **Evidence / handoff:** Pending; record actual preflight/Alembic commands, exit codes, revision ID, and supported fingerprints.

- [ ] **NR-0.1-B-T03 — Implement separate fresh-install and supported-upgrade procedures**
  - **Priority / state:** P1 / Blocked.
  - **Owner / reviewer / last update:** Unassigned / data/platform reviewer to be assigned / 2026-10-16 (planning).
  - **Depends on:** NR-0.1-B-T02.
  - **Blocks:** NR-0.1-B-T04.
  - **Source / purpose:** Pathway B-T03; existing installations cannot safely be treated like empty databases.
  - **Target files / outputs:** Alembic revision history, preflight/adoption entrypoint, migration tests/fixtures, proposed migration runbook.
  - **Implementation:**
    1. Define an empty-database path that applies the reviewed revisions from scratch without any implicit production seed.
    2. Define a recognized-current-schema adoption path: require successful exact compatibility preflight before recording its initial revision; never use blind stamping.
    3. Define a recognized-older-layout upgrade path with explicit reconciliation operations and validated data mapping before it reaches the current revision.
    4. Reject unknown, ambiguous, partially applied, or newer incompatible layouts with a recovery/remediation report; preserve unexplained columns and records.
    5. Document backup prerequisites, dry-run/preflight expectations, command order, retry behavior, and compatibility with existing application records and APIs.
  - **Acceptance criteria:** Empty and every supported legacy fixture converge to the same intended schema; records/relationships survive; unsupported layouts remain unchanged and return a clear error.
  - **Verification:** Exercise fresh install, safe adoption, known upgrades, repeated invocation, partial state, and unknown drift using disposable SQLite/PostgreSQL fixtures; compare schema fingerprints and data invariants.
  - **Migration / recovery:** Require a readable pre-upgrade backup before actual deployment; failed adoption must not falsely mark a schema current.
  - **Blocker / next action:** Await B-T02's revision/preflight contract; missing PostgreSQL execution evidence remains explicit rather than counted as a pass.
  - **Evidence / handoff:** Pending; record supported starting layouts, resulting revision IDs, and invariant checks.

- [ ] **NR-0.1-B-T04 — Move production DDL out of application startup**
  - **Priority / state:** P1 / Blocked.
  - **Owner / reviewer / last update:** Unassigned / release integrator to be assigned / 2026-10-16 (planning).
  - **Depends on:** NR-0.1-B-T03.
  - **Blocks:** NR-0.1-B-T05.
  - **Source / purpose:** Pathway B-T04, I-17. Both `main` and the admin seed path can mutate schema and swallow errors.
  - **Target files / outputs:** `backend/main.py`, `backend/scripts/seed_admin.py`, `backend/services/db_migration.py`, `backend/database.py`, `render.yaml`, relevant startup tests, migration runbook; deployment entrypoint if needed.
  - **Implementation:**
    1. Trace all production callers of `create_all` and `run_schema_migrations`, including the seed helper. Remove their production startup DDL path while preserving explicitly invoked disposable test/dev setup.
    2. Make startup perform a read-only schema compatibility check with actionable failure for incompatible state; no swallowed migration exception should make an incompatible app appear healthy.
    3. Define a separate one-time deployment migration command/job, with a single migration owner and concurrency control, before application instances start. Choose a supported mechanism for the actual deployment; do not assume a host feature exists.
    4. Ensure seeding cannot bypass the compatibility check or secretly recreate/migrate production schema. Coordinate the seam with the later NR-1.1-A production-seeding/auth fix; do not mark I-03 resolved from DDL removal alone.
    5. Update test setup, deployment/runbook instructions, and migration callers that depended on startup side effects. Keep full container/worker build-out assigned to NR-3.1-A.
  - **Acceptance criteria:** A compatible production-mode app starts without DDL from either main or seeding; incompatible state fails clearly; only the explicit migration path changes schema, once per deployment.
  - **Verification:** Start the app against disposable compatible/incompatible schemas with DDL blocked or instrumented; inspect all startup paths and concurrent migration attempts. Verify import failure does not mutate schema.
  - **Migration / recovery:** Preflight/backup → explicit migration → compatibility check → app start. Roll back only to a demonstrated compatible app/schema combination; never restore hidden startup migration as a fallback.
  - **Blocker / next action:** Await B-T03 installation/upgrade evidence and serialize ownership of shared startup/deployment files.
  - **Evidence / handoff:** Pending; capture DDL instrumentation and explicit migration/start commands.

- [ ] **NR-0.1-B-T05 — Establish additive expansion, validated backfill, and constraint enforcement**
  - **Priority / state:** P1 / Blocked.
  - **Owner / reviewer / last update:** Unassigned / data/platform reviewer to be assigned / 2026-10-16 (planning).
  - **Depends on:** NR-0.1-B-T04.
  - **Blocks:** NR-0.1-B-T06.
  - **Source / purpose:** Pathway B-T05; later releases need a reusable safe pattern for changing persistent fields.
  - **Target files / outputs:** Reviewed migration revisions/helpers, synthetic legacy fixtures, `tests/test_nr0_migrations.py`, reconciliation report and migration runbook; models/schemas/canonical SQL only for justified reconciliation.
  - **Implementation:**
    1. Select an actual reconciled addition from B-T01 for the exercise; if the accepted baseline needs no new production field, demonstrate the sequence with test-only schema fixtures rather than inventing a feature column.
    2. Expand with compatible nullable/defaulted fields or tables; preserve existing data, old readers, and relationships.
    3. Backfill in bounded, restartable steps using validated mappings, preserving ambiguous records and reporting exceptions without assigning guessed ownership, publishing internal content, or changing account authority.
    4. Validate row counts, null/duplicate/orphan counts, types, and required relationships before enforcing non-null/unique/foreign-key constraints.
    5. Enforce constraints only when checks pass. Document transactional/SQLite batch-rebuild differences, interruption behavior, and any later consumer cutover required before retiring old fields.
  - **Acceptance criteria:** Repeat/restart is safe; malformed or ambiguous rows block constraint enforcement with an actionable report; no unexplained drop/rename or invented business data occurs.
  - **Verification:** Test empty/valid/invalid/duplicate/orphan rows, interruption and rerun, and SQLite/PostgreSQL behavior. Confirm constraints are not applied when validation fails and secrets are absent from reports.
  - **Migration / recovery:** Keep an expansion-compatible application version and backup; document restore/forward-fix for irreversible steps, not a fictional universally safe downgrade.
  - **Blocker / next action:** Await B-T04's explicit migration entrypoint and reviewed reconciliation fixture.
  - **Evidence / handoff:** Pending; record chosen example, validation counts, interruption results, and compatibility limits.

- [ ] **NR-0.1-B-T06 — Rehearse upgrade, restore, and application rollback; close NR-0**
  - **Priority / state:** P1 / Blocked.
  - **Owner / reviewer / last update:** Unassigned / release integrator to be assigned / 2026-10-16 (planning).
  - **Depends on:** NR-0.1-B-T05.
  - **Blocks:** NR-0 phase exit; migration-dependent persisted changes in later NR phases.
  - **Source / purpose:** Pathway B-T06, I-17 schema portion; prove recovery rather than relying on a documented procedure alone.
  - **Target files / outputs:** Migration tests/fixtures, baseline report, schema reconciliation report, migration runbook, required task/changelog/handoff records.
  - **Implementation:**
    1. Create readable backups of populated disposable supported layouts; record schema version/fingerprint, row counts, key relationships, and synthetic source/index references where relevant.
    2. Run fresh installs and full supported upgrades on SQLite and disposable PostgreSQL, then compare converged schema, records, constraints, and application smoke behavior.
    3. Inject migration/backfill interruption and unknown drift; verify safe stopping and the documented retry/recovery behavior.
    4. Restore the backup into a separate empty disposable destination and verify data and application behavior. Record measured recovery time and any data-loss window instead of promising unmeasured recovery targets.
    5. Rehearse application rollback only to a demonstrated compatible version; if an older revision has unsafe startup mutation, document that restriction and verify the supported restore/forward-fix alternative.
    6. Run required final backend/frontend checks, review both sprint gates, and link the remaining known issue failures to their owning later phases. Publish the NR-0 completion evidence and next ready phase/task recommendation without claiming NR1 is release-ready.
  - **Acceptance criteria:** All supported install/upgrade/restore scenarios have actual passing evidence; unsupported layouts fail without destructive changes; compatible rollback or an explicitly verified recovery alternative exists; all 12 NR-0 task requirements are accounted for.
  - **Verification:** Reviewer checks commands, actual revisions/runtimes, restored row/relationship invariants, startup DDL checks, and baseline suite results. Mocked PostgreSQL behavior or an unexecuted restore is not sufficient to close this task.
  - **Migration / recovery:** Use disposable copies only in this implementation phase; actual production migration/deployment is a separate operation requiring its own selected target and execution scope.
  - **Blocker / next action:** Await B-T05 and real disposable PostgreSQL/recovery evidence; record missing infrastructure as a blocker if necessary.
  - **Evidence / handoff:** Pending; archive verified task records and retain current phase summary plus unresolved later-phase defects.

#### NR-0 completion checklist for the implementation/review session

This is a gate description, not a claim that any check is complete.

| Gate | Required evidence | Current status |
|---|---|---|
| Reproducible isolated baseline | A-T01/A-T02 records and pre-collection isolation checks | Pending |
| Actual defect coverage and offline SSE | A-T03 issue-linked regressions; A-T04 real passing offline tests | Pending |
| Deployment-runtime and performance evidence | A-T05 Python 3.11/frontend results; A-T06 crosswalk and measured baselines | Pending |
| Reviewed schema and explicit upgrade paths | B-T01 decisions; B-T02 preflight/history; B-T03 fresh/legacy convergence | Pending |
| Controlled schema changes and backfill | B-T04 startup DDL absence; B-T05 validation/retry evidence | Pending |
| Recovery and integration | B-T06 executed SQLite/PostgreSQL upgrade/restore/rollback evidence and review | Pending |
| Accurate project records | Archived task IDs with evidence; current summaries; required implementation records; legacy history preserved | Pending |

**Suggested implementation handoff:** Read AGENTS.md and implement Phase NR-0 from this selected-phase work area, beginning with NR-0.1-A-T01. Execute ready tasks, establish isolation before backend imports, verify the stated acceptance criteria, archive complete task blocks, and revisit blocked tasks after prerequisites pass. Continue through NR-0 only; report unresolved blockers and remaining known product defects. Do not commit, push, or deploy unless separately requested.

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
