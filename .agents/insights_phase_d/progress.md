# Insights Phase D progress

- Date: 2026-10-20
- Branch: `feat/insights-wip-baseline`
- D2: completed for bounded calendar filters, matching prior-year comparisons, server-backed presets, and applied-range metadata.
- D3: completed for centralized SQL fragments and unknown-dialect rejection; live SQL connectors remain unverified.
- D4: completed for Mongo branch priority, exact filtered count/chart bounds, and client cleanup; live MongoDB remains unverified.
- Generic fixtures: orders/status, misleading names, quantity without price, HR/inventory, and Mongo mock covered. Chinook was not used.
- Verification: scoped Insights suite `41 passed, 1 xfailed, 22 warnings`; Python compile and Vite build passed.
- Outstanding: `missing_table` strict xfail; schema-derived planning, live connector execution, browser rendering, signed HTTP auth, and 100-user capacity remain unverified.
- Seven pre-existing connection-layer and Databases page worktree modifications were not staged or committed.
