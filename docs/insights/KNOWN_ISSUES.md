# Insights Known Issues

## INS-FAIL-01: SQLite double-quoted unknown columns need live validation

SQLite can interpret a double-quoted unknown column as a string literal, making a numeric aggregate return a misleading zero. INS-D1-01 checks generated SQLite identifiers against the live schema before pooled execution and marks a stale metric column `unavailable/missing_role` (`backend/services/db_pipeline_service.py:399-446,1886-1901`). The generic temporary SQLite regression at `tests/test_insights_failure_semantics.py:93-138` first failed with `zero`, then passed with no aggregate query sent for the stale column. Arbitrary SQL outside this pipeline and other dialects are not verified by execution.

## INS-FAIL-02: Missing selected table status remains expected-failure

`test_missing_selected_table_has_missing_table_reason` is marked strict xfail at `tests/test_insights_failure_semantics.py:231-235`. The current pipeline may select another available table and does not assign `missing_table` to the requested metric. The expected behavior is not implemented.

## INS-FAIL-03: Query-failure status mapping still uses a mocked fallback service

`test_query_failure_is_reported_by_mocked_service_unit` uses a non-SQLite connection and replaces `db_connection_service.execute_query` with a synthetic failing result at `tests/test_insights_failure_semantics.py:160-181`. The separate pooled SQLite regression (`tests/test_insights_failure_semantics.py:184-228`) executes a real SQLite query that raises, then uses a mocked fallback service failure to reach the pipeline's `error/query_failed` state. The real SQL engine error is exercised; the complete fallback-service integration path is not verified by execution.

## INS-D2: Calendar filter limitations

INS-D2-01 validates strict `YYYY-MM-DD` dates before cache reads, rejects reversed ranges, binds SQL values, and uses a half-open interval (`date_from` inclusive, next day after `date_to` exclusive). INS-D2-02 sends preset ranges to the API and displays the range returned by the service. INS-D2-03 versions both Redis keys and DB L2 payloads so an old unfiltered cached report is not served after the calculation changes. The former recent-points chart slicing and fabricated unavailable KPI overlay are removed. Temporary SQLite tests verify federated and single-table totals, charts, NULL dates, boundary inclusion, distinct cache entries, and stale-cache rejection. INS-D2-04 additionally verifies that a filtered request ignores a current-version DB L2 payload from another range, and an offline FastAPI `TestClient` request with an invalid date returns HTTP 400. Browser rendering is **not verified by execution**.

The planner selects a named transaction date, then a creation date, or the only detected date column. Ambiguous date roles fail closed. A filtered query shape without the selected fact table is marked `unavailable/unsupported_with_filter`; a table without a usable date role is `unavailable/missing_role`. This means independent customer/catalog dimensions do not gain a guessed date relationship. Full schema-derived joins and per-table date lineage remain outside Phase D.

SPLY uses the same requested inclusive calendar days in the previous year, with bound parameters, only when both dates and a fact-table money measure exist. INS-D2-04's temporary SQLite tests assert that a 2024-02-29 filter binds the prior window to 2023-02-28 through 2023-03-01 and that a 2025-01-01 through 2025-01-02 filter binds the corresponding 2024 window. Leap day maps to February 28 in a non-leap comparison year. When prior-year rows or a complete window are unavailable, the trend is omitted and `trend_reason` records why. The browser display of that reason is **not verified by execution**.

## INS-D3: Dialect and execution boundary

`services/sql_dialect.py` now builds month buckets, concatenation, text casts, numeric rounding, and identifier quotes for SQLite, PostgreSQL, MySQL, and MariaDB. Unknown SQL dialects raise `UnsupportedDialectError`; they no longer inherit MySQL syntax. SQL string tests cover all four dialect names and SQLite fragments run against a temporary database. PostgreSQL/MySQL/MariaDB execution is **not verified by execution**.

