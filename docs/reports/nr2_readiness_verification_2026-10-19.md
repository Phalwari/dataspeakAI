# NR-2 readiness verification — 2026-10-19

**Decision: NR-2 is not ready for completion sign-off.** The current frontend and focused FYP checks pass, but seven additional acceptance probes reproduce unresolved correctness/reliability defects. Continue corrective work in NR-2. The independent NR-3.1-A infrastructure work and NR-3.2-A verification work may start according to their dependencies; this is not permission to skip the NR-2 gate or begin NR-4/NR-5 features.

## Scope and baseline

- Reviewed revision: `6764c5713ef8c49bd4ea55d27e36e56ca02f4f46` on `main`, `D:\dataspeakAI`. Working tree was clean at the start.
- Reviewed repository instructions, current changelog/tracker, next-release pathway, prior FYP evidence, migration/runbook documentation, and relevant implementation/test spans through Graft.
- Interpreted "until NR 2" as **Phase NR-2**, the currently selected phase. The roadmap separately uses **Release NR2** for Phase NR-4; that later release is not complete.
- No application implementation was changed. Added opt-in verification tests and audit records. Existing databases, uploads and indexes were not used as test fixtures.
- Runtime: Python 3.11.9 from `backend/venv`, pytest 9.1.1, Node 24.16.0, Vite 6.3.5, Vitest 3.0.7.

## Verification results

| Check | Current observation |
|---|---|
| Tracked Python source syntax | 178 files parsed successfully; no syntax errors |
| Installed backend dependency consistency | `pip check`: no broken requirements |
| Frontend unit tests | **35 passed**, 3 test files |
| Frontend production build | **Passed** in 47.52 seconds; main JS 1,684.50 kB (462.26 kB gzip), bundle-size warning |
| Existing FYP acceptance probes | **19 passed**, 23 warnings, 12.11 seconds |
| Additional NR-2 acceptance probes | **7 failed**, 23 warnings, 7.59 seconds; failures deliberately remain visible, without `xfail` |
| Full existing backend suite, fresh offline model cache | **620 passed, 10 failed, 5 setup errors**, 28 warnings, 893.92 seconds; 635 collected |
| NR-2 suites rerun with existing local embedding cache | **44 passed**, 23 warnings, 344.26 seconds; ingestion, evaluation, grounding and metric-parity suites |
| NR-0 / NR-1 suites within the full run | **37 / 44 passed**, respectively; no failures/errors |
| Existing AutoML suite within the full run | **18 passed**; the additional probes expose gaps outside its assertions |
| Production startup behavior | Existing tests for empty/drifted schema rejection and current-schema startup without DDL/seeding all passed |

Initial frontend invocations were blocked by the execution sandbox's Windows `realpath` permissions. Re-running the same commands with the required file access produced the passing results above. These initial permission errors are not source-code failures. Vite's build is not a standalone TypeScript type check: the current project has no tracked `tsconfig` and no explicit type-check script.

### Full-suite failure triage

The first full run used a fresh, empty HuggingFace cache with downloads disabled. Two ingestion assertions and five evaluation setup errors were caused by the missing embedding model. Rerunning the four affected NR-2 suites against the already-downloaded local model produced **44 passes** without changing application code or tests. These seven outcomes are an environment/test-isolation issue, not seven additional application defects. The cached rerun is not a second complete-project run and does not replace its result.

Eight other failures remain from the full run:

| Tests | Observation and interpretation |
|---|---|
| `test_phase1_5d_readiness_gate.py`: `test_task1_apply_mapping_rejects_missing_or_blank_aggregation`, `test_task5_legacy_generators_not_invoked_during_live_dashboard`, `test_task9_query_error_does_not_leak_credentials_or_raw_driver` | Query/write requests stop at 403 instead of the intended 200/400 assertion. The synthetic users omit an allowed role; current query permission requires Admin/Developer/Business Owner. Reconcile fixtures with the permission contract so the tests exercise their intended behavior. |
| `test_stage_c2_verification.py::test_non_streaming_chat_json_keys_unit` | Fixture uses lowercase `admin` and lacks initialized active flags; current policy rejects it with 403. This does not establish that authorized dashboard chat is broken. |
| `test_phase2_1_hardening_regression.py::test_sec02_ast_fail_closed_parsing`, `test_phase2_security_qa_followups.py::test_sec02_malformed_unparseable_sql_fails_closed` | Malformed SQL is rejected; the tests expect different error wording (`parsing failed` versus `SQL parse error`). Keep the rejection assertion and align the error contract. |
| `test_phase7_2_2_hierarchical_chunking.py::test_build_grounded_rag_context_parent_deduplication` | Parent content and child citations pass preceding assertions. The final assertion counts obsolete `(Parent Context)` text; the implementation now uses `<parent_section>`. Update the test to verify content deduplication under the current prompt format. |
| `test_phase2_stage_b_chat_widget.py::test_sql_disabled_never_executes_sql` | The SQL-disabled request returns `query_type="sql"` where the test expects `rag`. Resolve the response contract and verify execution-call counts. This assertion alone does **not** demonstrate unauthorized SQL execution. |

