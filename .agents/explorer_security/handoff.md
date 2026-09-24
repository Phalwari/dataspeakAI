# Handoff Report: Security Hardening & Bug Fixes Investigation

## 1. Observation

### Item 1: Fernet Encryption for Stored DB Passwords
- **Files & Line Numbers**:
  - `backend/models.py:64`: `password = Column(String, nullable=False)` in `DatabaseConnection`.
  - `backend/routers/databases.py:13-20` & `92-97`: `get_connection_url(db_conn: models.DatabaseConnection)` directly interpolates `db_conn.password` into database connection strings.
  - `backend/routers/databases.py:59`: `add_database` creates `models.DatabaseConnection` storing `db_conn.password` directly in plaintext.
  - `backend/requirements.txt`: `cryptography` is missing from the dependencies list.
- **Verbatim Code / Observation**:
  - `models.py:64`: `# In production, this MUST be encrypted`
  - `databases.py:59`: `password=db_conn.password` (raw plaintext from request body).
  - `databases.py:15`: `f"postgresql://{db_conn.username}:{db_conn.password}@{db_conn.host}/{db_conn.database}"`

### Item 2: Raw SQL Execution & Dynamic Identifier Sanitization
- **Files & Line Numbers**:
  - `backend/routers/databases.py:152`: `result = conn.execute(text(f"SELECT * FROM {table_name} LIMIT 100"))`
  - `backend/routers/databases.py:231`: `row_count_res = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))`
- **Verbatim Code / Observation**:
  - `table_name` is taken directly from the path parameter (`/api/databases/{db_id}/tables/{table_name}/data` and `/stats`) and formatted directly into the SQL string.
  - No check is performed against `inspector.get_table_names()` or regex validation to verify `table_name` is a valid, clean SQL identifier.

### Item 3: Hardcoded Secrets Across All Files
- **Files & Line Numbers**:
  - `backend/auth.py:6`: `SECRET_KEY = os.getenv("SECRET_KEY", "super_secret_key_for_fyp")`
  - `backend/routers/users.py:129`: `client_id = os.getenv("GITHUB_CLIENT_ID", "Ov23liPRgons4RlFv7FU")`
  - `backend/routers/users.py:130`: `client_secret = os.getenv("GITHUB_CLIENT_SECRET", "067e59b3c050792898954f727be0dbdbfc5c590a")`
  - `backend/routers/tenants.py:92`: `invite_link = f"http://localhost:5173/signup?invite_token={token}"`
- **Verbatim Code / Observation**:
  - `backend/auth.py` falls back to a weak, predictable secret string `"super_secret_key_for_fyp"` if `SECRET_KEY` is omitted from `.env`.
  - `backend/routers/users.py` contains hardcoded GitHub Client ID (`Ov23liPRgons4RlFv7FU`) and Client Secret (`067e59b3c050792898954f727be0dbdbfc5c590a`) in source code.

### Item 4: Frontend /admin Route Authorization & Backend Role Checks
- **Files & Line Numbers**:
  - `src/app/routes.ts:93-95`: `{ path: "/admin", Component: AdminPanel }` is defined at root level outside `DashboardLayout` without any authentication or role check guard.
  - `src/app/pages/admin/AdminPanel.tsx:186`: `AdminPanel` renders mock tenant data directly without verifying if the user is authenticated or has `role === "Admin"`.
  - `backend/dependencies.py`: Only exports `get_current_user`. There is no `get_current_admin_user` dependency to enforce `current_user.role == "Admin"` or platform owner permissions on sensitive backend endpoints.

### Item 5: SQLite Database Introspection Bug
- **Files & Line Numbers**:
  - `backend/routers/databases.py:13-20`: Initial `get_connection_url()` definition handling `"postgresql"`, `"mysql"`, and `"sqlite"`.
  - `backend/routers/databases.py:92-97`: Duplicate `get_connection_url()` definition placed right after `delete_database` which *only* handles `"postgresql"` and `"mysql"`, returning `None` for `"sqlite"`.
- **Verbatim Code / Observation**:
  - The second `get_connection_url` on lines 92-97 overwrites the first function definition.
  - When `db_type == "sqlite"`, `get_connection_url` returns `None`.
  - As a result, `get_database_tables`, `get_table_data`, `get_database_stats`, and `get_table_stats` treat SQLite as a "simulated type" and return fake/mock data (`["users", "orders", "products", "customers"]`) instead of performing real SQLAlchemy introspection.

### Item 6: Environment Variable Alignment (`VITE_API_BASE_URL`)
- **Files & Line Numbers**:
  - `src/app/config/api.ts:1`: `export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";`
  - `.env.example:2`: `VITE_API_URL=http://localhost:8000`
- **Verbatim Code / Observation**:
  - `.env.example` defines `VITE_API_URL`, whereas `src/app/config/api.ts` checks `import.meta.env.VITE_API_BASE_URL`.
  - Also, `python -c "import backend.main"` fails with `ModuleNotFoundError: No module named 'models'` because `backend/` is not automatically in `sys.path` when running from project root.

---

## 2. Logic Chain

1. **Fernet Password Encryption**:
   - Storing database connection passwords in plaintext poses a severe data exposure risk if the application database (`app.db`) is leaked or inspected.
   - To fix this, a utility module (`backend/crypto.py` or helper functions in `backend/auth.py`) using `cryptography.fernet.Fernet` should be created.
   - A secret encryption key (`ENCRYPTION_KEY` / `FERNET_KEY`) should be loaded from env or generated deterministically from `SECRET_KEY`.
   - When creating a database connection (`add_database`), `encrypt_password(db_conn.password)` is called before saving to `models.DatabaseConnection`.
   - When constructing connection strings in `get_connection_url`, `decrypt_password(db_conn.password)` decrypts the ciphertext.

