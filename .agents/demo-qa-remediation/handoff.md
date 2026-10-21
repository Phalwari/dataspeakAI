# Handoff — chatbot and Insights QA remediation

## Observation
The original ten defects are corrected. Core SQL and native Mongo calculations match the synthetic oracle, document/widget answers use correct passages, and supported citations now agree with the answer evidence.

## Logic Chain
RRF identity collisions lost individual chunks; widget omitted parent evidence; grounding compared claims to whole chapters and counted nonclaims. SQL filters ignored non-fact queries and L2 filter scope, while Decimal values were omitted from summaries. Mongo selections entered SQLAlchemy, dates used the catalog datetime label, and dimension-only distinct counts lost scope. Each cause was corrected, with typed scope rejection, read-only Mongo plan validation, and truthful fallback behavior.

## Caveats
Configured provider quotas still produce honest fallbacks. Mongo supports a restricted bounded read subset, not arbitrary code/joins. Browser screenshots failed to capture; accessibility evidence was saved. No load, multi-worker, mobile, PDF/OCR, or V2 cutover certification. Existing local demo administrator identities remain development-only. Existing staged work was preserved; no commit/push/deployment was performed.

## Conclusion
DQA-01..10 are archived in todo.md with completion metadata. Changelog and session notes are updated. App and three demo servers are running. Production readiness outside the reviewed acceptance scope is not claimed.

## Verification Method
231 affected backend tests passed; final overlapping edge suite 38 passed; frontend 47 passed; production Vite build and Python compilation passed; diff check clean except informational line-ending notices. Signed live HTTP: East 6 customers / 240 units, all three dashboard policies supported after recorded quota retry, two widget answers supported, Mongo 160 / 16300 and paid 14736, October 60 / 6140, cancelled-only 16 / 1564 with paid 0 and one distinct status, and terminal Mongo SSE done with 14736. See docs/reports/demo_qa_remediation_2026-10-22/REPORT.md, evidence.json and logs.
