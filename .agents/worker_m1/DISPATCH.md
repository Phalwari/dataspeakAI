## 2026-08-05T21:58:48Z

You are worker_m1.
Your working directory is d:\dataspeak\.agents\worker_m1\.
Please read d:\dataspeak\.agents\ORIGINAL_REQUEST.md, d:\dataspeak\PROJECT.md, and d:\dataspeak\.agents\explorer_security\handoff.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your Task: Implement Milestone 1 - Security Hardening & Bug Fixes:
1. Add `cryptography` to `backend/requirements.txt`.
2. Implement Fernet encryption and decryption functions in `backend/crypto.py` (using `SECRET_KEY` or `ENCRYPTION_KEY`). Update `backend/routers/databases.py` and `backend/models.py` so database passwords are encrypted on `add_database` and decrypted when creating connection URLs in `get_connection_url`. Include fallback handling for existing unencrypted plaintext passwords.
3. Fix dynamic SQL identifier injection in `backend/routers/databases.py`: In `/api/databases/{db_id}/tables/{table_name}/data` and `/stats`, retrieve valid table names from `inspector.get_table_names()` and verify `table_name` is valid before query execution. Reject invalid table names with HTTP 400.
4. Remove hardcoded secrets:
   - Remove hardcoded default `SECRET_KEY = "super_secret_key_for_fyp"` fallback in `backend/auth.py` (load safely from env).
   - Remove hardcoded GitHub OAuth Client ID (`Ov23liPRgons4RlFv7FU`) and Secret (`067e59b3c050792898954f727be0dbdbfc5c590a`) in `backend/routers/users.py`. Require environment variables `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET`. If missing when route is called, raise an HTTP 500 error explaining they are not configured.
   - Replace hardcoded `http://localhost:5173` in `backend/routers/tenants.py` with `os.getenv("FRONTEND_URL", "http://localhost:5173")`.
5. Authorize Admin access:
   - Add `get_current_admin_user` dependency in `backend/dependencies.py` checking `current_user.role == "Admin"`.
   - Update `src/app/routes.ts` and `src/app/pages/admin/AdminPanel.tsx` to guard `/admin` and redirect non-admin/unauthenticated users to `/dashboard`.
6. Fix SQLite Introspection Bug:
   - Remove the duplicate `get_connection_url` function definition in `backend/routers/databases.py` (lines 92-97) so SQLite connection strings are handled properly by the primary `get_connection_url` function.
7. Environment & Backend Import Alignment:
   - Change `.env.example` line 2 from `VITE_API_URL` to `VITE_API_BASE_URL`.
   - Update `backend/main.py` so `python -c "import backend.main"` succeeds from project root.

Verification Commands:
Run `python -c "import backend.main"` to verify backend imports cleanly.
Run `npm run build` to verify frontend builds with 0 errors.

Write your handoff report to `d:\dataspeak\.agents\worker_m1\handoff.md` and update `progress.md`.
Send a message when completed.
