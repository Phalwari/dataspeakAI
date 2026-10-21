# DB AI Insights — Presentation aur Viva Preparation

Prepared: 22 October 2026. Code baseline: branch `pull_review_all_changes`, commit `4c22c84`. Roman Urdu study guide; app behavior was traced from source, not inferred from the screenshot alone. This preparation does not change the app or repeat yesterday's live tests.

## 1. Sab se pehle ye statement yaad karein

“DataSpeakAI ka DB Insights feature connected database ki schema discover karta hai, supported analytical roles identify karta hai, aur database queries se KPIs aur charts calculate karta hai. AI ko restricted aggregate context diya jata hai taake wo executive explanation aur recommendations bana sake. Is liye numerical calculation aur natural-language interpretation separate responsibilities hain. AI unavailable ho to calculated metrics aur clearly labelled deterministic summary phir bhi mil sakti hai.”

Three terms:
- **Schema:** tables/collections, fields, data types aur relationships ki structure.
- **Deterministic:** same supported input data, same scope aur same calculation rules par reproducible result; fresh data/cache state aur concurrency result ko affect kar sakte hain.
- **Aggregation pushdown:** raw records browser/LLM mein calculate karne ke bajaye SUM, AVG, COUNT aur GROUP BY database engine se karwana.

## 2. Teen minute ki opening presentation

“Business users ke paas structured data hota hai lekin har user SQL expert nahi hota. Hamara module us data se initial business overview automatically banata hai.

User saved connection select karta hai aur all tables ya specific table ka scope choose karta hai. Date aur supported dimension filters bhi apply ho sakte hain. React frontend authenticated request FastAPI ko bhejta hai. Backend current user ke tenant ke against connection ownership check karta hai, phir cache aur schema resolve karta hai.

Relational databases mein SQLAlchemy metadata aur dialect-specific SELECT aggregations use hoti hain. MongoDB mein collections aur fields discover karke native aggregation pipelines chalti hain. Numeric measures, categorical dimensions aur dates ki classification chart aur metric selection guide karti hai.

Screenshot subscription billing example hai. Invoices collection ke all-status amounts ka sum 16,300 dollars hai. Paid-status subset ka sum 14,736 dollars hai. Dono ko separate dikhana zaroori hai: total billing aur paid billing same business fact nahi hain. Average invoice amount 101.875 hai jo UI mein 101.88 display hota hai.

System time series aur category breakdowns bhi banata hai. Frontend returned chart definitions ko Recharts mein render karta hai. Latest observed monthly amount ko previous observed month se compare kiya jata hai. Ye descriptive comparison hai, future prediction nahi.

AI layer calculated aggregates ko explain karti hai. Screenshot mein AI unavailable label hai, is liye displayed summary deterministic fallback hai. Is design ka benefit ye hai ke provider outage core arithmetic ko unavailable nahi banata. Current implementation ki boundaries bhi hain: legacy role detection convention-based hai, Mongo collection scope limited hai, aur distributed cache aur production-scale capacity separately validate karni hogi.”

## 3. End-to-end flow jo board par draw karna hai

```text
User: connection + table + date + dimension
                  |
BusinessInsightsPage.runDatabaseAnalysis()
                  |
GET /api/insights/generate/{connection_id}
Authorization: Bearer <session token>
                  |
FastAPI get_current_user -> tenant ownership -> date/scope checks
                  |
DatabasePipelineService.run_db_pipeline()
                  |
L1 memory cache / eligible L2 persisted cache
                  |
Schema discovery -> role classification -> analysis mode
                  |
       SQL SELECTs             Mongo aggregation
       SUM/AVG/COUNT           $match/$group/$sort
                  \             /
           Metrics + charts + result statuses
                  |
      Aggregate-only synthesis context -> LLM Gateway
                  |                       |
         Valid AI JSON              Failure/timeout
                  |                       |
            AI explanation       Deterministic fallback
                  \                       /
        Response + quality warnings + cache + audit
                  |
React KPI cards, rankings, charts, summary, inspection drawer
```

