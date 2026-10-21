# Live demo acceptance review — 21 October 2026

**Historical baseline:** DQA-01..10 were subsequently addressed and verified in the [22 October remediation report](../demo_qa_remediation_2026-10-22/REPORT.md). The findings and 30/10 results below describe the original pre-fix run.

**Verdict: the chatbot and DB AI Insights are not ready for professional sign-off.** Core relational calculations work on these fixtures, but document retrieval/grounding, MongoDB chat, filtered metric consistency, and presentation contain reproducible defects. Findings are recorded, not repaired by this task.

## Environment and completed setup

- Tested the local app at `http://localhost:5173` and API at `http://127.0.0.1:8000`, branch `pull_review_all_changes`, observed revision `a26610f`.
- Used the second account supplied by the owner: user 2, tenant 2. The first account's supplied password was rejected; no password was changed.
- Removed tenant 2's two saved connections, three uploaded datasets, and twelve pre-demo conversations. No external database was dropped. Other tenants and audit/usage history were retained.
- Saved the pre-cleanup application SQLite database and source inventory in the ignored `_qa_tmp/demo-runtime/` directory. Uploaded dataset files may have been removed by their normal deletion endpoint; the SQLite backup alone is not a complete file-content restore.
- Created three actual servers, bound only to loopback, with generated credentials. The existing system PostgreSQL service on port 5432 was left intact. Native binaries were used because Docker was unavailable.
- Registered connection 61: PostgreSQL 18, port 55432, `demo_coffee_retail`; 24 customers, 6 products, 240 orders, 240 order lines.
- Registered connection 62: MySQL Community 8.4.13, port 53306, `demo_solar_wholesale`; 24 customers, 6 products, 180 orders, 180 order lines.
- Registered connection 63: MongoDB 8.0.16, port 57017, `demo_subscription_billing`; 32 customers, 160 invoices, 80 support tickets.
- Uploaded and indexed `coffee_retail_policy.txt`, `solar_wholesale_policy.txt`, and `subscription_billing_policy.txt`: document IDs 3–5, all Completed/ready, two embedding chunks each.
- Created a localhost-only demo widget key named **Demo QA | Local Policy Bot**, with SQL disabled and only demo documents 3–5 published. Existing widget keys were retained.
- Backend was restarted with process-local `ALLOW_PRIVATE_DB_HOSTS=true` to access the requested local databases. No production configuration or planner default was changed.

All business data is synthetic and represents realistic scenarios, not real customer records. Dates span September–October 2026; money is USD. Demo server credentials and API session tokens are excluded from this report and tracked evidence.

## Observed checks

The evaluator performs **40 explicit checks: 30 passed, 10 failed**. This is a collection of targeted checks, not a general accuracy percentage or production benchmark. See `evidence.json` for expected/actual results and captured responses.

- Six relational chatbot cases matched the oracle: PostgreSQL all-status total $30,200 / 240 orders; delivered total $23,695; October $11,255 / 90 orders; top product Espresso Maker / $14,400; MySQL all-status total $116,550 / 180 orders; delivered total $94,125.
- A follow-up, “Now only delivered orders, please,” initially failed during provider cooldown, then correctly returned 185 orders / $23,695 in the original PostgreSQL conversation. Automatic selection with an explicit coffee/PostgreSQL name also chose connection 61 correctly.
- Twelve relational Insights revenue/count checks matched across all-time and October windows. Mongo invoice counts and monetary sums matched in both windows: 160 / $16,300 all-time and 60 / $6,140 in October.
- Empty January 2027 windows returned zero transaction counts on all three engines, with monetary values unavailable rather than fabricated nonzero results.
- After indexing, dashboard RAG answered all three factual document questions correctly: coffee 30 days / $100; solar Net 45 / inverter warranty 5 years; Orbit 1 business hour / ORBIT-SLA-81. Their grounding classifications failed separately.
- Real SQL and RAG SSE streams produced 113 and 93 nonempty chunk events, respectively, ending with `done=true`, message IDs, and completion metadata. First observed event / completion were approximately 4.266s / 4.578s for SQL and 2.641s / 4.406s for RAG. These are two samples, not percentile or load measurements.
- Standalone widget handshake returned 200 for localhost and 403 for an unapproved origin. Its two known-answer questions failed fact retrieval despite published, ready documents.
- Frontend production build passed: 2,893 modules, nonfatal large-bundle warning. New Python utility files passed compilation. FastAPI startup and authenticated HTTP requests succeeded.

## Findings and reproduction

### DQA-01 — P1: market share is rendered as historical growth

On the coffee dashboard, **Top Market** shows current 12,400, previous 8,788.094, change +41.1%. The backend's 41.1 is East's share of all sales, not growth. `BusinessInsightsPage.tsx:561–575` treats arbitrary `trend_pct` as period growth and derives `previous = current / (1 + trend_pct/100)`. There is no observed prior-period value supporting 8,788.094. Only render growth when the metric supplies genuine comparable current/prior periods and semantic metadata.

### DQA-02 — P1: a dimension filter mixes scoped and unscoped metrics

Request `GET /api/insights/generate/61?filter_column=orders.region&filter_value=East&refresh=true`. Revenue correctly becomes $12,400 and orders 60. Active customers remains **24 instead of 6**, units sold **600 instead of 240**, and the displayed CLV uses all 24 customers. Apply the same filter through verified joins, or mark unsupported metrics unavailable; never combine different populations in a single filtered dashboard.

### DQA-03 — P1: standalone widget misses explicitly published facts

