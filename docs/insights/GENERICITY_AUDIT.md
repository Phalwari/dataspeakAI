# DB AI Insights Pipeline Genericity Audit

**Scope:** static review of `backend/services/db_pipeline_service.py`, `backend/services/metric_recipes.py`, `backend/services/dashboard_composer.py`, and `backend/routers/insights.py`, with `backend/services/metric_semantics.py` consulted for the called semantic-validation rules. This audit covers the SQLite, MySQL/MariaDB, PostgreSQL, and MongoDB branches.

**State reviewed:** current working-tree source, which contains pre-existing uncommitted changes. No source files were changed for this audit. Findings therefore describe the reviewed working tree and may differ from committed `HEAD`.

**Execution status:** static inspection only. No tests, compile checks, live database connections, or load tests were run. All runtime behavior below is **not verified by execution**.

## Summary

The pipeline is **partly generic, not schema-agnostic**. Its selected-table SQL mode builds row-count, measure-aggregation, distinct-count, date-trend, and categorical-breakdown families from discovered columns. The all-tables SQL mode first recognizes a fixed set of business table names and assumes familiar commerce joins and fields. MongoDB has a separate collection/document aggregation path, but it still relies on shallow profile heuristics and a small fixed number of collections.

For a transparent, limited count, this audit treats each independently emitted metric/chart template as one family. In the SQL paths, the current code has **9 federated headline KPI families that are business-domain-specific** and **4 selected-table KPI families that are generic** (row count, sum, average, distinct count): 4/13, about **31% generic**. It has **6 commerce-oriented federated chart families** and **3 selected-table chart families** (time trend, dimension breakdown, secondary measure by dimension): 3/9, about **33% generic**. These are template-family counts, not a coverage or quality score; MongoDB's per-collection templates and supporting summary cards are not included in the denominator. The selected-table path is the most portable SQL mode, subject to column-role and dialect limits.

`metric_recipes.py` provides schema-registry-aware recipe validation, and `dashboard_composer.py` is a schema-neutral assembler. The current pipeline imports recipe model types but its aggregation path directly emits SQL; the generic recipe validator is not the planner that drives these metrics. Accordingly, generic infrastructure does not make the emitted KPI/chart catalog generic by itself.

## Counting method and limits

- A “generic” family derives its target table/columns from discovered schema profiles and does not require a commerce table or join convention.
- A “schema-specific” family depends on commerce-oriented labels, known table-name candidates, named columns, or a fixed relationship pattern.
- Counts are limited to SQL metric/chart templates visible in `db_pipeline_service.py`; they do not count each dynamically generated metric instance, dashboard composition, AI prose, or Mongo per-field instances.
- No fixture was executed. Counts and impacts are a static code estimate, not measured schema coverage.

## Findings

### G-01 — All-tables mode is gated by a fixed commerce table vocabulary

**Severity: High**  
**Evidence:** `backend/services/db_pipeline_service.py:469-498` normalizes names and matches fixed candidates for fact, line-item, customer, catalog, category, and artist/vendor tables. The federated path requires a recognized fact table (`:558`).

**Impact:** Common order/invoice/sales schemas may enter the richer path; arbitrary names such as `ledger_entries`, `work_logs`, `payroll_runs`, or `stock_movements` will not be recognized as the fact table. Those schemas fall back to selected-table behavior only when a table is explicitly selected; otherwise they do not receive the domain KPI set. Similar prefixed/suffixed names may fail exact normalized matching. HR and inventory can still receive generic selected-table counts/measures if columns are discovered, but should not be expected to produce commerce KPIs.

### G-02 — Federated relationship discovery assumes naming conventions rather than FK metadata

**Severity: High**  
**Evidence:** schema profiles contain column names/types (`:501-531`); the relationship logic searches conventional ID names and constructs joins for customer, geo, line-item, catalog/category, and rental paths (`:577-810`, `:1097-1115`, `:1160-1208`, `:1230-1276`). Pipeline schema profiling does not populate relationship metadata. Separately, `metric_semantics.py:50-61` can consult `SchemaRegistry.is_primary_key` / `is_foreign_key`, but that is not evidence that the pipeline's federated planner uses those flags.

