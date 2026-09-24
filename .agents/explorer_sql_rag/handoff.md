# 5-Component Handoff Report: NL-to-SQL Query Engine & RAG Answer Synthesis

**Agent:** explorer_sql_rag  
**Working Directory:** `d:\dataspeak\.agents\explorer_sql_rag\`  
**Date:** 2026-08-05  

---

## 1. Observation

### 1.1 Codebase & File Inspection Findings

1. **Backend Router Declarations (`backend/main.py`)**:
   - `main.py` lines 5 & 25-30 currently mount routers for `users`, `tenants`, `databases`, `api_keys`, `chatbot_config`, `documents`.
   - **Missing Router**: No `/api/query` endpoint or router is mounted for natural language SQL query processing.

2. **Database Introspection & Connection Handling (`backend/routers/databases.py`)**:
   - `get_connection_url` (lines 13–20 & 92–97) formats connection strings for `postgresql`, `mysql`/`mariadb`, and `sqlite`.
   - `get_database_tables` (lines 99–123) and `get_table_data` (lines 125–157) fetch table names and raw data (up to 100 rows).
   - **Missing Component**: No schema introspection utility exists to extract column names, data types, primary keys, and foreign keys into a structured context string formatted for an LLM prompt.

3. **Backend Services (`backend/services/`)**:
   - **Missing Directory & Service**: The directory `backend/services/` does not exist. `backend/services/sql_engine.py` is entirely missing.

4. **Gemini 2.5 Flash API Pattern (`backend/scratch/test_gemini.py` & `backend/routers/documents.py`)**:
   - `test_gemini.py` lines 33–56 and `documents.py` lines 101–119 demonstrate the REST endpoint pattern for Google Gemini 2.5 Flash:
     - Endpoint: `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}`
     - Request Header: `{"Content-Type": "application/json"}`
     - Request Payload: `{"contents": [{"parts": [{"text": "<prompt>"}]}]}`
     - Response Extraction: `res_data["candidates"][0]["content"]["parts"][0]["text"]`

5. **Document Search & FAISS Retrieval (`backend/routers/documents.py`)**:
   - `search_documents` (lines 350–401) executes FAISS vector similarity search against `vector_store/tenant_{tenant_id}` using `HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")`.
   - Returns raw chunk matches: `{"results": [{"content": "...", "metadata": {...}, "score": 0.12}]}`.
   - **Missing Component**: Does not send retrieved chunks to Gemini 2.5 Flash for natural language answer synthesis or generate inline source citations.

6. **Backend Schemas (`backend/schemas.py`)**:
   - `SearchQuery` (lines 144–145) only defines `query: str`.
   - **Missing Schemas**: Lacks `SearchSynthesisResponse`, `NLQueryRequest`, and `NLQueryResponse`.

7. **Frontend Database Explorer (`src/app/pages/dashboard/DatabasesPage.tsx`)**:
   - `DatabasesPage.tsx` lines 437–567 provide a table explorer modal for viewing raw rows.
   - **Missing Component**: Lacks a conversational NL-to-SQL query chat panel, sample query prompts, generated SQL view, and execution results grid.

8. **Frontend Knowledge Base (`src/app/pages/dashboard/KnowledgeBasePage.tsx`)**:
   - `KnowledgeBasePage.tsx` lines 404–464 contain a "Test AI Query" modal rendering raw search chunk cards.
   - **Missing Component**: Lacks a synthesized AI answer view and source citation breakdown.

---

## 2. Logic Chain

From the observations above, the implementation must be structured into two primary modules:

```
[User Request] 
      │
      ├───► 1. Conversational NL-to-SQL Query Engine
      │         │
      │         ├──► Service: backend/services/sql_engine.py
      │         │     ├── Introspect Schema (Tables, Columns, Types, PKs/FKs)
      │         │     ├── Prompt Gemini 2.5 Flash REST API
      │         │     ├── Enforce Read-Only SELECT Guardrails (Regex/AST)
      │         │     └── Execute Safe SQL (LIMIT 100) via SQLAlchemy
      │         │
      │         ├──► Router: backend/routers/query.py (POST /api/query)
      │         │
      │         └──► Frontend: Interactive Chat Panel in DatabasesPage.tsx
      │
      └───► 2. RAG Knowledge Base Answer Synthesis
                │
                ├──► Upgrade Endpoint: POST /api/documents/search (backend/routers/documents.py)
                │     ├── FAISS Semantic Vector Search (k=5 chunks)
                │     ├── Pass Chunks & Query to Gemini 2.5 Flash
                │     ├── Synthesize Natural Language Answer + Citations
                │     └── Graceful Fallback if GEMINI_API_KEY missing
                │
                └──► Frontend: Synthesized Answer + Citations in KnowledgeBasePage.tsx
```

### 2.1 NL-to-SQL Engine Design Logic (`backend/services/sql_engine.py`)

1. **Schema Context Introspection (`get_db_schema_context`)**:
   - Query SQLAlchemy `inspect(engine)` for connected database `db_conn`.
   - Extract table names, column names, column data types, primary keys, and foreign key references.
   - Format into a clean, markdown schema declaration for Gemini context.
