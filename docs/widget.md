# DataSpeakAI — Standalone Chatbot Widget & Embedding Guide

## 1. Overview & Architecture

The **DataSpeakAI Standalone Chatbot Widget** (Phase 2) is an embeddable, enterprise-grade AI chatbot that can be integrated into any web application or CMS with a single `<script>` tag.

### Core Architectural Principles
* **Ultra-Lightweight Bundle:** Built with Vite and Preact in an isolated IIFE configuration (`vite.widget.config.ts`), producing a single bundle under **32 kB (11.92 kB gzipped)** with zero external runtime dependencies.
* **Non-Invasive Shadow DOM Isolation:** Mounted inside an open Shadow DOM root (`attachShadow({ mode: 'open' })`). Host application styles (e.g. Tailwind, Bootstrap, CSS resets) cannot penetrate or distort widget sizing, typography, or layouts. All dimensions use absolute `px` measurements to resist host `html { font-size: 62.5% }` root scaling.
* **Synchronous Config Capture:** Host attributes are read synchronously from `document.currentScript` at top-level initialization before DOM readiness.
* **Multi-Tenant Security & Separation:** Publishable keys (`pk_live_...`) identify tenant accounts without exposing secret API keys or database connection credentials. Origin allowlists, short-lived HMAC session tokens, and deterministic SQL guardrails protect all data access.

---

## 2. Embedding Options

### Option A: Standalone Shadow DOM Script Tag (Recommended)
Paste this snippet before the closing `</body>` tag of your HTML pages:

```html
<!-- DataSpeakAI Standalone Chatbot Widget -->
<script 
  src="https://api.dataspeak.ai/widget.js" 
  data-key="pk_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" 
  async
></script>
```

#### Optional Host Script Attributes:
| Attribute | Type | Default | Description |
|---|---|---|---|
| `data-key` | `string` | **Required** | The tenant's publishable widget key (`pk_live_...`). |
| `data-api` | `string` | Script Origin | Custom API endpoint origin (e.g. `https://api.dataspeak.ai`). |
| `data-position` | `"bottom-right"` \| `"bottom-left"` | Server Config | Overrides widget launcher dock position. |
| `data-title` | `string` | Server Config | Overrides widget window title in the header. |

---

### Option B: Fallback Sandboxed Iframe
For environments with strict legacy restrictions or CMS platforms that forbid custom script execution:

```html
<iframe 
  src="https://api.dataspeak.ai/embed/pk_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" 
  width="400" 
  height="640" 
  style="border:none; border-radius:16px; box-shadow:0 10px 25px rgba(0,0,0,0.15);" 
  allow="clipboard-write"
></iframe>
```

---

## 3. Host Content Security Policy (CSP)

If your website enforces a strict Content Security Policy (CSP), configure your HTTP response headers to whitelist the DataSpeakAI API domain:

```http
Content-Security-Policy: 
  script-src 'self' https://api.dataspeak.ai; 
  connect-src 'self' https://api.dataspeak.ai;
```

* `script-src`: Permits the browser to download `/widget.js`.
* `connect-src`: Permits the widget to perform `/api/widget/session` handshakes and `/api/widget/chat` SSE streams over POST.

---

## 4. Multi-Layer Security Model

```
┌────────────────────────────────────────────────────────┐
│ Host Website Browser (Visitor)                        │
└──────────────────────────┬─────────────────────────────┘
                           │ 1. POST /api/widget/session
                           │    (Origin header + pk_live_...)
                           ▼
┌────────────────────────────────────────────────────────┐
│ DataSpeakAI Gateway                                   │
│  - Check WidgetKey (enabled, unrevoked)                │
│  - Match Origin against allowed_origins allowlist     │
│  - Rate Limiter (Token bucket + Monthly cap check)    │
│  - Issue short-lived HMAC-signed session token (60m)  │
└──────────────────────────┬─────────────────────────────┘
                           │ 2. POST /api/widget/chat
                           │    (session_token + query)
                           ▼
┌────────────────────────────────────────────────────────┐
│ Chat Pipeline & Deterministic Security Guardrails      │
│  - Extract tenant_id from cryptographically verified  │
│    HMAC claims (NEVER from client request body)        │
│  - Check allow_sql flag:                              │
│      * False: Strict RAG (FAISS + MiniLM embeddings)   │
│      * True: Read-only SELECT on allowed_database_ids  │
│        (Blocks DDL/DML, multi-statement, masks PII)    │
└────────────────────────────────────────────────────────┘
```

