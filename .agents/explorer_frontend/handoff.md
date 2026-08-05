# DataSpeakAI Frontend UI Codebase Investigation Report

## 1. Observation

### 1.1 Technical Stack & Build Setup
- **Framework**: React 18.3.1 with React Router v7 (`react-router` ^7.13.0) and Vite 6.3.5.
- **Styling**: Tailwind CSS v4 (`@tailwindcss/vite` 4.1.12), Emotion, Tw-Animate, Lucide React icons.
- **UI Components**: Shadcn UI primitives built on Radix UI (`@radix-ui/react-*`), Material UI icons, Recharts for charts, Sonner for toasts.
- **Base API Configuration**: Single entry point `src/app/config/api.ts`:
  ```ts
  export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
  ```
- **Local Dev Proxy**: `proxy.js` proxies `/api`, `/docs`, `/openapi.json` to `http://localhost:8000` (port 9000).

---

### 1.2 Frontend Routes & Navigation Flow
Routes are defined in `src/app/routes.ts` using `createBrowserRouter`:

| Route Path | Page Component | Access Control / Navigation Context | File Path |
|---|---|---|---|
| `/` | `LandingPage` | Public marketing landing page; includes GitHub OAuth code handler (`?code=...`) | `src/app/pages/LandingPage.tsx` |
| `/login` | `LoginPage` | Public auth page (Email/Password & GitHub OAuth button) | `src/app/pages/LoginPage.tsx` |
| `/signup` | `SignupPage` | Public auth page (Company registration / invite token handling) | `src/app/pages/SignupPage.tsx` |
| `/forgot-password` | `ForgotPasswordPage` | Public auth page (3-step OTP password reset) | `src/app/pages/ForgotPasswordPage.tsx` |
| `/verify-email` | `EmailVerificationPage` | Public auth page (6-digit email OTP verification with auto-resend) | `src/app/pages/EmailVerificationPage.tsx` |
| `/dashboard` | `DashboardLayout` | Protected parent layout; sidebar nav + header; checks `localStorage.getItem("token")` | `src/app/components/DashboardLayout.tsx` |
| `/dashboard` (index) | `DashboardOverview` | Sub-route under `/dashboard` | `src/app/pages/dashboard/DashboardOverview.tsx` |
| `/dashboard/databases` | `DatabasesPage` | Sub-route under `/dashboard` | `src/app/pages/dashboard/DatabasesPage.tsx` |
| `/dashboard/knowledge-base` | `KnowledgeBasePage` | Sub-route under `/dashboard` | `src/app/pages/dashboard/KnowledgeBasePage.tsx` |
| `/dashboard/upload-documents` | `UploadDocumentsPage` | Sub-route under `/dashboard` | `src/app/pages/dashboard/UploadDocumentsPage.tsx` |
| `/dashboard/analytics` | `AnalyticsPage` | Sub-route under `/dashboard` | `src/app/pages/dashboard/AnalyticsPage.tsx` |
| `/dashboard/ai-insights` | `AIInsightsPage` | Sub-route under `/dashboard` | `src/app/pages/dashboard/AIInsightsPage.tsx` |
| `/dashboard/api-keys` | `ApiKeysPage` | Sub-route under `/dashboard` | `src/app/pages/dashboard/ApiKeysPage.tsx` |
| `/dashboard/chatbot` | `ChatbotWidgetPage` | Sub-route under `/dashboard` | `src/app/pages/dashboard/ChatbotWidgetPage.tsx` |
| `/dashboard/usage` | `UsagePage` | Sub-route under `/dashboard` | `src/app/pages/dashboard/UsagePage.tsx` |
| `/dashboard/logs` | `LogsPage` | Sub-route under `/dashboard` | `src/app/pages/dashboard/LogsPage.tsx` |
| `/dashboard/settings` | `SettingsPage` | Sub-route under `/dashboard` | `src/app/pages/dashboard/SettingsPage.tsx` |
| `/admin` | `AdminPanel` | Independent platform owner admin dashboard | `src/app/pages/admin/AdminPanel.tsx` |

---

### 1.3 UI Components & Functional Responsibilities

