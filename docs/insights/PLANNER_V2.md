# Insights Planner V2

## Status and rollout

The deterministic, schema-derived planner is implemented behind `INSIGHTS_PLANNER=v2`. The default remains `legacy`; V2 is opt-in until the fixture parity gate has a full review and the product owner approves cutover. This is not a claim of arbitrary-schema support or production readiness.

The product owner reported the Phase E browser check complete on 2026-10-21. It was not independently repeated during Phase F. No live database, live LLM, or browser request was made for this implementation.

## Request flow

1. A relational catalog is discovered with SQLAlchemy Inspector: tables/views, column types/nullability, primary keys, composite keys, foreign keys, and an optional engine-maintained row estimate. SQLite has no low-cost catalog estimate, so its `row_estimate` is `null`; the planner never performs a whole-table `COUNT(*)` just to estimate size.
2. Up to 10,000 rows per relational table and 256 columns per table are sampled. Profile objects contain counts, null/distinct ratios, parse rates, min/max and value-shape flags; they do not retain raw row values. PII-like fields are excluded from analytical roles. Complete profiles are cached for five minutes under tenant, connection generation, schema version, sample size, and profile version.
3. The role classifier emits a role, confidence and evidence. Metadata and observed values carry the score; names are tie-breakers. Low-confidence columns are not selected for KPIs. Revenue needs a transaction-like table and an explicit additive revenue signal. Salary, cost, fee, balance, unit price, quantity and rates do not become revenue by themselves.
4. The pure Python planner emits `MetricSpec`, `ChartSpec` and join intents. It does not produce SQL. Metrics include row count, distinct identifier count, additive sums, averages, trends, category breakdowns, gross revenue across all statuses and delivered-only net revenue. Missing requirements are represented as `unavailable` with a reason.
5. The SQL compiler accepts only identifiers in the discovered catalog, quotes them with the supported dialect helper, and binds date values. It supports SQLite, PostgreSQL, MySQL and MariaDB SQL generation. Unsupported dialects are rejected before query execution. Metric query failures are returned as `error/query_failed`; null aggregates are `unavailable/no_rows`; executed zero counts/sums are `zero`.
6. Relationships use declared FK paths first. A single-column inferred path is considered only with compatible identifier/key evidence and at least 95% bounded value containment. Ambiguous paths and paths deeper than two edges are skipped. Joined breakdowns use inner joins, so orphan facts are excluded from those breakdowns and a warning is returned; base-table aggregates retain those facts.
7. MongoDB uses a separate bounded planner. It samples up to 1,000 documents per collection, at most 100 collections per run, and nested paths to depth five. One array level may be unwound. Mixed-type numeric fields and PII-like fields are omitted. Aggregations use `maxTimeMS` bounded by the remaining planner budget; filtered failures never fall back to unfiltered counts.

## Output contract

Each metric and chart carries `status` (`available`, `zero`, `unavailable`, or `error`) and a `reason` when unavailable/error. Main reasons include `missing_role`, `missing_table`, `missing_relationship`, `no_rows`, `query_failed`, `invalid_date`, `unsupported_dialect`, `unsupported_array_depth`, `unsupported_array_shape`, and `budget_exceeded`. Values are `null` when no value is available; numeric zero is preserved as zero. `data_quality.warnings` describes catalog truncation, inference, profiling and skipped metrics.

Headline revenue labels are `Gross Revenue (all statuses)` and `Net Revenue (delivered only)`. Gross includes all row statuses. Net uses an exact allowlist of completed/delivered/shipped/success/closed status values; `unpaid`, cancelled, and returned rows are not counted as delivered.

## Safety bounds and limits

| Operation | Bound | Notes |
|---|---:|---|
| Relational sample | 10,000 rows/table | `LIMIT sample + 1` identifies truncation |
| Columns profiled | 256/table | Excess columns are omitted with a warning |
| Tables/collections | 100/run | Deterministic ordering and truncation warning |
| Mongo document sample | 1,000/collection | Metadata-only output; no source documents returned |
| Mongo nested path depth | 5 | Deeper paths are not discovered |
| Mongo array unwind | 1 level | Multiple/deeper array shapes are unavailable |
| Inferred relationship checks | 500 checks, max depth 2 | Requires at least 95% sample containment |
| Planner wall budget | 30 seconds | Stops starting work after budget; SQLite uses its progress handler and Mongo operations receive `maxTimeMS` |

The synchronous PostgreSQL/MySQL drivers do not have a common cancellable statement API in this planner. Their active query cancellation is **not verified by execution** and relies on the existing driver/server timeout configuration. Mongo `list_collection_names()` itself returns the full collection-name list before the 100-collection cap is applied.

## Fixture coverage

Offline tests use temporary SQLite databases and fake Mongo collections for: orders with paid/unpaid/cancelled/returned/delivered states; misleading numeric names; quantity without price and nullable dates; HR salaries; inventory cost/quantity; declared FK multi-table breakdowns; inferred no-FK breakdowns with orphan rows; empty tables/catalogs; nested Mongo arrays/objects; Mongo mixed types, PII-like fields, status-aware revenue, filtered errors and collection caps. Direct paired legacy/V2 SQLite runs cover orders/status, misleading names, quantity without price, HR salary, and empty tables. Chinook is not used as a target or golden fixture.

## Verification boundary

| Area | Status |
|---|---|
| SQLite catalog, profiling, roles, compiler and generated-query execution | Verified by execution with temporary in-memory SQLite fixtures |
| PostgreSQL/MySQL/MariaDB SQL generation | Offline SQL-fragment tests only; live execution **not verified by execution** |
| Mongo planner and aggregation pipeline | Offline fake-client tests only; live MongoDB **not verified by execution** |
| Ten-family legacy/V2 parity | Partial: direct paired SQLite execution covers orders/status, misleading names, quantity without price, HR salary, and empty table. FK/no-FK and Mongo families still lack direct legacy/V2 comparison. |
| Feature-flag default and F9 legacy removal | Pending parity review and owner cutover approval; default remains `legacy` |
| Signed HTTP authentication, multi-worker cache, browser, live LLM, and 100-user load | **Not verified by execution** |

## Safe product claims

Safe: “An opt-in deterministic planner discovers supported SQL schemas and emits metrics only when role evidence is sufficient; otherwise it reports unavailable/error.” SQLite fixtures and fake Mongo tests support this statement.

Not safe: “Works with any database/schema,” “all four database families are live verified,” “enterprise secure,” “production ready,” or “supports 100 concurrent users.”
