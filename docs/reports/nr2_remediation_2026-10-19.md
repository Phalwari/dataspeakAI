# NR-2 remediation and verification — 2026-10-19

The seven reproduced readiness defects are repaired and the full offline verification passes. The project is ready to proceed with the NR-3 infrastructure and verification prerequisites. Formal production acceptance remains open until those prerequisites are exercised.

## Scope and implementation

The original audit reviewed `6764c57`. During remediation, workspace HEAD advanced externally to `c3fb304`, incorporating the initial fixes and separate database connector work. Those changes were retained. Verification completed before publication; the user subsequently authorized committing and pushing the tested history to remote `main`. No deployment was performed.

| Finding | Implemented behavior | Direct evidence |
|---|---|---|
| F01: invented growth | Dataframe trends require a date column and explicit non-overlapping prior/current intervals. Naive dates use the declared business timezone; unavailable/invalid periods return no percentage. No row-order split or row-count scaling. | Undated, zero-baseline, invalid-overlap and Asia/Karachi boundary tests |
| F02: timeout waits for training | All AutoML work, including clustering, runs in a spawned process. Deadline expiry terminates and joins it. Capacity is two jobs per API process; estimator/native thread concurrency is limited. Busy/timeout/error results have no invented model score. | Real sleeping subprocess exceeds a one-second budget, is terminated, and leaves no live child; actual model-training tests |
| F03: temporal/group leakage | Temporal outer split and validation both respect chronology, including repeated timestamps. Grouped outer split and GroupKFold keep repeated entities apart. Missing timestamps/group configuration fail explicitly. | Fold-inspection tests, outer split checks and grouped entity fixtures |
| F04: repeated holdout evaluation | Candidate selection uses training-only validation. Only the winner is fitted and evaluated on the final holdout. Non-winners have validation-labelled scores and `test_score: null`. | Holdout evaluator is called once; model-selection regression tests |
| F05: grounding initialization crash | Embedding initialization and inference both return typed unverified grounding on failure. Common explicit insufficient-information responses are recognized as abstentions. | Initialization outage, inference outage, contradiction and abstention tests |
| F06: swallowed ingestion failures | Processing/reindex errors persist failure and propagate to the task system. Transport/timeout/operational errors receive bounded exponential retries; permanent errors do not. The durable original survives retries. Background reindex uses its own session. | Real failing task wrapper, retry exhaustion/backoff, concurrent retry and retained-source tests |
| F07: dense/sparse lost updates | The merged dense generation is the common manifest for BM25. Publication rechecks tombstones inside the lock. Lock contention fails closed. Duplicate jobs serialize per document. Delete publishes a new generation; pinned generations are retained. | Overlapping stale snapshots, repeated publication, empty index, failed staging, file-lock contention and concurrent retry tests |

Additional repair: `stream_chat_response` explicitly closes its upstream async generator on every exit, including disconnect, so provider cleanup runs immediately. The disabled-SQL widget response uses the RAG route contract and never calls SQL generation/execution.

Index reconciliation now compares a persisted chunk/version/content-hash manifest with SQL, repairs missing pointers or drift by publishing a fresh generation under the publication lock, and defers rebuilding while ingestion is active. Orphan and previous published generations are reported and retained for reader safety. Re-embedding selects the document's actual model and indexes child chunks consistently with initial ingestion.

Older tests now use valid authorized-user fixtures and current error/prompt contracts; role enforcement was not relaxed. The original seven probes are part of normal test discovery in `tests/test_nr2_readiness.py`, expanded to 16 regression checks. The original manual path remains a compatibility entry point.

## Verification

