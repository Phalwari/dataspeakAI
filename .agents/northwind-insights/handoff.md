# Northwind Insights correction

## Observation
Connection 64 returned a partial dashboard: two SQLite identifier warnings, no monthly chart, categorical city rows masquerading as historical zero comparisons, and a provider fallback summary.

## Logic Chain
Orders holds transaction dates, customer references and shipping attributes; monetary inputs live in Order Details. Revenue was calculated correctly, but segment and named-customer paths omitted the line join. Qualified amount expressions and a shared fact/line source now preserve lineage; lifecycle counts use distinct order IDs when lines are joined. Transaction-date matching normalizes separators and case, so OrderDate takes priority over RequiredDate/ShippedDate. Frontend comparisons select only available numeric line/area series with at least two observations. Cache payload version advanced from 5 to 6.

Executive-summary parsing retains strict shape validation, accepts uppercase/lowercase JSON fences, and performs one format-repair request after invalid textual output within the same deadline. Rejected response text is neither logged nor forwarded to the repair prompt. Provider transport/envelope failures still follow gateway/fallback behavior.

## Caveats
Provider quota remains external. No successful live model response, browser rerender or automatic restart of the owner's existing backend is claimed. A local direct service check intentionally stubbed synthesis to avoid consuming quota; it updated connection 64's report cache and schema metadata, not its source rows. An absent delivered-status field remains unavailable rather than inferred from shipping dates. This targeted correction does not establish arbitrary-schema or join-topology support.

Sandboxed backend runs stalled at threaded TestClient/provider tests; they were interrupted. One early run also encountered default temporary-directory fixture errors. A fresh explicit temporary directory outside the sandbox completed the full selected set.

## Conclusion
Source fixes are implemented. Restart the serving backend if it is not using reload, then refresh Insights. No Git commit/push was performed in this correction session.

## Verification Method
- `python -m pytest tests/test_demo_qa_remediation.py tests/test_insights_date_filters.py tests/test_insights_sql_dialect.py tests/test_insights_llm_resilience.py tests/test_insights_regression_snapshots.py -q --basetemp=_qa_tmp/northwind-unsandboxed --disable-warnings`: **70 passed**, 22 warnings.
- `npm test -- --run`: **50 passed**, five files.
- `npm run build`: passed, 2,894 modules; existing large-chunk warning remains.
- FastAPI `import main`: passed with embedding warmup disabled and HF offline; existing administrator password preserved by startup seed check.
- Python compilation and diff whitespace checks passed; informational CRLF warnings remain.
- Actual local Northwind source, direct pipeline for owned connection 64: quality warnings empty; monthly, market, segment, customer and catalog charts available. Revenue 448386633.17, latest months September 2023 = 3544698.51, October 2023 = 2923364.35. Monthly series contains 136 observations. Independent read-only SQLite aggregate matched revenue and 16282 orders / 15538602 units.
- Synthetic multi-line regression verifies order counts remain distinct while revenue sums lines and discounts; malformed synthesis then fenced valid JSON succeeds on the single repair attempt; frontend regressions reject categorical/unavailable/missing-value sources and preserve numeric zero.