The Insights pipeline still executes generated SELECTs through its own pooled-engine path. It does not apply `sql_engine.py`'s session guardrails, including its MySQL `ANSI_QUOTES` setup, to those pooled connections. The dialect helper emits MySQL backtick identifiers, so generated identifiers do not require `ANSI_QUOTES`, but the execution-path mismatch, actual server SQL modes, and safe execution behavior need a separate integration fix and live verification in the later Docker phase before production claims.

## INS-D4: MongoDB scope and verification boundary

MongoDB mode is selected before relational federation even when a collection is named `orders`. Filtered document counts use `$ne: None`, `$gte` and exclusive `$lt` UTC calendar bounds. A filtered count failure returns `error/query_failed` with a null value and never falls back to an unfiltered count. A missing date role skips all other collection aggregates for that filtered request. Chart and measure filters use the same bounds, and chart sampling was removed so displayed aggregates are exact when queries succeed. These exact-aggregate assertions use an offline fake client only; real MongoDB behavior is **not verified by execution**.

All-collections mode still analyzes only the first three collections. Nested document fields and high-volume query latency are not verified. Mongo clients now close after both successful and unexpected analytics paths; a full failure may still leave a partial payload with a warning.

## INS-GEN-01: Role detection remains convention-based

Generic SQLite fixture assertions document the expected outputs: `total_orders` and `discount_rate` are numeric rather than currency, `network_id` is excluded as an identifier, `void` remains a dimension, quantity without price produces no revenue and excludes null dates, and HR/inventory schemas do not fabricate revenue. The orders/status fixture checks filtered totals and delivered-only revenue. Nested Mongo documents have no corresponding fixture. Role discovery still depends on names and coarse types rather than foreign-key metadata and a validated semantic plan. These fixtures do not prove that arbitrary customer schemas are supported.

## Phase D review decision and execution boundary

The D2–D4 commit hunks in `backend/services/db_pipeline_service.py` were checked against their date-filter, dialect, and Mongo scopes; no unrelated Phase D hunk was identified. The earlier `f594d22` WIP baseline contains a separate 1,144-line mixed change in that file and has not received a full hunk-level review. **Decision: keep the branch implemented and partially reviewed; do not label Phase D reviewed or closed on the strength of the D2–D4 review alone.**

On 2026-10-20, `python -m pytest tests/test_insights_date_filters.py tests/test_insights_failure_semantics.py tests/test_insights_export.py tests/test_insights_llm_payload.py tests/test_insights_tenant_cache.py -q --disable-warnings` returned `29 passed, 1 xfailed, 22 warnings`; the eight-file Insights run including dialect, Mongo, and generic fixtures returned `52 passed, 1 xfailed, 22 warnings`. The strict xfail is the selected-table `missing_table` gap above. These are offline tests with temporary SQLite and mocked external clients; no Chinook run was used as the primary fixture or as a regression in these commands. Frontend presets and unavailable cards still need a manual browser check.

## INS-SEC-01: Tenant check is verified at the service boundary only

`run_db_pipeline` and `run_db_pipeline_stream` reject a missing `tenant_id` before querying or reading cached results (`backend/services/db_pipeline_service.py:272-279,2210-2217`). Offline tests cover the service boundary and tenant-scoped cache behavior. A signed HTTP authentication request through the router is not verified by execution.

## INS-SEC-02: LLM prompt sanitization is limited to the aggregate payload

`_llm_safe_points` (`backend/services/db_pipeline_service.py:61-89`) omits metric IDs/labels, chart titles, chart axis keys, and point labels. It passes numeric KPI `raw_value` values and numeric chart aggregates with fixed category names to the synthesis prompt. This does not establish that every pipeline path or LLM interaction is free of PII. The prompt-capture test mocks `generate`; a live LLM call is not verified by execution.

## INS-SEC-03: Export CSP allows inline styles

