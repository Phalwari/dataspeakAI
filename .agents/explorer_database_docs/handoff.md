# Comprehensive Handoff Report: DataSpeakAI Database Schemas & Documentation Analysis

**Agent:** explorer_database_docs  
**Working Directory:** `d:\dataspeak\.agents\explorer_database_docs`  
**Date:** 2026-08-04  

---

## 1. Observation

### A. Database Schemas & ERD Artifacts
1. **`d:\dataspeak\Full_Project_Schemas.sql`**:
   - Contains 333 lines of PostgreSQL SQL DDL creating **35 distinct tables** across 9 enterprise modules:
     - *Module 1 (Tenant Management)*: `tenants` (lines 5-12), `tenant_settings` (lines 14-21)
     - *Module 2 (User & Access Control)*: `users` (lines 27-35), `roles` (lines 37-41), `permissions` (lines 43-48), `memberships` (lines 50-57)
     - *Module 3 (Database Connection & Metadata)*: `database_connections` (lines 63-73), `secrets` (lines 75-82), `database_schemas` (lines 84-89), `table_metadata` (lines 91-98), `column_metadata` (lines 100-108)
     - *Module 4 (AI Engine & Chatbot)*: `chatbot_configs` (lines 114-124), `conversations` (lines 126-132), `messages` (lines 134-142), `intents` (lines 144-149), `query_templates` (lines 151-157), `executed_queries` (lines 159-167), `query_safety_logs` (lines 169-175)
     - *Module 5 (Knowledge Base RAG)*: `documents` (lines 181-189), `document_chunks` (lines 191-196), `collections` (lines 198-203), `vector_records` (lines 205-210)
     - *Module 6 (AI Insights & Analytics)*: `generated_insights` (lines 216-223), `recommendations` (lines 225-230), `dashboards` (lines 232-237), `widgets` (lines 239-244)
     - *Module 7 (Billing & Subscription)*: `subscriptions` (lines 250-257), `invoices` (lines 259-266), `payments` (lines 268-274), `metered_usage` (lines 276-282)
     - *Module 8 (API & Security)*: `api_keys` (lines 288-295), `rate_limits` (lines 297-302), `security_policies` (lines 304-310)
     - *Module 9 (Monitoring & Audit)*: `audit_logs` (lines 316-323), `system_metrics` (lines 325-332)
2. **`d:\dataspeak\Database_ERD.md`**:
   - Defines a simplified **10-table logical ERD** using Mermaid Crow's Foot notation (lines 11-134) and a data dictionary (lines 138-296):
     - `tenants`, `users`, `user_database_access`, `tenant_invites`, `database_connections`, `api_keys`, `chatbot_configs`, `documents`, `document_chunks`, `password_reset_otps`.
3. **`d:\dataspeak\DataSpeakAI_Complete_EERD.md`**:
   - Contains a 22-entity high-level Mermaid EERD diagram (lines 5-227) depicting full platform capability.
4. **Backend SQL / Migrations**:
   - No Alembic migration scripts (`alembic/`) or SQL migration scripts exist in `backend/` or project root.
   - `d:\dataspeak\backend\main.py:12` executes `models.Base.metadata.create_all(bind=engine)` on server load to initialize tables directly in SQLite/PostgreSQL.

