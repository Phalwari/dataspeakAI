# Insights Known Issues

## INS-FAIL-01: SQLite double-quoted unknown columns need live validation

SQLite can interpret a double-quoted unknown column as a string literal, making a numeric aggregate return a misleading zero. INS-D1-01 checks generated SQLite identifiers against the live schema before pooled execution and marks a stale metric column `unavailable/missing_role` (`backend/services/db_pipeline_service.py:399-446,1886-1901`). The generic temporary SQLite regression at `tests/test_insights_failure_semantics.py:93-138` first failed with `zero`, then passed with no aggregate query sent for the stale column. Arbitrary SQL outside this pipeline and other dialects are not verified by execution.

## INS-FAIL-02: Missing selected table status remains expected-failure

`test_missing_selected_table_has_missing_table_reason` is marked strict xfail at `tests/test_insights_failure_semantics.py:231-235`. The current pipeline may select another available table and does not assign `missing_table` to the requested metric. The expected behavior is not implemented.

## INS-FAIL-03: Query-failure status mapping still uses a mocked fallback service

`test_query_failure_is_reported_by_mocked_service_unit` uses a non-SQLite connection and replaces `db_connection_service.execute_query` with a synthetic failing result at `tests/test_insights_failure_semantics.py:160-181`. The separate pooled SQLite regression (`tests/test_insights_failure_semantics.py:184-228`) executes a real SQLite query that raises, then uses a mocked fallback service failure to reach the pipeline's `error/query_failed` state. The real SQL engine error is exercised; the complete fallback-service integration path is not verified by execution.

## INS-UI-01: Date presets slice recent chart points

`BusinessInsightsPage.tsx:455-466` selects the last few line/area chart points for a preset. It does not compare point dates with calendar boundaries. A preset must not be described as a true date filter; browser rendering is not verified by execution.

## INS-SEC-01: Tenant check is verified at the service boundary only

`run_db_pipeline` and `run_db_pipeline_stream` reject a missing `tenant_id` before querying or reading cached results (`backend/services/db_pipeline_service.py:272-279,2210-2217`). Offline tests cover the service boundary and tenant-scoped cache behavior. A signed HTTP authentication request through the router is not verified by execution.

## INS-SEC-02: LLM prompt sanitization is limited to the aggregate payload

`_llm_safe_points` (`backend/services/db_pipeline_service.py:61-89`) omits metric IDs/labels, chart titles, chart axis keys, and point labels. It passes numeric KPI `raw_value` values and numeric chart aggregates with fixed category names to the synthesis prompt. This does not establish that every pipeline path or LLM interaction is free of PII. The prompt-capture test mocks `generate`; a live LLM call is not verified by execution.

## INS-SEC-03: Export CSP allows inline styles

The export HTML meta policy (`backend/routers/insights.py:487`) is `default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'`. Scripts, images, and connections inherit the restrictive default, while inline CSS remains allowed for the report layout. `tests/test_insights_export.py` checks only that the meta tag exists and contains `default-src 'none'`; it does not prove CSP security or browser enforcement. Tightening styles is pending separate approval for INS-SEC-05: hash the inline style block and verify the rendered report in a browser before calling it fixed.

## Verification boundary

The Insights checks run offline with mocked external services. The query-failure regression also runs a real pooled engine against a temporary local SQLite database; its fallback service is mocked. Live MySQL/PostgreSQL/MongoDB, browser rendering and CSP enforcement, signed HTTP authentication, and a live LLM call are **not verified by execution**.