Cache hit schema/computation ko skip kar sakta hai. Ye always fresh full-scan workflow nahi.

## 4. Code tour — examiner ko ye files khol kar dikhana

Paths repo-relative hain. Line numbers preparation baseline ke hain; later edits mein shift ho sakte hain.

1. `src/app/pages/dashboard/BusinessInsightsPage.tsx`, around 302–357: `runDatabaseAnalysis` constructs request, scope, date presets, Authorization header; HTTP error handling; result state update.
2. Same file, around 260–281: `triggerAnalysisAnimation` timer-based workflow explanation. Current main screen uses normal JSON GET, not the SSE endpoint.
3. Same file, around 369–398: `handleOpenDrilldown`, preview request with limit 30.
4. Same file, around 505–579: observed-period comparisons and categorical top-performer extraction.
5. `backend/routers/insights.py:349`: `generate_database_insights` authenticates through dependencies, forwards scope, logs audit; invalid selected scope -> 422, unresolved owned connection -> 404, unexpected failure -> 500. Date validation uses `_validated_dates`.
6. `backend/services/db_pipeline_service.py:740`: `run_db_pipeline` orchestrator; requires tenant, looks up owned connection, checks planner flag/cache, decrypts credentials, discovers schema, computes dashboard.
7. Same file, 83–190: date normalization, date/dimension predicates, cache key, planner selection.
8. Same file, 1041–1207: metadata lookup/reflection, selected-table validation, heuristic fact/customer/product detection, measure/date/dimension classification, Mongo-first mode selection.
9. Same file, 1211 onward: relational federation, gross and delivered-only revenue, counts, averages, dimensions and joins.
10. Same file, approximately 2090–2460: native Mongo aggregation. First three collections in all-collection legacy mode; selected collection can be analyzed separately.
11. Same file, 2748–2847: AI prompt, JSON shape validation, deterministic fallback.
12. Same file, 2849–2872: basic SQL-only anomaly rule.
13. Same file, approximately 2900–2990: response fields, layout composition, L1/L2 writes.
14. `backend/services/database_connection_service.py:453`: legacy Mongo schema inference from one sample document, shallow nested-path extraction, estimated collection size.
15. `backend/services/sql_dialect.py:21`: SQLite/PostgreSQL/MySQL month bucket differences. `quote_ident` around 59 quotes identifiers; quoting alone is not authorization.
16. `backend/services/redis_service.py`: `_MEM_CACHE` dictionary and TTL. Despite module/cache-source naming, current backend is not a real shared Redis service.
17. `backend/routers/insights.py:468` and pipeline service 2992: optional SSE route. It emits coarse milestones around the synchronous pipeline; not exact per-query telemetry.
18. `backend/services/llm_generation_service.py`: shared provider gateway. Model/provider availability depends on actual configured keys and upstream service; don't promise a fixed model is used on every run.

Do not confuse `backend/services/ai_insights.py` or other generated-insight listing routes with the specific DB dashboard request. Trace the URL used by this frontend.

## 5. Screenshot ke har section ka meaning

### Header: MongoDB, All dates, 14 metrics, 9 charts

MongoDB is source type. All dates means no requested calendar date predicate. Metric/chart counts are lengths of generated output lists, not a fixed product-wide promise. Three analyzed collections here: invoices, support_tickets, customers. “Relational Intelligence” is generic UI wording; this Mongo path does not join collections using SQL or `$lookup`.

### Invoices ke 6 metrics

1. Total invoice documents: 160. Legacy unfiltered Mongo count prefers `estimated_document_count()`. Demo verification independently matched 160; the implementation should not be described as guaranteed exact unfiltered COUNT on every deployment.
2. Total amount: `$sum` of amount across the matching invoice population = $16,300.
3. Paid amount: same requested population AND case-insensitive exact `paid` status = $14,736.
4. Average amount: `$avg` of non-null matching amount = 16,300 / 160 = 101.875 -> $101.88 for this fixture. Null/mixed-type production data requires denominator/type interpretation.
5. Distinct plan: 3 unique observed plan values.
6. Distinct status: 2 unique observed status values.