### B. Python ORM Models (`d:\dataspeak\backend\models.py`)
- `backend/models.py` (140 lines) defines **10 SQLAlchemy ORM models**:
  1. `Tenant` (`tenants`, lines 6-16): `id`, `name`, `website`, `industry`, `address`, `created_at`.
  2. `User` (`users`, lines 18-32): `id`, `email`, `hashed_password`, `full_name`, `role`, `is_active`, `is_verified`, `tenant_id`, `created_at`.
  3. `UserDatabaseAccess` (`user_database_access`, lines 33-39): `id`, `user_id`, `database_id`.
  4. `TenantInvite` (`tenant_invites`, lines 40-54): `id`, `email`, `token`, `tenant_id`, `role`, `database_ids`, `expires_at`, `is_accepted`, `created_at`.
  5. `DatabaseConnection` (`database_connections`, lines 55-70): `id`, `tenant_id`, `name`, `db_type`, `host`, `username`, `password`, `database`, `status`, `created_at`.
  6. `ApiKey` (`api_keys`, lines 71-85): `id`, `tenant_id`, `name`, `description`, `key`, `status`, `total_requests`, `last_used_at`, `created_at`.
  7. `ChatbotConfig` (`chatbot_configs`, lines 86-101): `id`, `tenant_id`, `theme_color`, `widget_title`, `greeting_message`, `position`, `welcome_delay`, `max_history`, `sound_enabled`, `created_at`.
  8. `Document` (`documents`, lines 102-119): `id`, `tenant_id`, `name`, `file_type`, `size`, `status`, `embeddings_count`, `line_count`, `paragraph_count`, `table_count`, `image_count`, `created_at`.
  9. `DocumentChunk` (`document_chunks`, lines 120-131): `id`, `document_id`, `content`, `overlap_chars`, `chunk_index`, `created_at`.
  10. `PasswordResetOTP` (`password_reset_otps`, lines 132-139): `id`, `email`, `otp_code`, `expires_at`, `created_at`.

### C. Project Setup, Workflow & Configuration Artifacts
1. **Setup Guides**:
   - `SETUP_GUIDE.md`, `SETUP_GUIDE_v4.md`, and `setup_guide_v5.md` exist concurrently in root.
   - `setup_guide_v5.md:71` asserts `"Module 1-20 Implementation: Full support for all defined SaaS modules"`, despite 25 SQL tables/modules lacking Python models.
2. **Environment Variables**:
   - `d:\dataspeak\.env.example`: Defines `VITE_API_URL=http://localhost:8000` and `VITE_APP_NAME=DataSpeakAI`.
   - `SETUP_GUIDE.md:49` & `WORKFLOW.md:25`: Instruct setting `VITE_API_BASE_URL=http://localhost:8000`.
   - `backend/routers/users.py:129-130`: Hardcodes fallback GitHub credentials (`client_id="Ov23liPRgons4RlFv7FU"`, `client_secret="067e59b3c050792898954f727be0dbdbfc5c590a"`).
   - `backend/routers/users.py:226-273`: Uses `EMAIL_USER`, `EMAIL_PASS`, `EMAIL_HOST`, `EMAIL_PORT`, or `RESEND_API_KEY` (undocumented in `.env.example`).
   - `backend/routers/documents.py:85`: Uses `GEMINI_API_KEY` (undocumented in `.env.example`).
3. **Deployment & Proxy Configuration**:
   - `render.yaml`: Provisions Python web service (`uvicorn backend.main:app`), sets `PYTHONPATH="backend"`, but does not configure a PostgreSQL database resource.
   - `proxy.js`: A Node.js reverse proxy listening on port 9000 (routing `/api`, `/docs`, `/openapi.json` to 8000 and others to 5173). It is not referenced in any `package.json` scripts or documentation.
   - **Docker**: No `Dockerfile` or `docker-compose.yml` exists in the repository.

---

## 2. Logic Chain

### Step 1: Comparison of Database Schemas (`Full_Project_Schemas.sql` vs `Database_ERD.md` vs `backend/models.py`)
- **Observation**: `backend/models.py` implements **10 models**, matching `Database_ERD.md` 100% in table count and field structure.
- **Reasoning**: `Database_ERD.md` reflects the active MVP schema designed for SQLite/FastAPI. In contrast, `Full_Project_Schemas.sql` represents an expanded 35-table enterprise blueprint (likely designed for production PostgreSQL).
- **Deduction**: **25 tables** in `Full_Project_Schemas.sql` are completely unbuilt in `backend/models.py`.

