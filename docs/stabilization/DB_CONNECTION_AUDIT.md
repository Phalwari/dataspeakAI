# Database connection layer audit

- **Date:** 2026-10-20
- **Branch:** `fix/db-connection-enterprise`
- **Scope:** connection creation, URL validation, encryption, SSRF and SQLite sandboxing, pooling, schema discovery, previews, query execution, errors, and tenant access.
- **Audit status:** baseline review completed before this task's fixes. Existing uncommitted workspace changes were present in several backend and frontend files before the audit; they are being preserved and are not treated as changes authored by this task.
- **Execution note:** no external database, server, or package installation was used during this audit. SQLite execution tests are pending the user's approval, which has now been granted for temporary local SQLite files only.

## Findings

### DB-01 — Raw SQL connection endpoint permits write statements

- **Severity:** Critical
- **Location:** `backend/services/database_connection_service.py:748-846`
- **Evidence:** PostgreSQL, MySQL, and SQLite use `is_safe_sql`, a deny-list, then execute the caller's query directly. No dialect read-only transaction or strict SELECT-only parser is applied. The PostgreSQL and MySQL branches can commit statements with no result set; SQLite opens a writable connection and commits non-result statements. This is the `/api/connections/{id}/query` execution path.

### DB-02 — Credential encryption has a shared fallback and no production key guard

- **Severity:** Critical
- **Location:** `backend/services/crypto_service.py:23-29`, `backend/services/crypto_service.py:32-44`
- **Evidence:** `_get_fernet` selects a built-in fallback when neither configured key is present and does not reject production mode. As a result, stored credentials can be encrypted under a predictable shared key in production. Legacy plaintext compatibility is intentionally supported by `decrypt_secret` at lines 47-56 and must remain.

### DB-03 — URI validation misses hosts supplied in query parameters and local sockets

- **Severity:** High
- **Location:** `backend/services/connection_factory.py:155-176`
- **Evidence:** The validator checks `url_obj.host` only when present. It neither rejects a hostless network URI with a `host` query override nor blocks `unix_socket`/socket-path query options, so the validated endpoint may differ from the host checked or may bypass the network-host check.

### DB-04 — Persisted connection operations bypass the central SSRF and sandbox checks

- **Severity:** High
- **Location:** `backend/routers/connections.py:180-220`, `backend/routers/connections.py:332-380`; `backend/services/database_connection_service.py:272-347`, `backend/services/database_connection_service.py:351-419`, `backend/services/database_connection_service.py:534-598`, `backend/services/database_connection_service.py:601-745`, `backend/services/database_connection_service.py:748-955`
- **Evidence:** Retest, schema, list, preview, and query helpers make direct `psycopg2`, `pymysql`, `pymongo`, or `sqlite3` connections. They do not consistently call `DatabaseConnectionFactory.validate_connection_string`, `validate_host_ssrf`, or `validate_sqlite_path`. An old or directly modified stored connection can therefore bypass the checks used by create/test routes.

### DB-05 — SQLite sandbox enforcement is inconsistent across paths

- **Severity:** High
- **Location:** `backend/services/connection_factory.py:108-152`; `backend/services/database_connection_service.py:335-348`, `backend/services/database_connection_service.py:506-531`, `backend/services/database_connection_service.py:577-589`, `backend/services/database_connection_service.py:707-717`, `backend/services/database_connection_service.py:830-846`
- **Evidence:** The factory checks a managed root, but direct SQLite test/schema/table/preview/query paths call `sqlite3.connect` without passing through that validator. Thus stored paths can bypass the sandbox. The factory's test-mode exception intentionally allows external temporary paths and should remain test-only.

### DB-06 — Pool registry retains unbounded, stale, and credential-sensitive entries

- **Severity:** High
- **Location:** `backend/services/db_pool.py:4-28`; `backend/services/database_connection_service.py:36-40`, `backend/services/database_connection_service.py:46-79`, `backend/services/database_connection_service.py:82-112`
- **Evidence:** The SQLAlchemy engine registry is unbounded and keyed by the full URL; there is no disposal/invalidation method. PostgreSQL and MySQL pool keys omit the password, so credential changes can reuse connections authenticated with stale credentials. The MySQL cache shares one live connection for a key across request threads. Mongo clients are keyed by the raw URI and have no removal path. This also leaves credential-bearing URLs in long-lived process memory.

