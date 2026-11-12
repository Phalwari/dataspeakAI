# Session: chatbot and Insights demo QA remediation

- Date: 2026-10-22 (Asia/Karachi)
- Agent: Codex / implementation and QA
- Objective: fix all ten findings from the previous live demo review without reseeding sources or switching the Insights planner default.
- Completed: DQA-01..10. Changes cover chart/period semantics, filtered populations and caches, typed scope rejection, Decimal summaries, passage identity and shared parent context, claim grounding, bounded native Mongo generation/execution, status-specific billing, and honest streaming/nonstreaming fallback.
- Verification: 231 affected backend tests passed; later overlapping Mongo edge regressions 38 passed; frontend 47 passed; production Vite build passed; changed Python modules compile; diff check clean except informational line-ending warnings.
- Live evidence: PostgreSQL East 6 customers / 240 units; dashboard coffee/solar/Orbit correct and fully supported (Orbit after a recorded quota fallback and retry); standalone widget both facts correct and supported; Mongo 160 / $16,300, paid $14,736, October 60 / $6,140, cancelled-only paid $0 / one distinct status; native Mongo SSE completed with correct result.
- Report: `docs/reports/demo_qa_remediation_2026-10-22/REPORT.md`, `evidence.json`, test/build logs, and `browser-insights.txt`. Browser screenshot capture was unavailable, so no new screenshot is claimed.
- Runtime: app and three demo servers left running. No source cleanup, reseeding, password reset, merge, push, or deployment during remediation. Existing staged work was preserved.
- Boundaries: real provider quotas remain; Mongo supports a restricted read-only subset; no load/multi-worker/PDF-OCR/mobile certification; Planner V2 stays opt-in.
- Handoff: `.agents/demo-qa-remediation/handoff.md`.