All-status amount minus paid amount = $1,564. Demo has cancelled invoices in this difference; don't automatically call it receivables, losses, refunds or unpaid debt. Status/business semantics matter.

### Support tickets ke 5 metrics

80 documents, 512 total resolution hours, 6.4 average resolution hours, 2 distinct priorities, 2 distinct statuses.

512 / 80 = 6.4 for this fixture. Current generic average is over matching non-null values; it is not explicitly restricted to resolved tickets. Don't call it “resolved-ticket SLA” without verifying that business rule. “Resolution hours” sum is an operational measure, not currency/revenue.

### Customers ke 3 metrics

32 customer documents, 32 distinct company names, 2 segments. Distinct company names and customer identity count happen to match here; they need not match when company names duplicate.

### Period velocity

September amount = $10,160, October amount = $6,140. Together = $16,300.

```text
change % = (current - previous) / abs(previous) × 100
         = (6140 - 10160) / 10160 × 100
         = -39.5669...% -> -39.6%
```

This is invoice AMOUNT change, not invoice COUNT change. Backend trend sums the first selected measure; without one it counts documents. The frontend takes the last two returned periods. A partial current month is not directly comparable to a complete previous month for a causal business conclusion. Missing months are not necessarily filled with zero. Monthly bucket list is ascending and capped at 24; long histories need review before claiming the chart always contains the newest 24 months. Zero previous value currently yields 0% in frontend, a display limitation; mathematically growth from a zero baseline needs special handling.

### Top performers

Enterprise $10,547; Growth $4,187; Starter $1,566. Sum = $16,300.

Ranking here is amount by plan, not customers by plan, profit by plan, or predicted future demand. Backend sorts category aggregate descending. Frontend respects chart `yKey`, falling back to `value`, `val`, `count`, and shows up to seven rows. Backend breakdown limits to eight categories. Top-N charts may omit other categories, so visible shares need denominator care.

### Nine charts

- Invoice time trend: monthly amount by created_at.
- Invoice plan breakdown: amount grouped by plan.
- Invoice status breakdown: amount grouped by status; paid slice is dollar share, not necessarily invoice-count share.
- Invoice region breakdown: amount grouped by region.
- Support time trend: sum of resolution_hours by month. One monthly observation appears as a point; no multi-period trend is established.
- Support priority breakdown: first numeric measure, here resolution_hours, grouped by priority.
- Support status breakdown: resolution_hours grouped by status.
- Customer company breakdown: document count by company_name when no numeric measure is selected. Many bars equal one, so low business value; inclusion of a chart doesn't guarantee an insightful metric.
- Customer segment breakdown: document count by segment.

Always read source collection, group field and measured field. “Distribution” can mean sum of a measure or count; pie slices alone do not tell you which.

### Summary and recommendation

“AUTO-GENERATED SUMMARY (AI UNAVAILABLE)” + “Computed monetary sum is $16,300.00 across 160 records” = deterministic fallback, not a successful model explanation. The label alone does not prove whether failure was quota, timeout, connectivity or invalid JSON; inspect error metadata/logs for exact cause.

“Computed monetary aggregate” is fallback finding. “Medium Impact” and “Take data-driven action” are generic defaults in this path, not a measured impact estimate or a sophisticated personalized AI strategy. Mention this honestly if asked.

“Statistical Baselines Stable” is shown when anomaly list is empty. Current legacy anomaly routine returns an empty list for Mongo without running its SQL outlier rule. Therefore this screenshot does NOT prove statistical stability or that Mongo passed anomaly testing.

## 6. Mongo calculations ko code mein explain karna

These are illustrative equivalents of the real recipe, not copied logs or a guarantee of byte-for-byte emitted syntax.