1. **`src/app/components/DashboardLayout.tsx`**:
   - Renders responsive side navigation bar (10 links: Overview, Databases, Knowledge Base, Analytics, AI Insights, API Keys, Chatbot, Usage, Logs, Settings).
   - Authenticates current user on mount (`GET /api/auth/me`), fetches organization details (`GET /api/tenant/current`). Redirects to `/login` if token missing or invalid.
   - User dropdown menu with Profile, Billing, Team navigation and Logout.

2. **`src/app/pages/LandingPage.tsx`**:
   - Marketing overview, feature showcase cards, 4-step workflow, 4 pricing tier cards.
   - Extracts GitHub OAuth authorization code (`?code=...`) from URL and calls `POST /api/auth/github-login`.

3. **`src/app/pages/LoginPage.tsx`**:
   - Form for email and password authentication (`POST /api/auth/login`).
   - If response status is `403` (email unverified), redirects user to `/verify-email?email=...&auto_resend=true`.
   - GitHub OAuth sign-in trigger (`handleGithubLogin`) and OAuth callback handler.

4. **`src/app/pages/SignupPage.tsx`**:
   - Registration form (`POST /api/auth/register`) supporting both new tenant company creation and joining via `invite_token`.
   - On registration success, redirects to `/verify-email?email=...`.

5. **`src/app/pages/ForgotPasswordPage.tsx`**:
   - Multi-step password recovery: Step 1 (`POST /api/auth/forgot-password`), Step 2 (`POST /api/auth/verify-otp`), Step 3 (`POST /api/auth/reset-password`).

6. **`src/app/pages/EmailVerificationPage.tsx`**:
   - 6-digit OTP code verification (`POST /api/auth/verify-email`) and resend verification code (`POST /api/auth/resend-verification`).

7. **`src/app/pages/dashboard/DatabasesPage.tsx`**:
   - Full CRUD & Management interface for database connections.
   - Connects new databases with connection testing (`POST /api/databases/test`, `POST /api/databases`).
   - Displays live stats (`GET /api/databases/{id}/stats`).
   - Interactive Database Explorer modal: lists tables (`GET /api/databases/{id}/tables`), previews table data (`GET /api/databases/{id}/tables/{table}/data`), shows row/col stats (`GET /api/databases/{id}/tables/{table}/stats`).

8. **`src/app/pages/dashboard/KnowledgeBasePage.tsx`**:
   - RAG document management dashboard: document listing with auto-polling every 5s (`GET /api/documents`).
   - Interactive Document Embeddings viewer (`GET /api/documents/{id}/chunks`).
   - Test AI Search Query modal (`POST /api/documents/search`).
   - Document deletion (`DELETE /api/documents/{id}`).

9. **`src/app/pages/dashboard/UploadDocumentsPage.tsx`**:
   - Multi-file drag-and-drop uploader for PDF/DOCX/TXT/CSV files.
   - Sends file uploads with chunk size, overlap, strategy parameters (`POST /api/documents/upload`).

10. **`src/app/pages/dashboard/ApiKeysPage.tsx`**:
    - Manage developer API keys: list (`GET /api/keys`), create (`POST /api/keys`), revoke (`PUT /api/keys/{id}/revoke`), delete (`DELETE /api/keys/{id}`).
    - Key masking/unmasking and clipboard copy functionality.

11. **`src/app/pages/dashboard/ChatbotWidgetPage.tsx`**:
    - Embeddable widget builder: fetch/save theme, greeting, position, title, history limits (`GET` and `PUT /api/chatbot-config`).
    - Live interactive widget preview and HTML embed code generator.

12. **`src/app/pages/dashboard/SettingsPage.tsx`**:
    - Multi-tab configuration:
      - *Company Tab*: View/update company details (`GET` & `PUT /api/tenant/current`).
      - *Team Tab*: List team members (`GET /api/tenant/members`), invite member with database permissions (`POST /api/tenant/invite`), remove member (`DELETE /api/tenant/members/{id}`).
      - *Security Tab*: Password change (`POST /api/auth/change-password`).
      - *Profile / Billing / Notifications Tabs*: Purely static/mock UI.

