## 2026-08-05T22:25:24Z
You are worker_m4 (teamwork_preview_worker) for DataSpeakAI.
Your working directory is d:\dataspeak\.agents\worker_m4\.
You must read ORIGINAL_REQUEST.md (at d:\dataspeak\.agents\ORIGINAL_REQUEST.md) and PROJECT.md (at d:\dataspeak\PROJECT.md) before starting work.

Your task is to implement Milestone 4: Dashboard Live Data Binding & Analytics.

Instructions:
1. Add `QueryLog` ORM model in `backend/models.py`:
   - Table name: `query_logs`
   - Fields: `id` (Integer PK), `tenant_id` (Integer FK to tenants.id, nullable=True), `user_id` (Integer FK to users.id, nullable=True), `database_id` (Integer FK to database_connections.id, nullable=True), `natural_query` (Text), `generated_sql` (Text), `status` (String(50)), `execution_time_ms` (Float), `rows_returned` (Integer), `tokens_used` (Integer), `error_message` (Text), `created_at` (DateTime, default utcnow).
   - Update `backend/routers/query.py` or wherever queries execute to write a `QueryLog` record on query execution.

2. Create `backend/routers/analytics.py`:
   - Implement endpoints:
     - `GET /api/analytics/overview` -> returns overview metrics (total_queries, connected_databases, uploaded_documents, api_calls_today, subscription_plan, query_data timeline, database_activity, recent_queries) calculated dynamically from DB (QueryLog, DatabaseConnection, Document, Tenant).
     - `GET /api/analytics/trends` -> returns time-series analytics (daily query volume, average latency, success rates).
     - `GET /api/logs` -> returns paginated logs (`items`, `total`, `page`, `limit`, `total_queries`, `successful`, `failed`, `avg_response_time_ms`) from `QueryLog`.
     - `GET /api/usage` -> returns resource & token usage data for current tenant.
     - `GET /api/admin/stats` -> requires `get_current_admin_user`, returns platform-wide admin stats (total tenants, total users, total queries, DB count, document count).
     - `GET /api/admin/tenants` -> requires `get_current_admin_user`, returns list of tenants with user count, status, created_at.
   - Mount router in `backend/main.py`.

3. Bind Frontend Pages to Backend Endpoints:
   - `DashboardOverview.tsx`: Fetch live data from `GET /api/analytics/overview`.
   - `AnalyticsPage.tsx`: Fetch live data from `GET /api/analytics/trends`.
   - `LogsPage.tsx`: Fetch live data from `GET /api/logs`.
   - `UsagePage.tsx`: Fetch live data from `GET /api/usage`.
   - `AdminPanel.tsx`: Fetch live data from `GET /api/admin/stats` and `GET /api/admin/tenants`.
   - Use `VITE_API_BASE_URL` from `@/app/config/api` or `import.meta.env.VITE_API_BASE_URL` for API requests. Ensure authorization headers (Bearer token) are sent where appropriate. Ensure graceful fallback or empty state handling if backend returns empty lists.

4. Verification:
   - Run `python -c "import backend.main"` to ensure backend imports cleanly.
   - Run `npm run build` to ensure zero React/TypeScript compilation errors.
   - Include test/verification output in your `handoff.md` in `d:\dataspeak\.agents\worker_m4\handoff.md`.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

When finished, write your handoff report to `d:\dataspeak\.agents\worker_m4\handoff.md` and send a message back to parent orchestrator.