```javascript
// Sum and average amount over non-null amount values
db.invoices.aggregate([
  {$match: {amount: {$ne: null}}},
  {$group: {_id: null,
    s_val: {$sum: '$amount'},
    a_val: {$avg: '$amount'},
    cnt: {$sum: 1}}}
])

// Exact paid status, intersected with an existing scope
db.invoices.aggregate([
  {$match: {$and: [
    {amount: {$ne: null}},
    {status: {$regex: '^paid$', $options: 'i'}}
  ]}},
  {$group: {_id: null, value: {$sum: '$amount'}}}
])

// Category breakdown
db.invoices.aggregate([
  {$match: {plan: {$ne: null}, amount: {$ne: null}}},
  {$group: {_id: '$plan', value: {$sum: '$amount'}}},
  {$sort: {value: -1}}, {$limit: 8}
])
```

`$match` rows/documents filter karta hai. `$group` group keys aur accumulators define karta hai. `_id: null` whole matching population ko one group banata hai. `$sum: 1` count hai; `$sum: '$amount'` monetary aggregate hai. `$avg` numeric average hai. `$dateToString` month key banata hai. `$sort` ordering aur `$limit` output groups bound karte hain; output group limit underlying aggregation scan cost ko necessarily bound nahi karti.

Status `paid` ko `contains('paid')` se match nahi karte, warna `unpaid` bhi match ho sakta hai. `^paid$` exact word anchors hain. Requested cancelled filter aur paid predicate ko `$and` se intersect karna paid filter ke overwrite se bachata hai: cancelled-only demo -> 16 invoices, $1,564 total, $0 paid, 1 distinct status.

## 7. SQL route aur relational reasoning

Conceptual parameterized query:

```sql
SELECT SUM(amount) AS amount_total,
       COUNT(*) AS transaction_count,
       AVG(amount) AS amount_average
FROM invoices
WHERE created_at >= :date_from
  AND created_at < :date_to_excl
  AND region = :dimension_value;
```

Illustration mein fixed identifiers hain. Real supported identifiers schema se resolve aur dialect ke mutabiq quote hote hain. User values bindings ke through jati hain; SQL identifier ko `:table_name` parameter se replace nahi kar sakte. Identifier ke liye catalog validation plus quoting chahiye.

PostgreSQL monthly bucket `to_char(column, 'YYYY-MM')`, MySQL `DATE_FORMAT(column, '%Y-%m')`, SQLite `strftime('%Y-%m', column)`. PostgreSQL monetary ROUND ko numeric cast ki zaroorat ho sakti hai. Same logical metric ka SQL engine-specific syntax hota hai.

Fact table transactional records rakhti hai, dimension table descriptive entities: orders + customers + products. Order items ka grain one row per line item hai. Orders ka grain one row per order hai. Join karne ke baad order amount multiple lines ki wajah se repeat ho sakta hai. Is liye aggregate grain aur join cardinality samajhna important hai; every join safe/correct assume nahi karna.

Legacy topology detection mein name heuristics bhi hain; selected fixes mein scoped unit totals declared FK use karte hain. V2 ka stricter evidence-based join architecture legacy ki har query ka description nahi hai.

Date/dimension-scoped customer count ko same fact population se follow karna chahiye. Independent global customer count ko filtered order metric ke saath silently mix nahi karna. Verified East coffee result: $12,400, 60 orders, 6 customers, 240 units, $2,066.67 spend/customer. Unsupported lineage -> unavailable instead of global fallback.

## 8. AI layer ki exact responsibility

`_llm_safe_points` finite numeric KPI values aur restricted numeric chart points bhejta hai. Supported canonical relational KPI IDs ke liye fixed semantic names bhi attach hote hain. Arbitrary customer names, chart labels aur raw rows is synthesis payload se omit hote hain. Chart context first three numeric points tak restrict hota hai. Generic Mongo KPI IDs ko har case mein rich semantic labels nahi milte; context ki ye limitation explanation quality reduce kar sakti hai.

Prompt JSON fields demand karta hai: `business_domain`, `executive_summary`, `strategic_insights`, `tactical_recommendations`. Parser checks object/list/string shapes. Valid JSON aur correct field types factual correctness ka proof nahi; prompt instruction bhi mathematical proof nahi. Deterministic KPIs remain independent, but AI narrative needs evaluation and stronger numeric/claim verification for production assurance.