13. **`src/app/pages/dashboard/DashboardOverview.tsx`** (Mocked):
    - Visual metrics cards, query volume line chart, database activity bar chart, recent query list.

14. **`src/app/pages/dashboard/AnalyticsPage.tsx`** (Mocked):
    - Data growth area chart, query trend line chart, top tables bar chart, database distribution pie chart.

15. **`src/app/pages/dashboard/AIInsightsPage.tsx`** (Mocked):
    - Machine learning recommendations list with confidence scores and sparklines.

16. **`src/app/pages/dashboard/UsagePage.tsx`** (Mocked):
    - Query volume & token consumption charts, hourly activity pattern.

17. **`src/app/pages/dashboard/LogsPage.tsx`** (Mocked):
    - Query execution history table with client-side status filters.

18. **`src/app/pages/admin/AdminPanel.tsx`** (Mocked):
    - Platform administrator metrics, system health list, tenant management table.

---

### 1.4 API Client Calls Inventory

All API calls use the native browser `fetch` API. `axios` is not used anywhere in `src/`.

| # | Endpoint URL | HTTP Method | Header Requirements | Payload Structure | Source File & Line |
|---|---|---|---|---|---|
| 1 | `${API_BASE_URL}/api/auth/github-login` | `POST` | `Content-Type: application/json` | `{ code: string }` | `LandingPage.tsx:178`, `LoginPage.tsx:31` |
| 2 | `${API_BASE_URL}/api/auth/login` | `POST` | `Content-Type: application/json` | `{ email, password }` | `LoginPage.tsx:63` |
| 3 | `${API_BASE_URL}/api/auth/register` | `POST` | `Content-Type: application/json` | `{ email, password, full_name, company_name?, invite_token? }` | `SignupPage.tsx:50` |
| 4 | `${API_BASE_URL}/api/auth/forgot-password` | `POST` | `Content-Type: application/json` | `{ email }` | `ForgotPasswordPage.tsx:30, 79` |
| 5 | `${API_BASE_URL}/api/auth/verify-otp` | `POST` | `Content-Type: application/json` | `{ email, otp_code }` | `ForgotPasswordPage.tsx:107` |
| 6 | `${API_BASE_URL}/api/auth/reset-password` | `POST` | `Content-Type: application/json` | `{ email, otp_code, new_password }` | `ForgotPasswordPage.tsx:134` |
| 7 | `${API_BASE_URL}/api/auth/verify-email` | `POST` | `Content-Type: application/json` | `{ email, otp_code }` | `EmailVerificationPage.tsx:64` |
| 8 | `${API_BASE_URL}/api/auth/resend-verification` | `POST` | `Content-Type: application/json` | `{ email }` | `EmailVerificationPage.tsx:91` |
| 9 | `${API_BASE_URL}/api/auth/me` | `GET` | `Authorization: Bearer <token>` | None | `DashboardLayout.tsx:59` |
| 10 | `${API_BASE_URL}/api/tenant/current` | `GET` | `Authorization: Bearer <token>` | None | `DashboardLayout.tsx:73`, `SettingsPage.tsx:44` |
| 11 | `${API_BASE_URL}/api/tenant/current` | `PUT` | `Authorization: Bearer <token>`, `Content-Type: application/json` | `{ website, industry, address }` | `SettingsPage.tsx:90` |
| 12 | `${API_BASE_URL}/api/tenant/members` | `GET` | `Authorization: Bearer <token>` | None | `SettingsPage.tsx:57` |
| 13 | `${API_BASE_URL}/api/tenant/invite` | `POST` | `Authorization: Bearer <token>`, `Content-Type: application/json` | `{ email, role, database_ids }` | `SettingsPage.tsx:124` |
| 14 | `${API_BASE_URL}/api/tenant/members/${id}` | `DELETE` | `Authorization: Bearer <token>` | None | `SettingsPage.tsx:156` |
| 15 | `${API_BASE_URL}/api/auth/change-password` | `POST` | `Authorization: Bearer <token>`, `Content-Type: application/json` | `{ current_password, new_password }` | `SettingsPage.tsx:196` |
| 16 | `${API_BASE_URL}/api/databases` | `GET` | `Authorization: Bearer <token>` | None | `DatabasesPage.tsx:90`, `SettingsPage.tsx:67` |
| 17 | `${API_BASE_URL}/api/databases/${id}/stats` | `GET` | `Authorization: Bearer <token>` | None | `DatabasesPage.tsx:101` |
| 18 | `${API_BASE_URL}/api/databases/test` | `POST` | `Authorization: Bearer <token>`, `Content-Type: application/json` | `{ name, db_type, host, username, password, database }` | `DatabasesPage.tsx:132` |
| 19 | `${API_BASE_URL}/api/databases` | `POST` | `Authorization: Bearer <token>`, `Content-Type: application/json` | `{ name, db_type, host, username, password, database }` | `DatabasesPage.tsx:160` |
| 20 | `${API_BASE_URL}/api/databases/${id}` | `DELETE` | `Authorization: Bearer <token>` | None | `DatabasesPage.tsx:190` |
| 21 | `${API_BASE_URL}/api/databases/${id}/tables` | `GET` | `Authorization: Bearer <token>` | None | `DatabasesPage.tsx:214` |
| 22 | `${API_BASE_URL}/api/databases/${id}/tables/${table}/data` | `GET` | `Authorization: Bearer <token>` | None | `DatabasesPage.tsx:240` |
| 23 | `${API_BASE_URL}/api/databases/${id}/tables/${table}/stats` | `GET` | `Authorization: Bearer <token>` | None | `DatabasesPage.tsx:252` |
| 24 | `${API_BASE_URL}/api/documents` | `GET` | `Authorization: Bearer <token>` | None | `KnowledgeBasePage.tsx:92` |
| 25 | `${API_BASE_URL}/api/documents/${id}` | `DELETE` | `Authorization: Bearer <token>` | None | `KnowledgeBasePage.tsx:118` |
| 26 | `${API_BASE_URL}/api/documents/${id}/chunks` | `GET` | `Authorization: Bearer <token>` | None | `KnowledgeBasePage.tsx:137` |
| 27 | `${API_BASE_URL}/api/documents/search` | `POST` | `Authorization: Bearer <token>`, `Content-Type: application/json` | `{ query: string }` | `KnowledgeBasePage.tsx:67` |
| 28 | `${API_BASE_URL}/api/documents/upload` | `POST` | `Authorization: Bearer <token>` | Multipart `FormData` (`file`, `chunk_size`, `chunk_overlap`, `chunking_strategy`) | `UploadDocumentsPage.tsx:77` |
| 29 | `${API_BASE_URL}/api/keys` | `GET` | `Authorization: Bearer <token>` | None | `ApiKeysPage.tsx:41` |
| 30 | `${API_BASE_URL}/api/keys` | `POST` | `Authorization: Bearer <token>`, `Content-Type: application/json` | `{ name, description }` | `ApiKeysPage.tsx:64` |
| 31 | `${API_BASE_URL}/api/keys/${id}/revoke` | `PUT` | `Authorization: Bearer <token>` | None | `ApiKeysPage.tsx:89` |
| 32 | `${API_BASE_URL}/api/keys/${id}` | `DELETE` | `Authorization: Bearer <token>` | None | `ApiKeysPage.tsx:107` |
| 33 | `${API_BASE_URL}/api/chatbot-config` | `GET` | `Authorization: Bearer <token>` | None | `ChatbotWidgetPage.tsx:33` |
| 34 | `${API_BASE_URL}/api/chatbot-config` | `PUT` | `Authorization: Bearer <token>`, `Content-Type: application/json` | `{ theme_color, greeting_message, position, welcome_delay, max_history, widget_title, sound_enabled }` | `ChatbotWidgetPage.tsx:59` |