**Impact:** Renamed keys, composite keys, bridge tables with nonstandard names, and legitimate relationships that are not inferable from matching suffixes can be missed or joined incorrectly. The category bridge branch constructs identifiers from table names, which is especially sensitive to naming convention. Generic recipe validation in `metric_recipes.py:303-369` is not a substitute for planner relationship discovery.

### G-03 — The federated KPI set encodes commerce concepts

**Severity: Medium**  
**Evidence:** the federated branch emits fixed metric IDs/labels in `backend/services/db_pipeline_service.py:884-988`: gross/total revenue, delivered-only revenue, order count, average order value, active customers, customer lifetime value, units sold, catalog size, and top market.

**Impact:** These KPIs are meaningful only where the assumed fact/customer/product semantics exist. A generic numeric column does not establish “revenue,” a row is not necessarily an “order,” and a customer table is not necessarily an active buyer population. Missing prerequisites often yield `N/A`, zero-valued raw fields, or omitted charts rather than a clearly typed “not applicable” result. Non-commerce HR/inventory schemas should not be marketed as receiving equivalent business KPIs.

### G-04 — Role detection is heuristic and name-biased

**Severity: High**  
**Evidence:** `is_id_column` uses name rules and suffix matching (`:122-145`); `is_monetary_column` uses substrings such as `total`, `discount`, and `salary` (`:182-191`); `is_date_column` uses type/name tokens (`:194-203`); remaining eligible columns become dimensions (`:206-220`).

**Impact / examples:** `total_orders` matches `total` and may be treated as a monetary measure; `discount_rate` matches `discount` and may be summed despite representing a rate; `network_id` matches the `_id` identifier rule; `void` ends with `id` and is also classified as an ID because it is not in `SAFE_WORDS_ENDING_ID`. Type is used for date detection, but monetary and most ID decisions are largely name-based. Columns with misleading names can be assigned the wrong semantic role and generate plausible but meaningless statistics.

### G-05 — Status recognition is exact after normalization, but its vocabulary is incomplete and gated

**Severity: Medium**  
**Evidence:** the status column is selected by the presence of status/state-like name tokens (`:658-661`); `classify_status` maps exact normalized values (`:48-58`), and each grouped status row is classified before accumulating delivered/cancelled/returned counts (`:676-694`).

**Impact:** Exact matching prevents `unpaid` from being counted as `paid`/delivered. Values such as `fulfilled`, `partially_shipped`, localized labels, numeric codes, or organization-specific lifecycle terms fall into `other`. The status aggregation is currently guarded by both a detected status column and a money expression (`:672` vicinity), so status-only schemas or schemas without an inferred monetary column do not receive the full status breakdown. This static conclusion is not verified by a test in this audit.

### G-06 — Optional metric prerequisites produce mixed “missing” and zero semantics

**Severity: Medium**  
**Evidence:** selected-table row counts and measure aggregates are conditionally appended only when a query returns rows (`:1669-1732`); sum/average values coerce SQL NULL to `0` (`:1692-1714`). Generic charts are appended only when their result is truthy (`:1746-1825`). The federated chart branch has a `segment_dim and money_expr` guard (`:1067-1074`).

**Impact:** A missing role or failed query may omit a card/chart; a successful SQL aggregate over an empty/all-NULL set may instead display zero. The payload has a `data_quality.warnings` list (`:1972`), but metric records do not consistently encode unavailable vs. zero. One misleading fallback remains: when a date exists without a money expression, the trend query counts rows but labels the output “Monthly Revenue Velocity” / “Revenue ($)” (`:1025-1043`).

### G-07 — SQL query failures can degrade the dashboard instead of failing the request

**Severity: Medium**  
**Evidence:** `execute_sql` catches failures, logs them, appends a generic warning, and returns `[]` (`:331-400`). Callers generally conditionally append metrics/charts from returned rows (`:1669-1825`). The response exposes aggregated warnings under `data_quality.warnings` (`:1972`).