| Check | Result |
|---|---|
| Frontend tests | 35 passed across 3 files |
| Frontend production build | Passed, 32.63 seconds; main JS 1,685.96 kB / 462.65 kB gzip; existing size warning remains |
| FYP acceptance | 19 passed in the final lifecycle group, additional to the default backend suite |
| New complete workflow benchmark | 50/50 cases passed: 15 SQL, 15 RAG, 5 abstention, 10 contradictory completions, 5 untrusted-source cases |
| Stream lifecycle measurements | 30/30 runs passed: 15 saved completions and 15 disconnects with upstream closure and no saved completion |
| Full default backend suite | 656 passed, 4 explicitly skipped, 0 failures/errors; all 55 test files covered across three disjoint groups |
| Remediation regressions | 16 passed, included in the backend total |
| Dependency consistency | `pip check` passed |

The final core group contains 590 passes and four skips; migrations contains 32 passes; lifecycle contains 34 default-suite passes plus 19 FYP passes. These are separate isolated processes covering the complete default suite, not a claim of one monolithic pytest invocation. Machine-readable counts, coverage and XML hashes are recorded in `nr2_evidence_2026-10-19/verification-summary.json`.

The new workflow benchmark uses real application handlers, SQLite execution, ORM persistence, ingestion, FAISS/BM25, retrieval and citation verification. The controlled provider emits SQL, extracts facts from the actual synthesis prompt, or injects deliberately wrong numbers. Token-hash embeddings and the provider are explicit test doubles. The benchmark is an orchestration/contract test, not a semantic model quality estimate. Untrusted-source cases check prompt boundaries and the controlled provider's behavior; they do not establish immunity to every prompt injection.

Structured measured outputs are in `docs/reports/nr2_evidence_2026-10-19/`. Stream timing excludes HTTP transport, real provider latency and real billing. No before/after percentage or token-cost saving is claimed. Historical reports now carry evidence corrections.

## Reproduction

Use Python 3.11 with the installed backend dependencies and an already-downloaded `all-MiniLM-L6-v2` HuggingFace cache for the existing semantic-model tests. The launcher disables model downloads and external provider HTTP traffic, removes provider credentials, and creates isolated SQL/storage paths. Its main guard supports spawned training workers on Windows.

```powershell
$env:AUDIT_HF_HOME = Join-Path $env:USERPROFILE '.cache\huggingface'
$groups = Get-Content .agents/nr2-remediation/final_test_groups.json -Raw | ConvertFrom-Json
& .\backend\venv\Scripts\python.exe .\.agents\nr2-remediation\run_verification.py final_core @($groups.core)
& .\backend\venv\Scripts\python.exe .\.agents\nr2-remediation\run_verification.py final_migrations @($groups.migrations)
& .\backend\venv\Scripts\python.exe .\.agents\nr2-remediation\run_verification.py lifecycle_final @($groups.lifecycle) tests/manual/fyp_core_verification.py
$env:NR2_EVIDENCE_DIR = Join-Path $PWD 'docs\reports\nr2_evidence_2026-10-19'
& .\backend\venv\Scripts\python.exe .\.agents\nr2-remediation\run_verification.py workflow tests/test_nr2_workflow_evidence.py
cmd.exe /c "npm test"
cmd.exe /c "npm run build"
```

Four external PostgreSQL/MySQL tests added in `c3fb304` require `RUN_LIVE_DATABASE_TESTS=1` and an authorized network environment. They are explicitly skipped in the offline default suite; skipped integrations are not counted as passing. MongoDB driver doubles remain in the default suite.

## Release boundary and next phase

NR-3.1-A remains the named prerequisite for production ingestion integration: shared durable object/index storage, Redis/Celery service availability, worker replacement/restart, backup and restore evidence. Current local file locks coordinate processes sharing the same filesystem, not unrelated hosts. Historical index generations are retained for reader safety; capacity/retention operations must account for that growth.

No live Gemini/Groq quality comparison, real database-network integration, production load or disaster-recovery rehearsal was established here. Browser end-to-end coverage, explicit TypeScript checks and bundle splitting remain NR-3.2-A work. The repository's formal production release gate must remain pending until those dependencies are exercised. Phase NR-4/NR-5 product work should follow the NR1 release gate.
