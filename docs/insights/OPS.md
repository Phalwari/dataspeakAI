# Insights operations: LLM synthesis

## Runtime limits

The synchronous generation facade uses a 20-second overall deadline by default (`LLM_HTTP_TIMEOUT_SECONDS`). Each provider request receives at most the remaining time. The Insights pipeline waits at most 30 seconds for synthesis and anomaly detection (`LLM_PIPELINE_BUDGET_SECONDS`); an LLM timeout returns a deterministic summary. Both settings accept positive finite seconds. `LLM_RETRY_BACKOFF_SECONDS` defaults to 1 second and also accepts zero. Invalid values use these defaults and log only the setting name.

A timeout, transport error, or provider 5xx permits one outer retry if the deadline has enough time for backoff. HTTP 429/quota rotates to another configured key or provider in the existing gateway chain and has no outer retry. Failure categories exposed to the pipeline are `Timeout`, `Quota`, `ProviderError`, and `InvalidResponse`; raw provider responses and exception text are not part of the summary.

The response's `executive_summary.source` is `llm` for a valid generated summary and `deterministic_fallback` otherwise. Fallbacks include `llm_error` with the category. The UI and HTML export label a deterministic fallback as “Auto-generated summary (AI unavailable)”. The fallback uses computed numeric aggregates when available and states that data is insufficient otherwise.

The executor stops waiting after its budget, but Python cannot kill a running worker thread. An in-flight provider request can continue in the background until its own timeout. Monitor worker and memory use before increasing concurrency or deploying to multiple processes. The cache is process-local, as documented in `KNOWN_ISSUES.md`.

## Verification

`tests/test_insights_llm_resilience.py` runs offline with mocked provider HTTP and a temporary SQLite data source. It checks deadline behavior, one retry, quota rotation, fallback attribution, invalid responses, and safe log fields. Live Gemini, Groq, and Ollama behavior, production environment overrides, browser rendering, and concurrent-user capacity are **not verified by execution**.

## Insight action audit

The router reuses the existing `audit_logs` application table. Generate (GET), pipeline (POST), refresh, export, and stream write actions under `insights.*`. Each record carries tenant/user IDs, connection ID, result status (`success`, `fallback`, or `error`), elapsed milliseconds, and only the selected table and normalized date filters. The stream writes `in_progress` before sending data and updates the same record after completion. A malformed table filter is omitted from audit details. Audit write failure returns a generic 503 for non-stream actions; a stream can already have sent data before its final audit update fails.

No new schema migration is needed because this table is already in the application model and initial schema. The audit path is tested against an isolated SQLite application DB. Existing deployed schemas, retention policy, administrative access control to audit rows, interrupted-stream behavior across worker crashes, and production database persistence are **not verified by execution**.

## Generic regression snapshots

`tests/golden/insights/` contains projected structure/status snapshots for orders with statuses, misleading column names, quantity without price, HR/inventory, and fake Mongo nested metadata. The snapshots omit metric values, chart points, source rows, connection details, and generated text. `tests/test_insights_regression_snapshots.py` rebuilds each fixture in temporary SQLite or a fake Mongo client and compares its projection to the committed snapshot. The script below compares a baseline snapshot with a projected snapshot or a full pipeline JSON response, printing only structural and status differences:

```text
python scripts/insights_diff.py BASELINE_JSON CURRENT_JSON
```

A zero exit code means the projected shape matches, and a nonzero code reports differences. The committed snapshots were captured after E1–E3; a historical pre-E execution baseline was not available. They are a regression baseline for future changes, not proof of before/after parity. Chinook was not used as a golden target. Real Mongo nested extraction and non-SQLite database execution are **not verified by execution**.