After documents 3–5 report ready, ask the demo widget for coffee returns/free shipping or Orbit's high-priority response target. Both return an apology claiming the documents lack that information. The coffee policy explicitly says 30 days and $100; Orbit explicitly says 1 business hour. Returned snippets are the wrong sections (reporting definitions/cancellation). This is a retrieval/context assembly failure, not a missing-document condition. Verify widget retrieval and parent/child expansion independently of dashboard RAG.

### DQA-04 — P1: correct document answers are labeled unsupported/contradicted

Ask each of the three ready-document questions listed above. Answers contain the correct facts, but all three responses have `grounding_status=unsupported`, coverage 0.0, and citations marked false. The browser labels the correct coffee answer **Evidence Contradicted**. The verifier says “30” or “100” is missing from evidence while attaching the coffee *reporting definitions* chunk rather than its returns/shipping section. It also evaluates numbered follow-up suggestions as factual claims. Match claims to the actual evidence used for synthesis; exclude navigation, citations, and suggestions from factual coverage. See `chat-grounding.png` and claim reasons in `evidence.json`.

### DQA-05 — P1: MongoDB is connectable but chatbot execution uses SQLAlchemy SQL

Mongo connection/table discovery and deterministic Insights work. Explicit dashboard chat questions for connection 63 fail. A retry after cooldown returned **“Can't load plugin: sqlalchemy.dialects:mongodb”**. The chat route `backend/routers/chat.py:1078–1158` sends database queries to `generate_sql_from_nl` / `execute_safe_sql`, including Mongo selections. Add a bounded, read-only Mongo query route, or explicitly state unsupported capability before generation; do not present this as a bad connection or generic provider problem.

### DQA-06 — P2: valid relational metrics get an “insufficient data” summary

All-time coffee and solar responses contain correct available gross revenue/order counts, yet the executive summary says **“Insufficient data to generate a reliable business summary.”** The browser visibly reproduces this on coffee. `db_pipeline_service.py:2709–2759` rejects a valid `total_revenue` metric when `fallback_revenue_column` is absent/incompatible, then fails to find another recognized monetary metric. The prompt sanitizer at lines 201–229 also removes metric names/units, yielding summaries such as “Key metrics recorded are 8490.0, 90, and 4480.0.” Preserve safe semantic labels and summarize verified available values. See `insights.png`.

### DQA-07 — P2: region rankings display false zero values

Coffee Insights' Revenue by Region chart correctly includes East $12,400, but **Top Performers Ranking** renders East/South/North/West as 0.00. Chart points use `val`; ranking code reads only `value || count || 0` at `BusinessInsightsPage.tsx:594–596,1484–1503`. Use the declared chart `yKey` and null-aware numeric extraction. A missing key must not silently become zero.

### DQA-08 — P2: nonexistent selected table returns a different table's success

Request `GET /api/insights/generate/61?table=missing_table&refresh=true`. It returns HTTP 200, `success=true`, `selected_table=missing_table`, and **customers** metrics (24 rows) rather than rejecting the table. Validate scope against the discovered catalog and return a clear validation/not-found result. This reproduces a previously documented acceptance gap; it is not newly introduced here.

### DQA-09 — P2: provider fallback and unknown-answer behavior are inconsistent

One SQL follow-up failed with a cooldown/provider-unreachable explanation and succeeded on retry. An unknown loyalty-conversion question initially correctly abstained, but after indexing another run returned unrelated document excerpts instead of stating the fact is unspecified. The guaranteed-2027-revenue question similarly produced excerpts rather than a direct uncertainty statement. Fallback must preserve the requested intent, clearly identify unavailable generation, and explicitly abstain when evidence cannot answer.

### DQA-10 — P2: Mongo Insights lacks paid-revenue business semantics

Mongo Insights correctly reports $16,300 as a generic monetary sum, including cancelled invoices, but exposes no paid-revenue KPI even though status is available and the document defines paid revenue as **$14,736**. This is a capability/semantic gap rather than a wrong arithmetic result: a billing dashboard needs an explicit gross-billed/paid distinction. Do not relabel the all-status sum as collected revenue or infer MRR/churn from this dataset.

## Recovery and repeat runs

The app and demo servers were left running. Open `http://localhost:5173`. Runtime files, generated secrets, database data directories, and the pre-cleanup SQLite backup are in ignored `_qa_tmp/demo-runtime/`. These are local development assets, not a deployment package.

From the repository root, restart existing demo servers without reseeding:

```powershell
.\.venv\Scripts\python.exe tests/manual/provision_demo_sources.py --start
```

Start the backend from `backend/` with the local-demo setting in that shell:

```powershell
$env:ALLOW_PRIVATE_DB_HOSTS='true'
$env:EMBEDDING_WARMUP='false'
..\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Start the frontend from the repository root with `npm run dev`. Existing listeners must be reused or stopped before starting duplicates. The app stores generated connection secrets encrypted; no login password belongs in source files.

The setup utility is intentionally single-use per runtime and refuses reseeding an existing runtime. The live runner's `setup` action is also intended only for an empty, prepared account; rerunning it can duplicate connections/documents. Other runner actions require an unexpired local API session. Run `python tests/manual/evaluate_demo_acceptance.py` to reevaluate captured evidence without contacting providers.

## Scope limits and next action

This task did not fix production code, switch Planner V2 on, change user passwords, drop external databases, or claim load/security certification. The baseline/default planner was tested. Three text documents do not establish PDF/OCR extraction quality. Browser layout was inspected at the available desktop size; responsive/mobile layout, disconnect reclamation under load, multi-worker behavior, and database restart durability remain untested. Generated demo connections currently use isolated demo-server administrator accounts; use dedicated read-only identities before adapting this fixture to any shared environment.

Repair P1 findings first, retain these fixtures as acceptance data, and rerun semantic checks, widget known-answer tests, and filtered population checks before sign-off.
