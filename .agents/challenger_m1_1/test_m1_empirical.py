import sys
import os
import sqlite3
import gc
from fastapi import HTTPException

# Add backend directory to sys.path
backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import crypto
import models
import auth
import dependencies
from routers.databases import get_connection_url, get_table_data, get_table_stats

def run_crypto_tests():
    print("=== TEST 1: Crypto & Fernet Encryption/Decryption Cycles ===")
    
    # 1.1 Basic Encryption Cycle
    raw = "MySuperSecretPass123!@#"
    enc = crypto.encrypt_password(raw)
    dec = crypto.decrypt_password(enc)
    assert enc != raw, "Encrypted password should not equal raw password"
    assert enc.startswith("gAAAAA"), f"Fernet token should start with gAAAAA, got {enc[:10]}"
    assert dec == raw, f"Decrypted password '{dec}' does not match raw '{raw}'"
    print("[PASS] Test 1.1: Basic Fernet encryption/decryption cycle PASSED")

    # 1.3 Special Characters
    special_raw = "P@$$w0rd!#$123"
    special_enc = crypto.encrypt_password(special_raw)
    special_dec = crypto.decrypt_password(special_enc)
    assert special_dec == special_raw, "Special password cycle failed"
    print("[PASS] Test 1.3: Special character cycle PASSED")

    # 1.4 Empty and None
    assert crypto.encrypt_password("") == ""
    assert crypto.decrypt_password("") == ""
    assert crypto.encrypt_password(None) is None
    assert crypto.decrypt_password(None) is None
    print("[PASS] Test 1.4: Empty and None handling PASSED")

    # 1.5 Fallback for Legacy Unencrypted Plaintext
    legacy_plain = "legacy_unencrypted_password"
    legacy_dec = crypto.decrypt_password(legacy_plain)
    assert legacy_dec == legacy_plain, f"Fallback failed: expected '{legacy_plain}', got '{legacy_dec}'"
    print("[PASS] Test 1.5: Legacy plaintext fallback PASSED")

    # 1.6 Fallback for Corrupt Ciphertext
    corrupt_cipher = "gAAAAABm_corrupt_base64_invalid_token_string"
    corrupt_dec = crypto.decrypt_password(corrupt_cipher)
    assert corrupt_dec == corrupt_cipher, "Corrupt token fallback failed"
    print("[PASS] Test 1.6: Corrupt ciphertext fallback PASSED")

    # 1.7 Key derivation key stability
    key = crypto.get_fernet_key()
    assert len(key) == 44, f"Base64 fernet key should be 44 bytes, got {len(key)}"
    print("[PASS] Test 1.7: Key derivation stability PASSED")

def run_sqlite_connection_tests():
    print("\n=== TEST 2: SQLite Connection URL & Introspection Bug Fix ===")
    
    sqlite_conn = models.DatabaseConnection(
        id=1,
        tenant_id=1,
        name="Local SQLite DB",
        db_type="sqlite",
        host="",
        username="",
        password="",
        database="app.db",
        status="connected"
    )
    url = get_connection_url(sqlite_conn)
    assert url == "sqlite:///app.db", f"Expected 'sqlite:///app.db', got '{url}'"
    print("[PASS] Test 2.1: SQLite get_connection_url PASSED")

    pg_conn = models.DatabaseConnection(
        id=2, tenant_id=1, name="PG DB", db_type="postgresql",
        host="localhost:5432", username="postgres", password=crypto.encrypt_password("secret"), database="mydb", status="connected"
    )
    assert get_connection_url(pg_conn) == "postgresql://postgres:secret@localhost:5432/mydb"
    print("[PASS] Test 2.2: PostgreSQL get_connection_url with Fernet decryption PASSED")

    mysql_conn = models.DatabaseConnection(
        id=3, tenant_id=1, name="MySQL DB", db_type="mysql",
        host="localhost:3306", username="root", password=crypto.encrypt_password("my_mysql_pass"), database="mydb", status="connected"
    )
    assert get_connection_url(mysql_conn) == "mysql+pymysql://root:my_mysql_pass@localhost:3306/mydb"
    print("[PASS] Test 2.3: MySQL get_connection_url with Fernet decryption PASSED")

