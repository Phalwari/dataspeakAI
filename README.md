# DataSpeakAI

DataSpeakAI is an enterprise-grade Conversational AI and Business Intelligence SaaS platform that enables users to query relational databases and document knowledge bases using natural language. It combines schema introspection and Natural Language to SQL (NL-to-SQL) with a multi-modal Retrieval-Augmented Generation (RAG) engine to deliver conversational insights, interactive data exploration, and embeddable chatbot capabilities.

---

## Tech Stack

The project consists of a React single-page application frontend and a FastAPI backend microservice.

### Frontend
- **Runtime & Build Tooling**: Node.js, Vite (`vite` 6.3.5, `@vitejs/plugin-react` 4.7.0), TypeScript
- **Framework & Routing**: React 18.3.1 (`react`, `react-dom`), React Router v7 (`react-router` ^7.13.0)
- **Styling & Animation**: Tailwind CSS v4 (`@tailwindcss/vite`, `tailwindcss`), Emotion (`@emotion/react`, `@emotion/styled`), Framer Motion (`motion`), Lucide React (`lucide-react`)
- **UI Components**: MUI v7 (`@mui/material`, `@mui/icons-material`), Radix UI Primitives (`@radix-ui/react-*`), Sonner (`sonner`), CMDK (`cmdk`), Vaul (`vaul`)
- **Data Visualization & Layout**: Recharts (`recharts`), React DnD (`react-dnd`), React Resizable Panels (`react-resizable-panels`), React Hook Form (`react-hook-form`)

### Backend
- **Runtime & Framework**: Python 3.10+, FastAPI, Uvicorn ASGI Server
- **Database & ORM**: SQLAlchemy 2.0+, SQLite (default), PostgreSQL (`psycopg2-binary`), MySQL / MariaDB (`pymysql`)
- **Validation & Serialization**: Pydantic v2 (`pydantic[email]`)
- **Authentication & Security**: Passlib with bcrypt (`passlib[bcrypt]`), PyJWT (`PyJWT`), Cryptography (`cryptography`)
- **Background Tasks**: Celery (`celery`), Redis (`redis`), Flower (`flower`), FastAPI `BackgroundTasks` fallback

### AI, RAG & Data Extraction
- **Embeddings & Vector Index**: HuggingFace Sentence Transformers (`sentence-transformers`, `all-MiniLM-L6-v2`), FAISS (`faiss-cpu`), LangChain (`langchain`, `langchain-huggingface`, `langchain-community`, `langchain-text-splitters`)
- **Sparse Search & Re-Ranking**: Rank-BM25 (`rank-bm25`), Cross-Encoder (`sentence-transformers/ms-marco-MiniLM-L-6-v2`)
- **Document & Multi-Modal Ingestion**: PyMuPDF (`fitz`), pdfplumber, python-docx, openpyxl, python-pptx, BeautifulSoup4, Pandas
- **AI & Vision APIs**: Google Gemini API (`gemini-2.5-flash`), Google Auth (`google-auth`)
- **Email Delivery**: Resend API (`resend`), Python `smtplib` fallback

---

## Quickstart

Follow these steps to set up and run DataSpeakAI locally.

### Prerequisites
- **Node.js** (v18.0 or higher) and **npm**
- **Python** (v3.10 or higher)

### 1. Clone the Repository
```bash
git clone <repository-url>
cd dataspeak
```

### 2. Backend Setup
Navigate to the `backend` directory, create a virtual environment, and install dependencies:

```bash
cd backend

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On Windows (Command Prompt):
.\venv\Scripts\activate.bat
# On macOS/Linux:
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Frontend Setup
Open a new terminal at the repository root and install dependencies:

```bash
# From repository root
npm install
```

### 4. Configuration
Create your local environment files based on the provided templates:

**Frontend configuration (project root):**
```bash
cp .env.example .env
```
*(On Windows PowerShell: `Copy-Item .env.example .env`)*

**Backend configuration (`backend` folder):**
```bash
cp backend/.env.example backend/.env
```
*(On Windows PowerShell: `Copy-Item backend\.env.example backend\.env`)*

Update the `.env` files with your secret keys and credentials (see [Configuration](#configuration) below).

### 5. Running the Application

Start both the backend and frontend development servers.

**Terminal 1 — Backend Server:**
```bash
cd backend
.\venv\Scripts\Activate.ps1
python -m uvicorn main:app --reload --port 8000
```
The FastAPI backend will start at `http://localhost:8000`. Interactive OpenAPI documentation is available at `http://localhost:8000/docs`.