Gateway failure/timeout/invalid response -> `source='deterministic_fallback'` and `llm_error` category. Success -> `source='llm'`. Configurable `LLM_PIPELINE_BUDGET_SECONDS`, default 30 seconds, bounds synthesis waiting. AI synthesis aur anomaly work two executor tasks mein submit hote hain. Ye total request wall-clock ka universal 30-second bound nahi: discovery and metric work earlier run hota hai; active driver calls separately matter karte hain.

Chatbot se difference: Chat arbitrary natural-language question route karta hai aur SQL/Mongo generation ya document RAG use kar sakta hai. This dashboard pre-defined supported metric recipes automatically runs. Document embeddings/FAISS ka hona DB dashboard ke SUM ka calculation mechanism nahi. Chat citation grounding ko automatically DB executive summary ki identical verification samajhna incorrect hoga.

## 9. Cache, freshness, scope, statuses

L1 is actual process-local `_MEM_CACHE`, despite `redis_l1` source naming. L2 connection row mein persisted report JSON plus cached timestamp. Legacy insights TTL is 86,400 seconds (24 hours). L2 reuse sirf all-table, all-date, no-dimension requests ke liye allowed hai. L1 key tenant, connection, cache generation, table, date bounds, dimension field/value se scoped hai; V2 keys extra planner/catalog/plan context use karte hain.

Refresh cache generation increment karta hai aur old payload invalidate karta hai. Version-checked writes old in-flight runs ko fresh generation overwrite karne se rokne mein help karte hain. Ye transactionally consistent analytical snapshot across multiple source queries ka guarantee nahi. Concurrent source updates se different query results slightly different moments represent kar sakte hain. Source updates automatically push nahi hote; “Live Analysis” continuous CDC/websocket monitoring ka proof nahi.

Four result states:
- available: calculated result available.
- zero: successful calculation really produced zero.
- unavailable: no supported role/data/path, value null, reason present.
- error: query failed; zero ki tarah show nahi karna.

Mongo unfiltered metadata estimate aur exact aggregation ko distinguish karein. Cached output stale ho sakta hai. Date field null records requested date interval mein include nahi hote.

## 10. Legacy aur V2 ko mix nahi karna

`_insights_planner_mode()` default `legacy` hai; `INSIGHTS_PLANNER=v2` explicit opt-in hai. Preparation mein inspected shell/backend config mein explicit setting nahi mili; already-running process environment ko independently certify nahi kiya. Demo remediation ne default change nahi kiya.

Legacy: convention/name/type rules, Mongo schema one document sample, shallow nested discovery, first three collections for all-table analytics, established dashboard recipes.

Opt-in V2: normalized catalogs, bounded profiling, evidence/confidence-based roles, typed metric plans, separate compiler/executor, declared and conservatively inferred joins, wider bounded Mongo discovery. Relational profiling up to 10,000 rows/table, Mongo up to 1,000 docs/collection, up to 100 collections/run per documented bounds. V2 complete parity/default rollout and production-scale verification remain pending. These V2 numbers must not be claimed as legacy behavior.

`docs/insights/KNOWN_ISSUES.md` contains historical verification notes and a missing-table xfail that later remediation fixed. Latest 22 October report supersedes those specific earlier findings, not all broader known limitations.

## 11. Security answer jo defend kar sakte hain

JWT/current-user dependency identifies user; tenant is derived server-side. Connection lookup filters tenant_id before cache/result access. Saved credentials are decrypted server-side for connection; browser should never receive database passwords. Scope identifiers are checked against available schema. SQL user values are bound. Generated insights use SELECT aggregation recipes; Mongo dashboard uses native read aggregations.

Use least-privilege read-only source accounts for production defense in depth. Demo used isolated local development database assets, not a certified production access setup. Connection host/SSRF checks exist at the connection layer, with explicit private-host allowance for local development. Don't claim every legacy execution path reuses chatbot sql_engine timeout/guardrail functions: Insights has its own pooled path. Mongo sum/paid aggregations use 10-second maxTimeMS, but not every legacy Mongo operation has the same explicit timeout. Tenant checks and parameterization alone are not full security certification.

