# Investigation Report: Dashboard Live Data Binding, Interactive ERD Visualizer & Standalone Chatbot Widget Bundle

## 1. Observation

### 1.1 Static Mock Data in Frontend Dashboard Pages
Direct inspection of frontend components revealed extensive static mock data with zero backend API bindings:

1. **`src/app/pages/dashboard/DashboardOverview.tsx`**:
   - Lines 25–61: `stats` constant hardcodes `Total Queries: "24,567"`, `Connected Databases: "5"`, `Uploaded Documents: "42"`, `API Calls Today: "1,234"`, and `Subscription Plan: "Starter"`.
   - Lines 63–71: `queryData` hardcodes static weekly query volume (`Mon` to `Sun`).
   - Lines 73–77: `databaseActivity` hardcodes `PostgreSQL: 8500`, `MongoDB: 6200`, `Firebase: 4300`.
   - Lines 79–104: `recentQueries` hardcodes 4 static query objects.
   - Zero `useEffect` hooks or `fetch` calls exist in `DashboardOverview.tsx`.

2. **`src/app/pages/dashboard/AnalyticsPage.tsx`**:
   - Lines 37–70: `queryTrendsData`, `topTablesData`, `databaseDistribution`, and `dataGrowthData` hardcode chart data.
   - Lines 74–75: `dateRange` and `database` select states exist but trigger no backend requests.
   - Lines 118–170: Hardcodes KPI values (`Total Records: 1.2M`, `Monthly Growth: +18%`, `Most Queried: Orders`, `Most Active: Sales`).

3. **`src/app/pages/dashboard/LogsPage.tsx`**:
   - Lines 30–102: `logs` constant hardcodes 7 sample query logs.
   - Lines 136–181: Hardcodes log summary stats (`Total Queries: 2,547`, `Successful: 2,431`, `Failed: 116`, `Avg Response: 142ms`).
   - Filter inputs operate only on the client-side static `logs` array.

4. **`src/app/pages/dashboard/UsagePage.tsx`**:
   - Lines 26–49: `usageData`, `databaseTypeData`, `hourlyData` hardcode chart data.
   - Lines 85–130: Hardcodes stats (`Total Queries: 13,200`, `Tokens Used: 472K`, `Databases: 19,000`, `Current Cost: $29`).

5. **`src/app/pages/admin/AdminPanel.tsx`**:
   - Unprotected route: No role-based access control check (anyone can navigate to `/admin`).
   - Lines 44–73: `platformStats` hardcodes `Total Tenants: 1,247`, `Total Queries: 2.4M`, `Active Databases: 3,891`, `System Health: 99.8%`.
   - Lines 75–142: `tenants` hardcodes 6 sample tenant organizations.
   - Lines 144–184: `systemMetrics` and `systemHealth` hardcode CPU/Memory usage and component health statuses.

6. **`src/app/pages/dashboard/AIInsightsPage.tsx`**:
   - Lines 16–131: `insights` constant hardcodes 6 static insight cards.

### 1.2 Database Introspection & Missing ERD Endpoint
- **`backend/routers/databases.py`**:
  - `GET /api/databases`: Returns list of user's tenant database connections.
  - `GET /api/databases/{db_id}/tables`: Introspects table names via SQLAlchemy `inspect(engine).get_table_names()`.
  - `GET /api/databases/{db_id}/tables/{table_name}/data`: Queries `SELECT * FROM {table_name} LIMIT 100`.
  - `GET /api/databases/{db_id}/stats`: Counts tables.
  - **MISSING**: No `/api/databases/{db_id}/erd` endpoint exists for foreign key and primary key introspection.
- **`src/app/pages/dashboard/DatabasesPage.tsx`**:
  - Has a "View Data" modal for previewing table rows (Lines 438–570), but lacks an ERD diagram visualizer component.

### 1.3 Chatbot Widget Embedding Setup
- **`backend/models.py`**: `ChatbotConfig` model exists (lines 86–100) storing `theme_color`, `widget_title`, `greeting_message`, `position`, `welcome_delay`, `max_history`, `sound_enabled`.
- **`backend/routers/chatbot_config.py`**: Exposes `GET /api/chatbot-config` and `PUT /api/chatbot-config` for authenticated users.
- **`src/app/pages/dashboard/ChatbotWidgetPage.tsx`**:
  - Displays configuration controls and embed code snippet (`<script src="https://cdn.omniquery.ai/widget.js"></script>`).
  - Lacks a public endpoint for unauthenticated third-party sites using API keys (`GET /api/chatbot-config/public?api_key=...`).
  - Lacks the compiled standalone script asset `widget.js` and Vite bundling setup.

---

## 2. Logic Chain

1. **Dashboard Live Data Binding**:
   - To replace static mock data across `DashboardOverview.tsx`, `AnalyticsPage.tsx`, `LogsPage.tsx`, `UsagePage.tsx`, and `AdminPanel.tsx`, backend models must track query execution history.
   - Adding a `QueryLog` ORM model in `backend/models.py` (matching `executed_queries` in `Full_Project_Schemas.sql`) allows logging every query processed by the NL-to-SQL or RAG engine.
   - Dynamic endpoints (`/api/analytics/overview`, `/api/analytics/trends`, `/api/logs`, `/api/usage`, `/api/admin/stats`, `/api/admin/tenants`) can aggregate data directly from `QueryLog`, `DatabaseConnection`, `Document`, `User`, and `Tenant` tables.

