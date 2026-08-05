# Original User Request

## 2026-08-05T06:59:37Z

Reorganize the DataSpeakAI project directory into a disciplined, clean structure and establish an AI Agent Context System (AGENTS.md, structured docs/, CHANGELOG.md, and task templates) to support multi-developer collaboration using AI coding tools.

Working directory: d:\dataspeak
Integrity mode: development

## Requirements

### R1. Directory Restructuring & Documentation Consolidation
Move root-level documentation files, diagrams, SQL scripts, and module reports into organized subdirectories under docs/:
- docs/architecture/ (workflow, activity diagrams, system design)
- docs/database/ (ERDs, EERDs, SQL schemas)
- docs/setup/ (setup guides, environment guides)
- docs/reports/ (implementation reports, mock analyses, technical reports)

Ensure root directory retains only essential runtime files (package.json, vite.config.ts, index.html, .gitignore, README.md, AGENTS.md, CHANGELOG.md).

### R2. AI Agent Context Standard (AGENTS.md)
Create a comprehensive AGENTS.md file at the root of the project to serve as the single source of truth for any AI agent (Antigravity, Cursor, Copilot, Claude Code) working on the codebase. It must include:
- Executive Summary & Project Purpose.
- Tech Stack Breakdown (Frontend, Backend, AI/RAG engine, Database).
- Architecture & Key File Map (where components, routers, services, and schemas live).
- Code Conventions & Engineering Rules (naming, error handling, SQL safety, environment variables).
- Instructions for AI agents on how to read context before starting work.

### R3. Multi-Developer Context Tracking (CHANGELOG.md & Session Logs)
Create a CHANGELOG.md and a dedicated docs/sessions/ directory template system so team members and AI agents can:
- Record work sessions, completed tasks, and architectural changes.
- Provide prompt/task templates for team members delegating work to AI agents.
- Maintain seamless context transfer between different developers and AI agents.

## Acceptance Criteria

### Project Organization & AI Context Readiness
- [ ] Root directory cleaned: markdown/diagram/sql files relocated logically into docs/.
- [ ] Operational check: npm run dev or build configurations are unaffected by doc relocation.
- [ ] AGENTS.md created with full project context, architecture map, and coding guidelines for AI agents.
- [ ] CHANGELOG.md initialized with project baseline history and session logging standard.
- [ ] docs/templates/AI_TASK_TEMPLATE.md created for team members to write clear instructions for AI agents.
