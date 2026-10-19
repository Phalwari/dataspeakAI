# Insights Known Issues

## INS-FAIL-01: SQLite may accept a double-quoted unknown column as a string

SQLite can interpret a double-quoted identifier that does not resolve to a column as a string literal in compatible configurations. A generated aggregate may therefore return a value instead of raising a missing-column error. This behavior was encountered while preparing the query-failure regression test; the real-engine regression now uses a SQLite function that raises an operational error instead. The engine behavior is covered by `tests/test_insights_failure_semantics.py`, but generated-query handling of every unknown identifier form is not verified by execution.

## INS-FAIL-02: Missing selected table status remains expected-failure

`test_missing_selected_table_has_missing_table_reason` is marked strict xfail at `tests/test_insights_failure_semantics.py:183-187`. The current pipeline may select another available table and does not assign `missing_table` to the requested metric. The expected behavior is not implemented.

## INS-FAIL-03: Query-failure status mapping still uses a mocked fallback service

`test_query_failure_is_reported_by_mocked_service_unit` replaces `db_connection_service.execute_query` with a synthetic failing result at `tests/test_insights_failure_semantics.py:113-134`. The separate pooled SQLite regression (`tests/test_insights_failure_semantics.py:136-180`) executes a real SQLite query that raises, then uses a mocked fallback service failure to reach the pipeline's `error/query_failed` state. The real SQL engine error is exercised; the complete fallback-service integration path is not verified by execution.
