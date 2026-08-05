# DataSpeakAI — AI Task Delegation Template

This template (`docs/templates/AI_TASK_TEMPLATE.md`) is the standard prompt format for human team members and orchestrating agents delegating software development tasks to AI coding tools (Google Antigravity, Cursor, GitHub Copilot, Claude Code).

---

## Instructions for Team Members

When assigning a new feature, bug fix, refactoring, or documentation task to an AI agent:
1. **Copy the template below**.
2. **Fill out all fields completely** with exact file paths, explicit requirements, and verification commands.
3. **Provide the filled prompt to the AI agent** at the start of its session or task dispatch.
4. **Enforce verification**: Ensure the agent performs build and test checks before declaring completion.

---

```markdown
# AI TASK DISPATCH: [Insert Descriptive Task Title]

- **Task Title**: [Short descriptive name of the task]
- **Target Working Directory**: `d:\dataspeak`
- **Assigned Agent Archetype / Role**: [implementer | qa | specialist | explorer]
- **Agent ID / Workspace Folder**: `d:\dataspeak\.agents\[agent_folder_name]`
- **Parent / Caller Conversation ID**: [Insert caller conversation ID]

---

## 1. Task Objective
[Provide a clear, high-level summary of what the AI agent is expected to build, modify, fix, or analyze. Be specific about expected functional behavior.]

---

## 2. Context & Reference Files
Before making any changes or writing code, the AI agent MUST read and inspect the following files:
- `AGENTS.md` (DataSpeakAI AI Agent Context Standard & Engineering Guide)
- `CHANGELOG.md` (Baseline project version history & change guidelines)
- [Specific file path 1, e.g., `backend/routers/databases.py`]
- [Specific file path 2, e.g., `src/app/pages/dashboard/DatabasesPage.tsx`]
- [Specific schema file, e.g., `docs/database/Full_Project_Schemas.sql`]

---

## 3. Mandatory Engineering Rules & Constraints
The AI agent must strictly enforce the following rules throughout implementation:

* **SQL Injection Safety**: NEVER construct dynamic SQL queries using string formatting, f-strings, or string concatenation with user input. ALWAYS use SQLAlchemy parameterized `text()` constructs or ORM queries.
* **Minimal Change Principle**: Modify only what is necessary to accomplish the target task. Do NOT perform unrelated code refactoring or cleanup.
* **Secrets Policy**: NEVER hardcode API keys, passwords, or secrets. Read all credentials from environment variables.
* **Architecture Compliance**:
  * Frontend: React 18, Vite 6, Tailwind CSS v4, MUI v7, Radix UI.
  * Backend: FastAPI, SQLAlchemy, Pydantic v2, Python 3.10+.
  * RAG Engine: FAISS, HuggingFace embeddings (`all-MiniLM-L6-v2`), LangChain text splitters, Google Gemini 2.5 Flash API.
* **File System Discipline**: Agent metadata (plans, progress, handoffs) belongs ONLY in `.agents/[agent_folder]/`. NEVER write source code, tests, or documentation inside `.agents/`.

---

## 4. Required Deliverables
The AI agent must produce the following concrete deliverables:

1. [Deliverable 1: e.g. New FastAPI router file `backend/routers/analytics.py`]
2. [Deliverable 2: e.g. Updated Pydantic schemas in `backend/schemas.py`]
3. [Deliverable 3: e.g. React Analytics component in `src/app/pages/dashboard/AnalyticsPage.tsx`]
4. [Deliverable 4: Session log entry in `docs/sessions/YYYY-MM-DD_[topic].md`]
5. [Deliverable 5: Handoff report in `.agents/[agent_folder]/handoff.md`]

---

## 5. Step-by-Step Implementation Plan
1. **Pre-Task Inspection**: Re-read target files using `view_file` to confirm current imports, lines, and types.
2. **Execute Modifications**: Make precise code changes using atomic file replacement tools.
3. **Verify Implementation**: Execute verification commands and validate API responses or UI compilation.
4. **Document & Log**: Update `CHANGELOG.md` (unreleased section), create a session log in `docs/sessions/`, and write `handoff.md`.

---

## 6. Verification Steps & Commands
The AI agent must execute and document the following verification checks:

- [ ] **Frontend Build Verification**: Run `npm run build` from `d:\dataspeak` to confirm React TypeScript compilation with 0 errors.
- [ ] **Backend Startup & Syntax Check**: Confirm FastAPI backend initializes cleanly (`python -c "import backend.main"` or pytest).
- [ ] **API & Schema Consistency**: Confirm Pydantic schemas match SQLAlchemy model definitions and frontend interface types.
- [ ] **Security Inspection**: Verify all SQL execution blocks use parameterized queries (`sqlalchemy.text()`).

---

## 7. Completion & Handoff Criteria
The task will be considered complete ONLY when:
- [ ] All required deliverables are implemented cleanly without syntax or lint errors.
- [ ] All verification steps have been executed and passed.
- [ ] `progress.md` in `.agents/[agent_folder]/` is updated with completed status.
- [ ] Self-contained 5-component handoff report (`handoff.md`) is written to `.agents/[agent_folder]/handoff.md` (containing: Observation, Logic Chain, Caveats, Conclusion, Verification Method).
- [ ] Completion message is sent to the parent caller with a summary of changes and paths to generated artifacts.
```

---

## Sample Filled Task Prompt Example

Below is an example of how a developer should fill out this template to delegate a backend feature:

```markdown
# AI TASK DISPATCH: Add Tenant Audit Logs Endpoint

- **Task Title**: Add Tenant Audit Logs FastAPI Endpoint
- **Target Working Directory**: `d:\dataspeak`
- **Assigned Agent Archetype / Role**: implementer
- **Agent ID / Workspace Folder**: `d:\dataspeak\.agents\worker_backend_logs`
- **Parent / Caller Conversation ID**: `abc12345-6789-0000-1111-222233334444`

---

## 1. Task Objective
Implement a new FastAPI endpoint `/api/tenant/logs` that retrieves paginated tenant audit log entries from the database using SQLAlchemy parameterized queries. Expose query params for page size, log level, and date range.

## 2. Context & Reference Files
- `AGENTS.md`
- `backend/main.py`
- `backend/models.py`
- `backend/schemas.py`
- `docs/database/Full_Project_Schemas.sql` (Audit log schema definition)

## 3. Mandatory Engineering Rules & Constraints
- Parameterized SQL execution mandatory.
- Must validate JWT auth via `get_current_user` dependency.
- Return Pydantic schema list matching frontend `LogsPage.tsx` interface.

## 4. Required Deliverables
1. `backend/routers/audit_logs.py`
2. Update `backend/main.py` to register audit logs router.
3. Update `backend/schemas.py` with `AuditLogResponse` Pydantic model.
4. `docs/sessions/2026-08-10_audit_logs_endpoint.md`
5. `.agents\worker_backend_logs\handoff.md`

## 5. Verification Steps & Commands
- Run `python -c "import backend.main"`
- Test endpoint via pytest or curl request.
```
