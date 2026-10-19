# NR-2 remediation handoff — 2026-10-19

## Observation

The user requested that the project be verified and repaired through Phase NR-2. Seven independent probes reproduced real defects despite historical completion labels. The initial audit used revision 6764c57. Workspace HEAD advanced externally to c3fb304 during remediation; its connector and other changes were preserved.

## Logic Chain

Explicit date intervals replace invented row-order growth. A bounded spawned process contains AutoML training; chronological/grouped validation selects one candidate before final holdout evaluation. Grounding initialization failures return typed unverified results. Durable ingestion originals survive retries; failures propagate and duplicate document jobs serialize. Dense and sparse indexes publish together from one merged manifest, recheck tombstones and retain pinned generations. Reconciliation compares SQL with chunk/version/content hashes and repairs by atomic publication, deferring active ingestion. Re-embedding uses the correct model and child chunks. Stream generators explicitly close upstream resources on all exits.

## Caveats

Tests use isolated local SQL/storage and controlled providers; no live-provider quality, distributed worker replacement, real database-network coverage or production recovery claim is made. Four PostgreSQL/MySQL integrations require RUN_LIVE_DATABASE_TESTS=1. NR-3.1-A shared storage/Redis/Celery services and restart/restore evidence remain prerequisites. Local file locks require a shared filesystem. Published generations are retained for reader safety and need operational capacity planning. The existing frontend bundle-size warning remains. Verification preceded publication. The user subsequently authorized committing and pushing the tested history to origin/main; no deployment was performed.

## Conclusion

All seven repair tasks and local verification are complete. The tracker has 43 unique historical NR-2 roadmap task blocks, seven archived repairs and one active phase section. The remaining evidence task and production gate stay unchecked. NR-3.1-A infrastructure and NR-3.2-A verification can proceed according to prerequisites; NR-4/NR-5 remain behind the NR1 release gate.

## Verification Method

The isolated launcher run_verification.py disables provider traffic/downloads, uses a cached embedding model and separate temporary SQL/storage. final_test_groups.json selects all 55 default files without overlap (54 contain collected test cases). Final JUnit results: final_core 590 passed/4 skipped, final_migrations 32 passed, lifecycle_final 34 default passes plus 19 FYP passes. Thus default backend: 656 passed/4 skipped/0 failures/0 errors. Remediation regressions: 16 included passes. Controlled workflow tests exercise 50 cases and 30 stream samples. Frontend: 35 passed and production build passed. Dependency consistency passed. git diff --check passed after tracker cleanup.

Authoritative user-facing record: docs/reports/nr2_remediation_2026-10-19.md. Machine-readable counts, selected files and XML hashes: docs/reports/nr2_evidence_2026-10-19/verification-summary.json. Session history: docs/sessions/2026-10-19_nr2_remediation.md. Earlier failed/superseded XML files are historical diagnostics, not final evidence.