**Impact:** The endpoint can return a success-shaped payload with partial omissions after query errors. This is better than silently hiding all error evidence, but consumers must inspect `data_quality.warnings`; otherwise partial results can appear complete. Mongo collection aggregations also contain local fallback/catch behavior (`:1331-1652`), and some failures fall back to unfiltered counts or are logged at a broad outer catch.

### G-08 — Date expressions are selected by SQL dialect, with portability edges

**Severity: High**  
**Evidence:** `date_trunc_fmt` selects SQLite `strftime`, PostgreSQL `to_char`, and `DATE_FORMAT` for the remaining SQL dialect (`:552-553`). Customer name assembly uses `||` (`:1160-1170` vicinity), and customer identifiers are cast with `CAST(... AS TEXT)` (`:1172-1208`). Monetary aggregations use `ROUND(SUM(...), 2)` in multiple branches (`:822`, `:865-866`, `:1009-1019`, `:1692`, `:1814`). MongoDB uses native aggregation operators such as `$dateToString` (`:1512` vicinity) rather than these SQL expressions.

**Dialect assessment (static; not verified by execution):**

- **SQLite:** `strftime` and `ROUND(x, 2)` are native. `CAST(... AS TEXT)` and `||` are supported.
- **PostgreSQL:** `to_char` and two-argument `ROUND` are suitable for numeric values. `CAST(... AS TEXT)` and `||` are supported.
- **MySQL/MariaDB:** `DATE_FORMAT` and `ROUND` are supported. `||` is logical OR by default unless a SQL mode changes it, so first/last-name concatenation can be wrong. `CAST(... AS TEXT)` is not the portable MySQL cast form (`CHAR` is customary) and may fail depending on server/version. The current branch treats the non-SQLite/non-PostgreSQL dialect as the MySQL expression branch, so an unrecognized SQL dialect would also receive MySQL syntax.
- **MongoDB:** Mongo-specific aggregation is used, not SQL. SQL expressions above do not apply; support depends on collection profiler and aggregation shape.

### G-09 — Date filters are present and parameter-bound in SQL but not uniformly applicable

**Severity: Medium**  
**Evidence:** HTTP routes accept `date_from` / `date_to` (`backend/routers/insights.py:298-318`, `:331-354`, `:371-391`). Pipeline parsing validates date strings (`backend/services/db_pipeline_service.py:319-329`); SQL execution binds values as `:date_from` / `:date_to` and adds predicates to queries involving the detected fact reference (`:331-355`). MongoDB parses its own date match (`:1342-1354` vicinity).

**Impact:** SQL values are bound rather than inserted as user values, but the predicate is applied only when an active fact/date pair is inferred and the query text matches that fact reference. Selected-table paths, non-fact tables, invalid dates, or nullable/mixed-format date fields can therefore have different behavior. Mongo date matching requires compatible stored date values; this has not been exercised.

### G-10 — MongoDB path is distinct and collection-limited; nested-document coverage is not established

**Severity: Medium**  
**Evidence:** MongoDB bypasses the relational federation condition (`:549-558`) and enters its own collection loop (`:1331-1372`); all-tables mode chooses at most the first three available collections (`:1361-1370`). It derives document counts and up to a limited number of inferred measures/dimensions from table profiles (`:1370-1652`).

**Impact:** The pipeline does not provide relational joins for MongoDB and may omit collections beyond the first three. Static profile shape does not establish recursive handling of nested paths, arrays, heterogeneous documents, or BSON date/numeric variants. No end-to-end nested-document behavior was run. Do not claim broad MongoDB schema support from the presence of the Mongo branch alone.

### G-11 — The recipe layer is more generic than the current pipeline execution path