---

### 1.5 Mock Data Usage vs. Live Backend Connection Classification

#### A. Fully Integrated / Live Backend Components
1. **Authentication Flow** (`LoginPage`, `SignupPage`, `ForgotPasswordPage`, `EmailVerificationPage`, `LandingPage` OAuth code handler).
2. **Databases Management & Explorer** (`DatabasesPage`): Complete database connection CRUD, table listing, data preview, and table row/col stats.
3. **Knowledge Base & RAG Search** (`KnowledgeBasePage`, `UploadDocumentsPage`): Document listing, polling, chunk viewer, semantic search testing, and document upload.
4. **API Keys Management** (`ApiKeysPage`): Dynamic listing, creation, revocation, and deletion (except one static stats card "Requests Today").
5. **Chatbot Config** (`ChatbotWidgetPage`): Live GET/PUT for widget configuration.
6. **Tenant & Member Settings** (`SettingsPage` Company, Team, and Security tabs).

#### B. Fully Mocked / Disconnected Components
1. **`DashboardOverview.tsx`**: 100% hardcoded mock data (`stats`, `queryData`, `databaseActivity`, `recentQueries`). Zero API calls.
2. **`AnalyticsPage.tsx`**: 100% hardcoded mock data (`queryTrendsData`, `topTablesData`, `databaseDistribution`, `dataGrowthData`). Dropdowns (`database`, `dateRange`) have state but do not trigger API requests.
3. **`AIInsightsPage.tsx`**: 100% hardcoded recommendations array (`insights`). "Generate New Insights" and "View Details" buttons have no click handlers.
4. **`UsagePage.tsx`**: 100% hardcoded mock data (`usageData`, `databaseTypeData`, `hourlyData`).
5. **`LogsPage.tsx`**: 100% hardcoded mock data (`logs` array). Search/filter controls operate client-side only on hardcoded array. "Export Logs" button does nothing.
6. **`AdminPanel.tsx`**: 100% hardcoded mock data (`platformStats`, `tenants`, `systemMetrics`, `systemHealth`). Zero API calls.
7. **`SettingsPage.tsx` Sub-tabs**:
   - *Profile Tab*: Hardcoded `defaultValue` for user name, email, phone. "Save Changes" does nothing.
   - *Billing Tab*: Static mock plan ("Starter Plan"), mock credit card, mock invoice history.
   - *Notifications Tab*: Local switch state; "Save Preferences" button does nothing.

