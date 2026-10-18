# DataSpeakAI — Implementation Baseline & Verification Record (Phase NR-0)

**Document Reference:** `docs/reports/nr0_baseline.md`  
**Creation Date:** 2026-10-16  
**Parent Task:** `NR-0.1-A-T01 — Record the reproducible implementation baseline`  
**Governing Standard:** [`AGENTS.md`](../../AGENTS.md) & [`docs/next_release_implementation_pathway.md`](../next_release_implementation_pathway.md)  
**Status:** Baseline established and verified  

---

## 1. System & Environment Baseline

### 1.1 Source Control Baseline
* **Current Branch:** `main`
* **Commit Hash (HEAD):** `36f74a91233444935bede87bc852da1a15a9d668`
* **Parent Commit:** `36065f2107e30b499302bd68ea299d51fbb2dcf5`
* **Working Tree State:** Clean (zero uncommitted dirty files at implementation start)
* **Workspace Path:** `c:\Users\waliu\OneDrive - Higher Education Commission\Desktop\dataspeakAI`

### 1.2 Host & Runtime Inventory
* **Operating System:** Windows 11 Pro / Enterprise (x86_64 MSVC)
* **Shell Environment:** PowerShell 7 / Windows PowerShell
* **Node.js Executable & Version:** `v22.17.0` (`node --version`)
* **npm Executable & Version:** `10.9.2` (`npm --version`)
* **Host Global Python:** `Python 3.13.2` (`python --version`)
* **Package & Tooling Manager:** `uv 0.11.15` installed (`uv --version`)
* **Target Deployment Python:** `3.11.0` (mandated by [`render.yaml`](../../render.yaml#L11)) and `3.11` (mandated by [`.github/workflows/ci-cd.yml`](../../.github/workflows/ci-cd.yml#L24))
* **Dedicated Project Virtualenv:** CPython `3.11.15` provisioned via `uv` at `.venv/`
  - Activation: `.venv\Scripts\activate`
  - Direct Binary: `.\.venv\Scripts\python.exe` (Verified: `Python 3.11.15`)

---

## 2. Configuration & Secrets Inventory

All environment variable references have been audited across `backend/`. No plain-text secrets, API keys, or database credentials are captured in this record.

| Environment Variable | Source File References | Purpose | Default / Fallback Behavior | Sensitivity |
|---|---|---|---|---|
| `DATABASE_URL` | `backend/database.py:9` | Application persistence database connection URI | Defaults to `sqlite:///./app.db` | High (may contain DB credentials) |
| `SECRET_KEY` | `backend/auth.py:7`, `backend/main.py:33`, `backend/services/db_utils.py:5` | JWT access token signing & symmetric encryption for DB passwords | Defaults to insecure hardcoded string in development | Critical (cryptographic key) |
| `ALGORITHM` | `backend/auth.py:10` | JWT signing algorithm | Defaults to `HS256` | Low |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `backend/auth.py:11` | Access token lifespan in minutes | Defaults to `1440` (24 hours) | Low |
| `ENVIRONMENT` | `backend/main.py:26`, `backend/services/widget_session_service.py:13` | Environment mode (`development` vs `production`) | Defaults to `development` | Medium |
| `WIDGET_HMAC_SECRET` | `backend/main.py:27`, `backend/services/widget_session_service.py:14` | Secret for HMAC signing of widget session tokens | Enforced in `production`, falls back to `SECRET_KEY` | Critical |
| `GEMINI_API_KEY*` | `backend/services/llm_generation_service.py`, `backend/routers/widget.py` | Google Gemini API key(s) (1..15+) | Empty string / skipped if absent | Critical (external billing) |
| `GROQ_API_KEY*` | `backend/services/llm_generation_service.py` | Groq LLM API key(s) (1..15+) | Empty string / skipped if absent | Critical (external billing) |
| `CELERY_BROKER_URL` | `backend/celery_app.py:6`, `backend/routers/documents.py:413` | Redis message broker URL for Celery workers | Defaults to `redis://localhost:6379/0` | High |
| `CELERY_RESULT_BACKEND` | `backend/celery_app.py:7` | Redis backend URL for Celery task results | Defaults to `redis://localhost:6379/1` | High |
| `REDIS_URL` | `backend/services/widget_rate_limiter.py:60` | Shared Redis store for widget rate limiting | In-memory token bucket fallback if absent | High |
| `DEFAULT_ADMIN_EMAIL` | `backend/scripts/seed_admin.py:13` | Initial bootstrap superadmin user email | Defaults to `admin@dataspeak.ai` | Medium |
| `DEFAULT_ADMIN_PASSWORD` | `backend/scripts/seed_admin.py:14` | Initial bootstrap superadmin user password | Defaults to `AdminPassword123!` | Critical |
| `ALLOW_PRIVATE_DB_HOSTS` | `backend/services/erd_service.py:29` | Allows loopback / private IP subnets in ERD reflection | Defaults to `false` | High (SSRF boundary) |
| `ERD_MAX_TABLES` | `backend/services/erd_service.py:27` | Maximum tables reflected in ERD | Defaults to `300` | Low |
| `ERD_REFRESH_COOLDOWN_SECONDS` | `backend/services/erd_service.py:28` | Per-tenant rate limit cooldown for schema reflection | Defaults to `30` | Low |
| `EMBEDDING_WARMUP` | `backend/main.py:54` | Flag controlling startup HuggingFace embedding warm-up | Defaults to `true` in non-test environments | Medium |

---

## 3. Startup DDL, Seeding & State Side-Effects Audit

A critical finding from source inspection is that simply importing `backend/main.py` causes persistent state mutations on disk:

1. **Unconditional Engine Instantiation (`backend/database.py:L7-L19`):**
   - Calls `load_dotenv()` immediately on module load.
   - Immediately creates `engine = create_engine(os.getenv("DATABASE_URL", "sqlite:///./app.db"))`.
   - If tests or scripts import modules before overriding `os.environ["DATABASE_URL"]`, an active engine bound to the repository's `./app.db` is opened.

2. **Startup DDL & Seeding (`backend/main.py:L38-L60`):**
   - Line 38: `models.Base.metadata.create_all(bind=engine)` creates any missing tables in `./app.db`.
   - Line 43: `run_schema_migrations(engine)` alters existing tables dynamically.
   - Line 50: `seed_superadmin()` creates/resets the default admin user.
   - Line 57: `warmup_embeddings()` downloads/loads the sentence-transformer embedding model.

3. **Seeding Password Reset Defect (`backend/scripts/seed_admin.py:L66-L68`):**
   - If `admin@dataspeak.ai` already exists, line 67 unconditionally resets its password:
     ```python
     admin_user.hashed_password = get_password_hash(DEFAULT_ADMIN_PASSWORD)
     db.commit()
     ```
   - This causes development/testing runs to overwrite admin passwords on disk.

4. **Pytest Collection Hazard (`tests/test_phase2_stage_b_chat_widget.py:L46`):**
   - Executes `from main import app` at top level.
   - At pytest collection time (before any test fixture executes), `backend/main.py` is loaded, triggering table creation and seeding on `./app.db`.

---

## 4. Test Isolation Protocol (Prerequisite for NR-0.1-A-T02)

To prevent pytest collection or test runs from mutating `./app.db`, exhausting external LLM quotas, or downloading models, the following **Pre-Collection Isolation Protocol** is mandatory for all test execution:

```powershell
# Set process-level environment overrides BEFORE running pytest or importing backend
$env:DATABASE_URL = "sqlite:///:memory:"
$env:ENVIRONMENT = "test"
$env:EMBEDDING_WARMUP = "false"
$env:SECRET_KEY = "test-isolated-secret-key-for-unit-testing-32b"
$env:WIDGET_HMAC_SECRET = "test-isolated-widget-hmac-secret-64b"
$env:CELERY_BROKER_URL = ""
$env:CELERY_RESULT_BACKEND = ""
$env:REDIS_URL = ""

# Execute isolated tests using dedicated Python 3.11 virtualenv
.\.venv\Scripts\python.exe -m pytest tests -q
```

---

## 5. Verification Commands & Baseline Suite Inventory

### 5.1 Frontend Verification Entrypoints
* **Frontend Vitest Suite:**
  ```powershell
  cmd.exe /c "npm test"
  ```
* **Frontend Production Build:**
  ```powershell
  cmd.exe /c "npm run build"
  ```
* **Widget Standalone Build:**
  ```powershell
  npm run build:widget
  ```

### 5.2 Backend Verification Entrypoints
* **Isolated Backend Test Run:**
  ```powershell
  .\.venv\Scripts\python.exe -m pytest tests -q
  ```
* **Isolated Single Test Family (e.g., Widget SSE):**
  ```powershell
  .\.venv\Scripts\python.exe -m pytest tests/test_phase2_stage_b_chat_widget.py -k "test_widget_chat_sse_streaming" -q
  ```

---

## 6. Fresh Python 3.11 & Frontend Baseline Execution Results

### 6.1 Backend Test Suite (Python 3.11.15 in `.venv`)
* **Execution Command:**
  ```powershell
  .\.venv\Scripts\python.exe -m pytest tests/test_nr0_isolation.py tests/test_nr0_regressions.py tests/test_phase2_stage_b_chat_widget.py -k "test_widget_chat_sse_streaming or test_probe or test_nr0" -v
  ```
* **Runtime & Environment:** CPython `3.11.15`, pytest `9.1.1`, pluggy `1.7.0`
* **Duration:** 202.69s (3m 22s)
* **Results Summary:**
  - Total Tests Evaluated: 17
  - **Passed Tests:** 11 (5 isolation tests, 5 regression controls, 1 isolated widget SSE streaming test)
  - **Expected Failures (Strict XFAIL):** 6 (I-01, I-02, I-08, I-09, I-11, I-14)
  - **Unexpected Failures:** 0
  - **Skipped / Deselected:** 13 (unselected tests in `test_phase2_stage_b_chat_widget.py`)
  - **Warnings:** 17 (Pydantic V2 deprecation notices on Config classes, SQLAlchemy MovedIn20Warning)

### 6.2 Frontend Vitest Suite
* **Execution Command:**
  ```powershell
  cmd.exe /c "npm test"
  ```
* **Runtime:** Node.js `v22.17.0`, npm `10.9.2`
* **Test Files:** 1 passed (`src/app/components/ui/button.test.tsx`)
* **Tests:** 20 passed (20 total)
* **Duration:** 6.53s

---

## 7. Performance & Bundle Size Baseline

### 7.1 Production Build Measurement
* **Build Command:**
  ```powershell
  cmd.exe /c "npm run build"
  ```
* **Build Duration:** 52.77s (0 errors)
* **Bundle Asset Breakdown:**
  | Output File | Size | Gzip Size | Notes |
  |---|---|---|---|
  | `dist/index.html` | 0.49 kB | 0.31 kB | Clean HTML entry shell |
  | `dist/assets/index-DB2RLBm0.js` | 1,663.11 kB | 456.74 kB | Main application bundle (>500 kB chunk warning) |
  | `dist/assets/index-D7Uu6y4Q.css` | 78.47 kB | 13.79 kB | Tailwind CSS & design tokens |

* **Optimization Opportunity (Tracked for NR-2.3-A / NR-3.2-A):**
  - Main bundle exceeds 500 kB chunk threshold due to inline loading of heavy chart primitives, editor components, and lucide icon maps. Dynamic code-splitting via `React.lazy()` recommended for secondary dashboard routes.

---

## 8. Legacy Work Reconciliation Crosswalk (Section 14)

Per `docs/next_release_implementation_pathway.md` Section 14, existing debt and historical Phase 6/7 items are mapped to sole ownership under NR releases to prevent duplicate implementations:

| Historical / Legacy Backlog Task | Pathway Owning Task | Scope & Reconciliation Rules |
|---|---|---|
| **Task 6.1 — Stripe Billing & Webhooks** | `NR-5.2-B` | Retain historical record; implement only after durable tenant metering in `NR-3.1-B`. |
| **Task 6.2 — Production Docker & Compose** | `NR-3.1-A` | Expand acceptance criteria to include persistent SQLite/PostgreSQL storage, Celery worker concurrency, and automated health checks. |
| **Task 6.3 — Production Security Hardening** | `NR-1.1-A` & `NR-1.2-A` | Split into explicit ownership: tenant authorization/CORS (`NR-1.1-A`) and database connection SSRF/credential encryption (`NR-1.2-A`). |
| **Legacy ApiKey Hashing Debt** | `NR-1.2-A` | Include database migration, one-time plaintext reveal on creation, cryptographic hashing verification, and key rotation. |
| **CORS Strictness Debt** | `NR-1.1-A` | Decouple dashboard CORS from standalone widget embed policy (`pk_live_*`). |
| **Connection Creation SSRF Validation** | `NR-1.2-A` | Validate all database host connection attempts across private RFC 1918 subnets, not only creation or ERD reflection. |
| **Persistent Metadata Catalog as ERD Source** | `NR-0.1-A` (verified) | Inspect current catalog-first implementation (`backend/services/erd_service.py`); live reflection runs only on cache miss. |
| **CI Lint/Type Checks & Test Automation** | `NR-3.2-A` | Re-enable automated test execution in `.github/workflows/ci-cd.yml` with disposable test database services. |
| **Phase 7 Streaming, Memory & Grounding** | `NR-1.2-B` & `NR-2.x` | Retain streaming foundations (`backend/services/chat_stream.py`); repair identified test isolation, SQL LIMIT caps, and citation confidence bounds. |

---

## 9. Issue Coverage & Regression Probe Map (I-01 to I-18)

| Issue ID | Defect Description | Severity | Permanent Test Node ID | Owning Fix Task | Status in NR-0 Baseline |
|---|---|---|---|---|---|
| **I-01** | Tenant Admin cross-tenant listing via global endpoint | P0 | `test_nr0_regressions.py::test_probe_i01_tenant_admin_cannot_list_all_platform_tenants` | `NR-1.1-A` | **XFAIL** (strict) — Defect verified |
| **I-02** | Anonymous widget session adopting private dashboard conversation | P0 | `test_nr0_regressions.py::test_probe_i02_widget_cannot_adopt_private_dashboard_conversation` | `NR-1.1-B` | **XFAIL** (strict) — Defect verified |
| **I-03** | Missing tenant scoping in conversation lookups | P0 | Integrated with I-02 probe | `NR-1.1-B` | Tracked under I-02 |
| **I-04** | Plaintext API keys stored in database | P1 | Contract test in `NR-1.2-A` | `NR-1.2-A` | Owned by NR-1.2-A |
| **I-05** | SSRF vulnerability in database connection strings | P1 | Contract test in `NR-1.2-A` | `NR-1.2-A` | Owned by NR-1.2-A |
| **I-06** | Database credentials logged or exposed in stack traces | P1 | Contract test in `NR-1.2-A` | `NR-1.2-A` | Owned by NR-1.2-A |
| **I-07** | Write queries allowed on read-only database connections | P0 | Contract test in `NR-1.2-B` | `NR-1.2-B` | Owned by NR-1.2-B |
| **I-08** | SQL query LIMIT bypasses outer `max_rows` cap | P1 | `test_nr0_regressions.py::test_probe_i08_sql_executor_enforces_max_rows_when_query_has_limit` | `NR-1.2-B` | **XFAIL** (strict) — Defect verified |
| **I-09** | KPI trend computation compares sum to row mean (900% phantom trend) | P1 | `test_nr0_regressions.py::test_probe_i09_kpi_trend_does_not_compare_sum_to_mean` | `NR-2.1-A` | **XFAIL** (strict) — Defect verified |
| **I-10** | Missing confidence scoring calibration in AutoML insights | P2 | Contract test in `NR-2.1-A` | `NR-2.1-A` | Owned by NR-2.1-A |
| **I-11** | Grounding failure returns positive 0.7 confidence score | P1 | `test_nr0_regressions.py::test_probe_i11_citation_grounding_reports_failure_honestly` | `NR-2.2-A` | **XFAIL** (strict) — Defect verified |
| **I-12** | PDF chunking creates orphan citations without page metadata | P2 | Contract test in `NR-2.2-B` | `NR-2.2-B` | Owned by NR-2.2-B |
| **I-13** | In-memory FAISS index lost on worker restart | P1 | Contract test in `NR-3.1-A` | `NR-3.1-A` | Owned by NR-3.1-A |
| **I-14** | Widget non-streaming generates answer twice (double billing) | P1 | `test_nr0_regressions.py::test_probe_i14_widget_non_streaming_generates_answer_only_once` | `NR-2.3-A` | **XFAIL** (strict) — Defect verified |
| **I-15** | Conversation memory manager deadlocks on concurrent stream termination | P2 | Contract test in `NR-2.3-A` | `NR-2.3-A` | Owned by NR-2.3-A |
| **I-16** | Unbounded rate limit in-memory dictionary leaks memory | P2 | Contract test in `NR-3.1-B` | `NR-3.1-B` | Owned by NR-3.1-B |
| **I-17** | Tenant quota bypass during high concurrency | P1 | Contract test in `NR-3.1-B` | `NR-3.1-B` | Owned by NR-3.1-B |
| **I-18** | Baseline reproducibility & test isolation gap | P0 | `test_nr0_isolation.py`, `test_phase2_stage_b_chat_widget.py` | `NR-0.1-A` | **RESOLVED & VERIFIED** |

---

## 10. Sprint NR-0.1-A Verification & Completion Sign-Off

- [x] **NR-0.1-A-T01:** System & environment baseline documented; Python 3.11 provisioned at `.venv/`.
- [x] **NR-0.1-A-T02:** Isolated synthetic security & data fixtures built in `tests/conftest.py` and `tests/fixtures/nr0/`; verified 5/5 passing in `tests/test_nr0_isolation.py`.
- [x] **NR-0.1-A-T03:** Six audit probe families converted into permanent regression tests in `tests/test_nr0_regressions.py`; verified 5 controls PASSED, 6 defects strictly XFAILED.
- [x] **NR-0.1-A-T04:** Widget SSE test in `tests/test_phase2_stage_b_chat_widget.py` isolated from live LLM providers with deterministic double; verified PASSED offline.
- [x] **NR-0.1-A-T05:** Fresh Python 3.11 (`11 passed, 6 xfailed, 0 errors`) and frontend baseline (`20 passed`, 0 build errors) verified.
- [x] **NR-0.1-A-T06:** Legacy work crosswalk and issue coverage map complete; bundle size recorded.

