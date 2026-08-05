# Backend Exploration & Architectural Analysis Report

**Target Scope**: `d:\dataspeak\backend`  
**Explorer Agent**: `explorer_backend`  
**Date**: 2026-08-04  

---

## 1. Observation

### 1.1 Backend Directory & File Structure
Direct filesystem listing of `d:\dataspeak\backend`:
- `main.py` (App initialization, CORS middleware, router registration)
- `database.py` (SQLAlchemy engine, session factory, `get_db` dependency)
- `models.py` (SQLAlchemy ORM data models)
- `schemas.py` (Pydantic validation schemas)
- `auth.py` (Password hashing via bcrypt, JWT token issuance)
- `dependencies.py` (OAuth2 bearer authentication dependency `get_current_user`)
- `requirements.txt` (Python dependencies list)
- `.env.example` (Template file for environment configuration)
- `routers/`:
  - `users.py` (Authentication, user registration, login, OAuth, password reset, OTP verification)
  - `tenants.py` (Tenant profile management, organization member listing & invite handling)
  - `databases.py` (External database connection management, table introspection, test connections)
  - `api_keys.py` (API Key CRUD operations and key revocation)
  - `chatbot_config.py` (Chatbot widget configuration settings)
  - `documents.py` (RAG document upload, text/table/image extraction, chunking, FAISS vector indexing, vector search)
- `test_backend_rag.py`, `test_rag.py`, `scratch/` (RAG test suites and diagnostic utilities)

---

### 1.2 Complete API Endpoint Mapping