---

### 1.6 Unbuilt, Partially Built, or Disconnected UI Features

1. **Absence of NL-to-SQL Query Interface / Natural Language Analytics Tool**:
   - Crucial architectural gap: Although DataSpeakAI is described as an AI-driven database query platform, there is **no page or component** in `src/` where a user can enter a natural language prompt against a connected SQL/NoSQL database and see generated SQL or query execution results.
   - The chatbot preview on `ChatbotWidgetPage.tsx` is only a static UI simulator. `DashboardOverview.tsx` lists mock query logs.

2. **Absence of ERD / Schema Visualizer Component**:
   - Despite documentation files (`Database_ERD.md`, `DataSpeakAI_Complete_EERD.md`) existing in the project root, no UI route or component exists for visualizing database ERDs or schema diagrams.

3. **Absence of Dynamic Dashboard / Visualization Builder**:
   - `AnalyticsPage.tsx` displays fixed Recharts graphs with hardcoded mock numbers instead of generating dynamic charts based on query results.

4. **Upload Document Configuration Disconnect**:
   - In `UploadDocumentsPage.tsx`, options for `Embedding Model` (`embeddingModel`) and `Auto Re-index` (`autoIndex`) exist in the UI state but are **omitted from the `FormData` payload** when uploading to `/api/documents/upload`.

5. **Legacy Branding / OmniQuery Artifact Mismatches**:
   - `ChatbotWidgetPage.tsx` (lines 84–94): Generated HTML embed snippet targets `https://cdn.omniquery.ai/widget.js` and initializes `OmniQueryAI.init(...)`.
   - `ApiKeysPage.tsx` (line 352): API cURL code snippet targets `https://api.omniquery.ai/v1/query`.

---

### 1.7 Environment Variable Audit (`.env.example` vs Implementation)

- **.env.example Content**:
  ```env
  # Frontend Environment Variables
  VITE_API_URL=http://localhost:8000
  VITE_APP_NAME=DataSpeakAI
  ```

