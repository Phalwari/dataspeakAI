import os
import sys

# Ensure backend directory is in sys.path (matching backend/main.py pattern)
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from backend.services.sql_engine import validate_read_only_sql, execute_safe_sql, get_db_schema_context
import models

def test_sql_guardrails():
    valid_cases = [
        ("SELECT * FROM users", True),
        ("SELECT id, name FROM users WHERE role = 'Admin'", True),
        ("WITH cte AS (SELECT * FROM orders) SELECT * FROM cte", True),
        ("SELECT user_id, COUNT(*) FROM orders GROUP BY user_id HAVING COUNT(*) > 5 ORDER BY user_id DESC", True),
        ("SELECT * FROM users WHERE email LIKE '%@example.com'", True),
        ("SELECT * FROM users;", True),
        ("  SELECT   *  FROM   users  ;  ", True),
        ("/* comment */ SELECT * FROM users", True),
        ("SELECT * FROM users -- inline comment", True),
        ("WITH u AS (SELECT id, email FROM users), o AS (SELECT user_id, total_amount FROM orders) SELECT u.email, o.total_amount FROM u JOIN o ON u.id = o.user_id", True),
    ]

    malicious_cases = [
        # Direct DML / DDL
        ("DELETE FROM users WHERE 1=1", False),
        ("DROP TABLE users", False),
        ("UPDATE users SET role = 'admin'", False),
        ("INSERT INTO users (email) VALUES ('hacker@evil.com')", False),
        ("ALTER TABLE users ADD COLUMN secret TEXT", False),
        ("TRUNCATE TABLE logs", False),
        ("CREATE TABLE evil (id INT)", False),
        ("REPLACE INTO users VALUES (1, 'test')", False),
        ("MERGE INTO target USING source ON target.id = source.id", False),
        ("UPSERT INTO users VALUES (1)", False),
        ("EXEC sp_executesql", False),
        ("EXECUTE ('DELETE FROM users')", False),
        ("ATTACH DATABASE 'evil.db' AS evil", False),
        ("DETACH DATABASE evil", False),
        # Stacked / Semicolon Chaining
        ("SELECT * FROM users; DROP TABLE users", False),
        ("SELECT * FROM users; DELETE FROM users;", False),
        ("SELECT * FROM users; SELECT * FROM orders;", False),
        ("; DROP TABLE users", False),
        ("SELECT 1;\nUPDATE users SET name='x';", False),
        ("SELECT * FROM users ; DROP TABLE users ;", False),
        # CTE mutations
        ("WITH deleted AS (DELETE FROM users RETURNING *) SELECT * FROM deleted", False),
        ("WITH inserted AS (INSERT INTO users (email) VALUES ('a') RETURNING *) SELECT * FROM inserted", False),
        # Evasion / Obfuscation / Casing
        ("dElEtE fRoM uSeRs", False),
        ("SELECT * FROM users; dRoP tAbLe uSeRs", False),
        ("/* test */ DROP TABLE users", False),
        ("EXPLAIN SELECT * FROM users", False),
        ("SHOW TABLES", False),
        ("GRANT ALL ON users TO public", False),
        ("REVOKE ALL ON users FROM public", False),
        ("SHUTDOWN", False),
    ]

    print("=== RUNNING SQL GUARDRAIL TEST SUITE ===")
    passed = 0
    failed = 0

    print("\n--- Testing Valid Read-Only Queries ---")
    for query, expected in valid_cases:
        is_valid, reason = validate_read_only_sql(query)
        if is_valid == expected:
            print(f"[PASS] Valid Query Allowed: {repr(query)}")
            passed += 1
        else:
            print(f"[FAIL] Valid Query Blocked: {repr(query)} | Reason: {reason}")
            failed += 1

    print("\n--- Testing Malicious / Mutation / Injection Queries ---")
    for query, expected in malicious_cases:
        is_valid, reason = validate_read_only_sql(query)
        if is_valid == expected:
            print(f"[PASS] Malicious Query Blocked: {repr(query)} | Reason: {reason}")
            passed += 1
        else:
            print(f"[FAIL] Malicious Query ALLOWED (VULNERABILITY!): {repr(query)}")
            failed += 1

    print(f"\nGuardrail Test Summary: {passed} passed, {failed} failed out of {len(valid_cases) + len(malicious_cases)} tests.")
    return failed == 0

def test_backend_import():
    print("\n=== RUNNING BACKEND IMPORT TEST ===")
    try:
        import backend.main
        print("[PASS] Successfully imported backend.main")
        return True
    except Exception as e:
        print(f"[FAIL] Failed to import backend.main: {e}")
        return False

def test_live_execution():
    print("\n=== RUNNING LIVE EXECUTION TEST ===")
    try:
        app_db_path = os.path.abspath(os.path.join(root_dir, "app.db"))
        conn = models.DatabaseConnection(
            id=1,
            tenant_id=1,
            name="Test SQLite",
            db_type="sqlite",
            host="localhost",
            username="admin",
            password="fake",
            database=app_db_path
        )
        
        ctx = get_db_schema_context(conn)
        print(f"[PASS] Introspected Schema Context ({len(ctx)} chars)")

        res = execute_safe_sql(conn, "SELECT * FROM users;")
        print(f"[PASS] Executed Safe SQL: returned {res['row_count']} rows in {res['execution_time_ms']} ms")
        print(f"       Columns: {res['columns']}")
        
        try:
            execute_safe_sql(conn, "DELETE FROM users;")
            print("[FAIL] execute_safe_sql allowed DELETE query!")
            return False
        except ValueError as ve:
            print(f"[PASS] execute_safe_sql blocked DELETE query as expected: {ve}")

        return True
    except Exception as e:
        print(f"[FAIL] Live execution error: {e}")
        return False

if __name__ == "__main__":
    guardrail_ok = test_sql_guardrails()
    live_ok = test_live_execution()
    import_ok = test_backend_import()
    
    if guardrail_ok and import_ok and live_ok:
        print("\nALL EMPIRICAL TESTS PASSED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print("\nEMPIRICAL TESTS FAILED!")
        sys.exit(1)
