# DataSpeakAI — Database Schema Reconciliation Report (Phase NR-0)

**Document Reference:** `docs/database/nr0_schema_reconciliation.md`  
**Creation Date:** 2026-10-16  
**Parent Task:** `NR-0.1-B-T01 — Reconcile ORM, canonical SQL, and supported installed layouts`  
**Governing Standard:** [`AGENTS.md`](../../AGENTS.md) & [`docs/next_release_implementation_pathway.md`](../next_release_implementation_pathway.md)  
**Status:** Completed & Verified  

---

## 1. Executive Summary & Inventory Scope

This document provides the definitive, audit-grade reconciliation between:
1. **SQLAlchemy ORM Metadata (`backend/models.py`):** 46 declared database models (`Base.metadata.tables`).
2. **Canonical SQL Specification (`docs/database/Full_Project_Schemas.sql`):** 35 `CREATE TABLE` definitions.
3. **Ad-Hoc Startup Migrations (`backend/services/db_migration.py`):** 99 column alterations in `MIGRATION_COLUMNS`.

### 1.1 Core Audit Discovery
- **Total Tables in ORM:** 46
- **Total Tables in SQL Spec:** 35
- **Tables in SQL Spec but Missing in ORM:** **0** (100% of canonical SQL tables are implemented in the ORM).
- **Tables in ORM but Missing in SQL Spec:** **11** (Runtime-only operational tables added during product evolution).

---

## 2. Table-Level Reconciliation & Classification

The 11 tables present in the ORM but absent in `Full_Project_Schemas.sql` are active operational components of DataSpeakAI:

| # | Table Name | Purpose / Operational Domain | Backing Features & Routers | Baseline Decision |
|---|---|---|---|---|
| 1 | `ai_insights` | AI-generated business insights | `/api/analytics/insights`, Dashboard UI | **Retain in baseline** |
| 2 | `dashboard_layouts` | Visual widget grid positions & domain mapping | `/api/dashboards/layout`, Recharts UI | **Retain in baseline** |
| 3 | `datasets` | Uploaded raw data tables for CSV/Excel exploration | `/api/datasets`, File ingestion | **Retain in baseline** |
| 4 | `kpi_definitions` | Deterministic KPI metric recipes (Phase 2) | `/api/analytics/kpis`, MetricExecutor | **Retain in baseline** |
| 5 | `password_reset_otps` | 6-digit OTP verification codes for password recovery | `/api/auth/password-reset` | **Retain in baseline** |
| 6 | `query_logs` | Real-time query execution telemetry & execution time | `/api/analytics/overview`, `/api/logs` | **Retain in baseline** |
| 7 | `schema_registry` | Semantic column metadata & foreign key targets | NL-to-SQL translation engine | **Retain in baseline** |
| 8 | `table_relationships` | Foreign key constraint graph for ERD | `backend/services/erd_service.py` | **Retain in baseline** |
| 9 | `tenant_invites` | Tokenized email invites for tenant team onboarding | `/api/tenant/invites` | **Retain in baseline** |
| 10 | `user_database_access` | Granular user-to-database connection permissions | `/api/databases/{id}/access` | **Retain in baseline** |
| 11 | `widget_keys` | Embeddable standalone chatbot keys (`pk_live_*`) | `/api/widget/*`, standalone chatbot | **Retain in baseline** |

> **Architectural Ruling:** None of the 11 tables will be dropped. They represent essential SaaS capabilities. The canonical SQL specification (`docs/database/Full_Project_Schemas.sql`) must be updated to include these 11 tables to align specification with runtime truth.

---

## 3. Column-Level Discrepancies & Semantic Decisions

### 3.1 `conversations` Table
* **SQL Specification (`Full_Project_Schemas.sql:L129`):**
  ```sql
  CREATE TABLE conversations (
      id SERIAL PRIMARY KEY,
      tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
      session_token VARCHAR(255) UNIQUE NOT NULL,
      platform VARCHAR(50) DEFAULT 'web',
      created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
  );
  ```
* **ORM Implementation (`backend/models.py:L435`):**
  - `id`: `Integer`, Primary Key
  - `tenant_id`: `Integer`, Not Null
  - `user_id`: `Integer`, Nullable (Foreign key to `users.id`)
  - `title`: `String`, Nullable (Auto-generated 3-6 word conversation title)
  - `platform`: `String`, Default `'web'`
  - `summary_text`: `Text`, Nullable (Sliding window conversation memory summary)
  - `summary_turn_count`: `Integer`, Default `0`
  - `created_at`: `DateTime`
  - `updated_at`: `DateTime`
