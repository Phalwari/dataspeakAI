# DataSpeakAI — System & Engineering Guidelines

Welcome to the **DataSpeakAI** engineering and developer guidelines. This document outlines general engineering standards, design system rules, and task lifecycle management for human contributors and AI agents.

---

## 1. Core Engineering & Agent Standards

All developers and AI agents must follow the canonical project standards defined in:
* **[`AGENTS.md`](file:///d:/dataspeak/AGENTS.md)**: AI Agent Context Standard, Security Guidelines, and Architecture Maps.
* **[`todo.md`](file:///d:/dataspeak/todo.md)**: Master Engineering Roadmap & Task Tracker.
* **[`CHANGELOG.md`](file:///d:/dataspeak/CHANGELOG.md)**: Release and session tracking.

### 1.1 Task Lifecycle & `todo.md` Protocol
* **Task Claiming**: Check [`todo.md`](file:///d:/dataspeak/todo.md) before starting any task. Target the highest priority uncompleted item (`- [ ]`).
* **Task Completion**: Upon finishing and verifying work (via `cmd.exe /c "npm run build"` or backend tests):
  1. Mark checkbox as complete: `- [x]`.
  2. Append completion metadata: `[Completed: YYYY-MM-DD | <Agent/Role> | <Summary>]`.
  3. **Move the completed task** out of the active phase list into the `## 📦 Archived / Completed Tasks` section at the bottom of [`todo.md`](file:///d:/dataspeak/todo.md).
  4. Log the feature or fix under `## [Unreleased]` in [`CHANGELOG.md`](file:///d:/dataspeak/CHANGELOG.md).

### 1.2 Mandatory Security Rules
* **Parameterized SQL**: Never use string interpolation, f-strings, or string concatenation with user input in database queries. Always use SQLAlchemy parameterized `text()` constructs.
* **No Plaintext Passwords**: Database connection credentials must always be encrypted using Fernet (`backend/crypto.py`).
* **No Hardcoded Secrets**: Secrets and API keys must be loaded via environment variables or `.env`.

---

## 2. Frontend & UI Guidelines

### 2.1 Layout & Responsiveness
* Prefer responsive flexbox and grid layouts (`flex`, `grid`, `gap-*`, `max-w-*`). Avoid arbitrary fixed widths or absolute positioning unless specifically required for overlay elements (modals, dropdowns, tooltips).
* Use standard Tailwind CSS v4 design tokens and CSS variables defined in `src/styles/theme.css`.
* Follow component standards in `src/app/components/ui/` (Radix primitives styled with Tailwind).

### 2.2 Notifications & User Feedback
* Always provide asynchronous user feedback using Sonner toast notifications:
  * Success: `toast.success("Connection verified successfully")`
  * Error: `toast.error("Failed to load schema: " + err.message)`
* Avoid silent promise rejections or unhandled catch blocks.

### 2.3 Verification Commands
* **Build Check**: `cmd.exe /c "npm run build"` must succeed before committing code changes.

---

## 3. Backend & API Guidelines

### 3.1 Architecture & Endpoints
* Build FastAPI routers under `backend/routers/` and bind them in `backend/main.py`.
* Validate all request and response bodies with Pydantic v2 schemas in `backend/schemas.py`.
* Return explicit HTTP status codes (`HTTPException(status_code=..., detail=...)`).

### 3.2 Database Session Management
* Always use the `get_db` dependency for database sessions:
  ```python
  from database import get_db
  from sqlalchemy.orm import Session
  
  @router.get("/api/endpoint")
  def my_endpoint(db: Session = Depends(get_db)):
      ...
  ```