| HTTP Method | Route Path | Controller Handler File & Function | Request Body / Query Schema | Response Schema / Type | Auth / Role Required |
|---|---|---|---|---|---|
| `GET` | `/` | `main.py:read_root` | None | `dict` (`{"message": ...}`) | Public |
| **Auth & Users (`routers/users.py`)** | | | | | |
| `POST` | `/api/auth/register` | `users.py:register_user` | `schemas.UserCreate` | `schemas.UserResponse` | Public |
| `POST` | `/api/auth/login` | `users.py:login_user` | `schemas.UserLogin` | `schemas.Token` | Public (Requires verified email) |
| `POST` | `/api/auth/github-login` | `users.py:github_login` | `schemas.GithubLoginRequest` | `schemas.Token` | Public |
| `POST` | `/api/auth/change-password` | `users.py:change_password` | `schemas.UserChangePassword` | `dict` (`{"message": ...}`) | Authenticated User |
| `GET` | `/api/auth/me` | `users.py:get_user_me` | None | `schemas.UserResponse` | Authenticated User |
| `POST` | `/api/auth/forgot-password` | `users.py:forgot_password` | `schemas.ForgotPasswordRequest` | `dict` (`{"message": ...}`) | Public |
| `POST` | `/api/auth/verify-otp` | `users.py:verify_otp` | `schemas.VerifyOTPRequest` | `dict` (`{"message": ...}`) | Public |
| `POST` | `/api/auth/reset-password` | `users.py:reset_password` | `schemas.ResetPasswordRequest` | `dict` (`{"message": ...}`) | Public |
| `POST` | `/api/auth/verify-email` | `users.py:verify_email` | `schemas.EmailVerificationRequest` | `dict` (`{"message": ...}`) | Public |
| `POST` | `/api/auth/resend-verification` | `users.py:resend_verification` | `schemas.ResendVerificationRequest` | `dict` (`{"message": ...}`) | Public |
| **Tenant Management (`routers/tenants.py`)** | | | | | |
| `GET` | `/api/tenant/current` | `tenants.py:get_current_tenant` | None | `schemas.TenantResponse` | Authenticated User |
| `PUT` | `/api/tenant/current` | `tenants.py:update_current_tenant` | `schemas.TenantUpdate` | `schemas.TenantResponse` | Authenticated User |
| `GET` | `/api/tenant/members` | `tenants.py:get_tenant_members` | None | `List[schemas.UserResponse]` | Authenticated User |
| `POST` | `/api/tenant/invite` | `tenants.py:invite_member` | `schemas.InviteCreate` | `schemas.InviteResponse` | Authenticated User |
| `DELETE` | `/api/tenant/members/{user_id}` | `tenants.py:remove_tenant_member` | Path `user_id: int` | `dict` (`{"message": ...}`) | Admin Role Only |
| **Database Connections (`routers/databases.py`)** | | | | | |
| `GET` | `/api/databases` | `databases.py:get_databases` | None | `List[schemas.DatabaseConnectionResponse]` | Authenticated User (Admin gets all, others filtered by access) |
| `POST` | `/api/databases` | `databases.py:add_database` | `schemas.DatabaseConnectionCreate` | `schemas.DatabaseConnectionResponse` | Authenticated User |
| `DELETE` | `/api/databases/{db_id}` | `databases.py:delete_database` | Path `db_id: int` | `dict` (`{"message": ...}`) | Authenticated User |
| `GET` | `/api/databases/{db_id}/tables` | `databases.py:get_database_tables` | Path `db_id: int` | `List[str]` | Authenticated User |
| `GET` | `/api/databases/{db_id}/tables/{table_name}/data` | `databases.py:get_table_data` | Path `db_id: int`, `table_name: str` | `List[dict]` | Authenticated User |
| `GET` | `/api/databases/{db_id}/stats` | `databases.py:get_database_stats` | Path `db_id: int` | `dict` (`{"table_count": int, "tables": list}`) | Authenticated User |
| `GET` | `/api/databases/{db_id}/tables/{table_name}/stats` | `databases.py:get_table_stats` | Path `db_id: int`, `table_name: str` | `dict` (`{"rows": int, "columns": int}`) | Authenticated User |
| `POST` | `/api/databases/test` | `databases.py:test_database_connection` | `schemas.DatabaseConnectionCreate` | `dict` (`{"status": str, "message": str}`) | Authenticated User |
| **API Keys (`routers/api_keys.py`)** | | | | | |
| `GET` | `/api/keys` | `api_keys.py:get_api_keys` | None | `List[schemas.ApiKeyResponse]` | Authenticated User |
| `POST` | `/api/keys` | `api_keys.py:create_api_key` | `schemas.ApiKeyCreate` | `schemas.ApiKeyResponse` | Authenticated User |
| `PUT` | `/api/keys/{key_id}/revoke` | `api_keys.py:revoke_api_key` | Path `key_id: int` | `schemas.ApiKeyResponse` | Authenticated User |
| `DELETE` | `/api/keys/{key_id}` | `api_keys.py:delete_api_key` | Path `key_id: int` | `dict` (`{"message": ...}`) | Authenticated User |
| **Chatbot Config (`routers/chatbot_config.py`)** | | | | | |
| `GET` | `/api/chatbot-config` | `chatbot_config.py:get_chatbot_config` | None | `schemas.ChatbotConfigResponse` | Authenticated User |
| `PUT` | `/api/chatbot-config` | `chatbot_config.py:update_chatbot_config` | `schemas.ChatbotConfigCreate` | `schemas.ChatbotConfigResponse` | Authenticated User |
| **Document Processing & RAG (`routers/documents.py`)** | | | | | |
| `GET` | `/api/documents` | `documents.py:get_documents` | None | `List[schemas.DocumentResponse]` | Authenticated User |
| `POST` | `/api/documents/upload` | `documents.py:upload_document` | Form: `file`, `chunk_size`, `chunk_overlap`, `chunking_strategy` | `schemas.DocumentResponse` | Authenticated User |
| `DELETE` | `/api/documents/{document_id}` | `documents.py:delete_document` | Path `document_id: int` | `dict` (`{"message": ...}`) | Authenticated User |
| `GET` | `/api/documents/{document_id}/chunks` | `documents.py:get_document_chunks` | Path `document_id: int` | `dict` (`{"chunks": list}`) | Authenticated User |
| `POST` | `/api/documents/search` | `documents.py:search_documents` | `schemas.SearchQuery` (`{"query": str}`) | `dict` (`{"results": list}`) | Authenticated User |

---

### 1.3 Service Modules Inspection