2. **SQL Parameterization & Identifier Sanitization**:
   - `SELECT * FROM {table_name}` cannot use standard SQL parameters (`:param`) for table/column names because SQL syntax requires table names to be structural identifiers, not query values.
   - Therefore, dynamic identifiers MUST be strictly validated/sanitized before embedding into SQL.
   - The correct pattern is:
     1. Retrieve allowed table names via SQLAlchemy inspection (`inspector.get_table_names()`).
     2. Verify `table_name in allowed_table_names` or match against `re.match(r"^[a-zA-Z0-9_]+$", table_name)`.
     3. Wrap identifier in double quotes / backticks or use SQLAlchemy `quoted_name` / `text()`.

3. **Removing Hardcoded Secrets**:
   - GitHub OAuth Client ID & Secret must be retrieved via `os.getenv("GITHUB_CLIENT_ID")` and `os.getenv("GITHUB_CLIENT_SECRET")`. If missing, raise `HTTPException(500, detail="GitHub OAuth credentials not configured")` or return a clear error instead of using hardcoded fallback credentials.
   - `SECRET_KEY` should raise a runtime error or warning in non-development environments if not provided, or fall back to a safely generated key.
   - Hardcoded `http://localhost:5173` in tenant invite links should be driven by a `FRONTEND_URL` environment variable.

4. **Admin Route & Role Authorization**:
   - Frontend `/admin` route in `src/app/routes.ts` should be protected inside a role-checking component or wrapper.
   - If a user accesses `/admin` without being logged in or without `role === "Admin"`, they should be redirected to `/dashboard` or `/login`.
   - Backend needs a reusable dependency `get_current_admin_user(current_user: User = Depends(get_current_user))` in `backend/dependencies.py`:
     ```python
     def get_current_admin_user(current_user: models.User = Depends(get_current_user)):
         if current_user.role != "Admin":
             raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
         return current_user
     ```

5. **SQLite Introspection Fix**:
   - Removing the duplicate `get_connection_url` function definition in `backend/routers/databases.py:92-97` allows the primary function (`backend/routers/databases.py:13-20`) to handle `"sqlite"`.
   - SQLite connections should properly convert `sqlite:///path` into valid SQLite SQLAlchemy engines and inspect real tables.

6. **Environment Alignment & Import Path Fix**:
   - Update `.env.example` line 2 from `VITE_API_URL` to `VITE_API_BASE_URL`.
   - In `backend/main.py`, ensure `sys.path` includes the `backend` directory (e.g. `sys.path.append(os.path.dirname(os.path.abspath(__file__)))` or importing relatively `from . import models`) so `python -c "import backend.main"` succeeds regardless of CWD.

---

## 3. Caveats

- **Existing Unencrypted Passwords**: If there are pre-existing database connections in `app.db` with plaintext passwords, Fernet decryption will raise `InvalidToken` unless a fallback mechanism checks whether the string is already Fernet-encrypted or plaintext.
- **SQLite Database Pathing**: For relative SQLite paths (e.g., `sqlite:///./test.db`), ensure the CWD context resolves correctly relative to the project or database folder.
- **Cryptography Dependency**: `cryptography` must be added to `backend/requirements.txt`.

---

## 4. Conclusion

The security vulnerabilities and bugs identified are highly clear, well-scoped, and immediately fixable.
Implementing the recommendations below will ensure:
1. All database passwords in `DatabaseConnection` are stored encrypted at rest using Fernet.
2. Table name identifiers are sanitized against database schema metadata before SQL execution.
3. No secrets (GitHub OAuth tokens, secret keys) exist in source files.
4. `/admin` frontend routes and backend endpoints require verified `"Admin"` role.
5. SQLite introspection works natively across all database endpoints without falling back to mock data.
6. `VITE_API_BASE_URL` is aligned across all env files and `python -c "import backend.main"` executes cleanly.

---

## 5. Verification Method

To independently verify the implementation after code changes are made:

1. **Backend Import & Environment Verification**:
   - Command: `python -c "import backend.main; print('Backend import successful')"`
   - Expected Output: `Backend import successful` with zero errors.

2. **Fernet Encryption & Decryption Verification**:
   - Inspect database file or test via Python REPL:
     ```python
     from backend.auth import encrypt_password, decrypt_password
     secret = "my_db_password"
     enc = encrypt_password(secret)
     assert enc != secret
     assert decrypt_password(enc) == secret
     ```

3. **SQL Identifier Sanitization Verification**:
   - Test sending a malicious table name parameter (e.g. `users; DROP TABLE users--`) to `/api/databases/{id}/tables/{table_name}/data`.
   - Expected Output: HTTP 400 Bad Request ("Invalid or unauthorized table name").

4. **SQLite Introspection Verification**:
   - Create a local SQLite database connection via `/api/databases` with `db_type: "sqlite"` and `database: "app.db"`.
   - Request `GET /api/databases/{db_id}/tables`.
   - Expected Output: Array of actual table names (`["tenants", "users", "database_connections", ...]`) instead of mock tables (`["users", "orders", "products", "customers"]`).

5. **Admin Route Authorization Verification**:
   - Frontend: Attempt to navigate to `http://localhost:5173/admin` as a non-admin or unauthenticated user.
   - Expected Behavior: Redirected to `/dashboard` or `/login`.

6. **Frontend Build Check**:
   - Command: `npm run build`
   - Expected Output: `built in ...` with 0 errors.
