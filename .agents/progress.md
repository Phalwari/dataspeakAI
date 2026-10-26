# Progress — Insights Phase F

## Chatbot reliability fix — 2026-10-22

- **Status:** Implemented and live-tested.
- **Changes:** Added deterministic SQL/hybrid routing, MongoDB collection-aware selection, catalog-grounded Mongo fallback plans, and an 18-second total streaming provider deadline.
- **Verification:** Backend `compileall` passed; frontend production build passed; live PostgreSQL, MySQL, MongoDB, and mixed database/document chatbot scenarios were exercised. PostgreSQL returned 240 orders, MySQL returned 185 delivered orders/$23,695, MongoDB returned 144 paid invoices/$14,736, and the mixed query returned 240 orders/$30,200 plus the $100 free-shipping threshold from `coffee_retail_policy.txt`.
- **Frontend fix:** Chat SSE parsing now flushes a final unterminated frame, preventing completed answers from remaining stuck on “Thinking & streaming…” until reload.
- **Caveat:** Provider key validity/quota remains external; fallback behavior is bounded and explicit. Mixed-answer grounding reported partial confidence (2/7 claims), so document-derived claims should remain visibly caveated.

## Ten-turn chatbot verification — 2026-10-22

- **Scenario:** Fresh sequential conversation spanning PostgreSQL coffee orders, Harbor Coffee policy, MySQL solar orders, Orbit policy, MongoDB subscription invoices, and a cross-source comparison.
- **Measured outcome:** PostgreSQL turns 1–2 were correct (240 orders; $30,200). Harbor policy turns returned the $100 threshold and Orbit policy returned $199 Enterprise pricing with cancellation before renewal. The threshold-count turn returned 80 but was routed as SQL without document citation. MySQL turns returned the expected 185/$23,695 and $128.08, but persisted metadata incorrectly identified PostgreSQL database 1. MongoDB turns 8–9 incorrectly inherited PostgreSQL and returned 0/$0 and 240/$30,200 instead of the verified MongoDB 144/$14,736 and 160/$16,300. The final hybrid comparison therefore compared the wrong subscription source and reported low grounding confidence.
- **Primary issue:** Prior-database continuity executes before explicit source/database references and overrides `MySQL`, `MongoDB`, `Subscription Billing`, and `Solar Wholesale` mentions. The next fix should prioritize explicit source selection, normalize connection-label token matching, and add provenance assertions to the 10-turn regression test.
- **Operational issue:** The backend process dropped once during the first attempt; it restarted successfully and the second run completed. Gemini quota/provider errors were frequent, causing fallback generation and elevated response latency.

## Routing fix and retest — 2026-10-22

- **Implemented:** Explicit source matching now recognizes dialect aliases and connection-label tokens; prior-database continuity is skipped when a new source is named. Mixed policy/data questions route to hybrid. Multi-source comparisons route to a safe no-single-source fallback rather than allowing an LLM to synthesize from prior context.
- **Retest:** MongoDB paid invoices returned **144 / $14,736** and total invoices returned **160 / $16,300**, both with `database_id=3` and `Demo | Subscription Billing | MongoDB` provenance. A mixed PostgreSQL/policy question returned **80** qualifying orders and document citations. MySQL direct ground truth is **139 delivered / $94,125 / $677.158273 average**, and the corrected chatbot response matched those values and `database_id=2`.
- **Safety verification:** Cross-source comparison metadata is now `hybrid` with `database_id=null` and the UI states that source-specific queries must be run before comparison; no fabricated SQL is executed.
- **Remaining:** The New Conversation control intermittently redirects to `/dashboard` instead of clearing the chat, and Gemini/Groq quota errors still cause fallback responses and latency spikes.

- **Date:** 2026-10-21
- **Branch:** `feat/insights-planner-v2` (`8c9da10` base)
- **Worktree:** `C:\Users\waliu\OneDrive - Higher Education Commission\Desktop\dataspeakAI_phase_f`
- **Status:** F0–F7 implemented on the opt-in path; F8 paired checks cover five SQLite fixture families and remain partial. F9 default cutover and legacy removal pending ten-family parity and owner approval.
- **Latest verification:** Insights `148 passed, 1 xfailed, 22 warnings in 106.43s`; targeted Planner V2 `38 passed`; frontend unit tests `47 passed`; production build and targeted `py_compile` passed; `git diff --check` passed.
- **Unverified:** live PostgreSQL, MySQL/MariaDB, MongoDB, browser rerun, signed HTTP auth, production LLM, multi-worker cache, and load.
- **Next:** complete direct legacy/V2 fixture parity; do not change the default or remove legacy without explicit approval.