2. **Interactive ERD Visualizer**:
   - SQLAlchemy's `inspect(engine)` provides `get_pk_constraint(table_name)` and `get_foreign_keys(table_name)`.
   - By creating `GET /api/databases/{db_id}/erd`, backend can return a structured JSON response containing tables, column PK/FK flags, and explicit foreign key relationships (`source_table`, `source_column`, `target_table`, `target_column`).
   - On the frontend, a clean SVG/HTML canvas component embedded in `DatabasesPage.tsx` can render table cards with `PK`/`FK` badges and connecting SVG relationship lines.

3. **Embeddable Chatbot Widget Bundle**:
   - Third-party websites embedding `widget.js` cannot provide user JWT session tokens; they authenticate via an `apiKey` parameter.
   - Backend needs an unauthenticated endpoint `GET /api/chatbot-config/public?api_key=...` to validate the API key and return widget settings.
   - Vite can be configured to build a standalone IIFE library target (`src/widget/index.ts`) outputting `widget.js` to `public/` and FastAPI static assets directory, rendering in a Shadow DOM to avoid host CSS conflicts.

---

## 3. Caveats

- **External Live Databases**: In dev/offline environments without active PostgreSQL/MySQL instances, database introspection endpoints should return structured mock ERD schema & query logs so UI rendering never breaks.
- **Admin Security**: `/admin` route authorization must check `user.role == "Admin"`.

---

## 4. Conclusion & Step-by-Step Implementation Recommendations

### Recommendation 1: Database Model & Router Enhancements for Analytics & Logs
1. **Create `QueryLog` ORM Model** in `backend/models.py`:
   ```python
   class QueryLog(Base):
       __tablename__ = "query_logs"
       id = Column(Integer, primary_key=True, index=True)
       tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
       user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
       database_id = Column(Integer, ForeignKey("database_connections.id"), nullable=True)
       user_question = Column(String, nullable=False)
       generated_query = Column(String, nullable=True)
       status = Column(String, default="success") # success, failed
       execution_time_ms = Column(Float, default=0.0)
       rows_returned = Column(Integer, default=0)
       tokens_used = Column(Integer, default=0)
       error_message = Column(String, nullable=True)
       created_at = Column(DateTime, default=datetime.datetime.utcnow)
   ```

2. **Add Analytics & Logs Router** (`backend/routers/analytics.py`):
   - `GET /api/analytics/overview`: Aggregates total queries, connected DB count, uploaded document count, API calls today, query volume chart data (last 7 days), DB activity breakdown, and recent queries.
   - `GET /api/analytics/trends?period=7d&db_id=all`: Returns total records estimate, query trends line chart, top queried tables, database distribution, and growth data.
   - `GET /api/logs?page=1&limit=20&status=all&db_id=all`: Returns paginated query execution logs with total count, success/failed counts, and average response time.
   - `GET /api/usage?period=7d`: Returns query volume over time, token consumption, hourly activity patterns, and current plan usage.
   - `GET /api/admin/stats` & `GET /api/admin/tenants`: Returns platform-wide tenant counts, query counts, active databases, and tenant organization table (restricted to `role == 'Admin'`).

3. **Bind Frontend Components to Backend APIs**:
   - Update `DashboardOverview.tsx`, `AnalyticsPage.tsx`, `LogsPage.tsx`, `UsagePage.tsx`, `AdminPanel.tsx` with `useEffect` fetch calls and loading skeletons.

### Recommendation 2: Dynamic ERD Endpoint & Visualizer Component
1. **Implement `GET /api/databases/{db_id}/erd`** in `backend/routers/databases.py`:
   - Inspect table names, column PKs via `inspector.get_pk_constraint(table_name)`, and foreign keys via `inspector.get_foreign_keys(table_name)`.
   - Payload format:
     ```json
     {
       "database_id": 1,
       "database_name": "Production DB",
       "tables": [
         {
           "name": "users",
           "columns": [{"name": "id", "type": "INTEGER", "is_primary": true, "is_foreign": false}]
         }
       ],
       "relationships": [
         {"source_table": "orders", "source_column": "user_id", "target_table": "users", "target_column": "id"}
       ]
     }
     ```
2. **Create `ERDVisualizer` React Component**:
   - Add "View ERD" button & modal in `DatabasesPage.tsx`.
   - Draw table cards in a grid and overlay SVG connection paths for foreign key relationships.

### Recommendation 3: Embeddable Standalone Chatbot Widget Bundle (`widget.js`)
1. **Public Config Endpoint**: Add `GET /api/chatbot-config/public?api_key=...` in `backend/routers/chatbot_config.py`.
2. **Widget Source Code**: Create `src/widget/index.ts` that injects Shadow DOM, reads `data-token` or `apiKey`, fetches config, renders floating button and chat modal connecting to `/api/chatbot/chat`.
3. **Vite Bundle Config**: Add `vite.widget.config.ts` to output IIFE build `dist/widget.js` (and `public/widget.js`).
4. **Mount Static Path in FastAPI**:
   ```python
   app.mount("/static", StaticFiles(directory="public"), name="static")
   ```

---

## 5. Verification Method

1. **Backend Verification**:
   ```bash
   python -c "import backend.main"
   ```
2. **Frontend Build Verification**:
   ```bash
   npm run build
   ```
3. **API Inspection**:
   - Verify `/api/analytics/overview`, `/api/databases/{db_id}/erd`, `/api/logs`, and `/api/chatbot-config/public` return valid JSON.