**Terminal 2 — Frontend Server:**
```bash
# From repository root
npm run dev
```
The Vite development server will start at `http://localhost:5173`.

**Terminal 3 (Optional) — Celery Worker (for asynchronous document ingestion):**
```bash
cd backend
# Ensure virtual environment is active and Redis is running
celery -A celery_app.celery_app worker --loglevel=info
```
*Note: If Celery/Redis is not configured, the backend automatically falls back to in-process background tasks.*

---

## Configuration

The platform is configured via environment variables defined in root `.env` and `backend/.env`.

| Variable | Scope | Default Value | Description |
| :--- | :--- | :--- | :--- |
| `VITE_API_BASE_URL` | Frontend | `http://localhost:8000` | Target FastAPI backend URL for client-side API requests |
| `VITE_APP_NAME` | Frontend | `DataSpeakAI` | Application branding name displayed across the UI |
| `DATABASE_URL` | Backend | `sqlite:///./app.db` | SQLAlchemy database connection string (SQLite, PostgreSQL, or MySQL) |
| `SECRET_KEY` | Backend | — | Cryptographic secret key used to sign JWT access tokens and derive encryption keys |
| `ALGORITHM` | Backend | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Backend | `1440` | JWT access token validity period in minutes |
| `FRONTEND_URL` | Backend | `http://localhost:5173` | Frontend application origin used for CORS and tenant invitation links |
| `GEMINI_API_KEY` | Backend | — | Google Gemini API key used for query intent routing, multimodal VLM OCR, and conversational SQL/RAG synthesis |
| `GITHUB_CLIENT_ID` | Backend | — | GitHub OAuth application Client ID for third-party authentication |
| `GITHUB_CLIENT_SECRET` | Backend | — | GitHub OAuth application Client Secret |
| `RESEND_API_KEY` | Backend | — | Resend API key for sending email verification codes and password reset OTPs |
| `EMAIL_USER` | Backend | — | SMTP username (fallback email delivery when Resend is unconfigured) |
| `EMAIL_PASS` | Backend | — | SMTP password for fallback email delivery |
| `EMAIL_HOST` | Backend | `smtp.gmail.com` | SMTP host server address |
| `EMAIL_PORT` | Backend | `587` | SMTP port number |
| `CELERY_BROKER_URL` | Backend | `redis://localhost:6379/0` | Redis broker URL for asynchronous Celery worker tasks |
| `CELERY_RESULT_BACKEND` | Backend | `redis://localhost:6379/1` | Redis result backend URL for Celery |
| `ENCRYPTION_KEY` | Backend | Falls back to `SECRET_KEY` | Symmetric Fernet key for encrypting external database passwords at rest |
| `DEFAULT_ADMIN_EMAIL` | Backend | `admin@dataspeak.ai` | Pre-seeded superadmin email for local development |
| `DEFAULT_ADMIN_PASSWORD` | Backend | `AdminPassword123!` | Pre-seeded superadmin password for local development |
| `DEFAULT_ADMIN_NAME` | Backend | `Super Admin` | Pre-seeded superadmin display name |
| `DEFAULT_ORG_NAME` | Backend | `DataSpeak Enterprise` | Pre-seeded superadmin tenant organization name |

---

## Project Structure