**Severity: Medium**  
**Evidence:** `metric_recipes.py:91-93` includes `orders.*` examples in documentation; registry-based validation is implemented at `:303-369`. `metric_semantics.py:50-61` checks PK/FK metadata and `:64-147` rejects invalid aggregations when a registry record is supplied. `db_pipeline_service.py:26-31` imports recipe types, but the KPI/chart construction code directly builds SQL (`:1669-1825`).

**Impact:** A reader may infer that recipe and FK semantic validation drives every generated pipeline metric, but current pipeline construction is heuristic and imperative. Recipe-layer strengths should not be described as end-to-end protection without a call path and tests proving their use.

### G-12 — Dashboard composition and route layer are not the source of schema hardcoding

**Severity: Low (positive finding)**  
**Evidence:** `compose_dashboard_layout` copies supplied metrics/charts/filters into a typed plan without schema-specific table logic (`backend/services/dashboard_composer.py:15-48`). Pipeline routes forward the selected table/date bounds to the service (`backend/routers/insights.py:294-327`, `:331-354`, `:371-391`).

**Impact:** Main genericity limits are in discovery/planning/SQL generation and dialect behavior, not the layout composer. Fixed insight category labels in the router are presentation taxonomy, not database table/column requirements.

## Hardcoded schema vocabulary and assumptions

| Hardcoded item / expression | Evidence | Expected fit | Likely miss / risk |
|---|---|---|---|
| Fact tables: `invoice(s)`, `order(s)`, `sale(s)`, `transaction(s)`, `payment(s)`, `rental(s)` | `db_pipeline_service.py:483` | Common commerce/transaction schemas | Arbitrary names like `ledger_entries`, `payroll_runs`, `events` |
| Line items: invoice-line/order-detail/order-item/line-item/rental variants | `:486` | Familiar order-detail schemas | Custom detail tables, bridge naming variants |
| Customer tables: customer/client/user/member variants | `:489` | Common account/customer schemas | `people`, `employees`, `accounts`, custom CRM names |
| Catalog: track/product/item/book/course/film/movie variants | `:492` | Catalog/product domains | Inventory tables named `stock`, `assets`, `materials` |
| Category: genre/category variants; artist/vendor: actor/artist/supplier/vendor/brand variants | `:495-498` | Retail/media catalogs | Custom taxonomy/vendor labels |
| Geography relationship fields/tables (`customer_id`, address/city/country IDs; `address`, `city`, `country`) | `:795-810` | Conventional normalized geography schema | Different location model, denormalized address, composite/nonstandard keys |
| Customer join and display fields (`customer_id`, `first_name`, `last_name`, `name`, contact-name variants) | `:1160-1208` | Conventional customer schemas | Different person key/name fields; MySQL `||` portability risk |
| Rental/category bridge fields derived from table names (`rental_id`, `inventory_id`, `film_id`, `category_id`) | `:1097-1115` | Familiar sample/Chinook-like rental/catalog model | Arbitrary FK names and composite relationships |
| Direct catalog `category` field | `:1288-1301` | Denormalized product category | Different category attribute name/type |
| Column-name tokens for IDs, money, date, and dimensions | `:122-220` | Conventionally named columns | Misleading names, custom names, semantic false positives |
| SQL date functions/casts/concatenation | `:552-553`, `:1160-1208` | Known SQLite/PostgreSQL/MySQL branches | MySQL `||`, `CAST AS TEXT`, unrecognized dialect fallback |

## Role detection rules