1. **NL-to-SQL Engine**: **ABSENT**. There are no endpoints, service functions, or modules for natural language query parsing, SQL generation, schema grounding, SQL syntax validation, or natural language answer generation from query results.
2. **DB Connector & Connection Management**: Present in `database.py` and `routers/databases.py`. Uses SQLAlchemy to interact with the application database (SQLite default `sqlite:///./app.db`, PostgreSQL supported). Introspects external databases (`postgresql`, `mysql`, `mariadb`) dynamically via `create_engine`.
3. **ERD Generator**: **ABSENT**. There are no backend routes or services for extracting database foreign key constraint relationships or outputting ERD graph data (Mermaid.js/D3 data).
4. **Dashboard Service**: **ABSENT**. No backend endpoints or logic exist for dashboard metric aggregation, widget layout saving, or automated chart data generation.
5. **Export Services**: **ABSENT**. No service modules or endpoints exist for exporting dataset query results or report documents into PDF, CSV, or Excel formats.
6. **AI/LLM Integration & RAG**: Present in `routers/documents.py`.
   - Text parsing: `pdfplumber` for PDF pages and markdown table formatting via `table_to_markdown()`.
   - Vision parsing: PyMuPDF (`fitz`) image extraction paired with direct HTTP requests to Google Gemini 2.5 Flash API (`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent`).
   - Chunking: `langchain_text_splitters.RecursiveCharacterTextSplitter`.
   - Embeddings: `langchain_huggingface.HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")`.
   - Vector Store: `langchain_community.vectorstores.FAISS` stored locally per tenant at `vector_store/tenant_{tenant_id}`.
   - Relational Chunks: Dual-written into `document_chunks` table via `models.DocumentChunk`.
   - Vector Search: Custom FAISS index search converting embeddings and returning top 5 matches with scores. **Note**: Search returns raw context chunks; no LLM answer synthesis step is executed on top of the search results.

---

### 1.4 Database Connection Logic: Live Connections vs Mock/Fallback Data

In `routers/databases.py`:
- Function `get_connection_url(db_conn)` maps `db_type`:
  - `postgresql` -> `postgresql://username:password@host/database`
  - `mysql` / `mariadb` -> `mysql+pymysql://username:password@host/database`
  - `sqlite` -> `sqlite:///database` (only in the first definition, line 18)
- **Live Database Connection Behavior**:
  - For PostgreSQL and MySQL/MariaDB, `create_engine` establishes live connections to fetch table names (`inspector.get_table_names()`), sample data (`SELECT * FROM {table_name} LIMIT 100`), and table statistics (`SELECT COUNT(*)`).
- **Mock & Fallback Behavior**:
  - For any unsupported/simulated database engine type (e.g. MongoDB, Snowflake, Oracle, SQL Server):
    - `get_database_tables` returns mock array: `["users", "orders", "products", "customers"]` (line 116).
    - `get_table_data` returns mock array of 3 dictionary items (line 143).
    - `get_database_stats` returns static mock metrics for 4 tables with hardcoded row counts (line 176).
    - `test_database_connection` sleeps for 1 second and returns `{"status": "success", "message": f"Connection simulated for {db_conn.db_type}"}` (line 254).

---

### 1.5 Configuration & Environment Variables Audit

| Environment Variable | Code Location (`os.getenv`) | Default Value in Code | Present in `.env.example`? | Notes / Status |
|---|---|---|---|---|
| `DATABASE_URL` | `database.py:9` | `"sqlite:///./app.db"` | **Yes** (`sqlite:///./app.db`) | App metadata database |
| `SECRET_KEY` | `auth.py:6` | `"super_secret_key_for_fyp"` | **Yes** (`your_super_secret_key...`) | JWT signing secret |
| `ALGORITHM` | `auth.py:7` | `"HS256"` | **Yes** (`HS256`) | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `auth.py:8` | `1440` (60 * 24) | **Yes** (`30`) | Default mismatch (1440 in code vs 30 in .env.example) |
| `GEMINI_API_KEY` | `routers/documents.py:85` | `None` | **NO** | Required for PDF Image OCR / Vision parsing |
| `GITHUB_CLIENT_ID` | `routers/users.py:129` | `"Ov23liPRgons4RlFv7FU"` | **NO** | **HARDCODED CREDENTIAL IN CODE** |
| `GITHUB_CLIENT_SECRET` | `routers/users.py:130` | `"067e59b3c050792898954f727be0dbdbfc5c590a"` | **NO** | **HARDCODED CREDENTIAL IN CODE** |
| `EMAIL_USER` | `routers/users.py:226` | `None` | **NO** | SMTP Username for verification OTP emails |
| `EMAIL_PASS` | `routers/users.py:227` | `None` | **NO** | SMTP Password for verification OTP emails |
| `EMAIL_HOST` | `routers/users.py:228` | `"smtp.gmail.com"` | **NO** | SMTP Server host |
| `EMAIL_PORT` | `routers/users.py:229` | `587` | **NO** | SMTP Server port |
| `RESEND_API_KEY` | `routers/users.py:257` | `None` | **NO** | Fallback email delivery service API key |

---

## 2. Logic Chain