The export HTML meta policy (`backend/routers/insights.py:487`) is `default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'`. Scripts, images, and connections inherit the restrictive default, while inline CSS remains allowed for the report layout. `tests/test_insights_export.py` checks only that the meta tag exists and contains `default-src 'none'`; it does not prove CSP security or browser enforcement. Tightening styles is pending separate approval for INS-SEC-05: hash the inline style block and verify the rendered report in a browser before calling it fixed.

## Verification boundary

The Insights checks run offline with mocked external services and temporary local SQLite databases. The pooled SQLite query-failure regression runs a real SQLAlchemy engine; its fallback service is mocked. Live MySQL/MariaDB/PostgreSQL/MongoDB, browser rendering and CSP enforcement, signed HTTP authentication, concurrent-user capacity, and a live LLM call are **not verified by execution**.

## INS-E1: Cache backend and deployment boundary

Connection-level cache generations make old L1 keys unreachable after an owned refresh and clear the database L2 payload atomically with the version increment. `services/redis_service.py` currently stores L1 entries in a process-local in-memory dictionary; despite the module name, it does not use a shared Redis client. Cache hits and versioned misses can therefore be verified within one process only. Multi-worker cache sharing, cross-process eviction, and distributed refresh behavior remain **not verified by execution** and require a real shared cache backend before production scale claims.

`POST /api/insights/refresh` advances the pipeline cache generation only when an explicit owned `database_id` is supplied. A tenant-wide call without `database_id` continues to refresh the legacy generated-insights engine and does not enumerate or invalidate every connection cache.

The E1 regression tests were authored after the implementation was present in the working tree, so there is no pre-implementation failing run for the new test file. The first wider-suite run did catch an older cache fixture that lacked generation metadata; updating that fixture preserved the production fail-closed validation.

Cache payloads created before E1 do not contain `connection_cache_version`. L1 and L2 reads deliberately reject those legacy payloads, causing a one-time cache miss and recomputation instead of trusting data from an unknown generation.

## INS-E2: LLM resilience and attribution boundary

The Insights pipeline now stops waiting for synthesis after `LLM_PIPELINE_BUDGET_SECONDS` (default 30). Its synchronous generation facade uses one overall `LLM_HTTP_TIMEOUT_SECONDS` deadline (default 20) across provider and key attempts, with at most one retry after a retryable timeout, transport failure, or server error. Each HTTP request receives no more than the remaining deadline. Quota responses rotate through available keys/providers without an outer retry. `LLM_RETRY_BACKOFF_SECONDS` defaults to 1. Invalid numeric settings fall back to defaults with a warning that contains only the setting name.

An LLM failure yields a deterministic summary from available computed aggregates or an insufficient-data message. The summary records `source=deterministic_fallback` and a safe `llm_error` category; a valid LLM response records `source=llm`. Old L1/L2 Insights payloads without this attribution are rejected by the Insights payload version bump and recomputed. A timed-out worker thread may continue until its in-flight HTTP operation returns; `shutdown(wait=False)` limits request latency but does not terminate that thread. Under sustained provider stalls this can consume temporary thread and memory capacity.

The new tests use temporary SQLite and mocked HTTP/generation. They verify bounded waiting, retry count, quota rotation, classified errors, and prompt/error marker absence in captured logs. Real Gemini/Groq/Ollama latency, live quota and failover behavior, production environment settings, browser rendering, and load are **not verified by execution**. This is not a 100-user capacity claim.

## INS-E3: Audit persistence boundary

Insight actions reuse the existing application `AuditLog` model; no new migration was added. Only connection ID, a safe table identifier, validated date filters, status, and duration are stored in details. Offline SQLite tests cover success, fallback, error, refresh, export, and a fully consumed stream. A stream record may remain `in_progress` after process termination or a hard disconnect. Audit retention, production table presence, and multi-worker durability are **not verified by execution**. No tenant-facing audit listing endpoint was added.
