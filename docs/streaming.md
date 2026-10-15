# DataSpeakAI — Streaming Architecture & Real-Time Generation Standard

## 1. Overview
DataSpeakAI utilizes Server-Sent Events (SSE) for true token-level response streaming across both the Dashboard conversational playground (`/api/chat`) and the standalone embeddable chat widget (`/api/widget/chat`).

Artificial word splitting and `time.sleep(0.015)` chunking have been completely replaced with native, non-blocking asynchronous streaming from `LLMGateway` (`backend/services/chat_stream.py`).

---

## 2. Event Format Specification
All streaming routes emit UTF-8 formatted Server-Sent Events with `Content-Type: text/event-stream; charset=utf-8` and `Cache-Control: no-cache`.

### Intermediate Token Chunks
Each generated token is pushed immediately as a JSON string payload:
```http
data: {"chunk": " Quarterly", "done": false, "conversation_id": 42}

```
- `chunk` (string): Incremental token text.
- `done` (boolean): `false` during active token generation.
- `conversation_id` (integer): ID of the target conversation session.

### Final Completion Event (`done: true`)
The terminal event carries full session metadata, source citations, and optional executed SQL details:
```http
data: {
  "chunk": "",
  "done": true,
  "conversation_id": 42,
  "message_id": 105,
  "sources": [
    {
      "document_id": 3,
      "document_name": "q3_financials.pdf",
      "snippet": "Gross revenue increased by 14%...",
      "score": 0.89
    }
  ],
  "sql_data": null
}

```

### Sanitized Error Event
If upstream provider generation drops mid-stream after tokens have already been emitted, the stream delivers a sanitized error terminating cleanly with `done: true`:
```http
data: {"chunk": "", "done": true, "error": "AI generation was interrupted due to a temporary service error. Please try again.", "conversation_id": 42}

```
*Note:* Internal stack traces, raw HTTP status codes, provider error payloads, and API keys are strictly redacted.

---

## 3. Streaming Boundaries: What Is & Is Not Streamed

| Query Route | Streamed Components | Non-Streamed Components |
|---|---|---|
| **RAG Knowledge Base** | Synthesized natural-language answer (token-by-token) | Embedding generation, FAISS dense retrieval, BM25 sparse search, and reciprocal rank fusion |
| **NL-to-SQL Relational** | Natural-language query explanation and data summary | AST validation, safe nested SAVEPOINT execution, row fetching, and tabular data serialization |
| **Hybrid Route** | Integrated conversational synthesis | Vector retrieval, SQL execution, table joining |

### Rationale for SQL Path Non-Streaming
Relational database queries must execute deterministically and atomically within the engine-level statement timeout (10.0s) and row preview cap (100 rows). Once executed, the natural-language explanation and analytical interpretation stream token-by-token to the client.

---

## 4. Connection Lifecycle, Disconnection & Slot Management

1. **Client Disconnection Detection:**
   `stream_chat_response` periodically queries `await request.is_disconnected()` prior to yielding tokens.
2. **Immediate Generator Cleanup:**
   When a user clicks **Stop**, closes their browser tab, or cancels navigation, Starlette emits a `GeneratorExit` exception. The generator halts upstream LLM consumption immediately.
3. **Guaranteed Slot Release:**
   In `finally:`, the concurrent stream slot acquired for the publishable widget key (`widget_limiter.acquire_stream(public_key)`) is unconditionally released via `widget_limiter.release_stream(public_key)` whether completed, cancelled, or terminated on error.
4. **Monthly Quota Protection:**
   Assistant `Message` persistence and tenant `QueryLog` metered deduction occur solely in the `on_complete` callback upon successful stream completion. Cancelled partial answers never deduct from tenant quotas.

---

## 5. Failover Policy

- **Before First Token:** If the initial candidate LLM provider fails (e.g. HTTP 429 quota exhaustion or HTTP 403), `LLMGateway` automatically quarantines the key for 60 seconds and fails over to the next candidate key or backup provider (e.g. Groq / Gemini) before output starts.
- **Mid-Stream Drop:** If connection drops mid-stream after the first token has already reached the client, the stream yields a sanitized terminal error event with `done: true` to prevent UI hanging.

---

## 6. Cold Starts & Latency Telemetry (TTFT)

*Measurements conducted in development environment against local SQLite test environment:*

- **First-Call Embedding Cold Start:** ~1200ms – 1800ms (HuggingFace `all-MiniLM-L6-v2` weights loading). Mitigated in production via optional startup warmup (`EMBEDDING_WARMUP=true`).
- **Warm RAG Time-To-First-Token (TTFT):**
  - Dense + Sparse retrieval & fusion: ~45ms – 85ms
  - LLM Gateway TTFT (Gemini 2.5 Flash / Groq LLaMA 3.3): ~280ms – 420ms
  - Total RAG TTFT: **~350ms – 510ms**
- **NL-to-SQL Time-To-First-Token (TTFT):**
  - SQL generation + Dialect execution: ~350ms – 650ms (atomic)
  - Post-execution NL explanation TTFT: **~680ms – 950ms** (due to sequential SQL verification before LLM synthesis)