#### Table Discrepancy Matrix:
| Table Name | In `Full_Project_Schemas.sql` | In `Database_ERD.md` | In `backend/models.py` | Status |
| :--- | :---: | :---: | :---: | :--- |
| `tenants` | ✅ | ✅ | ✅ | Implemented (field differences) |
| `tenant_settings` | ✅ | ❌ | ❌ | **Missing in Model** |
| `users` | ✅ | ✅ | ✅ | Implemented (field differences) |
| `roles` | ✅ | ❌ | ❌ | **Missing in Model** |
| `permissions` | ✅ | ❌ | ❌ | **Missing in Model** |
| `memberships` | ✅ | ❌ | ❌ | **Missing in Model** |
| `user_database_access` | ❌ | ✅ | ✅ | Present in MVP Model only |
| `tenant_invites` | ❌ | ✅ | ✅ | Present in MVP Model only |
| `database_connections` | ✅ | ✅ | ✅ | Implemented (field differences) |
| `secrets` | ✅ | ❌ | ❌ | **Missing in Model** |
| `database_schemas` | ✅ | ❌ | ❌ | **Missing in Model** |
| `table_metadata` | ✅ | ❌ | ❌ | **Missing in Model** |
| `column_metadata` | ✅ | ❌ | ❌ | **Missing in Model** |
| `chatbot_configs` | ✅ | ✅ | ✅ | Implemented (field differences) |
| `conversations` | ✅ | ❌ | ❌ | **Missing in Model** |
| `messages` | ✅ | ❌ | ❌ | **Missing in Model** |
| `intents` | ✅ | ❌ | ❌ | **Missing in Model** |
| `query_templates` | ✅ | ❌ | ❌ | **Missing in Model** |
| `executed_queries` | ✅ | ❌ | ❌ | **Missing in Model** |
| `query_safety_logs` | ✅ | ❌ | ❌ | **Missing in Model** |
| `documents` | ✅ | ✅ | ✅ | Implemented (field differences) |
| `document_chunks` | ✅ | ✅ | ✅ | Implemented (field differences) |
| `collections` | ✅ | ❌ | ❌ | **Missing in Model** |
| `vector_records` | ✅ | ❌ | ❌ | **Missing in Model** |
| `generated_insights` | ✅ | ❌ | ❌ | **Missing in Model** |
| `recommendations` | ✅ | ❌ | ❌ | **Missing in Model** |
| `dashboards` | ✅ | ❌ | ❌ | **Missing in Model** |
| `widgets` | ✅ | ❌ | ❌ | **Missing in Model** |
| `subscriptions` | ✅ | ❌ | ❌ | **Missing in Model** |
| `invoices` | ✅ | ❌ | ❌ | **Missing in Model** |
| `payments` | ✅ | ❌ | ❌ | **Missing in Model** |
| `metered_usage` | ✅ | ❌ | ❌ | **Missing in Model** |
| `api_keys` | ✅ | ✅ | ✅ | Implemented (field differences) |
| `rate_limits` | ✅ | ❌ | ❌ | **Missing in Model** |
| `security_policies` | ✅ | ❌ | ❌ | **Missing in Model** |
| `audit_logs` | ✅ | ❌ | ❌ | **Missing in Model** |
| `system_metrics` | ✅ | ❌ | ❌ | **Missing in Model** |
| `password_reset_otps` | ❌ | ✅ | ✅ | Present in MVP Model only |

### Step 2: Column & Constraint Mismatches (Within Implemented Tables)
1. `tenants`:
   - `Full_Project_Schemas.sql` requires `org_id VARCHAR(50) UNIQUE NOT NULL` and has no `address` column.
   - `backend/models.py` has `address` (nullable) but **omits `org_id`**.
2. `users`:
   - `Full_Project_Schemas.sql` enforces normalized RBAC via `memberships` table (`user_id`, `tenant_id`, `role_id`). `users` table has no `role` or `tenant_id` column.
   - `backend/models.py` puts `role` (VARCHAR, default "Admin") and `tenant_id` (FK to `tenants.id`) directly inside `users`.
3. `database_connections`:
   - `Full_Project_Schemas.sql` stores engine name (`engine`) and database name (`db_name`), separating credentials into a `secrets` table.
   - `backend/models.py` stores `db_type`, `username`, `password` (plaintext in DB), and `database` inline.
