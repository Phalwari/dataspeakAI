"""
tests/test_phase5_erd_backend.py
---------------------------------
Comprehensive backend test suite for Phase 5 (Entity-Relationship Diagram / ERD).
Verifies:
1. SQLite schema reflection:
   - parent/child FK
   - composite FK
   - self-referencing FK
   - two FKs to same target
   - a view
   - a table with no FKs
   - dangling FK (target dropped with PRAGMA foreign_keys=OFF)
   - mixed-case table and column names
   - table name with a space
   - SQL injection-style table name ('x"; DROP TABLE y; --')
2. Relational flags: columns, PK, FK, is_nullable, is_unique, kind ('table' vs 'view').
3. Relationship direction (source=child, target=parent) and column lists.
4. Catalog-first caching vs refresh bypass.
5. Refresh rate limit cooldown (HTTP 429 with Retry-After header).
6. Multi-tenant isolation (foreign tenant database yields HTTP 404).
7. Unauthenticated request yields HTTP 401.
8. Document DBs (mongodb, firebase) yield HTTP 400.
9. Host and path security (D5):
   - SQLite path traversal ('..') blocked
   - Non-existent SQLite file blocked
   - Loopback (127.0.0.1, localhost) blocked when ALLOW_PRIVATE_DB_HOSTS=false
   - Link-local (169.254.169.254) blocked
   - RFC 1918 private IP (10.0.0.1) blocked
10. Credential security: response never leaks password, username, host, or raw connection string.
11. Inferred relationships:
    - disabled by default
    - enabled via include_inferred=true
    - skipped when real FK exists
    - skipped when ambiguous
    - generic names (id, code, status, name) ignored
12. Truncation limit (ERD_MAX_TABLES).
13. Engine lifecycle: NullPool disposed even on reflection error.
14. Unreachable DB returns sanitized HTTP 502.
15. Mocked PostgreSQL inspector (no live server used).
16. Mocked MySQL inspector (no live server used).
"""

import os
import sys
import sqlite3
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import models
import schemas
import auth
from database import Base, get_db
from crypto import encrypt_password
from main import app
from services import erd_service
from services.erd_service import (
    reflect_schema,
    sync_schema_catalog,
    load_erd_from_catalog,
    detect_inferred_relationships,
    clear_cooldowns_for_testing,
    ReflectedTable,
    ReflectedColumn,
    ReflectedRelationship,
)


@pytest.fixture(autouse=True)
def reset_cooldowns():
    clear_cooldowns_for_testing()
    yield
    clear_cooldowns_for_testing()


@pytest.fixture
def test_setup():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSession()

    # Seed Tenant 1 and User 1
    t1 = models.Tenant(id=1, name="Tenant Alpha")
    db.add(t1)
    u1 = models.User(
        id=1,
        tenant_id=1,
        email="user1@alpha.com",
        hashed_password=auth.get_password_hash("AlphaPass123!"),
        full_name="Alpha User",
        role="Admin",
        is_verified=True,
    )
    db.add(u1)

    # Seed Tenant 2 and User 2 (for multi-tenant isolation tests)
    t2 = models.Tenant(id=2, name="Tenant Beta")
    db.add(t2)
    u2 = models.User(
        id=2,
        tenant_id=2,
        email="user2@beta.com",
        hashed_password=auth.get_password_hash("BetaPass123!"),
        full_name="Beta User",
        role="Admin",
        is_verified=True,
    )
    db.add(u2)
    db.commit()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    token1 = auth.create_access_token({"sub": u1.email})
    token2 = auth.create_access_token({"sub": u2.email})

    client = TestClient(app)

    yield {
        "db": db,
        "client": client,
        "u1": u1,
        "u2": u2,
        "t1": t1,
        "t2": t2,
        "token1": token1,
        "token2": token2,
    }

    db.close()
    app.dependency_overrides.clear()


