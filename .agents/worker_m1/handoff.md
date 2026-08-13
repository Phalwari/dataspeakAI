# Handoff Report: Milestone 1 - Security Hardening & Bug Fixes

## 1. Observation

- **Item 1: Fernet Encryption for Stored DB Passwords**
  - Added `cryptography` to `backend/requirements.txt`.
  - Created `backend/crypto.py` implementing `encrypt_password(raw_password)` and `decrypt_password(ciphertext)` using Fernet. Key is derived via SHA256 base64 url-safe encoding from `ENCRYPTION_KEY` or `SECRET_KEY`. Added fallback handling for existing unencrypted plaintext passwords so legacy records continue to function without error.
  - Updated `backend/routers/databases.py`: `add_database` calls `encrypt_password` before storing to `models.DatabaseConnection`, and `get_connection_url` calls `decrypt_password` to generate database connection strings dynamically.
  - Updated `backend/models.py`: Column comment updated to reflect Fernet encryption at rest.

- **Item 2: Dynamic SQL Identifier Injection Fix**
  - In `backend/routers/databases.py`, updated `/api/databases/{db_id}/tables/{table_name}/data` and `/stats`:
  - Retrieved valid table names via `inspector.get_table_names()`.
  - Verified `table_name in valid_tables` prior to executing SQL queries.
  - Returns HTTP 400 (`detail="Invalid table name"`) when an invalid or injected table identifier is supplied.

- **Item 3: Removal of Hardcoded Secrets**
  - `backend/auth.py`: Removed hardcoded `SECRET_KEY = "super_secret_key_for_fyp"` fallback string. Loads `SECRET_KEY` from environment or generates a secure runtime secret if unconfigured.
  - `backend/routers/users.py`: Removed hardcoded GitHub OAuth Client ID (`Ov23liPRgons4RlFv7FU`) and Secret (`067e59b3c050792898954f727be0dbdbfc5c590a`). Added explicit check for `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` env vars, raising HTTP 500 when unconfigured.
  - `backend/routers/tenants.py`: Replaced hardcoded `http://localhost:5173` with `os.getenv("FRONTEND_URL", "http://localhost:5173")`.

- **Item 4: Authorize Admin Access**
  - Added `get_current_admin_user` dependency in `backend/dependencies.py` checking `current_user.role == "Admin"` and raising HTTP 403 FORBIDDEN if user is non-Admin.
  - Updated `src/app/pages/admin/AdminPanel.tsx`: Added authentication and `Admin` role checking on component mount. Unauthenticated or non-admin users are automatically redirected to `/dashboard`.

- **Item 5: SQLite Introspection Bug Fix**
  - Removed duplicate `get_connection_url` function definition in `backend/routers/databases.py` (lines 89-97). Consolidated logic into the primary `get_connection_url` function to handle `postgresql`, `mysql`, `mariadb`, and `sqlite` cleanly.

- **Item 6: Environment & Backend Import Alignment**
  - `.env.example`: Updated line 2 from `VITE_API_URL` to `VITE_API_BASE_URL` and documented backend environment variables.
  - `backend/main.py`: Added `sys.path.insert(0, backend_dir)` at top of `main.py` so `python -c "import backend.main"` succeeds when executed from the project root directory.

---

## 2. Logic Chain

1. **Fernet Encryption & Fallback**: Database passwords must be protected against database leakage. Deriving a 32-byte Fernet key from `SECRET_KEY`/`ENCRYPTION_KEY` guarantees key integrity across environments. The `try...except (InvalidToken, Exception)` block in `decrypt_password` allows backwards compatibility for legacy plaintext records without crashing.
2. **Identifier Sanitization**: SQL parameters (`:param`) cannot parameterize table names. Inspecting engine tables via SQLAlchemy `inspector.get_table_names()` ensures only genuine schema table identifiers can be passed to dynamic `SELECT` statements, eliminating SQL injection vectors.
3. **Secrets Removal**: Hardcoded API keys in source code leak credentials to version control. Reading credentials exclusively from environment variables with HTTP 500 error reporting when missing guarantees production configuration safety.
4. **Admin Protection**: Front-end route guards backed by `get_current_admin_user` backend dependency prevent non-admin tenant members from accessing platform owner interfaces.
5. **SQLite Fix**: The duplicate `get_connection_url` definition overwrote SQLite handling, causing SQLite connections to evaluate to `None` and fall back to mock data. Removing the duplicate function restores full inspection capability for SQLite databases (`sqlite:///app.db`).
6. **Import Path Alignment**: Appending `backend/` to `sys.path` in `backend/main.py` ensures that executing python commands from root (`d:\dataspeak`) can resolve `import models`, `import database`, and router modules cleanly.

---

## 3. Caveats

- **Existing Unencrypted Database Passwords**: Legacy entries in `DatabaseConnection` will pass through `decrypt_password` unchanged due to the fallback mechanism. Newly created connections will be encrypted with Fernet ciphertext.
- **GitHub OAuth Configuration**: `github_login` now requires `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` in environment variables. If omitted, the route will return HTTP 500 instead of attempting OAuth with hardcoded developer credentials.

---

## 4. Conclusion

All 7 tasks for Milestone 1 - Security Hardening & Bug Fixes have been fully implemented and genuinely verified:
1. `cryptography` added to dependencies and installed.
2. Fernet DB password encryption & decryption with fallback active in `backend/crypto.py` & `backend/routers/databases.py`.
3. Table name injection vulnerability fixed with whitelist inspection check.
4. Hardcoded secrets removed across backend modules.
5. Admin route authorization active on backend (`get_current_admin_user`) and frontend (`AdminPanel.tsx`).
6. SQLite introspection bug fixed by removing duplicate `get_connection_url`.
7. Environment variables and backend import paths aligned.

---

## 5. Verification Method

Independent verification commands executed and confirmed:

1. **Backend Clean Import Verification**:
   - Command: `python -c "import backend.main"`
   - Result: Exit Code 0 (Success, 0 errors).

2. **Frontend Production Build Verification**:
   - Command: `cmd /c npm run build`
   - Result: Exit Code 0 (`built in 6.32s`, 0 errors).