No failing expectations were weakened or marked expected failures in this audit. The normal suite still needs a clean, reproducible run with current fixtures/contracts before sign-off.

## Reproduced findings

### F01 — P1: Missing dates still produce invented period growth

**Source:** [automl_service.py:1446](../../backend/services/automl_service.py#L1446), [KPI use:1596](../../backend/services/automl_service.py#L1596). **Tasks:** NR-2.1-A-T05/T06.

With undated revenue rows `[1, 1, 10, 10]`, `compute_period_trend` reports `+900.0%`, status `ok`. It treats the first and second halves of arbitrary row order as prior/current periods; the KPI presentation consumes that result. Eliminating the old aggregate-versus-mean formula did not establish real business-period comparisons. Return an unavailable comparison without valid periods and use explicit date boundaries/timezone when periods are available.

**Probe:** `test_undated_rows_do_not_invent_period_growth`.

### F02 — P1: The AutoML timeout does not bound caller latency

**Source:** [automl_service.py:527](../../backend/services/automl_service.py#L527). **Task:** NR-2.1-B-T07.

`future.result(timeout=...)` runs inside a `ThreadPoolExecutor` context manager. On timeout, context exit waits for the running work before control reaches the timeout handler. A one-second budget with a controlled 2.5-second fitting operation returned after **2.55 seconds**. An indefinitely blocked fit can keep the caller blocked. Use independently managed, bounded execution with a real termination/cancellation policy, including clustering fits.

**Probe:** `test_training_budget_releases_caller`.

### F03 — P1: Temporal model selection still trains validation folds on future rows

**Source:** [automl_service.py:412](../../backend/services/automl_service.py#L412), [fold selection:518](../../backend/services/automl_service.py#L518), [TrainingSpecification:566](../../backend/schemas.py#L566). **Tasks:** NR-2.1-B-T03/T04.

Setting both `split_strategy="temporal"` and `validation_strategy="time_series"` produces a temporal outer holdout, but candidate selection still passes an integer to `cross_val_score`. The probe observed training row 47 included when validation started at row 0 or 16. This violates chronology during model selection. Respect the requested validation strategy and test actual fold membership. Grouped entity splitting is also absent from the current specification and partitioning branches; its completion is not established.

**Probe:** `test_temporal_validation_never_trains_on_future_rows`.

### F04 — P2: The final holdout is evaluated for every candidate

**Source:** [automl_service.py:415](../../backend/services/automl_service.py#L415), [candidate loop:520](../../backend/services/automl_service.py#L520). **Task:** NR-2.1-B-T05.

All three regression candidates predict/evaluate the final holdout before the winner is selected. The probe counted **three holdout evaluations**. Selection does use CV scores, so this does not demonstrate selection directly optimizing the holdout; it does contradict the stated single final evaluation contract and exposes every candidate's final test score. Select using training/validation results, then evaluate only the chosen model on the final holdout.

**Probe:** `test_only_selected_candidate_uses_final_holdout`.

### F05 — P2: Embedding initialization failures bypass the unverified result contract

**Source:** [citation_service.py:346](../../backend/services/citation_service.py#L346). **Task:** NR-2.2-A-T01.

The embedding loader runs outside the exception handler that creates an `unverified` response. Injecting an initialization outage raises `RuntimeError` instead of returning an unverified status/reason. Existing tests cover a supplied model failing during embedding, which is a different boundary. Include model resolution/initialization inside the failure contract and verify the dashboard/widget callers preserve it.

**Probe:** `test_embedding_initialization_failure_returns_unverified`.

### F06 — P1: Failed ingestion can complete the worker task successfully

**Source:** [documents.py:283](../../backend/routers/documents.py#L283), [task_queue.py:13](../../backend/ingestion/task_queue.py#L13). **Tasks:** NR-2.2-B-T03/T04.

`process_document` catches an extraction exception, marks the document Failed, and returns normally. The Celery wrapper retries only raised exceptions. A controlled transient extractor timeout passed through the real wrapper without an exception/retry. The document records failure while the task system sees a normal return. Preserve the document failure record, classify transient/permanent failures, and propagate the appropriate failure to the worker's bounded retry policy.

**Probe:** `test_failed_ingestion_is_not_reported_as_successful_worker_job`.

### F07 — P1: Publication locking does not preserve consistent dense/sparse contents

**Source:** [documents.py:228](../../backend/routers/documents.py#L228), [generation_manager.py:123](../../backend/search/generation_manager.py#L123), [BM25 construction:171](../../backend/search/generation_manager.py#L171). **Task:** NR-2.2-B-T07.

BM25's SQL snapshot is prepared before taking the publication lock, and excludes other documents still Processing. Two overlapping workers can prepare snapshots containing only their own new document. When those snapshots publish sequentially, FAISS merges into the newest active dense generation, while BM25 rebuilds from the stale caller snapshot. The deterministic interleaving probe ends with dense document IDs `{1, 2}` but sparse IDs `{2}`. Build/revalidate both index contents against the same generation manifest inside serialization, and test simultaneous uploads and retry/delete interleavings.

**Probe:** `test_serialized_publication_preserves_dense_sparse_membership`. This exercises the actual FAISS/BM25 publisher with offline embeddings and a reproducible overlapping-job ordering; it is not a multi-host load test.

## Remaining evidence and tracking gaps

- The formal [NR-2 delivery gate](../../todo.md#phase-nr-2-delivery-gate-verification-check-pending) is pending. There are **43 unique NR-2 task IDs** overall, **34 unique archived task blocks**, and **27 checked task blocks still in the active area**. Eighteen task IDs occur in both active/archive areas. Nine NR-2.2-B tasks are missing from the archive (T01–T04 and T06–T10). Do not archive/reconfirm the disputed completions until the corresponding acceptance evidence passes.
- Production ingestion still depends on **NR-3.1-A**. Local retained files and file locks do not verify durability across API/worker instance replacement, shared object storage, broker failures, or restore.
- The 25-case evaluation runner checks supplied `ground_truth_answer` text against supplied `context_evidence` ([example](../../tests/test_nr2_eval_benchmark.py#L53)). It is useful grounding regression coverage, but does not independently execute the SQL/RAG/hybrid question workflow or establish end-to-end retrieval/routing accuracy.
- The [streaming performance report](nr2_streaming_performance.md) claims specific TTFT percentiles and savings, but does not provide a reproducible load command, sample count, model/provider configuration, or linked raw observations. Those performance numbers were **not independently verified** in this audit.
- CI currently installs backend dependencies and builds the frontend, with test steps commented out. Explicit types, locked backend installs, real database/Redis integration, browser flows and smaller bundles belong to **NR-3.2-A**. These are next-phase work, not proof that NR-2's reproduced defects can be waived.
- Repository guidance still describes 10 MVP ORM models, while the NR-0 reconciliation document describes 46. Treat those historical maps as orientation; reconcile documentation against current source during NR-3.2-B.

## Recommended execution order

1. Fix F01–F07 against their existing task IDs, keeping these probes as regression coverage. Reopen the relevant completion claims rather than declaring the entire phase verified.
2. Run the full isolated backend suite, FYP probes, new readiness probes, frontend tests/build and required integration checks. Separate environment/test-fixture failures from application failures.
3. Start independent **NR-3.1-A storage/workers/recovery** and **NR-3.2-A CI/type/integration checks** once their explicit prerequisites are verified. Use these to finish the cross-phase ingestion acceptance gate.
4. Reconcile the tracker/archive and obtain NR-2 sign-off from current passing evidence. Complete NR-3 and the NR1 release gate before NR-4/NR-5 product features.

## Reproduction and evidence

From the repository root:

```powershell
& .\backend\venv\Scripts\python.exe .\.agents\nr2-readiness\run_verification.py full
& .\backend\venv\Scripts\python.exe .\.agents\nr2-readiness\run_verification.py manual
& .\backend\venv\Scripts\python.exe .\.agents\nr2-readiness\run_verification.py audit tests/manual/nr2_readiness_verification.py
$env:AUDIT_HF_HOME = Join-Path $env:USERPROFILE '.cache\huggingface'
& .\backend\venv\Scripts\python.exe .\.agents\nr2-readiness\run_verification.py nr2-cached tests/test_nr2_2_b_ingestion_lifecycle.py tests/test_nr2_eval_benchmark.py tests/test_nr2_grounding_verification.py tests/test_nr2_metric_parity.py
cmd.exe /c "npm test"
cmd.exe /c "npm run build"
& .\backend\venv\Scripts\python.exe -m pip check
```

The audit runner removes provider credentials before imports, disables dotenv loading/model downloads and external provider HTTP transports, changes to fresh isolated storage, and invokes existing tests without replacing their assertions. `AUDIT_HF_HOME` only selects an existing model cache; it does not enable downloads. JUnit evidence is stored in `.agents/nr2-readiness/full-results.xml`, `manual-results.xml`, `audit-results.xml`, and `nr2-cached-results.xml`. The added probe file is opt-in, outside default `test_*.py` discovery, and contains no expected-failure masking. It is not a claim that every project path has been exhaustively verified. Live provider quality, production load, browser end-to-end behavior and real PostgreSQL/MySQL/Redis recovery were not established by these offline checks.