4. `api_keys`:
   - `Full_Project_Schemas.sql` stores `hashed_key` (UNIQUE NOT NULL), `scopes` (JSONB), and `expires_at`.
   - `backend/models.py` stores plaintext/unhashed `key` (prefix `omq_pk_live_`), `description`, `status`, `total_requests`, `last_used_at`.
5. `documents`:
   - `Full_Project_Schemas.sql` stores `total_tokens`.
   - `backend/models.py` adds RAG/parsing stats (`size`, `embeddings_count`, `line_count`, `paragraph_count`, `table_count`, `image_count`).
6. `document_chunks`:
   - `Full_Project_Schemas.sql` omits `overlap_chars` and `created_at`.
   - `backend/models.py` includes `overlap_chars` and `created_at`.

### Step 3: Analysis of Setup Guides & Workflows
- **Documentation Fragmentation**: Having `SETUP_GUIDE.md`, `SETUP_GUIDE_v4.md`, and `setup_guide_v5.md` creates developer confusion. `setup_guide_v5.md` inaccurately claims full implementation of Modules 1-20.
- **Environment Variable Inconsistency**:
  - `.env.example` defines `VITE_API_URL`, whereas `SETUP_GUIDE.md` and `WORKFLOW.md` instruct setting `VITE_API_BASE_URL`.
  - Backend routers rely on `GEMINI_API_KEY`, `RESEND_API_KEY`, `EMAIL_USER`, `EMAIL_PASS`, `EMAIL_HOST`, `EMAIL_PORT`, `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, none of which are documented in `.env.example`.
- **Secret Hygiene Risk**: Hardcoded fallback values for GitHub OAuth secrets exist in `backend/routers/users.py:129-130`.

---

## 3. Caveats
- No live database runtime was executed during this static file inspection phase.
- Frontend source files (`src/`) were checked for environment variable usage references (`VITE_API_BASE_URL`), but detailed UI component integration is scoped under frontend/architectural tasks.

---

## 4. Conclusion

1. **Schema Mismatch**: The backend Python ORM (`backend/models.py`) strictly reflects the 10-table MVP model defined in `Database_ERD.md`. It does **not** implement 25 of the 35 tables defined in `Full_Project_Schemas.sql` (missing RBAC roles/permissions, RAG collections/vector_records, chatbot conversations/messages/safety logs, insights, dashboards, billing/invoices, audit logs).
2. **Field Drift**: Even among the 10 matching tables, column definitions differ significantly (e.g. `users.role` vs `memberships`, `database_connections.password` stored inline vs `secrets` table, missing `org_id` in `tenants`).
3. **Documentation Deficiencies**: Setup guides contain false completion claims (`v5`), mismatched environment variable names (`VITE_API_URL` vs `VITE_API_BASE_URL`), missing documentation for critical backend environment variables (Resend/SMTP, Gemini API key), and unreferenced scripts (`proxy.js`).

---

## 5. Verification Method

To independently verify these findings:
1. **Inspect Schema Tables**:
   - Compare `Full_Project_Schemas.sql` lines 5-332 against `backend/models.py` lines 6-139 using `view_file`.
   - Verify that 25 tables (`tenant_settings`, `roles`, `permissions`, `memberships`, `secrets`, `database_schemas`, `table_metadata`, `column_metadata`, `conversations`, `messages`, `intents`, `query_templates`, `executed_queries`, `query_safety_logs`, `collections`, `vector_records`, `generated_insights`, `recommendations`, `dashboards`, `widgets`, `subscriptions`, `invoices`, `payments`, `metered_usage`, `rate_limits`, `security_policies`, `audit_logs`, `system_metrics`) are absent from `backend/models.py`.
2. **Inspect Env Variables**:
   - Check `d:\dataspeak\.env.example` vs `d:\dataspeak\backend\routers\users.py:129-130,226-273` and `d:\dataspeak\backend\routers\documents.py:85`.
3. **Run Table Creation Test**:
   - Execute `python -c "import models, database; models.Base.metadata.create_all(bind=database.engine)"` inside `backend/` and inspect SQLite database tables using `sqlite3 app.db .tables`. Only 10 tables will be created.