## 12. Fifty-five viva questions with short answers

1. **AI Insights kya solve karta hai?** Initial data exploration aur business overview automate karta hai, without requiring the business user to write every aggregation manually.
2. **Ye sirf charts hain?** Schema discovery, role detection, calculation, scope, quality states, narrative, caching and inspection together feature banate hain; charts presentation layer hain.
3. **AI kahan hai?** Aggregate-based executive synthesis/recommendations; deterministic metric calculation separate hai.
4. **Kya AI numbers guess karti hai?** Displayed KPI arithmetic database recipes se aati hai. Narrative generation separately imperfect ho sakti hai.
5. **Own trained model hai?** Is dashboard mein custom trained prediction model ka claim nahi. Rule-based analytics plus configured external LLM gateway use hota hai.
6. **Kis model ka use hai?** Shared configured provider gateway; exact successful provider/model runtime config and telemetry se establish hoga, UI title se nahi.
7. **Schema kaise milti hai?** Saved metadata, refresh/cache miss par relational inspection or connector schema discovery; Mongo mein sampled document fields.
8. **Mongo schemaless hai to schema kaise?** Observed field/type profile infer karte hain, enforced universal schema nahi. Rare/mixed fields miss ho sakte hain.
9. **160 invoices exact hain?** Demo verification matched 160; legacy unfiltered UI count metadata estimate prefer karta hai. Filtered count uses count_documents.
10. **Total amount aur paid amount mein difference?** All matching statuses vs matching paid-status subset.
11. **1,564 kya unpaid debt hai?** Not automatically; fixture mein cancelled amount hai. Accounting meaning status definitions se decide hota hai.
12. **Average amount formula?** AVG of matching numeric amounts; fixture 16300/160 = 101.875 -> 101.88.
13. **Distinct plan 3 ka meaning?** Unique plan values, not three invoices or three customers.
14. **512 hours revenue hai?** No, operational sum of resolution_hours.
15. **6.4 hours SLA hai?** Not necessarily. Generic average doesn't explicitly filter resolved tickets or compare contractual SLA.
16. **Minus39.6% count reduction hai?** Screenshot mein monthly amount change, not document-count change.
17. **Ye prediction hai?** No, descriptive historical aggregation/comparison.
18. **October incomplete ho to?** Treat comparison as observed totals, explain unequal exposure; normalize or use matched elapsed dates before stronger conclusions.
19. **Previous month zero ho to?** Current frontend returns 0%; mathematically special undefined/new-baseline state should be supported.
20. **Top performer ka metric?** Selected chart's aggregation measure; screenshot plan amount, not profit/customer count.
21. **Pie chart percent customer share hai?** Only if underlying metric is customer count. Invoice amount chart represents amount share.
22. **Why only nine charts?** Detected supported fields and bounded recipe choices produced nine for this schema; output varies.
23. **Every company bar one means?** One document per displayed company_name here; low discriminatory value, not automatic business insight.
24. **All collections join hoti hain?** Current Mongo dashboard analyzes selected collections independently, no relational join/lookup guarantee.
25. **Relational federation ka matlab?** Supported multi-table analysis within a connection. It does not automatically join PostgreSQL, MySQL and Mongo across servers.
26. **How are relationships found?** Legacy conventions plus supported FK paths; V2 has explicit evidence-based catalog/join planning. Don't interchange them.
27. **Join duplication problem?** Order amount may duplicate across lines; preserve metric grain and aggregate correct fact/line expression.
28. **Filter lagana frontend ka kaam?** Request selection frontend ka; actual metric/chart scoping server/database par hoti hai.
29. **Wrong table name?** Reject invalid scope, current nonstream route returns422; silently substitute another table nahi.
30. **No date field?** Requested date-scoped metric unsupported/unavailable; unfiltered data ko filtered claim ke saath show nahi karna.
31. **Date end inclusive kaise?** API end date next-day exclusive upper bound banati hai; e.g. Oct31 -> < Nov1 midnight.
32. **SQL injection kaise rokte?** Bind values, validate schema identifiers, quote dialect identifiers. Read-only DB grants extra protection hain.
33. **Identifier ko parameter kyun nahi?** Bind parameters data values hain, table/column grammar replace nahi karte.
34. **Tenant leakage?** Server-derived tenant, owned connection filter before cache use, tenant-scoped keys; complete assurance still needs broader security testing.
35. **Kya raw customer data LLM ko jata?** This synthesis helper numeric aggregates/fixed context sends, omits raw rows and arbitrary labels. Not a whole-application privacy certification.
36. **AI hallucination impossible?** No. Deterministic calculations reduce numerical-generation dependence; JSON/prompt checks don't prove all narrative claims.
37. **AI unavailable kyun?** Possible quota, timeout, network/provider error or invalid response. Exact category metadata/logs se identify karein.
38. **Offline work karega?** Reachable source databases se deterministic analytics can work without external LLM; model narrative won't. Other infrastructure requirements still apply.
39. **Medium impact how computed?** Screenshot fallback uses generic default; not quantified causal impact prediction.
40. **Stable badge prove no anomalies?** No. Mongo legacy detector skips SQL rule, returns empty; UI empty-list badge is too broad.
41. **Anomaly algorithm?** Legacy SQL rule checks max monetary value >3× positive mean. No trained model, no z-score significance guarantee.
42. **SSE progress exact hai?** Optional route exists but main screen normal GET plus timer animation; not exact measured stage completion.
43. **Real-time hai?** On-demand live-source analysis with cache; not continuous streaming source updates.
44. **Redis use karte?** Current L1 implementation is in-memory dictionary despite naming. L2 report persists in app database.
45. **Cache TTL?** Legacy dashboard report 24hours, with scoped keys and explicit refresh/versioning.
46. **100 users supported?** No measured concurrent capacity claim from this QA. Need load tests, shared cache, pooling and per-source budgets.
47. **Huge Mongo collection?** Aggregation engine may scan many rows; output limits don't bound scan cost. Indexes, budgets and query explain/performance review needed.
48. **All schema supported?** No; supported roles/patterns and selected connector paths, unavailable/error when unsupported. Legacy naming and sampling limit generalization.
49. **Drilldown full proof?** It is capped30-row preview. Current caller doesn't pass exact calendar bounds; display aliases can differ from source field names. Need validate provenance/filter mapping before claiming exact reconciliation for every chart/KPI.
50. **Export kya hai?** Current UI captures dashboard PNG via html2canvas; separate API HTML export exists. Don't claim this button generates an Excel workbook or PDF.
51. **Dashboard vs chatbot?** Recipe-driven overview vs user-question-driven retrieval/query/synthesis. They share infrastructure but not identical calculation paths.
52. **V2 default hai?** No, default legacy; V2 opt-in pending full parity/rollout approval.
53. **Testing ka evidence?** Latest remediation report records affected backend231pass, overlapping final edge38pass, frontend47pass and Vite buildpass, plus signed live demo cases.
54. **231+38 =269 unique?** No, sets overlap; don't add as independent unique-test count.
55. **Next improvements?** Accurate status labels, explicit business metric/date mappings, exact count provenance, drilldown reconciliation, robust Mongo discovery, consistent query budgets, numeric narrative checks, shared cache and load testing.