```
dataspeak/
├── backend/                           # FastAPI backend microservice
│   ├── main.py                        # Application entry point, CORS, table creation & router mounts
│   ├── database.py                    # SQLAlchemy database engine and get_db session dependency
│   ├── models.py                      # SQLAlchemy ORM models (Tenant, User, Document, Chat, etc.)
│   ├── schemas.py                     # Pydantic request and response schemas
│   ├── auth.py                        # Passlib bcrypt password hashing and PyJWT token generation
│   ├── dependencies.py                # Authentication dependencies (get_current_user)
│   ├── crypto.py                      # Fernet symmetric credential encryption utilities
│   ├── celery_app.py                  # Celery application configuration and task broker bindings
│   ├── requirements.txt               # Backend Python dependencies
│   ├── ingestion/                     # Multimodal file extraction & document chunking
│   │   ├── extractor.py               # File format parsers (PDF, DOCX, XLSX, PPTX, CSV, HTML, TXT)
│   │   ├── chunking.py                # Recursive text splitter and table anchor strategies
│   │   └── task_queue.py              # Celery tasks for asynchronous ingestion & re-indexing
│   ├── routers/                       # FastAPI endpoint route controllers
│   │   ├── users.py                   # /api/auth (Login, register, OAuth, OTP, password recovery)
│   │   ├── tenants.py                 # /api/tenant (Organization profile, members, invites)
│   │   ├── databases.py               # /api/databases (Database CRUD, schema introspection, preview)
│   │   ├── query.py                   # /api/query (Direct NL-to-SQL query execution)
│   │   ├── documents.py               # /api/documents (Upload, FAISS search, re-indexing, deletion)
│   │   ├── chat.py                    # /api/chat & /api/conversations (Conversational sessions & assistant)
│   │   ├── analytics.py               # /api/analytics (Usage analytics & system metrics)
│   │   ├── api_keys.py                # /api/keys (Tenant API key creation and revocation)
│   │   └── chatbot_config.py          # /api/chatbot-config (Chatbot widget customizations)
│   ├── search/                        # Hybrid dense-sparse retrieval and ranking
│   │   ├── bm25_index.py              # BM25Okapi sparse index manager per tenant
│   │   └── hybrid.py                  # Reciprocal Rank Fusion (RRF) and Cross-Encoder re-ranking
│   ├── services/                      # Core business logic services
│   │   ├── query_router.py            # Query intent classification and auto-database routing
│   │   └── sql_engine.py              # Schema context extraction, SQL generation & safe execution
│   └── scripts/                       # Maintenance & initialization scripts
│       ├── seed_admin.py              # Local development superadmin auto-seeder
│       └── migrate_embeddings.py      # Embedding model migration and index rebuild CLI
├── src/                               # React + Vite frontend application
│   ├── main.tsx                       # React DOM entry point
│   ├── styles/                        # Master stylesheet, Tailwind v4 imports, theme tokens
│   └── app/
│       ├── App.tsx                    # Root component with RouterProvider and Sonner Toaster
│       ├── routes.ts                  # React Router v7 configuration (17 application routes)
│       ├── config/
│       │   └── api.ts                 # Central API configuration (VITE_API_BASE_URL)
│       ├── components/
│       │   ├── DashboardLayout.tsx    # Authenticated dashboard frame (sidebar, header, user menu)
│       │   └── ui/                    # Reusable UI primitives (buttons, dialogs, dropdowns, tables)
│       └── pages/                     # Frontend views
│           ├── LandingPage.tsx        # Public landing page & GitHub OAuth callback
│           ├── LoginPage.tsx          # Authentication page with dev auto-fill shortcut
│           ├── SignupPage.tsx         # Tenant & user registration
│           ├── ForgotPasswordPage.tsx # 3-step OTP password reset
│           ├── EmailVerificationPage.tsx # Email verification code entry
│           ├── admin/
│           │   └── AdminPanel.tsx     # Superadmin management panel
│           └── dashboard/
│               ├── DashboardOverview.tsx  # Executive metrics overview & activity charts
│               ├── ChatPage.tsx           # Conversational AI Assistant interface
│               ├── DatabasesPage.tsx      # Database connection management & table browser
│               ├── KnowledgeBasePage.tsx  # Document management & semantic search testing
│               ├── UploadDocumentsPage.tsx# Document upload with real-time extraction progress
│               ├── AnalyticsPage.tsx      # Analytics dashboard
│               ├── AIInsightsPage.tsx     # Automated AI insights feed
│               ├── ApiKeysPage.tsx        # API key management
│               ├── ChatbotWidgetPage.tsx  # Embeddable widget configuration
│               ├── UsagePage.tsx          # Resource meter & quota tracking
│               ├── LogsPage.tsx           # Execution audit & activity logs
│               └── SettingsPage.tsx       # Tenant profile & account settings
├── docs/                              # Project documentation (architecture, database schemas, setup)
├── .env.example                       # Root environment variable template
├── package.json                       # Frontend dependencies and npm scripts
├── vite.config.ts                     # Vite build configuration
└── README.md                          # Project documentation
```