### 4.1 Publishable Key vs. Secret Key
* **Secret API Keys (`sk_live_...`):** For backend-to-backend API integrations. Must never be exposed to browser clients.
* **Publishable Widget Keys (`pk_live_...`):** Designed for public frontend distribution. Bound to an origin allowlist and HMAC session tokens.

### 4.2 Origin Allowlisting
* **Strict Verification:** The server checks the `Origin` header (falling back to `Referer` origin).
* **Wildcards Forbidden:** Wildcard origins (`*`) are disallowed by design to prevent cross-site embedding abuse.
* **Empty Allowlist = Deny All:** If `allowed_origins` is empty, all session handshake requests receive `403 Forbidden`.

### 4.3 HMAC Session Tokens
* When a visitor opens the host website, `/api/widget/session` validates the origin and issues a short-lived HMAC token (signed using SHA-256 with the server's `WIDGET_HMAC_SECRET`).
* The token binds the `tenant_id`, `origin`, and `conversation_id`.
* The `tenant_id` for chat processing is **strictly derived from the verified token claims**, never from request body parameters or prompt text.

### 4.4 Rate Limiting & Concurrency Controls (SEC-10)
Rate limit values are unified across server code, documentation, and endpoint enforcement, and are configurable via environment variables with documented defaults:
* **Token Bucket Enforcement (Configurable Defaults):**
  * **Per Widget Key:** 60 requests/minute (Env: `WIDGET_RATE_LIMIT_KEY_PER_MIN=60`).
  * **Per Client IP:** 30 requests/minute (Env: `WIDGET_RATE_LIMIT_IP_PER_MIN=30`).
  * **Per Session Token:** 20 requests/minute (Env: `WIDGET_RATE_LIMIT_SESSION_PER_MIN=20`).
  * HTTP 429 response includes standard `Retry-After: <seconds>` header.
* **Concurrent Stream Cap:** Maximum 5 simultaneous SSE streams per widget key (Env: `WIDGET_MAX_CONCURRENT_STREAMS=5`) to prevent ASGI connection pool exhaustion.
* **Key-Scoped Monthly Message Cap (SEC-04):** Enforces message quotas per `widget_key_id`. Only admitted and successfully processed requests are recorded in `QueryLog` and counted toward the monthly quota; blocked requests (rate limited, origin rejected, or guardrail blocked) do **not** consume billable quota.

### 4.5 Reverse Proxy Security & IP Extraction (SEC-03)
To prevent IP rate limit bypass via spoofed `X-Forwarded-For` headers:
* When `TRUSTED_PROXIES` is unset or empty, the backend relies strictly on `request.client.host`. Any `X-Forwarded-For` headers supplied by direct clients are ignored.
* When `TRUSTED_PROXIES` is configured (comma-separated list of IPs or CIDRs, e.g. `127.0.0.1, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16`), the server verifies that the direct client is a trusted reverse proxy before parsing `X-Forwarded-For`.
* In a multi-proxy chain, the server scans backwards from right to left, selecting the right-most untrusted IP address as the client identifier.
* **Storage Backends & Multi-Worker Caveat:**
  * **In-Memory Default:** The rate limiter defaults to an in-process sliding token bucket.
  * **Multi-Worker Caveat:** When running in multi-worker or containerized production environments (e.g. Docker, Kubernetes, Uvicorn/Gunicorn with multiple workers), in-memory limits are isolated per process, potentially multiplying limits by worker count.
  * **Redis Distributed Backend (`REDIS_URL`):** Configure the `REDIS_URL` environment variable (e.g., `redis://localhost:6379/0` or `rediss://...`). When set, DataSpeakAI automatically switches to distributed Redis sorted sets for global atomic rate limiting and stream locks across all worker nodes. If Redis is temporarily unreachable, the system gracefully degrades to local in-memory limiting without dropping requests.

---

## 5. Data-Access & SQL Security Guardrails

### 5.1 Safe Default: RAG-Only Mode
By default, `allow_sql = False` for all widget keys.
* Queries from the widget only search through indexed knowledge base documents using semantic search and HuggingFace embeddings (`all-MiniLM-L6-v2`).
* SQL database connections are completely inaccessible.

### 5.2 SQL Mode Guardrails (When Explicitly Opted-In)
When a tenant administrator enables SQL querying for a widget key, the following deterministic security rules are enforced by `services/sql_engine.py`:
1. **Allowed Database IDs:** Queries are restricted exclusively to `allowed_database_ids` configured for that key.
2. **Per-Key Table Allowlist (`allowed_tables`):** All tables referenced in `FROM`, `JOIN`, and `TABLE` clauses are extracted and verified against the key's allowed table whitelist. Disallowed tables or unknown identifiers are rejected before query submission.
3. **Read-Only Connections & Transactions:** Connection engines enforce read-only execution modes (`PRAGMA query_only = ON;` in SQLite, `SET TRANSACTION READ ONLY;` in PostgreSQL/MySQL).
4. **Keyword & Statement Denylist:**
   * DDL/DML statements (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`, `CREATE`, `RENAME`, `PRAGMA`, `CALL`, `COPY`, `LOAD`, `OUTFILE`) are rejected.
   * Multi-statement and stacked queries (`statement1; statement2`) are blocked.
   * Database system catalog queries (`sqlite_master`, `sqlite_sequence`, `information_schema`, `pg_catalog`, `sys.`, `sysobjects`) are prohibited.
   * Comment stripping with token spacing prevents SQL injection via keyword-stitching comments (e.g. `SEL/**/ECT`).
5. **Row Cap & Execution Timeout:** All queries are bounded by a 100-row preview limit (`LIMIT 100`) and a strict 10-second driver execution timeout.
6. **PII Masking:** Columns matching sensitive patterns (`password`, `ssn`, `secret`, `token`, `credit_card`) are masked with `[REDACTED]`.
7. **No Raw Leakage:** Anonymous visitors receive synthesized natural language insights. Raw SQL queries and internal database connection credentials are never returned in widget responses.

> 🔒 **SECURITY RECOMMENDATION FOR SQL-ENABLED KEYS:** While DataSpeakAI deterministically blocks DDL/DML, catalog access, and multi-statements at the application layer, and enforces read-only transaction modes per dialect (SQLite `PRAGMA query_only = ON;`, PostgreSQL `SET TRANSACTION READ ONLY;`, MySQL `SET TRANSACTION READ ONLY;`), **we strongly recommend connecting databases designated for widget keys using a dedicated read-only database user** (e.g. `GRANT SELECT ON specific_tables TO widget_reader;`) at the database engine level for defense-in-depth.

---

## 6. Key Rotation & Grace Period

To rotate a publishable key without disrupting traffic on active host websites:

1. Navigate to **Dashboard > Chatbot Widget > Publishable Key**.
2. Click **Rotate Key**.
3. A new public key (`pk_live_new...`) is generated immediately.
4. **24-Hour Grace Window:** The previous key (`previous_key`) remains valid for 24 hours (`previous_key_expires_at`).
5. Update your host website `<script>` tag with the new key within the 24-hour window.

---

## 7. Build & Maintenance Commands

* **Build Standalone Widget:**
  ```bash
  npm run build:widget
  ```
  Generates `dist/widget.js` and synchronizes to `public/widget.js`.
* **Run Widget Test Suite:**
  ```bash
  pytest tests/test_phase2_widget_keys_sessions.py tests/test_phase2_stage_b_chat_widget.py
  ```
* **Build React SPA Dashboard:**
  ```bash
  npm run build
  ```
