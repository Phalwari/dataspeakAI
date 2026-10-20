# Insights Known Issues

## INS-FAIL-01: SQLite double-quoted unknown columns need live validation

SQLite can interpret a double-quoted unknown column as a string literal, making a numeric aggregate return a misleading zero. INS-D1-01 checks generated SQLite identifiers against the live schema before pooled execution and marks a stale metric column `unavailable/missing_role` (`backend/services/db_pipeline_service.py:399-446,1886-1901`). The generic temporary SQLite regression at `tests/test_insights_failure_semantics.py:93-138` first failed with `zero`, then passed with no aggregate query sent for the stale column. Arbitrary SQL outside this pipeline and other dialects are not verified by execution.

## INS-FAIL-02: Missing selected table status remains expected-failure

`test_missing_selected_table_has_missing_table_reason` is marked strict xfail at `tests/test_insights_failure_semantics.py:231-235`. The current pipeline may select another available table and does not assign `missing_table` to the requested metric. The expected behavior is not implemented.

## INS-FAIL-03: Query-failure status mapping still uses a mocked fallback service

`test_query_failure_is_reported_by_mocked_service_unit` uses a non-SQLite connection and replaces `db_connection_service.execute_query` with a synthetic failing result at `tests/test_insights_failure_semantics.py:160-181`. The separate pooled SQLite regression (`tests/test_insights_failure_semantics.py:184-228`) executes a real SQLite query that raises, then uses a mocked fallback service failure to reach the pipeline's `error/query_failed` state. The real SQL engine error is exercised; the complete fallback-service integration path is not verified by execution.

## INS-D2: Calendar filter limitations

INS-D2-01 validates strict `YYYY-MM-DD` dates before cache reads, rejects reversed ranges, binds SQL values, and uses a half-open interval (`date_from` inclusive, next day after `date_to` exclusive). INS-D2-02 sends preset ranges to the API and displays the range returned by the service. The former recent-points chart slicing and fabricated unavailable KPI overlay are removed. Temporary SQLite tests verify federated and single-table totals, charts, NULL dates, boundary inclusion, cache separation, and invalid inputs. Browser rendering is **not verified by execution**.

The planner selects a named transaction date, then a creation date, or the only detected date column. Ambiguous date roles fail closed. A filtered query shape without the selected fact table is marked `unavailable/unsupported_with_filter`; a table without a usable date role is `unavailable/missing_role`. This means independent customer/catalog dimensions do not gain a guessed date relationship. Full schema-derived joins and per-table date lineage remain outside Phase D.

SPLY uses the same requested inclusive calendar days in the previous year, with bound parameters, only when both dates and a fact-table money measure exist. Leap day maps to February 28 in a non-leap comparison year. When prior-year rows or a complete window are unavailable, the trend is omitted and `trend_reason` records why. The browser display of that reason is **not verified by execution**.

## INS-D3: Dialect and execution boundary

`services/sql_dialect.py` now builds month buckets, concatenation, text casts, numeric rounding, and identifier quotes for SQLite, PostgreSQL, MySQL, and MariaDB. Unknown SQL dialects raise `UnsupportedDialectError`; they no longer inherit MySQL syntax. SQL string tests cover all four dialect names and SQLite fragments run against a temporary database. PostgreSQL/MySQL/MariaDB execution is **not verified by execution**.

The Insights pipeline still executes generated SELECTs through its own pooled-engine path. It does not apply `sql_engine.py`'s session guardrails to those pooled connections. The dialect helper emits MySQL backtick identifiers, so generated identifiers do not require `ANSI_QUOTES`, but actual server SQL modes and safe execution behavior need live integration checks before production claims.

## INS-D4: MongoDB scope and verification boundary

MongoDB mode is selected before relational federation even when a collection is named `orders`. Filtered document counts use `$ne: None`, `$gte` and exclusive `$lt` UTC calendar bounds. A filtered count failure returns `error/query_failed` with a null value and never falls back to an unfiltered count. A missing date role skips all other collection aggregates for that filtered request. Chart and measure filters use the same bounds, and chart sampling was removed so displayed aggregates are exact when queries succeed. Offline fake-client tests cover these behaviors; live MongoDB is **not verified by execution**.

All-collections mode still analyzes only the first three collections. Nested document fields and high-volume query latency are not verified. Mongo clients now close after both successful and unexpected analytics paths; a full failure may still leave a partial payload with a warning.

## INS-GEN-01: Role detection remains convention-based

Generic SQLite fixtures verify that `total_orders` and `discount_rate` are not currency, `network_id` is an identifier, `void` remains a dimension, quantity without price is counted, and HR/inventory schemas do not fabricate revenue. Role discovery still depends on names and coarse types rather than foreign-key metadata and a validated semantic plan. These fixtures do not prove that arbitrary customer schemas are supported.

## INS-SEC-01: Tenant check is verified at the service boundary only

`run_db_pipeline` and `run_db_pipeline_stream` reject a missing `tenant_id` before querying or reading cached results (`backend/services/db_pipeline_service.py:272-279,2210-2217`). Offline tests cover the service boundary and tenant-scoped cache behavior. A signed HTTP authentication request through the router is not verified by execution.

## INS-SEC-02: LLM prompt sanitization is limited to the aggregate payload

`_llm_safe_points` (`backend/services/db_pipeline_service.py:61-89`) omits metric IDs/labels, chart titles, chart axis keys, and point labels. It passes numeric KPI `raw_value` values and numeric chart aggregates with fixed category names to the synthesis prompt. This does not establish that every pipeline path or LLM interaction is free of PII. The prompt-capture test mocks `generate`; a live LLM call is not verified by execution.

## INS-SEC-03: Export CSP allows inline styles

The export HTML meta policy (`backend/routers/insights.py:487`) is `default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'`. Scripts, images, and connections inherit the restrictive default, while inline CSS remains allowed for the report layout. `tests/test_insights_export.py` checks only that the meta tag exists and contains `default-src 'none'`; it does not prove CSP security or browser enforcement. Tightening styles is pending separate approval for INS-SEC-05: hash the inline style block and verify the rendered report in a browser before calling it fixed.

## Verification boundary

The Insights checks run offline with mocked external services and temporary local SQLite databases. The pooled SQLite query-failure regression runs a real SQLAlchemy engine; its fallback service is mocked. Live MySQL/MariaDB/PostgreSQL/MongoDB, browser rendering and CSP enforcement, signed HTTP authentication, concurrent-user capacity, and a live LLM call are **not verified by execution**.
