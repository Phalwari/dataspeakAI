# Handoff — Demo QA

## Observation
Three real demo engines and three policy documents are active for tenant 2. Several correctness and retrieval defects remain despite correct core relational aggregates.

## Logic Chain
Independent deterministic fixture totals were compared to actual authenticated API outputs; browser observations exposed presentation defects beyond arithmetic. Forty checks returned 30 passes and 10 failures. Known-answer widget questions both failed; correct dashboard policy answers were falsely labeled unsupported.

## Caveats
Live provider cooldowns affected some attempts. Initial document queries preceded readiness and were repeated after indexing. No multi-user/load/mobile/PDF-OCR certification. Generated runtime credentials and tokens are ignored local files. Pre-cleanup SQLite backup is not a complete file-content restore. Existing unrelated changes were preserved; another process committed them during the session.

## Conclusion
Owner-requested setup and evaluation complete; product sign-off withheld. DQA-01..10 are tracked as open fixes in todo.md. No production defect fixes were made.

## Verification Method
See docs/reports/demo_qa_2026-10-21/REPORT.md and evidence.json. Live HTTP, independent totals, browser snapshots, two SSE streams, widget origin and known-answer checks, successful Vite build, Python compilation, git diff --check. To restart demo listeners without reseeding: .venv/Scripts/python.exe tests/manual/provision_demo_sources.py --start.
