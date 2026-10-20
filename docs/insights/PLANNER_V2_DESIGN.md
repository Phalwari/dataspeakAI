# Insights Planner V2 Design (Phase F0)

**Status:** approved design baseline. Implementation and verification status are tracked in [`PLANNER_V2.md`](PLANNER_V2.md). The `v2` planner remains opt-in until F8 parity review and approval.

## Scope and claims

Planner V2 replaces schema-name assumptions in the planning core with a deterministic pipeline: discover catalog metadata, profile bounded samples, score column roles with evidence, plan metrics, compile validated plans, and execute with typed result states. The LLM may summarize numeric results; it does not select tables, columns, joins, or SQL.

The target is relational SQLite, PostgreSQL, MySQL/MariaDB and a separate MongoDB planner. SQLite is the offline execution target. PostgreSQL is the first SQL dialect target for SQL-string and eventual execution checks; MySQL/MariaDB follow. Live PostgreSQL, MySQL/MariaDB, and MongoDB execution remain unverified until the separately authorized D5 environment check. This design does not claim support for every database or arbitrary business semantics.

Phase E browser verification was reported complete by the product owner on 2026-10-21; it was not independently repeated during F0.

## F0 decisions

### 1. Column-role contract

The classifier emits exactly one primary role per column: `identifier`, `additive_measure`, `unit_price`, `quantity`, `rate`, `date`, `categorical`, `status`, `free_text`, `pii`, `excluded`, or `unknown`. A role includes a confidence in `[0, 1]` and nonempty evidence for every non-excluded, non-unknown decision. A low-confidence result is `unknown`; the planner does not emit a KPI that requires an unknown role.

Role classification is evidence-based. Evidence sources are declared type, PK/FK metadata, bounded-sample null and distinct ratios, numeric/date parseability, numeric/date min/max, value-shape checks, and name tokens as a tie-breaker. Sensitive and free-text columns are excluded before metric planning. Raw sampled values never enter catalog, profile, plan, cache, logs, or LLM payloads.

`total_orders` is count-like and cannot qualify as money from its name. `discount_rate` is a non-additive rate. `network_id` is an identifier only when key/cardinality evidence supports it. A low-cardinality boolean such as `void` is categorical/status evidence, not an identifier.

### 2. Revenue semantics

An additive measure does not automatically mean revenue. A `revenue` metric requires both a transaction-like grain established from schema evidence and a monetary measure with positive revenue evidence. `salary`, `cost`, `fee`, and `balance` may be additive measures for neutral sums but never qualify as revenue solely by being numeric or having a currency-like declared type. `unit_price`, `quantity`, and `rate` are not summed as additive totals. No supported revenue measure means `revenue` is `unavailable/missing_role`.

### 3. Relationship policy

Declared single- and composite-column FKs are authoritative. Inferred joins are considered only when compatible key types and a bounded child-to-parent containment sample meet the configured 95% threshold; the path is labeled `inferred`. Ambiguous paths, multiple equal-cost paths, or paths beyond depth 2 are not used and produce `unavailable/missing_relationship`. Orphan child records are excluded from joined metrics and surfaced as a data-quality warning; base-table metrics remain unaffected.

### 4. Domain packs

Commerce, HR, and inventory packs are optional presentation/metric bundles. A pack activates only when all declared prerequisites pass. Pack names and conventional table names are labels, never inputs to identifier selection or join planning. Generic count, distinct-count, trend, and category metrics remain available independently of a domain pack.

### 5. MongoDB planner

MongoDB has a separate planner and bounded profiler. Nested paths use dotted notation. Arrays may be unwound one level by default; deeper array expansion requires an explicit bounded plan and is unavailable otherwise. Mixed BSON types are profiled by type and excluded from numeric aggregates unless the numeric parse threshold passes. PII-like paths are excluded. Collection truncation and sample-budget exhaustion are returned as warnings.

### 6. Feature flag and rollout

