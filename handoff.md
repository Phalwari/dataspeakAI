# Handoff Report: Insights Planner V2 — Phase F

## 1. Observation

Phase F's deterministic schema-informed planner is implemented behind `INSIGHTS_PLANNER=v2` on branch `feat/insights-planner-v2`, based on `8c9da10`. The Insights suite passed offline; this does not validate live database providers or arbitrary business schemas.

## 2. Logic Chain

- Catalog discovery captures table/column types, nullability, PK/FK metadata, views and safe row estimates.
- Bounded profiling emits aggregate statistics only; raw sampled values are not retained in profiles.
- Evidence-scored roles feed a pure metric planner. SQL compilation uses catalog identifiers and bound date values; Mongo uses a separate bounded planner.
- The legacy path remains the default. The current direct legacy/V2 parity proof covers the orders/status fixture only.

## 3. Caveats

- F8 is partial; the requested broad ten-family direct legacy/V2 parity review remains open.
- F9 is gated: legacy vocabulary remains, and V2 is not default. Keep it that way until parity review and explicit owner approval.
- Live PostgreSQL, MySQL/MariaDB, MongoDB, browser, live LLM, signed HTTP authentication, multi-worker cache behavior and load are **not verified by execution**.
- The suite retains one expected xfail for the legacy selected-table `missing_table` case.

## 4. Conclusion

Planner V2 is suitable for further offline review and SQLite fixture work as an opt-in implementation. It is not ready to be described as production-ready, fully generic, live-verified across database families, or proven for 100 concurrent users.

## 5. Verification Method

- `python -m pytest @testFiles tests/test_phase3_ai_insights_regression.py -q --disable-warnings` (PowerShell `$testFiles` contains `tests/test_insights_*.py`): **148 passed, 1 xfailed, 22 warnings in 106.43s**.
- Targeted Planner V2 and generic fixtures: **38 passed, 1 warning in 6.68s**.
- `python -m py_compile` across the Planner V2 modules, pipeline, dialect helper, Insights router and FastAPI entry point: **PASS**.
- `git diff --check`: **PASS**.
- Frontend unit suite: **47 passed**. Production build: **PASS** (`2907 modules transformed`); Vite emitted a non-fatal large-chunk warning.
