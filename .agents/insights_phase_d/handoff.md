# Insights Phase D handoff

## Observation

The Insights pipeline previously treated date presets as a recent chart-point slice and could run unfiltered query shapes during a filtered request. Mongo filter bounds and role classification also produced misleading results on generic schemas.

## Logic Chain

Calendar inputs now normalize before cache access, SQL date values are bound, and unsupported query shapes become unavailable. The frontend asks the API for a calendar window and displays the returned range. SQL expression generation is dialect explicit. Mongo queries share the same half-open bounds and no longer sample displayed aggregates. Generic fixtures exposed and fixed count/ratio currency misclassification and quantity-only omission.

## Caveats

This is not a generic semantic planner. Some filtered dimension metrics are unavailable because a valid date join cannot be inferred. One `missing_table` test remains a strict expected failure. Live PostgreSQL, MySQL, MariaDB, MongoDB, browser behavior, signed HTTP authentication, and concurrent-user capacity are not verified by execution. The branch inherits an earlier WIP baseline that remains unreviewed.

## Conclusion

Phase D's offline acceptance checks pass for generic temporary SQLite and Mongo mock fixtures. This does not establish enterprise readiness for arbitrary customer databases.

## Verification Method

- `python -m pytest tests/test_insights_failure_semantics.py tests/test_insights_export.py tests/test_insights_date_filters.py tests/test_insights_sql_dialect.py tests/test_insights_mongo_filters.py tests/test_insights_generic_fixtures.py -q --disable-warnings` → `41 passed, 1 xfailed, 22 warnings in 10.75s`.
- `python -m py_compile backend/services/db_pipeline_service.py backend/services/sql_dialect.py backend/routers/insights.py` → exit 0.
- `npm run build` → Vite built successfully; large-chunk warning remains.
- No external DB, server, browser, or load test was run.