## 13. Agar examiner code likhne ko kahe

Start with a fixed, simple aggregation, explain every stage, then add the requested scope. Do not start by inventing a complex LLM query-generation subsystem for this dashboard.

Tasks to practice out loud:
1. Total billed and average invoice amount using Mongo `$group`.
2. Paid subset with anchored regex or exact normalized enum comparison.
3. October half-open date bounds using actual BSON datetime values.
4. Amount per plan using `$group`, descending `$sort`, bounded output.
5. Parameterized SQL count/sum under date and region scope.
6. Growth calculation and why partial/zero baselines need explicit interpretation.
7. Explain why cancelled AND paid should produce zero, not replace the cancelled filter.
8. Explain why customer count must follow scoped orders rather than global customers.

## 14. Eight-minute live demo script

0:00–1:00: Problem + deterministic/AI separation. Select Mongo subscription demo, all dates. Explain source and scope.

1:00–2:30: Show160,16300,14736,101.88. Explain cancelled difference and two statuses; check average arithmetic verbally.

2:30–3:30: Plan ranking and monthly trend. Say amount, not invoice count. Explain October partial-period caveat.

3:30–4:30: Show tickets/customers; explain measures vs dimensions and how chart selection varies. Don't claim every chart is equally business useful.

4:30–5:30: Table scope and a known-good date or dimension case. Relative “last7days” preset can produce zero if fixture dates are older: that's expected, not justification to fake data. Use all dates or a known supported API scope for reproducibility.