- **Implementation Discrepancies**:
  1. **Variable Name Mismatch**: `.env.example` provides `VITE_API_URL`, but `src/app/config/api.ts` (line 1) references `import.meta.env.VITE_API_BASE_URL`.
     - *Impact*: In production or configured environments, setting `VITE_API_URL` will be ignored by the frontend bundle, causing it to fall back to `http://localhost:8000`.
  2. **Missing Environment Variable for GitHub OAuth Client ID**:
     - `LoginPage.tsx` (line 19) and `SignupPage.tsx` (line 28) hardcode `clientId = "Ov23liPRgons4RlFv7FU"`.
     - *Impact*: GitHub OAuth client ID cannot be configured per environment without code edits. Should be `import.meta.env.VITE_GITHUB_CLIENT_ID`.
  3. **Unused Environment Variable**: `VITE_APP_NAME` is declared in `.env.example` but is never referenced anywhere in `src/`.

---

## 2. Logic Chain

1. **Route to File Mapping**: `src/app/routes.ts` imports 17 distinct page components and maps them via `createBrowserRouter`. Inspecting each imported component file allows deterministic mapping of the entire navigation structure.
2. **API Discovery**: Grepping `src/` for `fetch`, `axios`, and `API_BASE_URL` confirmed that all HTTP communication routes through `API_BASE_URL` (`src/app/config/api.ts`). Tracking each `fetch()` call yields the complete 34-endpoint inventory.
3. **Mock vs Live Differentiation**: Components containing `fetch()` calls in `useEffect` or event handlers process live server state. Components rendering static JavaScript arrays (`stats`, `insights`, `logs`, `platformStats`) without any `fetch()` calls are confirmed as purely mocked.
4. **Environment Gap Analysis**: Comparing string keys in `.env.example` (`VITE_API_URL`) against literal accesses of `import.meta.env` (`VITE_API_BASE_URL`) exposes configuration bugs that cause fallback behavior.

---

## 3. Caveats

- **Backend Route Availability**: This investigation analyzed the frontend implementation (`src/`). Backend implementation of the 34 endpoints was not executed or verified against live running Python services during this read-only phase.
- **Admin Panel Access Control**: `AdminPanel.tsx` currently has no auth check or role check inside its file structure.

---

## 4. Conclusion

The DataSpeakAI frontend UI codebase (`src/`) has a well-structured React Router v7 and Shadcn/Tailwind UI foundation. Core authentication, database connection management (including Database Explorer), document RAG management/search, API key management, chatbot config, and company/team settings are **fully wired to live backend API endpoints**.

However, there are significant functional and structural gaps:
1. **6 Key Dashboard Pages Are 100% Mocked**: `DashboardOverview`, `AnalyticsPage`, `AIInsightsPage`, `UsagePage`, `LogsPage`, and `AdminPanel` render hardcoded JSON and are completely disconnected from the backend.
2. **Core Feature Gaps**: The primary NL-to-SQL query interface, ERD visualizer, and dynamic dashboard builder are missing from `src/`.
3. **Env Var & Branding Mismatches**: `VITE_API_BASE_URL` mismatch, hardcoded GitHub Client ID, and residual `OmniQuery` references in embed/cURL snippets require cleanup.

---

## 5. Verification Method

To independently verify these findings:

1. **Verify Routes & Components**:
   - Inspect `d:\dataspeak\src\app\routes.ts` line 21–96 to confirm all 17 page component imports and paths.
2. **Verify API Endpoints & Env Mismatch**:
   - Run grep in `src/`: `grep -rn "API_BASE_URL" src/`
   - Inspect `d:\dataspeak\src\app\config\api.ts` line 1 vs `d:\dataspeak\.env.example` line 2 to confirm `VITE_API_BASE_URL` vs `VITE_API_URL`.
3. **Verify Mocked Components**:
   - View `src/app/pages/dashboard/DashboardOverview.tsx` (lines 25–104) and `src/app/pages/dashboard/AnalyticsPage.tsx` (lines 37–69) to verify static arrays with zero `fetch` references.
4. **Verify Live Components**:
   - View `src/app/pages/dashboard/DatabasesPage.tsx` (lines 85–264) and `src/app/pages/dashboard/KnowledgeBasePage.tsx` (lines 61–149) to verify active `fetch` requests with authorization headers.