`INSIGHTS_PLANNER=legacy|v2` selects the implementation. Missing, empty, or unrecognized configuration resolves to `legacy` and is logged as a configuration warning; it never silently opts a deployment into V2. V2 remains opt-in until F8 has zero unexplained fixture differences and the product owner approves the default switch. The legacy path is retained through F8 and removed only in F9 after parity approval.

### 7. Initial safety limits

These are upper bounds, configurable downward by deployment settings:

| Limit | Initial value | Behavior when reached |
|---|---:|---|
| Rows sampled per relational table | 10,000 | Stop sampling; mark profile sampled and report the sample limit |
| Tables/collections per run | 100 | Deterministic catalog truncation and warning |
| Columns profiled per table | 256 | Deterministic truncation and warning |
| Relationship traversal depth | 2 | Plan requiring deeper traversal is unavailable |
| Inferred relationship containment | 95% | Below threshold: no inferred relationship |
| Low-cardinality sample distinct cap | 50 values and at most 5% of sample | Above either cap: not a categorical breakdown candidate |
| Minimum role confidence | 0.80 | Below threshold: `unknown` |
| Total planner execution budget | 30 seconds | Stop new work and mark unfinished metrics `unavailable/budget_exceeded` |
| Mongo array unwind depth | 1 | Deeper expansion is unavailable by default |

For very small samples (fewer than 20 rows), a text column with at most five distinct values may be treated as categorical even when its distinct ratio exceeds 5%; this avoids rejecting dimensions merely because the source table is small. Confidence and the evidence remain visible to the planner and tests.

Budgets are enforced before opening further work and between query/sample batches. Database statement timeouts remain the responsibility of the existing connection execution layer; this design does not claim a hard cancellation guarantee where the driver cannot cancel an active statement.

### 8. Metric result states

Every planned metric and chart has one state: `available`, `zero`, `unavailable`, or `error`. `zero` is reserved for an executed count/aggregate with a mathematically defined zero result (for example `COUNT(*) = 0`). SQL `NULL` aggregates are `unavailable/no_rows`. Missing prerequisites are `unavailable/missing_role`, `missing_table`, or `missing_relationship`; an executed query failure is `error/query_failed`. Budget exhaustion is `unavailable/budget_exceeded`. No failure is converted to a numeric zero.

## Architecture and module boundaries

1. `services/insights/catalog.py`: immutable, normalized relational catalog and metadata discovery.
2. `services/insights/profiling.py`: bounded sample statistics, with no raw values in return objects.
3. `services/insights/roles.py`: deterministic role classifier and evidence.
4. `services/insights/planner.py`: pure Python metric plans; contains no SQL strings.
5. `services/insights/sql_compiler.py`: allowlisted plan compiler with quoted catalog identifiers and bound values.
6. `services/insights/relationships.py`: FK graph and conservative bounded inferred-path checks.
7. `services/insights/mongo.py`: separate Mongo catalog/profile/plan/aggregation implementation.
8. Existing pipeline adapter: feature-flag dispatch and response-contract mapping; existing legacy implementation stays intact through F8.

Catalog and profile hashes are deterministic and versioned. Cache keys include planner version, catalog version, role rules version, selected table, and date range. Query values and sampled records are never used as cache-key material.

## Validation gates

- Each phase adds focused offline tests using temporary SQLite databases and fake Mongo clients; no test connects to customer or production databases.
- SQL for PostgreSQL/MySQL/MariaDB receives compiler-string tests before any live execution claim.
- F8 compares legacy and V2 on at least ten fixture families; every numeric expectation is hand-computed. Intended semantic corrections are documented; unexplained differences block rollout.
- Chinook is compatibility regression coverage only, never the planner's target schema or golden baseline.
- `KNOWN_ISSUES.md` and `PLANNER_V2.md` must state the execution boundary for each supported dialect/provider.

## Open decisions

- Which database the first customer requires is not yet known. PostgreSQL is the provisional first dialect target; the product owner can reprioritize MySQL/MariaDB before F5/F8 live verification.
- D5 live database execution, production-scale budgets, and operational cancellation semantics need a separately authorized environment and test plan.
