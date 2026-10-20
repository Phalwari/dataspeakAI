# Insights operations: LLM synthesis

## Runtime limits

The synchronous generation facade uses a 20-second overall deadline by default (`LLM_HTTP_TIMEOUT_SECONDS`). Each provider request receives at most the remaining time. The Insights pipeline waits at most 30 seconds for synthesis and anomaly detection (`LLM_PIPELINE_BUDGET_SECONDS`); an LLM timeout returns a deterministic summary. Both settings accept positive finite seconds. `LLM_RETRY_BACKOFF_SECONDS` defaults to 1 second and also accepts zero. Invalid values use these defaults and log only the setting name.

A timeout, transport error, or provider 5xx permits one outer retry if the deadline has enough time for backoff. HTTP 429/quota rotates to another configured key or provider in the existing gateway chain and has no outer retry. Failure categories exposed to the pipeline are `Timeout`, `Quota`, `ProviderError`, and `InvalidResponse`; raw provider responses and exception text are not part of the summary.

The response's `executive_summary.source` is `llm` for a valid generated summary and `deterministic_fallback` otherwise. Fallbacks include `llm_error` with the category. The UI and HTML export label a deterministic fallback as “Auto-generated summary (AI unavailable)”. The fallback uses computed numeric aggregates when available and states that data is insufficient otherwise.

The executor stops waiting after its budget, but Python cannot kill a running worker thread. An in-flight provider request can continue in the background until its own timeout. Monitor worker and memory use before increasing concurrency or deploying to multiple processes. The cache is process-local, as documented in `KNOWN_ISSUES.md`.

## Verification

`tests/test_insights_llm_resilience.py` runs offline with mocked provider HTTP and a temporary SQLite data source. It checks deadline behavior, one retry, quota rotation, fallback attribution, invalid responses, and safe log fields. Live Gemini, Groq, and Ollama behavior, production environment overrides, browser rendering, and concurrent-user capacity are **not verified by execution**.