* **Semantic Analysis & Decision:**
  - Requiring `session_token UNIQUE NOT NULL` breaks internal dashboard chat where authenticated users create multiple named conversations without a widget session token.
  - In widget chat, sessions use HMAC-signed tokens verified against `widget_keys`.
  - **Resolution:** Retain ORM schema. `user_id` remains nullable (set for dashboard users, null for anonymous widget visitors). `session_token` is made nullable for backward compatibility.

### 3.2 `messages` Table
* **SQL Specification:** Defines `metadata JSONB`.
* **ORM Implementation:** Defines `metadata_json (JSON)`.
* **Semantic Analysis & Decision:**
  - In SQLAlchemy, `metadata` is a reserved attribute name on `DeclarativeBase` and `Base.metadata`. Defining a column named `metadata` triggers name collisions and ORM attribute shadowing.
  - **Resolution:** Retain `metadata_json` in the ORM and map it transparently.

### 3.3 `documents` Table
* **SQL Specification:** `id`, `tenant_id`, `name`, `file_type`, `status`, `total_tokens`, `created_at`.
* **ORM Implementation:** Adds multi-modal ingestion telemetry: `embeddings_count`, `line_count`, `paragraph_count`, `table_count`, `image_count`, `progress`, `error_message`, `total_pages`, `pages_processed`, `visual_pages`, `celery_task_id`, `embedding_model`.
* **Resolution:** Retain all ORM ingestion telemetry columns.

### 3.4 `document_chunks` Table
* **SQL Specification:** `id`, `document_id`, `content`, `chunk_index`, `parent_chunk_id`, `hierarchy_level`.
* **ORM Implementation:** Adds citation grounding attributes: `overlap_chars`, `page_number`, `content_type`, `section_heading`, `reference_id`, `created_at`.
* **Resolution:** Retain all ORM citation grounding columns.

---

## 4. Supported Installation Layout Matrix

To ensure zero-downtime upgrades, DataSpeakAI recognizes exactly four database installation layouts:

```
+---------------------------------------------------------------------------------+
|                               Supported Layouts Matrix                          |
+-------------------+-----------------------------+-------------------------------+
| Layout ID         | Database Fingerprint        | Preflight Action              |
+-------------------+-----------------------------+-------------------------------+
| Layout 0 (Empty)  | Zero tables detected        | Run `alembic upgrade head`    |
| Layout 1 (Legacy) | 35 canonical tables         | Run legacy migration bridge   |
| Layout 2 (Current)| 46 tables, Phase 7 columns  | Stamp `head` (already synced) |
| Layout 3 (Drift)  | Unknown extra/missing cols  | Reject with actionable error  |
+-------------------+-----------------------------+-------------------------------+
```

### Layout 0: Fresh Installation
- Target: Empty SQLite or PostgreSQL database.
- Action: Direct execution of `alembic upgrade head`.

### Layout 1: Known Legacy Installation (Phase 1–6)
- Target: Existing databases containing historical 35 tables without Phase 7 columns (`parent_chunk_id`, `summary_turn_count`).
- Action: Apply transitional migration revision to bring columns to current baseline.

### Layout 2: Phase 7 Migrated Installation
- Target: Current production databases where `db_migration.py` has already added the 99 columns.
- Action: Reconcile version table (`alembic_version`) by stamping baseline revision `001_initial_baseline`.

### Layout 3: Unsupported / Unknown Drift
- Target: Databases with schema modifications outside repository migrations (e.g., dropped foreign keys, untracked tables).
- Action: Preflight raises explicit error, details violating tables/columns, and halts startup without applying DDL.

---

## 5. Dialect Compatibility & Constraints

### 5.1 SQLite vs PostgreSQL Types
| Feature | SQLite Representation | PostgreSQL Representation |
|---|---|---|
| Primary Keys | `INTEGER PRIMARY KEY AUTOINCREMENT` | `SERIAL PRIMARY KEY` |
| JSON Documents | `JSON` (stored as text with json valid check) | `JSONB` (binary indexing) |
| Boolean Values | `INTEGER` (`0` or `1`) | `BOOLEAN` (`TRUE` or `FALSE`) |
| Timestamps | `DATETIME` (`YYYY-MM-DD HH:MM:SS`) | `TIMESTAMP WITH TIME ZONE` |
| Foreign Key Enforcement | `PRAGMA foreign_keys = ON;` required | Enabled by default |

---

## 6. Verification & Next Steps

- [x] ORM 46 tables and SQL spec 35 tables fully cross-referenced.
- [x] All 11 runtime-only tables audited and justified.
- [x] Column semantic discrepancies resolved (`conversations.user_id`, `messages.metadata_json`).
- [x] Supported layout matrix defined for migration preflight.
- **Next Task:** `NR-0.1-B-T02 — Add reviewed Alembic history and read-only schema preflight`.
