# Database connection security remediation

- **Branch:** `fix/db-connection-enterprise`
- **Audit:** [`DB_CONNECTION_AUDIT.md`](DB_CONNECTION_AUDIT.md)
- **Verification:** temporary SQLite and fake-client tests only; no external database or network target was contacted.

| Issue | Status | Remediation / remaining work |
|---|---|---|
| DB-01 Read-only query execution | Fixed | SQL query endpoint now uses strict read-only validation and the safe SQL execution path. SQLite end-to-end coverage confirms SELECT succeeds and INSERT is rejected. MySQL/PostgreSQL guardrail behavior is not verified by execution. |
| DB-02 Credential encryption key | Fixed | Removed predictable fallback key; encryption requires configured key material and production rejects missing keys. Legacy plaintext decryption remains supported. Key rotation procedure remains an owner decision. |
| DB-03 URI SSRF and sockets | Fixed | Network URI hosts, host overrides, private DNS/IP results, and Unix socket parameters are validated/rejected. Tests use stub DNS and fake URIs. |
| DB-04 Persisted direct-driver validation | Fixed | Direct-driver paths now call common host/URI/path validation before use. No live remote driver was used to verify these paths. |
| DB-05 SQLite sandbox | Fixed | Direct SQLite test/schema/table/preview paths resolve and validate paths against the configured sandbox. Temporary SQLite tests ran; production deployment path configuration still needs review. |
| DB-06 Pool registry | Partial | SQLAlchemy engine cache is bounded to 32 engines, keys are hashed, each engine allows two pooled connections plus three overflow connections, update/delete invalidates matching engines, and engines are disposed on eviction. Legacy psycopg2/MySQL/Mongo registries in `database_connection_service.py` remain and need a separate migration to bounded credential-fingerprinted registries; the old MySQL single-connection helper is unsafe for concurrent use if called. |
| DB-07 SQL pool and workers | Fixed | Safe SQL now reuses pooled engines and a bounded 32-worker executor; queued futures are cancelled when the request times out. This is a protective limit, not a validated 100-user capacity claim; queueing and target database budgets need load tests. |
| DB-08 Error disclosure | Fixed | Connection API/service errors are generic; exception logs use error class only and avoid raw driver messages/connection data. |
| DB-09 Validation logging | Fixed | Connection factory validation and connection-test logs no longer interpolate driver/parser exception text. |
| DB-10 Mongo collection route | Fixed | The connections-router table listing takes the PyMongo branch before SQLAlchemy; fake `orders` collection test passes. |
| DB-11 PII masking | Partial | Relational safe-SQL results use the shared PII masker. Mongo read operations do not yet apply equivalent field masking. |
| DB-12 Unsafe live tests | Fixed | The database connection/preview test file was replaced with offline fake-client coverage; the external test suite was not run. |
| DB-13 100-user capacity | Skipped | No 100-user load test was run. Requires owner-approved test environment, target database connection budgets, process/worker count, and load profile. |

## Verified test commands

```text
python -m py_compile backend/routers/connections.py backend/routers/databases.py backend/services/connection_factory.py backend/services/database_connection_service.py backend/services/db_pool.py backend/services/sql_engine.py
python -m pytest tests/test_database_connection_security.py tests/test_databases_connection_and_preview.py -q --basetemp=tests/.tmp_pytest
```

Latest test result: `21 passed, 22 warnings`. Warnings are existing dependency/API deprecations plus the local requests dependency compatibility warning. No execution against MySQL, MariaDB, PostgreSQL, MongoDB, internal hosts, or cloud services was performed.