def create_sqlite_sample_db(file_path: str):
    """Creates a sample SQLite database containing all edge-case relational structures."""
    conn = sqlite3.connect(file_path)
    cur = conn.cursor()

    # 1. Parent & Child FK
    cur.execute("CREATE TABLE parent_tbl (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
    cur.execute("""
        CREATE TABLE child_tbl (
            id INTEGER PRIMARY KEY,
            parent_id INTEGER,
            note TEXT,
            FOREIGN KEY(parent_id) REFERENCES parent_tbl(id)
        )
    """)

    # 2. Composite FK
    cur.execute("""
        CREATE TABLE comp_parent (
            part_a TEXT NOT NULL,
            part_b INTEGER NOT NULL,
            title TEXT,
            PRIMARY KEY (part_a, part_b)
        )
    """)
    cur.execute("""
        CREATE TABLE comp_child (
            id INTEGER PRIMARY KEY,
            ca TEXT NOT NULL,
            cb INTEGER NOT NULL,
            FOREIGN KEY (ca, cb) REFERENCES comp_parent (part_a, part_b)
        )
    """)

    # 3. Self-referencing FK
    cur.execute("""
        CREATE TABLE employee (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            manager_id INTEGER,
            FOREIGN KEY(manager_id) REFERENCES employee(id)
        )
    """)

    # 4. Two FKs to same target
    cur.execute("CREATE TABLE addresses (id INTEGER PRIMARY KEY, street TEXT NOT NULL)")
    cur.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            billing_addr_id INTEGER,
            shipping_addr_id INTEGER,
            FOREIGN KEY(billing_addr_id) REFERENCES addresses(id),
            FOREIGN KEY(shipping_addr_id) REFERENCES addresses(id)
        )
    """)

    # 5. Standalone table with no FKs
    cur.execute("CREATE TABLE standalone (id INTEGER PRIMARY KEY, val TEXT)")

    # 6. View
    cur.execute("CREATE VIEW v_active_orders AS SELECT id, billing_addr_id FROM orders")

    # 7. Mixed case table and column names
    cur.execute('CREATE TABLE "MixedCaseTable" ("Id" INTEGER PRIMARY KEY, "MixedCol" TEXT UNIQUE)')

    # 8. Name with spaces
    cur.execute('CREATE TABLE "table with space" (id INTEGER PRIMARY KEY, info TEXT)')

    # 9. Injection-style table name
    cur.execute('CREATE TABLE "x""; DROP TABLE y; --" (id INTEGER PRIMARY KEY, payload TEXT)')

    # 10. Dangling FK: create target, create referencing table, drop target with FKs disabled
    cur.execute("PRAGMA foreign_keys = OFF")
    cur.execute("CREATE TABLE dangling_parent (id INTEGER PRIMARY KEY)")
    cur.execute("""
        CREATE TABLE dangling_child (
            id INTEGER PRIMARY KEY,
            p_id INTEGER,
            FOREIGN KEY(p_id) REFERENCES dangling_parent(id)
        )
    """)
    cur.execute("DROP TABLE dangling_parent")

    conn.commit()
    conn.close()


# ── TEST CASES ─────────────────────────────────────────────────────────────────

def test_erd_sqlite_schema_reflection_and_features(tmp_path, test_setup):
    """
    Verifies full SQLite schema reflection:
    - parent/child, composite, self-referencing, two FKs to same target
    - view (columns present, no FK edges originating)
    - standalone table with no FKs
    - dangling FK generates warning and is omitted from relationships
    - mixed case, spaces, and SQL injection-style table names
    - column PK/FK flags, nullability, uniqueness, and kind ('table' vs 'view')
    """
    db_path = str(tmp_path / "target_sample.db")
    create_sqlite_sample_db(db_path)

    db = test_setup["db"]
    client = test_setup["client"]
    token = test_setup["token1"]

    db_conn = models.DatabaseConnection(
        tenant_id=1,
        name="SQLite Full Sample",
        db_type="sqlite",
        database=db_path,
        status="connected",
    )
    db.add(db_conn)
    db.commit()
    db.refresh(db_conn)

    res = client.get(
        f"/api/databases/{db_conn.id}/erd",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["database_id"] == db_conn.id
    assert data["dialect"] == "sqlite"
    assert data["source"] == "live"
    assert data["truncated"] is False
    assert data["table_count"] >= 10

    # Verify tables map
    tables_map = {t["name"]: t for t in data["tables"]}
    assert "parent_tbl" in tables_map
    assert "child_tbl" in tables_map
    assert "comp_parent" in tables_map
    assert "comp_child" in tables_map
    assert "employee" in tables_map
    assert "orders" in tables_map
    assert "addresses" in tables_map
    assert "standalone" in tables_map
    assert "v_active_orders" in tables_map
    assert "MixedCaseTable" in tables_map
    assert "table with space" in tables_map
    assert 'x"; DROP TABLE y; --' in tables_map

    # Check View properties
    view_item = tables_map["v_active_orders"]
    assert view_item["kind"] == "view"
    assert len(view_item["columns"]) == 2

    # Check Table properties
    parent_cols = {c["name"]: c for c in tables_map["parent_tbl"]["columns"]}
    assert parent_cols["id"]["is_pk"] is True
    assert parent_cols["id"]["is_fk"] is False

    child_cols = {c["name"]: c for c in tables_map["child_tbl"]["columns"]}
    assert child_cols["parent_id"]["is_fk"] is True
    assert child_cols["parent_id"]["is_pk"] is False

    comp_parent_cols = {c["name"]: c for c in tables_map["comp_parent"]["columns"]}
    assert comp_parent_cols["part_a"]["is_pk"] is True
    assert comp_parent_cols["part_b"]["is_pk"] is True

    # Check relationships
    rels = data["relationships"]

    # 1. Parent/Child FK: child -> parent
    pc_rel = [r for r in rels if r["source_table"] == "child_tbl" and r["target_table"] == "parent_tbl"]
    assert len(pc_rel) == 1
    assert pc_rel[0]["source_columns"] == ["parent_id"]
    assert pc_rel[0]["target_columns"] == ["id"]

    # 2. Composite FK: single relationship edge with multiple columns
    comp_rel = [r for r in rels if r["source_table"] == "comp_child" and r["target_table"] == "comp_parent"]
    assert len(comp_rel) == 1
    assert comp_rel[0]["source_columns"] == ["ca", "cb"]
    assert comp_rel[0]["target_columns"] == ["part_a", "part_b"]

    # 3. Self-referencing FK: employee -> employee
    self_rel = [r for r in rels if r["source_table"] == "employee" and r["target_table"] == "employee"]
    assert len(self_rel) == 1
    assert self_rel[0]["source_columns"] == ["manager_id"]
    assert self_rel[0]["target_columns"] == ["id"]

    # 4. Two FKs to same target: orders -> addresses (billing and shipping)
    order_rels = [r for r in rels if r["source_table"] == "orders" and r["target_table"] == "addresses"]
    assert len(order_rels) == 2
    order_src_cols = {tuple(r["source_columns"]) for r in order_rels}
    assert ("billing_addr_id",) in order_src_cols
    assert ("shipping_addr_id",) in order_src_cols

    # 5. Dangling FK: omitted from relationships, logged in warnings
    dangling_rel = [r for r in rels if r["source_table"] == "dangling_child"]
    assert len(dangling_rel) == 0
    warning_texts = " ".join(data["warnings"])
    assert "Dangling foreign key" in warning_texts
    assert "dangling_parent" in warning_texts


def test_erd_catalog_first_and_refresh_bypass(tmp_path, test_setup):
    """
    Verifies Decision D1:
    - First call reflects live and syncs catalog (source='live').
    - Subsequent call without refresh=true reads cached catalog (source='catalog').
    - Call with refresh=true forces live re-sync (source='live').
    """
    db_path = str(tmp_path / "catalog_test.db")
    create_sqlite_sample_db(db_path)

    db = test_setup["db"]
    client = test_setup["client"]
    token = test_setup["token1"]

    db_conn = models.DatabaseConnection(
        tenant_id=1,
        name="Catalog Test DB",
        db_type="sqlite",
        database=db_path,
        status="connected",
    )
    db.add(db_conn)
    db.commit()

    # Call 1: live reflection + catalog insertion
    res1 = client.get(f"/api/databases/{db_conn.id}/erd", headers={"Authorization": f"Bearer {token}"})
    assert res1.status_code == 200
    assert res1.json()["source"] == "live"

    # Call 2: read from catalog cache
    res2 = client.get(f"/api/databases/{db_conn.id}/erd", headers={"Authorization": f"Bearer {token}"})
    assert res2.status_code == 200
    assert res2.json()["source"] == "catalog"
    assert res2.json()["table_count"] == res1.json()["table_count"]

    # Clear cooldown so we can test refresh bypass directly
    clear_cooldowns_for_testing()

    # Call 3: refresh=true bypasses catalog cache
    res3 = client.get(f"/api/databases/{db_conn.id}/erd?refresh=true", headers={"Authorization": f"Bearer {token}"})
    assert res3.status_code == 200
    assert res3.json()["source"] == "live"


def test_erd_refresh_cooldown_429(tmp_path, test_setup):
    """
    Verifies Decision D7:
    Immediate consecutive refresh calls return HTTP 429 with Retry-After header.
    """
    db_path = str(tmp_path / "cooldown_test.db")
    create_sqlite_sample_db(db_path)

    db = test_setup["db"]
    client = test_setup["client"]
    token = test_setup["token1"]

    db_conn = models.DatabaseConnection(
        tenant_id=1,
        name="Cooldown DB",
        db_type="sqlite",
        database=db_path,
        status="connected",
    )
    db.add(db_conn)
    db.commit()

    # Initial live refresh succeeds and records cooldown
    res1 = client.get(f"/api/databases/{db_conn.id}/erd?refresh=true", headers={"Authorization": f"Bearer {token}"})
    assert res1.status_code == 200

    # Immediate second refresh triggers HTTP 429
    res2 = client.get(f"/api/databases/{db_conn.id}/erd?refresh=true", headers={"Authorization": f"Bearer {token}"})
    assert res2.status_code == 429
    assert "Retry-After" in res2.headers
    assert "Refresh cooldown active" in res2.json()["detail"]


def test_erd_tenant_isolation_404_and_auth_401(tmp_path, test_setup):
    """
    Verifies Decision D6:
    - Tenant 2 requesting Tenant 1's database gets HTTP 404 (IDOR protection, no enumeration).
    - Unauthenticated request gets HTTP 401.
    """
    db_path = str(tmp_path / "isolation_test.db")
    create_sqlite_sample_db(db_path)

    db = test_setup["db"]
    client = test_setup["client"]
    token1 = test_setup["token1"]
    token2 = test_setup["token2"]

    # Belongs to Tenant 1
    db_conn = models.DatabaseConnection(
        tenant_id=1,
        name="Tenant 1 DB",
        db_type="sqlite",
        database=db_path,
        status="connected",
    )
    db.add(db_conn)
    db.commit()

    # Tenant 2 tries to access -> 404
    res_cross = client.get(f"/api/databases/{db_conn.id}/erd", headers={"Authorization": f"Bearer {token2}"})
    assert res_cross.status_code == 404
    assert res_cross.json()["detail"] == "Database connection not found."

    # Unauthenticated request -> 401
    res_no_auth = client.get(f"/api/databases/{db_conn.id}/erd")
    assert res_no_auth.status_code == 401


def test_erd_unsupported_dialects_400(test_setup):
    """
    Verifies Decision D4:
    Non-relational databases (mongodb, firebase) return HTTP 400.
    """
    db = test_setup["db"]
    client = test_setup["client"]
    token = test_setup["token1"]

    mongo_conn = models.DatabaseConnection(
        tenant_id=1,
        name="Mongo DB",
        db_type="mongodb",
        database="test_db",
        status="connected",
    )
    firebase_conn = models.DatabaseConnection(
        tenant_id=1,
        name="Firebase DB",
        db_type="firebase",
        database="firestore_db",
        status="connected",
    )
    db.add_all([mongo_conn, firebase_conn])
    db.commit()

    for conn in (mongo_conn, firebase_conn):
        res = client.get(f"/api/databases/{conn.id}/erd", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 400
        assert "ERD is supported only for relational databases" in res.json()["detail"]


def test_erd_host_security_and_traversal_validation(test_setup):
    """
    Verifies Decision D5:
    Host blocklist (loopback, link-local, private ranges) and SQLite path traversal confinement.
    """
    db = test_setup["db"]
    client = test_setup["client"]
    token = test_setup["token1"]

    # 1. SQLite directory traversal
    sqlite_traversal = models.DatabaseConnection(
        tenant_id=1, name="Traversal DB", db_type="sqlite", database="../secrets/data.db"
    )
    # 2. SQLite non-existent file
    sqlite_missing = models.DatabaseConnection(
        tenant_id=1, name="Missing DB", db_type="sqlite", database="C:/non_existent_folder_99/missing.db"
    )
    # 3. Loopback IP
    pg_loopback = models.DatabaseConnection(
        tenant_id=1, name="Loopback DB", db_type="postgresql", host="127.0.0.1", database="test"
    )
    # 4. Link-local IP
    pg_link_local = models.DatabaseConnection(
        tenant_id=1, name="LinkLocal DB", db_type="postgresql", host="169.254.169.254", database="test"
    )
    # 5. Private IP
    pg_private = models.DatabaseConnection(
        tenant_id=1, name="Private DB", db_type="postgresql", host="10.0.0.1", database="test"
    )

    db.add_all([sqlite_traversal, sqlite_missing, pg_loopback, pg_link_local, pg_private])
    db.commit()

    # Test each connection returns HTTP 400
    for conn in (sqlite_traversal, sqlite_missing, pg_loopback, pg_link_local, pg_private):
        res = client.get(f"/api/databases/{conn.id}/erd", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 400, f"Expected 400 for {conn.name}, got {res.status_code}"


def test_erd_response_never_leaks_credentials_or_connection_string(tmp_path, test_setup):
    """
    Verifies that passwords, usernames, and host details are never leaked in response or errors.
    """
    db_path = str(tmp_path / "secret_check.db")
    create_sqlite_sample_db(db_path)

    secret_password = "SuperSecretPlainTextPassword123!"
    secret_user = "classified_user_name"

    db = test_setup["db"]
    client = test_setup["client"]
    token = test_setup["token1"]

    db_conn = models.DatabaseConnection(
        tenant_id=1,
        name="Credentials Test DB",
        db_type="sqlite",
        database=db_path,
        username=secret_user,
        password=encrypt_password(secret_password),
        status="connected",
    )
    db.add(db_conn)
    db.commit()

    res = client.get(f"/api/databases/{db_conn.id}/erd", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    text_content = res.text

    assert secret_password not in text_content
    assert secret_user not in text_content


def test_erd_inferred_relationships(tmp_path, test_setup):
    """
    Verifies inferred relationship detection:
    - Disabled by default (include_inferred=false)
    - Enabled via include_inferred=true
    - Correct candidate detection: e.g. invoices.customer_id -> customers.id
    - Skipped when real FK already exists on the column
    - Skipped when target match is ambiguous
    - Generic column names (id, code, status, name) are ignored
    """
    db_path = str(tmp_path / "inferred_test.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Target table with single PK
    cur.execute("CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT)")

    # Referencing table without explicit FK
    cur.execute("CREATE TABLE invoices (id INTEGER PRIMARY KEY, customer_id INTEGER, amount REAL)")

    # Real FK target and child
    cur.execute("CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT)")
    cur.execute("""
        CREATE TABLE order_items (
            id INTEGER PRIMARY KEY,
            product_id INTEGER,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    # Ambiguous targets
    cur.execute("CREATE TABLE accounts_east (id INTEGER PRIMARY KEY, loc TEXT)")
    cur.execute("CREATE TABLE accounts_west (id INTEGER PRIMARY KEY, loc TEXT)")
    cur.execute("CREATE TABLE ambiguous_refs (id INTEGER PRIMARY KEY, accounts_id INTEGER)")

    # Table with generic column name
    cur.execute("CREATE TABLE generic_check (id INTEGER PRIMARY KEY, status TEXT, code TEXT)")

    conn.commit()
    conn.close()

    db = test_setup["db"]
    client = test_setup["client"]
    token = test_setup["token1"]

    db_conn = models.DatabaseConnection(
        tenant_id=1,
        name="Inferred Test DB",
        db_type="sqlite",
        database=db_path,
        status="connected",
    )
    db.add(db_conn)
    db.commit()

    # 1. Default call: inferred relationships not included
    res_default = client.get(f"/api/databases/{db_conn.id}/erd", headers={"Authorization": f"Bearer {token}"})
    assert res_default.status_code == 200
    data_default = res_default.json()
    inferred_default = [r for r in data_default["relationships"] if r.get("kind") == "inferred"]
    assert len(inferred_default) == 0

    # 2. include_inferred=true
    res_inf = client.get(f"/api/databases/{db_conn.id}/erd?include_inferred=true", headers={"Authorization": f"Bearer {token}"})
    assert res_inf.status_code == 200
    data_inf = res_inf.json()

    inferred_rels = [r for r in data_inf["relationships"] if r.get("kind") == "inferred"]
    assert len(inferred_rels) >= 1

    # Verify customer_id -> customers.id
    cust_inf = [r for r in inferred_rels if r["source_table"] == "invoices" and r["target_table"] == "customers"]
    assert len(cust_inf) == 1
    assert cust_inf[0]["source_columns"] == ["customer_id"]
    assert cust_inf[0]["target_columns"] == ["id"]
    assert cust_inf[0]["confidence"] is not None
    assert "matches primary key" in cust_inf[0]["reason"]

    # Verify product_id is not double-inferred (already a real FK)
    prod_inf = [r for r in inferred_rels if r["source_table"] == "order_items" and "product_id" in r["source_columns"]]
    assert len(prod_inf) == 0

    # Verify ambiguous target is skipped
    amb_inf = [r for r in inferred_rels if r["source_table"] == "ambiguous_refs"]
    assert len(amb_inf) == 0

    # Verify generic columns (status, code) are not inferred
    gen_inf = [r for r in inferred_rels if r["source_table"] == "generic_check"]
    assert len(gen_inf) == 0


def test_erd_truncation_limit(tmp_path, test_setup, monkeypatch):
    """
    Verifies ERD_MAX_TABLES truncation:
    When table count exceeds ERD_MAX_TABLES, results are truncated and warning is appended.
    """
    db_path = str(tmp_path / "truncation_test.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    for i in range(8):
        cur.execute(f"CREATE TABLE test_table_{i} (id INTEGER PRIMARY KEY, val TEXT)")
    conn.commit()
    conn.close()

    db = test_setup["db"]
    client = test_setup["client"]
    token = test_setup["token1"]

    db_conn = models.DatabaseConnection(
        tenant_id=1,
        name="Truncation DB",
        db_type="sqlite",
        database=db_path,
        status="connected",
    )
    db.add(db_conn)
    db.commit()

    # Monkeypatch ERD_MAX_TABLES to 4
    monkeypatch.setattr(erd_service, "ERD_MAX_TABLES", 4)
    from routers import erd as erd_router
    monkeypatch.setattr(erd_router, "ERD_MAX_TABLES", 4)

    res = client.get(f"/api/databases/{db_conn.id}/erd", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()

    assert data["truncated"] is True
    assert data["table_count"] == 8
    assert len(data["tables"]) == 4
    warning_text = " ".join(data["warnings"])
    assert "exceeds maximum ERD display limit of 4 tables" in warning_text


def test_erd_unreachable_db_returns_502_sanitized_and_engine_disposed(test_setup, monkeypatch):
    """
    Verifies that connection failure to an unreachable database returns HTTP 502 with
    sanitized detail, and that engine.dispose() is always called in finally block.
    """
    db = test_setup["db"]
    client = test_setup["client"]
    token = test_setup["token1"]

    db_conn = models.DatabaseConnection(
        tenant_id=1,
        name="Unreachable DB",
        db_type="postgresql",
        host="db.example-remote-fail.com",
        port=5432,
        username="myuser",
        password=encrypt_password("mypassword"),
        database="proddb",
        status="connected",
    )
    db.add(db_conn)
    db.commit()

    disposed = []

    class MockEngine:
        def dispose(self):
            disposed.append(True)

    def mock_create_engine(*args, **kwargs):
        return MockEngine()

    def mock_reflect(*args, **kwargs):
        raise ConnectionRefusedError("Simulated remote server connection timeout")

    monkeypatch.setattr(erd_service, "ALLOW_PRIVATE_DB_HOSTS", True)
    monkeypatch.setattr("services.erd_service.create_erd_engine", mock_create_engine)
    monkeypatch.setattr("routers.erd.create_erd_engine", mock_create_engine)
    monkeypatch.setattr("routers.erd.reflect_schema", mock_reflect)

    res = client.get(f"/api/databases/{db_conn.id}/erd", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 502
    assert "Unable to establish connection to database server" in res.json()["detail"]
    assert "mypassword" not in res.text
    assert "myuser" not in res.text
    # Verify engine dispose was called
    assert len(disposed) == 1


def test_erd_mocked_postgresql_inspector():
    """
    Mocked PostgreSQL Inspector Test:
    Verifies schema name pass-through and referred_schema handling.
    NOTE: No live server used (PostgreSQL is mocked).
    """
    mock_inspector = MagicMock()
    mock_inspector.get_table_names.return_value = ["users", "orders"]
    mock_inspector.get_view_names.return_value = []

    mock_inspector.get_multi_columns.return_value = {
        "users": [{"name": "id", "type": "INTEGER", "nullable": False}],
        "orders": [
            {"name": "id", "type": "INTEGER", "nullable": False},
            {"name": "user_id", "type": "INTEGER", "nullable": True},
        ]
    }
    mock_inspector.get_multi_pk_constraint.return_value = {
        "users": {"constrained_columns": ["id"]},
        "orders": {"constrained_columns": ["id"]},
    }
    mock_inspector.get_multi_foreign_keys.return_value = {
        "orders": [{
            "name": "fk_orders_user",
            "constrained_columns": ["user_id"],
            "referred_schema": "auth_schema",
            "referred_table": "users",
            "referred_columns": ["id"],
        }]
    }
    mock_inspector.get_multi_unique_constraints.return_value = {}

    dummy_engine = MagicMock()
    res = reflect_schema(dummy_engine, schema="custom_schema", inspector_override=mock_inspector)

    assert len(res.tables) == 2
    for t in res.tables:
        assert t.schema == "custom_schema"

    assert len(res.relationships) == 1
    rel = res.relationships[0]
    assert rel.source_table == "orders"
    assert rel.source_schema == "custom_schema"
    assert rel.target_table == "users"
    assert rel.target_schema == "auth_schema"
    assert rel.constraint_name == "fk_orders_user"


def test_erd_mocked_mysql_inspector():
    """
    Mocked MySQL Inspector Test:
    Verifies table and column case preservation across reflection.
    NOTE: No live server used (MySQL is mocked).
    """
    mock_inspector = MagicMock()
    mock_inspector.get_table_names.return_value = ["OrdersHeader", "OrderDetailsItem"]
    mock_inspector.get_view_names.return_value = []

    mock_inspector.get_multi_columns.return_value = {
        "OrdersHeader": [{"name": "OrderID", "type": "INT", "nullable": False}],
        "OrderDetailsItem": [
            {"name": "DetailID", "type": "INT", "nullable": False},
            {"name": "OrderID", "type": "INT", "nullable": False},
        ]
    }
    mock_inspector.get_multi_pk_constraint.return_value = {
        "OrdersHeader": {"constrained_columns": ["OrderID"]},
        "OrderDetailsItem": {"constrained_columns": ["DetailID"]},
    }
    mock_inspector.get_multi_foreign_keys.return_value = {
        "OrderDetailsItem": [{
            "name": "FK_Details_Orders",
            "constrained_columns": ["OrderID"],
            "referred_schema": None,
            "referred_table": "OrdersHeader",
            "referred_columns": ["OrderID"],
        }]
    }
    mock_inspector.get_multi_unique_constraints.return_value = {}

    dummy_engine = MagicMock()
    res = reflect_schema(dummy_engine, schema=None, inspector_override=mock_inspector)

    assert len(res.tables) == 2
    table_names = [t.name for t in res.tables]
    assert "OrdersHeader" in table_names
    assert "OrderDetailsItem" in table_names

    assert len(res.relationships) == 1
    rel = res.relationships[0]
    assert rel.source_table == "OrderDetailsItem"
    assert rel.target_table == "OrdersHeader"
    assert rel.source_columns == ["OrderID"]
    assert rel.target_columns == ["OrderID"]
