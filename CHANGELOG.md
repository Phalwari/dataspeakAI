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

- **Master Engineering Roadmap & Task Tracker ([`todo.md`](file:///d:/dataspeak/todo.md))**:
  - Established canonical project-wide backlog organized into sequential prioritized phases (P0 to P3): Phase 1 (Frontend Analytics Wiring), Phase 2 (Embeddable Widget), Phase 3 (AI Insights Engine), Phase 4 (Enterprise Database Schemas), Phase 5 (Interactive ERD Generator), and Phase 6 (Production & Billing Hardening).
  - Defined mandatory 4-step task lifecycle protocol for AI agents and human developers.
  - Added dedicated Archived / Completed Tasks tracking section.
- **AI Agent Protocol & Instruction Standardization ([`AGENTS.md`](file:///d:/dataspeak/AGENTS.md), [`Guidelines.md`](file:///d:/dataspeak/docs/setup/Guidelines.md), [`AI_TASK_TEMPLATE.md`](file:///d:/dataspeak/docs/templates/AI_TASK_TEMPLATE.md))**:
  - Codified Section 5.5 in `AGENTS.md`: Mandatory rules requiring agents to mark tasks as `[x]`, append completion metadata, move completed items to the Archived section in `todo.md`, and log updates under `## [Unreleased]` in `CHANGELOG.md`.
  - Updated `Guidelines.md` and `AI_TASK_TEMPLATE.md` to enforce `todo.md` and `CHANGELOG.md` synchronization across all delegated agent tasks.
- **Default Superadmin Seed & Auto-Initialization (`backend/scripts/seed_admin.py`, `backend/main.py`, `LoginPage.tsx`)**:
  - Implemented automatic database seeding on startup ensuring a default verified Superadmin user (`admin@dataspeak.ai` / `AdminPassword123!`) and default tenant exist out-of-the-box.
  - Added an interactive **"⚡ Auto-fill Default Admin"** shortcut button on the frontend login page for fast multi-developer testing without re-registering.
  - *Production Hardening Note:* For production release, see [`AGENTS.md` Section 4.5](file:///d:/dataspeak/AGENTS.md) for instructions to disable auto-seeding in `main.py`, remove the login autofill card, and rotate the credentials.
- **Conversational Data Layer & Models (`backend/models.py`, `backend/schemas.py`)**:
  - Implemented `Conversation` (sessions, auto-generated titles, timestamps) and `Message` (turns, roles, query_type, metadata_json) SQLAlchemy models and Pydantic schemas.
- **Intelligent Query Router & Auto Database Selection (`backend/services/query_router.py`)**:
  - Developed multi-stage query intent classifier supporting heuristic keyword checks, schema metadata introspection, user preference overrides (`auto`, `documents`, `database`), and Google Gemini 2.5 Flash fallback.
  - Implemented automatic database connection selection (Option C) matching user queries to relevant database schemas.
- **Unified Chat API Endpoint (`backend/routers/chat.py`)**:
  - Built `POST /api/chat` supporting multi-turn conversational context windows (up to 8 turns), grounded RAG hybrid retrieval (FAISS + BM25 + RRF + Cross-Encoder re-ranking), safe NL-to-SQL execution, and multi-source Hybrid synthesis.
  - Added full conversation session management endpoints (`GET /api/conversations`, `GET /api/conversations/{id}`, `PATCH /api/conversations/{id}`, `DELETE /api/conversations/{id}`).
- **Conversational AI Assistant Workspace (`src/app/pages/dashboard/ChatPage.tsx`)**:
  - Built responsive 3-panel chat interface with conversation history sidebar, search filter, inline rename/delete, prompt suggestions, and engine switcher.
  - Added rich response rendering with engine status badges, syntax-highlighted SQL data tables, collapsible source citation cards, and modal chunk inspection.
  - Registered `/dashboard/chat` in router and updated navigation in `DashboardLayout.tsx`.
- **Architectural Documentation (`docs/architecture/`)**:
  - [`docs/architecture/RAG_SYSTEM_ARCHITECTURE.md`](file:///d:/dataspeak/docs/architecture/RAG_SYSTEM_ARCHITECTURE.md): Complete technical breakdown of multi-modal ingestion, table matrix preservation, recursive chunking, dual FAISS/BM25 indexing, intelligent query routing, and 5-stage hybrid retrieval.
  - [`docs/architecture/conversational_retrieval_architecture.md`](file:///d:/dataspeak/docs/architecture/conversational_retrieval_architecture.md): Conversational AI Assistant workflow and data flow specification.

### Added — Phase 1 & 2: Extraction Engine & Hybrid Search
- **Multimodal Document Extraction Pipeline & Structure-Aware Router (`backend/ingestion/`)**:
  - Implemented structure-aware pre-flight evaluation routing digital text pages to fast CPU text parsers and escalating scanned/image pages to Google Gemini 2.5 Flash VLM OCR.
  - Added native multi-format support for `.pdf`, `.docx`, `.xlsx`, `.pptx`, `.csv`, `.html`, `.md`, and `.txt` files.
  - Implemented streaming file upload handling in `backend/routers/documents.py` with 100MB chunked disk writing and post-processing file cleanup.
  - Created HTML table matrix generation with placeholder anchoring (`[[TABLE_REF_001]]`) inside narrative text streams.
- **Hybrid Dense-Sparse RAG Search & Reciprocal Rank Fusion (`backend/search/`)**:
  - Created BM25Okapi sparse keyword index manager (`backend/search/bm25_index.py`) per tenant.
  - Implemented Reciprocal Rank Fusion (`backend/search/hybrid.py`) combining dense FAISS embeddings with sparse BM25 scores.
  - Added metadata pre-filtering (document IDs, content types, page numbers) to `/api/documents/search`.
- **Extended Database Models & Pydantic Schemas**:
  - Added `progress`, `error_message`, `total_pages`, `pages_processed`, `visual_pages` to `Document` model.
  - Added `page_number`, `content_type`, `section_heading`, `reference_id` to `DocumentChunk` model.

### Added — Phase 3: Frontend Progress & Search Filters
- **Per-File Progress Tracking & Dual Progress Bars (`UploadDocumentsPage.tsx`)**:
  - Replaced global single-jump progress state with `FileUploadState` tracking per-file HTTP upload progress via `XMLHttpRequest` and backend processing progress via 3-second polling.
  - Added dual progress bars (blue for HTTP upload, green for backend processing).
  - Added VLM vision badge (`🔍 {visualPages} pages sent to AI vision`) when visual pages are extracted.
  - Added individual file error banners with `Retry` action buttons.
  - Replaced embedding model dropdown with static label: `Sentence Transformers (all-MiniLM-L6-v2)`.
- **Granular Search Filters & Progress Visualization (`KnowledgeBasePage.tsx`)**:
  - Added search filter panel inside Test AI Query dialog: document multi-select, content type toggles (Text 📄, Table 📊, Image 🖼️), page range inputs, Hybrid vs. Semantic search mode switch.
  - Added inline progress bar for documents with `Processing` status in the main table.
  - Wired `Re-index` context menu button to `POST /api/documents/{id}/reindex` with Sonner toast notifications.
  - Added red error message subtitles for documents in `Failed` status.

### Added — Phase 4: Scalability & Hardening
- **Celery Task Queue & Async Processing (`backend/celery_app.py`, `backend/ingestion/task_queue.py`)**:
  - Configured Celery with Redis broker/backend and `BackgroundTasks` fallback when Redis unavailable.
  - Wrapped document ingestion and reindexing into retriable Celery tasks with isolated DB sessions.
  - Added `celery_task_id` and `embedding_model` fields to `Document` model.
- **Document Reindexing Endpoint (`backend/routers/documents.py`)**:
  - Added `POST /api/documents/{id}/reindex` for on-demand re-embedding from stored chunks.
- **Search Mode Control & Cross-Encoder Re-Ranking (`backend/search/hybrid.py`)**:
  - Added `search_mode` ("hybrid"/"semantic") and `re_rank` flags to `SearchQuery` schema.
  - Implemented MS-MARCO Cross-Encoder re-ranking for improved retrieval precision.
- **Embedding Model Migration Tool (`backend/scripts/migrate_embeddings.py`)**:
  - CLI script to re-embed all tenant chunks with target model (default: `BAAI/bge-small-en-v1.5`), rebuild FAISS & BM25 indices, with `--dry-run` mode.

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
