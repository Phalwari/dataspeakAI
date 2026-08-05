# Project: DataSpeakAI Directory Reorganization & AI Agent Context System

## Architecture
- Root directory: Cleaned runtime files (`package.json`, `vite.config.ts`, `index.html`, `.gitignore`, `README.md`, `AGENTS.md`, `CHANGELOG.md`).
- Documentation subdirectories (`docs/`):
  - `docs/architecture/`: Workflow, activity diagrams, system design
  - `docs/database/`: ERDs, EERDs, SQL schemas
  - `docs/setup/`: Setup guides, environment guides
  - `docs/reports/`: Implementation reports, mock analyses, technical reports
  - `docs/sessions/`: Work session logs & context transfer logs
  - `docs/templates/`: `AI_TASK_TEMPLATE.md` for team members
- AI Agent Context System: `AGENTS.md` at root.
- Multi-Developer Tracking: `CHANGELOG.md` at root, session logs in `docs/sessions/`.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | File Inventory & Analysis | Discover all root-level docs, diagrams, SQL, reports, build config | Milestone 1 | ORIGINAL_REQUEST |
| 2 | Relocate Documentation Files | Move docs/diagrams/SQL/reports into structured `docs/` subdirs | Milestone 2 | ORIGINAL_REQUEST |
| 3 | Root Directory Cleanup | Ensure root retains only essential runtime files | Milestone 2 | ORIGINAL_REQUEST |
| 4 | Build & Runtime Protection | Verify package.json/vite.config.ts work after relocation | Milestone 2 | ORIGINAL_REQUEST |
| 5 | Create AGENTS.md | Comprehensive AI Context Standard at project root | Milestone 3 | ORIGINAL_REQUEST |
| 6 | Create CHANGELOG.md | Project baseline history and session logging standard | Milestone 4 | ORIGINAL_REQUEST |
| 7 | Create Session Log Structure | `docs/sessions/` structure & instructions | Milestone 4 | ORIGINAL_REQUEST |
| 8 | Create AI Task Template | `docs/templates/AI_TASK_TEMPLATE.md` | Milestone 4 | ORIGINAL_REQUEST |
| 9 | Operational Verification | Run build/dev check to confirm zero breakage | Milestone 5 | ORIGINAL_REQUEST |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Analysis & File Inventory | Map all root files, docs, diagrams, SQL, reports, package.json, vite.config.ts | None | DONE |
| 2 | Directory Restructuring & Documentation Consolidation | Create `docs/` subdirs, move files, check package.json / vite.config.ts | Milestone 1 | DONE |
| 3 | AI Agent Context Standard | Create `AGENTS.md` at project root with tech stack, architecture, guidelines | Milestone 1 | DONE |
| 4 | Multi-Developer Context Tracking | Create `CHANGELOG.md`, `docs/sessions/`, `docs/templates/AI_TASK_TEMPLATE.md` | Milestone 1 | DONE |
| 5 | Operational Verification | Run `npm run build` or equivalent and claim victory | Milestones 2, 3, 4 | DONE |

## Code Layout
- Root: `package.json`, `vite.config.ts`, `index.html`, `.gitignore`, `README.md`, `AGENTS.md`, `CHANGELOG.md`
- `docs/`: `architecture/`, `database/`, `setup/`, `reports/`, `sessions/`, `templates/`