1. **Observation**: `main.py` imports routers `users`, `tenants`, `databases`, `api_keys`, `chatbot_config`, `documents`. Grep search across `d:\dataspeak\backend` reveals no files or endpoints matching `nl2sql`, `query`, `erd`, `dashboard`, or `export`.
   - **Reasoning**: The backend scope is currently limited to Authentication, Tenant/Member Management, Database Connection Metadata, API Keys, Chatbot Config, and Document RAG. The core analytical engine capabilities (NL-to-SQL, ERD visualization, Dashboard builder, Export generation) have not been implemented in Python.

2. **Observation**: In `routers/databases.py`, `get_connection_url` is defined twice (lines 13-20 and lines 92-97).
   - **Reasoning**: In Python, defining a function twice in the same module silently overwrites the first definition. The second definition lacks the `sqlite` clause. As a result, any Database Connection configured as `sqlite` will have `get_connection_url` return `None`, causing SQLite database connections to fall through to mock data in table listing and table preview endpoints!

3. **Observation**: In `routers/databases.py:150`, `get_table_data` creates a new SQLAlchemy engine via `create_engine(connection_url)` on every request, executes `conn.execute(text(f"SELECT * FROM {table_name} LIMIT 100"))`, and never calls `engine.dispose()` or uses `NullPool`.
   - **Reasoning**: Every invocation of table previews allocates engine resources and connection pools without disposing of them. Under load or repeated inspection, this will exhaust socket handles or connection pools on external database hosts. Furthermore, using f-string interpolation for `table_name` introduces SQL injection vulnerability if `table_name` is manipulated.

4. **Observation**: `routers/users.py` lines 129-130 fallback to hardcoded GitHub client ID `"Ov23liPRgons4RlFv7FU"` and secret `"067e59b3c050792898954f727be0dbdbfc5c590a"`.
   - **Reasoning**: Storing secret keys directly in application source code poses a high security risk if committed to revision control.

5. **Observation**: `.env.example` contains only 4 environment variables, whereas `os.getenv()` calls across the backend reference 12 unique environment variables.
   - **Reasoning**: Developers or deployers relying on `.env.example` will miss critical configuration parameters (`GEMINI_API_KEY`, `EMAIL_USER`, `EMAIL_PASS`, `RESEND_API_KEY`, `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`), leading to silent fallbacks or runtime failures during document parsing or email sending.

---

## 3. Caveats

- **No Active Server Runtime Interrogation**: Analysis was conducted via read-only source code inspection and static analysis without launching `uvicorn main:app` or sending live HTTP requests.
- **Frontend-to-Backend Contract Differences**: This report covers backend endpoints as defined in `backend/routers/`. Cross-referencing with frontend API service calls (`src/services/api.ts`) is required to confirm whether frontend routes expect additional unbuilt backend endpoints.

---

## 4. Conclusion

The DataSpeakAI Python backend (`d:\dataspeak\backend`) provides a functional base for user authentication, tenant management, database connection registration, API key management, and document-based RAG indexing. 

However, critical functional gaps exist:
1. **Missing Core Features**: NL-to-SQL query generation, ERD diagram generation, Dashboard analytics, and Export services are entirely unbuilt in the backend.
2. **LLM Synthesis Gap**: Document search returns raw FAISS text chunks without feeding them into an LLM to generate natural language answers.
3. **Code Defect (Function Overwriting)**: `routers/databases.py` overwrites `get_connection_url`, breaking live SQLite inspection and forcing fallback to mock data.
4. **Security & Connection Leak Risks**: Hardcoded GitHub secrets in `users.py`, unencrypted database passwords in `models.py`, SQL string formatting in `databases.py`, and undisposed database engines.
5. **Environment Configuration Drift**: 8 environment variables used in code are absent from `.env.example`.

---

## 5. Verification Method

To independently verify these findings:

1. **Verify API Endpoints & Function Overwriting**:
   - Inspect `d:\dataspeak\backend\routers\databases.py` lines 13-20 and lines 92-97 to observe the duplicate `def get_connection_url` definition.
2. **Verify Hardcoded Secrets**:
   - Inspect `d:\dataspeak\backend\routers\users.py` lines 129-130.
3. **Verify Environment Variables**:
   - Compare `d:\dataspeak\backend\.env.example` against `os.getenv` occurrences in `d:\dataspeak\backend\auth.py`, `database.py`, `routers/users.py`, and `routers/documents.py`.
4. **Verify Missing Core Services**:
   - Search `d:\dataspeak\backend` for any references to `nl2sql`, `erd`, `dashboard`, or `export`.