- **ID:** exact names (`id`, `pk`, `uuid`, selected Chinook IDs), `_id` patterns, camel-case `Id`/`ID`, and any sufficiently long name ending in `id` (`db_pipeline_service.py:122-145`). Type/actual constraints are not the primary decision in this helper. Thus `network_id` is ID and `void` is a false-positive ID; `reportsto` is an explicit ID exception.
- **Money/measure:** substring tokens include `total`, `amount`, `revenue`, `sales`, `price`, `cost`, `fee`, `salary`, `balance`, `discount`, `spend`, and `net` (`:182-191`). `total_orders` may be monetary; `discount_rate` may be treated as an additive money measure. `metric_semantics.py:42-47,64-147` has ratio/rate validation, but pipeline use of it is not established.
- **Date:** date/time/timestamp type token or name token (`:194-203`). Nullable dates are filtered with `IS NOT NULL` in trend queries, but date source choice is the first matching profile column.
- **Dimension:** after ID/date exclusions and a name-based denylist for address/contact/secret/long-text-like fields, remaining columns are dimensions (`:206-220`). This can include high-cardinality or semantically sensitive values outside the denylist.
- **Status:** a column name containing `status`, `order_status`, `delivery_status`, or `state` (`:658-661`); normalized values are exact-matched by `classify_status` (`:48-58`).
- **Foreign keys:** the insights pipeline does not use FK metadata in the profile and federated-join discovery. Elsewhere, recipe semantic validation can read `SchemaRegistry` PK/FK flags (`metric_semantics.py:50-61`), but that does not prove this pipeline's generated queries are FK-validated.

## Failure-mode matrix

| Path / output | Missing role or schema | Query failure behavior | Zero vs unavailable |
|---|---|---|---|
| Federated commerce KPIs | Fixed cards may use `N/A`, zero defaults, or be omitted depending on KPI and whether its query result exists (`db_pipeline_service.py:884-988`) | `execute_sql` returns `[]` and records a generic warning (`:331-400`) | Not represented consistently; successful NULL aggregates can become zero, missing query results often omit/retain N/A |
| Generic selected-table row count | Query family needs a selected/available table (`:1669-1687`) | Empty result means no card is appended | Empty table count of 0 vs failed query with no result can be ambiguous without warning inspection |
| Generic selected-table sum/average | Needs inferred measure columns (`:1689-1732`) | Empty result omits those cards | SQL NULL coerces to zero; unavailable and true zero can look alike |
| Generic date trend | Needs date column; uses first date column (`:1746-1775`) | Empty result omits chart and warning may be present | Empty trend is omitted; no explicit unavailable state |
| Generic categorical chart | Needs inferred dimension (`:1777-1810`) | Empty result omits chart and warning may be present | No chart can mean no data, no eligible role, or query failure |
| Secondary measure chart | Needs at least two measures and a dimension (`:1812-1840` vicinity) | Empty result omits chart | Missing, zero, and failed are not encoded as distinct chart statuses |
| Mongo collection profile | Collection is included only among selected/first-three list (`:1361-1370`) | Local catches/fallback counts exist (`:1370-1652`) | Count fallback may return an unfiltered count; measure/chart omissions are not a typed unavailable state |

`data_quality.warnings` is a useful but global warning channel (`:1972`); it does not attach a failure reason to each metric/chart. The endpoint response may remain success-shaped after partial query failures.

## Dialect audit

| Expression | SQLite | MySQL/MariaDB | PostgreSQL | MongoDB |
|---|---|---|---|---|
| `strftime('%Y-%m', col)` | Native; selected in code | Not selected | Not selected | Not applicable |
| `to_char(col, 'YYYY-MM')` | Not selected | Not selected | Native; selected in code | Not applicable |
| `DATE_FORMAT(col, '%Y-%m')` | Not selected | Native; selected for other SQL DB types | Not selected | Not applicable |
| `CAST(expr AS TEXT)` | Supported | Portability/version concern; use `CHAR` for broad MySQL compatibility | Supported | Not applicable |
| `first_name || ' ' || last_name` | String concatenation | Usually logical OR unless SQL mode enables pipes-as-concat; correctness risk | String concatenation | Not applicable |
| `ROUND(SUM(expr), 2)` | Supported | Supported | Supported for numeric input | Replaced by Mongo aggregation operators |
| `COUNT`, `SUM`, `AVG`, `GROUP BY`, `LIMIT` | Common forms used | Common forms used | Common forms used | Not SQL; uses aggregation API |

Static review cannot verify server-version behavior, type coercion, SQL modes, collation, or driver-specific execution. No database dialect was connected for this audit.

## Fixture plan (not executed)