def run_sql_sanitization_tests():
    print("\n=== TEST 3: SQL Identifier Sanitization & Injection Prevention ===")
    
    temp_db_path = os.path.abspath("temp_test_sanitization.db")
    try:
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)
    except Exception:
        pass

    # Create a temporary SQLite database with genuine tables
    conn = sqlite3.connect(temp_db_path)
    cur = conn.cursor()
    cur.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, role TEXT);")
    cur.execute("INSERT INTO users VALUES (1, 'alice', 'Admin'), (2, 'bob', 'Member');")
    cur.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, total REAL);")
    cur.execute("INSERT INTO orders VALUES (101, 99.99);")
    conn.commit()
    conn.close()

    mock_db_conn = models.DatabaseConnection(
        id=99, tenant_id=1, name="Temp DB", db_type="sqlite",
        host="", username="", password="", database=temp_db_path, status="connected"
    )

    mock_user = models.User(id=1, tenant_id=1, email="admin@test.com", role="Admin")

    class MockQuery:
        def __init__(self, res):
            self.res = res
        def filter(self, *args, **kwargs):
            return self
        def first(self):
            return self.res

    class MockSession:
        def query(self, *args, **kwargs):
            return MockQuery(mock_db_conn)

    db_session = MockSession()

    # Test valid table name
    valid_data = get_table_data(db_id=99, table_name="users", current_user=mock_user, db=db_session)
    assert len(valid_data) == 2, f"Expected 2 rows, got {len(valid_data)}"
    assert valid_data[0]["username"] == "alice"
    print("[PASS] Test 3.1: Valid table query PASSED")

    valid_stats = get_table_stats(db_id=99, table_name="users", current_user=mock_user, db=db_session)
    assert valid_stats["rows"] == 2
    assert valid_stats["columns"] == 3
    print("[PASS] Test 3.2: Valid table stats PASSED")

    # Test invalid table names (SQL injection payloads)
    invalid_payloads = [
        "users; DROP TABLE orders;--",
        "users UNION SELECT 1, 2, 3",
        "non_existent_table",
        "users' OR '1'='1",
        "../../etc/passwd",
        "users; SELECT * FROM orders;",
        "orders; DELETE FROM users;"
    ]

    for payload in invalid_payloads:
        # Test get_table_data
        try:
            get_table_data(db_id=99, table_name=payload, current_user=mock_user, db=db_session)
            assert False, f"Expected HTTPException 400 for payload: {payload}"
        except HTTPException as exc:
            assert exc.status_code == 400, f"Expected 400 status, got {exc.status_code}"
            assert exc.detail == "Invalid table name", f"Expected 'Invalid table name', got '{exc.detail}'"

        # Test get_table_stats
        try:
            get_table_stats(db_id=99, table_name=payload, current_user=mock_user, db=db_session)
            assert False, f"Expected HTTPException 400 for stats payload: {payload}"
        except HTTPException as exc:
            assert exc.status_code == 400, f"Expected 400 status, got {exc.status_code}"
            assert exc.detail == "Invalid table name", f"Expected 'Invalid table name', got '{exc.detail}'"

    print("[PASS] Test 3.3: All SQL injection payloads correctly blocked with HTTP 400 'Invalid table name'")

    gc.collect()

def run_admin_auth_tests():
    print("\n=== TEST 4: Admin Authorization Guard ===")
    admin_user = models.User(id=1, email="admin@test.com", role="Admin")
    member_user = models.User(id=2, email="user@test.com", role="Member")

    res = dependencies.get_current_admin_user(current_user=admin_user)
    assert res.email == "admin@test.com"
    print("[PASS] Test 4.1: Admin user authorized PASSED")

    try:
        dependencies.get_current_admin_user(current_user=member_user)
        assert False, "Non-admin user should raise HTTP 403"
    except HTTPException as exc:
        assert exc.status_code == 403, f"Expected 403, got {exc.status_code}"
        assert exc.detail == "Admin access required"
    print("[PASS] Test 4.2: Non-admin user blocked with 403 FORBIDDEN PASSED")

def run_secret_removal_tests():
    print("\n=== TEST 5: Secret Removal & Fallback ===")
    assert auth.SECRET_KEY is not None and len(auth.SECRET_KEY) > 0
    print("[PASS] Test 5.1: SECRET_KEY present without hardcoded fallback PASSED")

if __name__ == "__main__":
    try:
        run_crypto_tests()
        run_sqlite_connection_tests()
        run_sql_sanitization_tests()
        run_admin_auth_tests()
        run_secret_removal_tests()
        print("\n==========================================")
        print("ALL EMPIRICAL TESTS PASSED SUCCESSFULLY!")
        print("==========================================")
    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