### DB-07 — Safe SQL path creates a fresh engine and connection for each request

- **Severity:** High
- **Location:** `backend/services/sql_engine.py:681-707`, `backend/services/sql_engine.py:723-751`
- **Evidence:** Each call creates an engine with `NullPool` and disposes it afterward; each call also creates a one-worker executor. Under 100 simultaneous requests this can create connection and thread churn rather than reusing a bounded pool. Pool sizing must still respect each customer's database capacity.

### DB-08 — Connection and query errors can disclose driver details

- **Severity:** High
- **Location:** `backend/routers/connections.py:150-159`, `backend/routers/connections.py:222-224`; `backend/routers/databases.py:150-151`, `backend/routers/databases.py:202-220`, `backend/routers/databases.py:252-273`, `backend/routers/databases.py:304-367`, `backend/routers/databases.py:390-422`; `backend/services/database_connection_service.py:301-316`, `backend/services/database_connection_service.py:954-955`
- **Evidence:** Several API error responses interpolate `str(e)` or return service errors directly. Driver exceptions can include host, database, or URI details. These are returned to users instead of a stable generic message with detailed server-side exception logging.

### DB-09 — Connection factory logs validation exceptions without guaranteed redaction

- **Severity:** Medium
- **Location:** `backend/services/connection_factory.py:189-215`
- **Evidence:** Exceptions from URL parsing, decryption, and host/path validation are interpolated into warnings. Parser and driver errors may contain URI components. Generic structured logging should avoid including input values.

### DB-10 — Mongo is not handled in the connections router table path

- **Severity:** Medium
- **Location:** `backend/routers/connections.py:119-159`
- **Evidence:** The `/api/connections/{id}/tables` handler obtains a SQLAlchemy URL and passes it to `get_engine` for all database types. MongoDB has a dedicated PyMongo route in `backend/routers/databases.py:202-209`, but this router path has no Mongo branch and attempts SQLAlchemy engine creation instead.

### DB-11 — PII detection is not consistently applied to raw-query paths

- **Severity:** Medium
- **Location:** `backend/services/sql_engine.py:530-578`; `backend/services/database_connection_service.py:748-955`
- **Evidence:** `sql_engine.mask_pii_rows` currently recognizes email, phone, salary, address, and date-of-birth patterns (the current worktree includes edits here). The direct connection-service query path returns serialized rows without applying the masker, so callers of the raw-query route can receive these columns unmasked.

### DB-12 — Existing database connection tests contain live external targets and inline credential material

- **Severity:** Critical
- **Location:** `tests/test_databases_connection_and_preview.py:16-70`
- **Evidence:** The PostgreSQL and MySQL cases target external hosts and include credential literals in test arguments. They are unsafe to run under this task's rules and put credential material in the repository. They must be replaced with offline tests/fakes; no such external test was run.

### DB-13 — Pool limits do not provide a verified 100-user service capacity

- **Severity:** Medium
- **Location:** `backend/services/database_connection_service.py:42-44`, `backend/services/database_connection_service.py:46-63`, `backend/services/database_connection_service.py:69-79`, `backend/services/db_pool.py:12-27`
- **Evidence:** Pool sizes are per process/per unique connection, and no load test or per-tenant connection budget is present in the inspected layer. Existing defaults alone cannot establish safe capacity for 100 concurrent users across multiple app workers and customer databases. This requires production capacity testing and database-owner limits.

## Areas that passed inspection

- `backend/routers/databases.py:17-45` scopes connection lookup by tenant and applies user database grants for non-admin/developer roles.
- `backend/routers/databases.py:127-169` encrypts credentials before persisting new connections and validates new targets before save.
- `backend/routers/databases.py:202-209` takes the Mongo branch before attempting relational SQLAlchemy inspection.
- `backend/schemas.py:179-197` redacts password fields and masks connection URL credentials in the database response schema.
- `backend/services/sql_engine.py:646-677` currently fails closed when its relational read-only guardrail cannot be applied; this implementation is present in the pre-existing worktree diff and will be preserved.

## Verification constraints

- `python -m pytest --version` reports `pytest 9.1.1`.
- Existing `tests/test_databases_connection_and_preview.py` was not run because it contains external database connections and credentials.
- No connection to MySQL, MariaDB, PostgreSQL, MongoDB, any internal IP, or any cloud resource was attempted.
- Temporary local SQLite execution tests may be run after implementation under the user's explicit approval.