5:30–6:30: Explain AI provenance label. If unavailable, demonstrate graceful degradation honestly; do not repeatedly refresh until a provider success is mistaken for guaranteed availability.

6:30–7:30: Open request construction, router and Mongo aggregation code. Show actual path rather than every project file.

7:30–8:00: State test evidence, current limitations and next improvement priorities.

Optional prepared known-answer checks from prior live QA: Mongo October60/$6140; cancelled16/$1564/paid0; East coffee6customers/240units/60orders/$12400. These are fixture-specific verification examples, not hardcoded app outputs. Recheck source availability before the presentation; this guide does not assert current server uptime.

## 15. Tonight ka 150-minute study plan

- 0–20min: Opening script + vocabulary + flow diagram. Explain it without reading twice.
- 20–45min: Screenshot arithmetic and nine charts. For each, say source, population, grouping, measure, meaning, limitation.
- 45–75min: Six code stops: frontend request, router, orchestrator, Mongo group, AI fallback, cache.
- 75–110min: Questions1–35 out loud; 30–60second answer each. Mark answers you cannot say clearly.
- 110–135min: Questions36–55, especially tricky limitations. Practice calm “current implementation…” answers.
- 135–150min: One full8minute demo + opening + three toughest follow-ups.

Morning: 15minute revision of opening, five formulas, six files, ten caveats. Keep report/source tabs ready, notifications closed, credentials out of slides/screenshare.

## 16. One-hour mock viva agenda and self-marking

First10minutes: problem, architecture, request flow. Next15: Mongo formulas and screenshot. Next15: SQL/dialects/joins/filter scope. Next10: AI/fallback/security/cache. Final10: testing/limitations/design improvements.

Score each answer out of4:
- 1point: direct correct first sentence.
- 1point: concrete code function/path.
- 1point: numerical/data example.
- 1point: limitation or tradeoff when relevant.

Don't memorize function bodies. Learn “input -> validation -> transformation -> execution -> output -> failure.” If you don't know a detail, say “Is exact behavior ko relevant function/test se verify karunga; current verified behavior ye hai…” and state what you can substantiate.

## 17. Ten sentences jo nahi bolni

“AI ne saare numbers calculate kiye.”
“Mongo ki saari collections join ho rahi hain.”
“Hamne custom ML model train kiya hai.”
“Minus39.6% future forecast hai.”
“Unpaid word bhi paid mein count hota hai.”
“Stable badge proves no anomaly in Mongo.”
“Redis distributed caching already running hai.”
“Loading percentage exact backend completion hai.”
“Every database/schema and100users fully certified hain.”
“Correct JSON means AI answer100%correct hai.”

## 18. Evidence and study sources

Primary: the source files/code stops above. Recent behavior and testing: `docs/reports/demo_qa_remediation_2026-10-22/REPORT.md` and accompanying evidence/logs. Baseline findings: `docs/reports/demo_qa_2026-10-21/REPORT.md`. Opt-in architecture: `docs/insights/PLANNER_V2.md`. Historical limitations: `docs/insights/KNOWN_ISSUES.md`, interpreted alongside the later remediation rather than as an up-to-date list of every remaining bug.

The explanations about count estimation, Mongo anomaly badge, timer progress, preview scope, zero-baseline growth and capped month ordering are current source observations for preparation. They are not newly executed end-to-end regression results or a claim that each issue was fixed in this study session.
