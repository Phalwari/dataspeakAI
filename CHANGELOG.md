# DataSpeakAI Changelog

All notable changes to the DataSpeakAI project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## Session Logging Guidelines

To maintain seamless multi-developer and AI agent collaboration:
1. **Work Session Logs**: For any major session, architectural change, or multi-agent handoff, create a session log file under `docs/sessions/` using the naming format `YYYY-MM-DD_<topic>.md` (see `docs/sessions/README.md` for standard structure).
2. **Updating `CHANGELOG.md`**: When completing features, bug fixes, or structural changes, add a summary under the `[Unreleased]` section of this file. When releasing a milestone, summarize all unreleased items under a new version header (e.g. `[v0.3.0] - YYYY-MM-DD`).
3. **Traceability**: Reference specific session logs in `docs/sessions/` or handoff reports in `.agents/` when logging major updates.

---

## [Unreleased]

### Planned / In Progress
- Implementation of remaining 25 enterprise database schema tables into `backend/models.py`.
- Dynamic SQL query generator with advanced schema-aware guardrails and parameterization.
- Live backend integration for Analytics, AI Insights, Usage metering, and Audit Logs pages.
- Embedded chat widget JS bundle compilation for external SaaS tenant websites.

---

## [v0.2.0] - 2026-08-05

### Added
- **AI Agent Context Standard (`AGENTS.md`)**: Single source of truth context file at project root providing technical stack breakdown, directory architecture maps, security guidelines, parameterization requirements, and pre-task context protocols for AI coding tools (Google Antigravity, Cursor, Copilot, Claude Code).
- **Consolidated Documentation Tree (`docs/`)**: Reorganized project documentation into structured subdirectories:
  - `docs/architecture/`: System design, workflow diagrams, and FYP roadmap plans.
  - `docs/database/`: Enterprise SQL schemas (`Full_Project_Schemas.sql`), ERDs, and visual EERD diagrams.
  - `docs/setup/`: System setup guides, guidelines, and environment setup instructions.
  - `docs/reports/`: Technical reports, module implementation walkthroughs, and mockup analysis documents.
  - `docs/sessions/`: Dedicated work session logs for developers and AI tools.
  - `docs/templates/`: AI task prompt delegation templates (`AI_TASK_TEMPLATE.md`).
- **Multi-Developer Context Tracking**:
  - `CHANGELOG.md`: Standardized version history and change log tracking.
  - `docs/sessions/README.md`: Session logging guidelines and standard format specifications.
  - `docs/templates/AI_TASK_TEMPLATE.md`: Standardized prompt template for team members delegating tasks to AI agents.

### Changed
- Relocated 20+ root documentation markdown files, SQL scripts, and diagram images into `docs/` subdirectories to establish a disciplined, clean root directory structure.
- Standardized API base URL environment variable on `VITE_API_BASE_URL` across frontend config (`src/app/config/api.ts`).

### Fixed
- Eliminated root directory clutter while retaining mandatory build and runtime configuration files (`package.json`, `vite.config.ts`, `index.html`, `postcss.config.mjs`, `proxy.js`, `.env.example`, `README.md`, `AGENTS.md`, `CHANGELOG.md`).

---

## [v0.1.0] - 2026-07-15

### Added
- **Natural Language to SQL (NL-to-SQL) Core Engine**:
  - Automated database schema introspection for SQLite, PostgreSQL, and MySQL.
  - FastAPI `/api/databases` router supporting connection creation, listing, deletion, schema inspection, connection testing, and 100-row table preview.
- **RAG & Vector Knowledge Base Engine**:
  - FAISS local vector index integrated with HuggingFace `SentenceTransformer` (`all-MiniLM-L6-v2`) embeddings.
  - LangChain `RecursiveCharacterTextSplitter` supporting fixed-size, paragraph, line, and sentence chunking strategies.
  - FastAPI `/api/documents` router for PDF upload, processing, vector indexing, and semantic similarity search.
- **Multi-Modal Document & Vision Extraction**:
  - Structured markdown table extraction via `pdfplumber`.
  - Image extraction using `PyMuPDF` (`fitz`).
  - Google Gemini 2.5 Flash API integration for visual OCR, chart interpretation, and diagram comprehension.
- **Multi-Tenant & User Management Backend**:
  - FastAPI microservice architecture (`backend/main.py`) using SQLAlchemy ORM and Pydantic v2 validation.
  - User authentication router (`/api/auth`) supporting registration, email/password login, bcrypt password hashing, and PyJWT token generation.
  - 6-digit email OTP verification and 3-step password recovery workflow.
  - GitHub OAuth 2.0 authentication integration.
  - Multi-tenant tenant configuration (`/api/tenant`) with team member invites and role management.
  - API key generation and management router (`/api/keys`) with key revocation.
  - Customizable chatbot widget configuration endpoint (`/api/chatbot-config`).
- **React Frontend Single-Page Application**:
  - React 18.3 + Vite 6 client built with TypeScript.
  - React Router v7 setup featuring 17 routes across landing, auth, admin, and dashboard modules.
  - Styling system powered by Tailwind CSS v4, MUI v7, Radix UI primitives, Framer Motion v12, and custom design tokens.
  - Data visualization dashboard with Recharts charts and Sonner toast feedback.
  - Dedicated pages for Databases, Knowledge Base, Document Upload, API Keys, Chatbot Customization, and Tenant Settings connected to live backend APIs.
- **Database Architecture & Specs**:
  - 10 core SQLAlchemy models (`Tenant`, `User`, `UserDatabaseAccess`, `TenantInvite`, `DatabaseConnection`, `ApiKey`, `ChatbotConfig`, `Document`, `DocumentChunk`, `PasswordResetOTP`) defined in `backend/models.py`.
  - Comprehensive 35-table enterprise SQL schema specification defined in `docs/database/Full_Project_Schemas.sql`.
