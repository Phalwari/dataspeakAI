# DB AI Insights Failure Semantics

## Step 1 status

**Partial (local working tree; not yet committed).** The pipeline now adds `status` and `reason` to KPI and chart objects produced by the handled SQL and MongoDB paths while retaining the existing `value`/`raw_value` roles. A not-available KPI uses `value: null` and `raw_value: null`; successful numeric values keep their previous formatted `value` and numeric `raw_value`.

| Status | Meaning | Reason |
|---|---|---|
| `available` | Successful result with a usable nonzero value or chart data | `null` |
| `zero` | Successful numeric result equals zero, including `COUNT(*) = 0` | `null` |
| `unavailable` | The result cannot be calculated meaningfully | `missing_role`, `missing_table`, or `no_rows` |
| `error` | The query/aggregation failed | `query_failed` |

The existing `data_quality.warnings` remains a string list. Tracked query warnings include the affected metric/chart ID as a prefix, e.g. `<metric-id>: ...`, so the response key and value type remain compatible with the current frontend. SQL aggregate NULLs are retained long enough to mark the metric `unavailable/no_rows`, rather than formatting them as zero. MongoDB date-filtered count failures no longer fall back to an unfiltered count; absence of a date role is `unavailable/missing_role`.

`BusinessInsightsPage.tsx` was read-only checked: KPI cards render values with `AnimatedCount`, whose `useCount` helper converts nullish values to an em dash (`—`) using `String(value ?? '—')` at `src/app/pages/dashboard/BusinessInsightsPage.tsx:44-66`; the card invokes it at `:1290`. This suggests null is render-safe, but a browser/UI run was not performed.

An offline SQLite run also exposed an adjacent exception-path crash: when LLM generation failed and fallback recommendations were empty, insight serialization indexed an empty list. Fallback serialization now supplies a generic action for that case.

## Verification

- `python -m py_compile backend/services/db_pipeline_service.py` — **passed**.
- Temporary SQLite pipeline run with paid/unpaid/cancelled/returned rows and LLM stubbed offline — **passed**: 9 KPI objects and 4 chart objects had statuses; gross total was 375 and delivered-only revenue was 100; offline synthesis fallback completed.
- Temporary SQLite run on an empty selected table — **passed**: row count reported `zero` with raw value 0; NULL sum reported `unavailable/no_rows` with `value: null` and `raw_value: null`.
- Temporary SQLite files were removed after each run. No test fixture or test source was created in this step.
- MongoDB behavior, query-error injection across every query family, browser rendering, and the full pytest suite are **not verified by execution**. MongoDB was not connected.

Typed results are not yet guaranteed for every conceivable unplanned metric when a required table/role is absent, and some non-metric SQL helper queries still produce only a generic warning. The `missing_table` reason is reserved but is not currently emitted. Step 1 remains partial until query/status coverage is exhaustively tested and closed.

## Remaining work

Step 2 fixtures and Step 3 pytest suite remain pending explicit approval. This local Step 1 change has not been committed; commit staging must exclude all pre-existing working-tree edits and include only failure-semantics changes.
