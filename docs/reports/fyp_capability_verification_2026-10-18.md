# DataSpeakAI FYP capability verification

Date: 18 October 2026. Scope: six core capability groups, plus the related embedded-widget privacy boundary. Verification only; application code and the Word document are unchanged.

## Assessment

All six areas contain real implementations. Controlled tests confirm useful working paths, but seven distinct defects remain reproducible. Eight assertions fail because the SQL-cap issue has two cases. These results do not establish an exact overall completion percentage.

| Capability | Evidence | Assessment |
|---|---|---|
| Database understanding | 16 existing ERD backend tests and 9 frontend ERD tests passed. Includes real SQLite reflection, relationships, catalog caching and refresh controls. | Verified in the tested scope. PostgreSQL/MySQL inspectors are mocked; no live server or browser acceptance run. |
| Natural-language SQL | A controlled provider candidate traversed the actual SQL agent, validation, dry-run, execution and dashboard handler. The real result matched an independently computed total of 313,750 over 250 synthetic rows. DELETE was rejected. Eight existing SQL-agent tests passed. | Partial: row caps can be bypassed, and unsupported sources can return example data. Live LLM semantic accuracy is unmeasured. |
| Query routing | Six new cases passed: automatic SQL/document keyword routes, both manual preferences, database-only/no-foreign-asset handling, and a controlled HYBRID classifier response. | Verified for these cases. HYBRID used a provider double; live classification quality was not measured. |
| Conversations | Actual handlers stored user/assistant messages, read them back and renamed a conversation. Existing memory/title suites passed 6 and 5 tests. | Partial: SQL generation lacks prior-question context for follow-ups, although answer synthesis receives history. |
| Answer delivery | Nine backend streaming and eleven frontend SSE-parser tests passed. | Partial: a failed persistence callback still leads to a success completion frame. Widget conversation binding also fails the privacy check below. |
| Document intelligence | Two text documents passed real extraction/chunking/ORM/FAISS/BM25 storage. Parent-child links, retrieval, parent context and isolation from a tenant with no index passed. Existing chunking/grounding/vector suites passed 4 tests each. | Partial: sparse-index source names are overwritten by the newest filename; embedding failure produces positive grounding confidence. Embeddings were offline doubles, not a real MiniLM-quality evaluation. |

## Reproduced issues

| ID | Priority | Observed behavior | Source |
|---|---|---|---|
| FYP-01 | P0 | A permitted public-widget key/origin from the same synthetic tenant obtained a signed session bound to a private dashboard conversation when its ID was supplied. This proves improper binding; no real user messages were accessed. | `backend/routers/widget.py:181`; existing I-02 |
| FYP-02 | P1 | With a maximum of 100, both `SELECT * FROM sales LIMIT 250` and a query with nested `LIMIT 250` returned 250 rows. The no-LIMIT control correctly returned 100. | `backend/services/sql_engine.py:521`; I-08 |
| FYP-03 | P1 | An unsupported synthetic database type without a usable connection URL returned four built-in example people as ordinary results. | `backend/services/sql_engine.py:628`; I-16 |
| FYP-04 | P1 | After storing “What was total sales revenue in January 2026?”, the SQL-generation prompt for “What about the previous month?” included only the new question and schema, omitting the prior question. | `backend/routers/chat.py:469`; `backend/services/sql_agent.py:275`; related NR-4.1-C |
| FYP-05 | P1 | A synthetic embedding outage returned `grounding_confidence=0.7`, `has_low_confidence=False` and no disclaimer. | `backend/services/citation_service.py:128`; I-11 |
| FYP-06 | P1 | After processing `leave_policy.txt`, then `travel_policy.txt`, persisted sparse-index entries for the first document were labelled `travel_policy.txt`. | `backend/routers/documents.py:214`; I-12 |
| FYP-07 | P1 | A persistence callback raised an exception after token generation; the actual stream emitted `done=true` with no error event. | `backend/services/chat_stream.py:165`; I-14 |

Prioritize widget privacy and SQL caps/fallbacks, followed by contextual follow-ups, reliable citation attribution/grounding and explicit stream-save failures. Existing engineering tasks remain unresolved; this audit does not close them.

## Fresh execution evidence

- Python 3.11.9, repository backend virtual environment.
- Existing selected backend suites: **80 passed**, including FastAPI initialization and endpoint checks.
- Final additional probes: **19 total; 11 passed, 8 failed, 0 errors, 0 skipped**, 17 warnings, 7.76 seconds.
- Existing frontend tests: **20 passed in 2 files** (11 SSE, 9 ERD).
- Production frontend build: **passed**, 2,905 modules, 43.72 seconds; large-bundle warning remains.
- Initial combined backend run: 99 total, 91 passed, 8 failed. One attribution test initially received no BM25 hits because the tiny corpus produced zero ranking scores. It was refined to inspect persisted metadata independently of ranking. All 19 probes were rerun; the final failure directly confirms the filename mismatch. Repeated runs are not added together.

Before imports, the launcher creates a temporary working directory and SQLite application database, disables dotenv and embedding warmup, removes provider/database-related environment settings, disables model downloads, and denies external requests/httpx transports. Synthetic doubles are used for generation, embeddings and optional reranking. Actual SQL, ORM, application routing, document processing, FAISS/BM25 and streaming logic are exercised.

No live provider, real MiniLM, PDF-to-answer browser journey, OAuth, email, payment or production database acceptance test was performed. Passing controlled tests is not evidence of arbitrary answer correctness, production readiness, or full module completion.

## Reproduction

Opt-in assertions: `tests/manual/fyp_core_verification.py`. They express desired behavior, have no expected-failure masking, and remain outside default pytest discovery because the implementation gaps are unresolved.

```powershell
& 'D:\dataspeakAI\backend\venv\Scripts\python.exe' 'D:\dataspeakAI\.agents\fyp-verification\run_checks.py'
& 'D:\dataspeakAI\backend\venv\Scripts\python.exe' 'D:\dataspeakAI\.agents\fyp-verification\run_checks.py' --probe-only
cmd.exe /c "npm test -- --reporter=default"
cmd.exe /c "npm run build"
```

Raw evidence: `.agents/fyp-verification/backend-results.xml` (initial combined run) and `.agents/fyp-verification/probe-results.xml` (final added checks). The latter is authoritative for the corrected attribution probe. This report supplements the SDS's earlier 80-pass record; the SDS's unexecuted live functional cases remain Not run. Submission claims must remain qualified until the failing checks are repaired and rerun.