2. **Strict Read-Only Guardrails (`validate_read_only_sql`)**:
   - To guarantee zero data modification, incoming generated SQL must pass security checks:
     - Must start with `SELECT` or `WITH` (for CTEs leading to SELECT).
     - Forbidden keywords: `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `CREATE`, `RENAME`, `GRANT`, `REVOKE`, `REPLACE`, `EXEC`, `EXECUTE`, `SHUTDOWN`.
     - Multi-statement prevention: Reject strings containing `;` (except optional trailing semicolon) to eliminate stacked query injection.
3. **Gemini 2.5 Flash Prompting (`generate_sql_from_nl`)**:
   - System prompt provides schema context, target DB dialect (`postgresql`, `mysql`, `sqlite`), and strict instructions to return SQL in ` ```sql ... ``` ` blocks along with a brief explanation.
   - Parses LLM output, extracts raw SQL and natural language explanation.
4. **Safe Query Execution (`execute_safe_sql`)**:
   - Runs query on database engine using `text(sql)` with `LIMIT 100` restriction.
   - Returns `{ columns: [...], rows: [...], row_count: N, execution_time_ms: X }`.

### 2.2 RAG Synthesis Upgrade Logic (`backend/routers/documents.py`)

1. **Retrospect FAISS Search**:
   - Execute similarity search across tenant vector store `vector_store/tenant_{tenant_id}` for query top_k matches.
2. **Context Formatting & Gemini Synthesis**:
   - Build document context snippet concatenating chunk text and source file metadata:
     `[Source 1: document.pdf, Chunk 1] ...`
   - Prompt Gemini 2.5 Flash REST API to answer user query strictly grounded in document context, citing source filenames inline (`[Source: document.pdf]`).
3. **Fallback Handling**:
   - If `GEMINI_API_KEY` is missing or API request fails, set `answer = None` or fallback message while still returning the raw search chunks.

---

## 3. Caveats

1. **Gemini API Key Availability**:
   - If `GEMINI_API_KEY` is not present in `.env`, LLM SQL generation and RAG answer synthesis will fail unless a fallback mechanism is provided. The backend must handle missing key exceptions gracefully and return readable error responses to the frontend.
2. **SQL Dialect Nuances**:
   - Gemini must be explicitly informed of the target database dialect (`postgresql`, `mysql`, `sqlite`) so it generates compatible syntax (e.g., handling double quotes vs backticks for column aliases).
3. **Simulated / Non-Relational Database Types**:
   - For database connections marked as `mongodb` or `firebase` or simulated types, `sql_engine.py` should return mock tabular answers or an informative message stating natural language SQL is designed for relational DBs.
4. **Large Result Sets**:
   - Queries must always enforce `LIMIT 100` at the execution layer to prevent OOM errors on large database tables.

---

## 4. Conclusion & Implementation Specifications

### 4.1 Required Schemas (`backend/schemas.py`)

```python
class NLQueryRequest(BaseModel):
    database_id: int
    query: str

class NLQueryResponse(BaseModel):
    query: str
    generated_sql: str
    explanation: str
    columns: List[str]
    rows: List[dict]
    row_count: int
    execution_time_ms: float
    status: str
    error_detail: Optional[str] = None

class SearchQuery(BaseModel):
    query: str
    top_k: Optional[int] = 5
    synthesize: Optional[bool] = True

class SearchSynthesisResponse(BaseModel):
    query: str
    answer: Optional[str] = None
    results: List[dict]
```

### 4.2 Backend Service File (`backend/services/sql_engine.py`)

Must provide the following core methods:
- `get_db_schema_context(db_conn: models.DatabaseConnection) -> str`
- `validate_read_only_sql(sql_query: str) -> tuple[bool, str]`
- `generate_sql_from_nl(db_conn: models.DatabaseConnection, nl_query: str) -> dict`
- `execute_safe_sql(db_conn: models.DatabaseConnection, sql_query: str, max_rows: int = 100) -> dict`

### 4.3 Query Router (`backend/routers/query.py`)

- Endpoint: `POST /api/query` (or `POST /api/databases/query`)
- Authenticated via `get_current_user` and `get_db`.
- Validates tenant access to `database_id`.
- Calls `sql_engine` methods to return `NLQueryResponse`.
- Registered in `backend/main.py`.

### 4.4 RAG Router Upgrade (`backend/routers/documents.py`)

- `POST /api/documents/search` updated to return `SearchSynthesisResponse`.
- Formats FAISS matches into LLM prompt context and invokes Gemini 2.5 Flash REST API to produce synthesized answer + inline citations.

### 4.5 Frontend Enhancements

1. **`DatabasesPage.tsx`**:
   - Add "AI Query Assistant" tab/modal.
   - Include NL input box, suggested quick queries, generated SQL code block with copy button, query explanation, and results table.
2. **`KnowledgeBasePage.tsx`**:
   - Upgrade "Test AI Query" modal and search results.
   - Render "AI Synthesized Answer" card at top, followed by source chunk reference cards.

---

## 5. Verification Method

To verify the implementation independently once built:

1. **Frontend Build Check**:
   ```powershell
   npm run build
   ```
   Must compile with 0 TypeScript/JSX errors.

2. **Backend Import & Router Check**:
   ```powershell
   python -c "import backend.main; print('Backend loaded successfully')"
   ```
   Must complete without import errors.

3. **NL-to-SQL Guardrail Test Script**:
   Create a test script validating that non-SELECT statements (`DELETE FROM users;`, `DROP TABLE orders;`) are blocked by `validate_read_only_sql`.

4. **API Endpoint Testing**:
   - Test `POST /api/query` with body `{"database_id": 1, "query": "Show all tables"}`.
   - Test `POST /api/documents/search` with body `{"query": "What is DataSpeakAI?"}` and verify `answer` field in JSON response.