| Fixture | What it checks | Expected behavior |
|---|---|---|
| Relational e-commerce, Chinook-like | Known invoice/order + detail + customer + catalog/category relationships; all-tables discovery; generic selected-table mode | Conventional names should trigger the federated KPI/chart families; selected-table generic families should work. This is a compatibility baseline, not proof for arbitrary schemas. |
| Orders with `paid`, `unpaid`, `cancelled`, `returned` status | Exact status classification and delivered-only revenue | `paid` counted delivered; `unpaid` classified unpaid and excluded from delivered revenue; cancelled/returned separate. Verify variants do not substring-match. |
| Quantity without unit price and nullable dates | Missing monetary role and sparse temporal values | Count-based activity may be available; no revenue should be asserted. Null dates excluded from trend. Ensure output does not label row count as revenue and reports unavailable distinctly from zero. |
| Misleading names: `total_orders`, `discount_rate`, `network_id` (also `void`) | ID/money/date/dimension classifier false positives | Demonstrate current classification risk (`total_orders`, `discount_rate` as money-like; `network_id` and `void` as ID-like). Treat as a regression fixture for a future semantic-role redesign. |
| Non-ecommerce HR/inventory with no revenue | Generic selected-table portability and absence of commerce assumptions | Generic counts and suitable numeric/date/dimension summaries only; no revenue/customer/catalog commerce claims. All-tables federated commerce KPIs should be absent or explicitly unavailable. |
| MongoDB nested documents | Nested path discovery, numeric/date arrays, heterogeneous documents, collection selection | Must verify if nested fields are flattened and safely aggregated; current static audit cannot establish this. Expect no relational joins, and test collections beyond the current all-tables cap separately. |

## Prioritized fix plan

1. **Generic discovery:** profile reliable types/nullability/cardinality and PK/FK relationships; make business-domain detection explainable and confidence-scored; avoid table-name-only federation; support nested Mongo paths intentionally.
2. **Metric planning:** use validated recipe/semantic layers as the actual planner; distinguish transaction totals, unit price, ratios, IDs, status, and additive measures; generate domain KPIs only when semantic prerequisites and relationship paths are proven.
3. **Dialect layer:** centralize date truncation, casts, string concatenation, booleans, and numeric rounding per supported dialect; reject unsupported dialects explicitly rather than treating all unknown SQL DBs as MySQL.
4. **Failure semantics:** return typed metric/chart states (`available`, `unavailable`, `error`, `zero`) with scoped warnings; never relabel count as revenue; ensure failed SQL is visible to callers and downstream UI.
5. **Date behavior:** retain bound parameters and test each query shape/dialect, including selected-table, joined-table, nullable dates, inclusive/exclusive bounds, and invalid inputs.
6. **Fixtures and verification:** implement the six fixture families above with SQLite and offline Mongo mocks where possible; add dialect-specific integration runs only in explicitly approved isolated environments. Add endpoint/auth tests for request-level tenant isolation separately.

## Pitch-safe claims

**Safe with the current evidence:**

- “The insights pipeline has generic, schema-derived summaries for selected SQL tables, including row counts, inferred measures, distinct values, and simple trends/breakdowns.”
- “It also has a separate MongoDB collection analytics path.”
- “Known commerce naming conventions receive additional specialized KPI and chart templates.”

**Not safe to claim from this audit:**

- “Works generically on any database/schema.”
- “Automatically understands arbitrary business semantics or relationships.”
- “Revenue/status metrics are correct for all schemas.”
- “Nested MongoDB is comprehensively supported.”
- “SQLite, MySQL/MariaDB, PostgreSQL, and MongoDB have all been execution-verified.”
- “Enterprise-ready, production-proven, or load-tested for 100+ concurrent users.”

**Verdict:** the pipeline is **not fully generic**. A selected SQL table with conventional scalar columns is the most defensible demo path; a familiar relational commerce schema is suitable only for demonstrating the specialized, convention-based metrics. Database-specific execution and arbitrary-schema behavior remain **not verified by execution**.
