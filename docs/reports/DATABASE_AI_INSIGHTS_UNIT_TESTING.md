# 5.3 Unit Testing: DB AI Insights & Analytics Engine

### Testing Objective
To rigorously evaluate and verify the functional correctness, multi-tenant security isolation, statistical accuracy, and deterministic execution of the **DataSpeakAI Database AI Insights & Analytics Engine**. 

Testing validates the entire **6-Layer Relational Intelligence Pipeline**:
1. **Layer 1: Schema Introspection & Discovery** — Automatic cataloging of tables, columns, data types, and primary/foreign keys.
2. **Layer 2: Deterministic Metric Recipes** — Zero-hallucination formula calculations (`SUM`, `AVG`, `COUNT_DISTINCT`, ratio metrics with divide-by-zero protection).
3. **Layer 3: Visual Chart Recommendation** — Dynamic chart planning (Area, Bar, Pie, Metric cards) matching dimensional cardinalities.
4. **Layer 4: SQL Multi-Dialect Aggregation** — Safe execution of group-by and time-series aggregations with query timeouts.
5. **Layer 5: AI Executive Playbook Synthesis** — Google Gemini 2.5 Flash narrative generation with automatic deterministic rule-based fallback.
6. **Layer 6: Statistical Outlier & Anomaly Detection** — Identification of surges, elevated failure rates, latency bottlenecks, and unprofiled databases.

---

### Table 5.3: DB AI Insights & Analytics Engine Unit Test Cases

| No. | Test case / Test script | Attribute and value | Expected result | Actual Result |
| :---: | :--- | :--- | :--- | :---: |
| **1** | Check AI insights overview & KPI summary retrieval | `endpoint: 'GET /api/insights/'`<br>`tenant_id: 1` | Returns HTTP 200 with JSON summary KPIs (`total_insights`, `critical_count`, `pending_actions`, `available_categories`). | **Pass** |
| **2** | Check category filtering (`Operational` insights) | `endpoint: 'GET /api/insights/?category=Operational'`<br>`category: 'Operational'` | Returns HTTP 200 and filters the insight stream strictly to operational domain items. | **Pass** |
| **3** | Check severity level filtering (`warning` severity) | `endpoint: 'GET /api/insights/?severity=warning'`<br>`severity: 'warning'` | Returns HTTP 200 and matches only items tagged with warning threshold. | **Pass** |
| **4** | Check cross-tenant database isolation & authorization | `database_id: 999999`<br>`tenant_id: 1` (unowned ID) | Blocks cross-tenant enumeration and returns HTTP 404 Not Found without leaking schema data. | **Pass** |
| **5** | Check telemetry collection engine & query anomaly triggers | `tenant_id: 1`<br>`database_id: 58` (Neon E-Commerce DB) | Gathers genuine stats from `QueryLog`, `DatabaseConnection`, and `Document` tables without leaks. | **Pass** |
| **6** | Check dual-engine deterministic fallback synthesis | `telemetry: Neon E-Commerce DB metrics`<br>`engine: InsightsEngine.generate_deterministic_fallback` | Synthesizes structured business insights and tactical recommendations without LLM hallucinations. | **Pass** |
| **7** | Check insight dismissal and status toggling workflow | `insight_id: Active Insight`<br>`status: 'dismissed'` $\rightarrow$ `'active'` | Updates insight status in database and toggles visibility cleanly between active and dismissed states. | **Pass** |
| **8** | Check recommendation action status update workflow | `recommendation_id: Active Rec`<br>`status: 'completed'` | Marks tactical recommendation as completed with verified audit persistence in SQLite. | **Pass** |
| **9** | Check Layer 2 deterministic metric recipes & zero-division guards | `recipes: AtomicMetricRecipe (SUM)`<br>`RatioMetricRecipe (zero_division='null')` | Constructs validated Pydantic metric formulas with strict type bounds and divide-by-zero guards. | **Pass** |
| **10** | Check Layer 3 dimensional chart planning & layout composition | `table: 'orders'`<br>`charts: ['Monthly Revenue Velocity']`<br>`fn: compose_dashboard_layout` | Generates validated `DashboardLayoutPlan` containing recommended chart types, dimensions, and KPI cards. | **Pass** |
| **11** | Check Layer 6 statistical outlier & anomaly boundary evaluation | `metric: 'Failure Rate' & 'Latency'`<br>`actual: 30% error / 1650ms avg latency` | Flags 30% error rate as `HIGH_FAILURE_RATE` (critical) and 1650ms as `LATENCY_BOTTLENECK` (warning). | **Pass** |
| **12** | Check cache invalidation & atomic re-generation lifecycle | `connection_id: 58`<br>`fn: db_pipeline_service.invalidate_connection_cache` | Clears stale cache and guarantees freshly reflected analytical processing on next request. | **Pass** |

---

### Test Execution Summary
* **Total Unit Tests Executed:** 12
* **Passed:** 12 (100%)
* **Failed:** 0 (0%)
* **Average Execution Latency:** 22.4 ms
* **Test Runner Environment:** Python 3.10+ / FastAPI / SQLite / SQLAlchemy 2.0 / Pydantic v2
* **Target Database Tested:** PostgreSQL (`Neon E-Commerce DB`, Connection ID 58)

---

### Visual Proof & Automated Execution Screenshots

#### Figure 5.3.1: Executive AI Playbook & Strategic Header
Verified rendering of the automated AI Executive Playbook synthesized for the connected `Neon E-Commerce DB`. Displays the operational health summary, total active insights, pending recommendations, and multi-dimensional filter bar.

![Executive AI Insights Header and Strategic Overview](assets/insights/db_insights_executive_header.png)

---

#### Figure 5.3.2: Layer 2 Deterministic KPI Metric Cards
Verified deterministic metric calculation cards generated from Layer 2 recipes: Gross Revenue ($2,330.86), Order Volume (10 orders), Average Order Value ($233.09), Minimum Order ($45.99), Maximum Order ($499.99), and customer counts without hallucinations.

![Layer 2 Deterministic KPI Metrics](assets/insights/db_insights_deterministic_kpis.png)

---

#### Figure 5.3.3: Layer 3 & 4 Time-Series Velocity Chart
Verified dynamic Area chart plotting monthly revenue velocity computed via Layer 4 SQL time-series aggregations on the `orders` table.

![Monthly Revenue Velocity Area Chart](assets/insights/db_insights_monthly_revenue_chart.png)

---

#### Figure 5.3.4: Dimensional Breakdown & Status Distribution Charts
Verified dual analytical charts: Revenue by Status (Bar Chart) and Order Volume by Fulfillment Status (Donut Chart) reflecting relational groupings (`completed`, `shipped`, `processing`, `delivered`).

![Revenue by Status and Order Distribution Charts](assets/insights/db_insights_revenue_status_charts.png)

---

#### Figure 5.3.5: Entity Ranking & Payment Gateway Distribution
Verified Top 5 Buyers by Spending (Horizontal Bar Chart) and Payment Method Distribution (Pie Chart) with verified percentage calculations across Credit Card, PayPal, and Bank Transfer.

![Top Buyers and Payment Method Distribution](assets/insights/db_insights_buyers_distribution_charts.png)
