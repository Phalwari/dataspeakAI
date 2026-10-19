"""
tests/test_phase2_security_qa_followups.py
-------------------------------------------
TDD verification suite for Phase 2 QA findings:
- SEC-01: Schema-qualified table allowlist bypass
- SEC-02: AST fail-closed SQL validation
- SEC-03: X-Forwarded-For trusted proxy validation
- SEC-09: Fail-closed dialect guardrails
- SEC-07: Strict allowed_origins regex validation
- SEC-04: Key-scoped monthly caps and widget_key_id tracking
- SEC-06 & SEC-05: Stream counter TTL, lease release, and rate limiter bucket eviction
"""

import os
import sys
import pytest

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from services.sql_engine import validate_widget_sql, extract_sql_referenced_tables


# ---------------------------------------------------------------------------
# SEC-01: Schema-qualified allowlist bypass tests
# ---------------------------------------------------------------------------

def test_sec01_unqualified_allowlist_rejects_schema_qualified_names():
    """
    SEC-01: When allowed_tables is ["products"], the query must REJECT:
    - other_schema.products (cross-schema access attempt)
    - public.products (schema-qualified form when only unqualified is allowed)
    and accept unqualified 'products'.
    """
    # 1. Unqualified table is accepted
    valid, msg = validate_widget_sql("SELECT * FROM products;", allowed_tables=["products"])
    assert valid is True, f"Expected products to be allowed: {msg}"

    # 2. other_schema.products must be strictly REJECTED
    valid_cross, msg_cross = validate_widget_sql("SELECT * FROM other_schema.products;", allowed_tables=["products"])
    assert valid_cross is False, "other_schema.products must be rejected when only 'products' is allowed"
    assert "other_schema.products" in msg_cross

    # 3. public.products must be strictly REJECTED when only 'products' is in allowlist
    valid_pub, msg_pub = validate_widget_sql("SELECT * FROM public.products;", allowed_tables=["products"])
    assert valid_pub is False, "public.products must be rejected when only 'products' is allowed"
    assert "public.products" in msg_pub


def test_sec01_schema_qualified_allowlist_accepts_only_exact_qualified_name():
    """
    SEC-01: When allowed_tables is ["public.products"], the query must:
    - ACCEPT public.products
    - REJECT unqualified products
    - REJECT other_schema.products
    """
    # 1. public.products is accepted
    valid, msg = validate_widget_sql("SELECT * FROM public.products;", allowed_tables=["public.products"])
    assert valid is True, f"Expected public.products to be allowed: {msg}"

    # 2. unqualified products is rejected
    valid_unq, msg_unq = validate_widget_sql("SELECT * FROM products;", allowed_tables=["public.products"])
    assert valid_unq is False, "unqualified products must be rejected when only 'public.products' is allowed"

    # 3. other_schema.products is rejected
    valid_other, msg_other = validate_widget_sql("SELECT * FROM other_schema.products;", allowed_tables=["public.products"])
    assert valid_other is False, "other_schema.products must be rejected when only 'public.products' is allowed"


# ---------------------------------------------------------------------------
# SEC-02: AST fail-closed SQL validation tests
# ---------------------------------------------------------------------------

def test_sec02_comma_join_with_disallowed_table_rejected():
    """
    SEC-02: Comma joins (e.g. FROM products, secret_payroll) must be detected
    by AST and rejected when any referenced table is not in allowed_tables.
    """
    valid, msg = validate_widget_sql(
        "SELECT * FROM products, secret_payroll WHERE products.id = secret_payroll.id;",
        allowed_tables=["products"]
    )
    assert valid is False, "Comma join with secret_payroll must be rejected"
    assert "secret_payroll" in msg


def test_sec02_malformed_unparseable_sql_fails_closed():
    """
    SEC-02: Malformed or dialect-specific SQL that cannot be parsed by sqlglot
    must FAIL CLOSED (be rejected) instead of falling back to permissive regex.
    """
    malformed_queries = [
        "SELECT * FROM products WHERE (unclosed_paren = 1",
        "SELECT * FROM products UNION SELECT ALL FROM ;",
        "SELECT FROM WHERE",
    ]
    for q in malformed_queries:
        valid, msg = validate_widget_sql(q, allowed_tables=["products"])
        assert valid is False, f"Malformed query should fail closed: {q}"
        assert "parse error" in msg.lower() or "parsing failed" in msg.lower() or "guardrail" in msg.lower() or "violation" in msg.lower()


# ---------------------------------------------------------------------------
# SEC-03: X-Forwarded-For spoofing defense tests
# ---------------------------------------------------------------------------

def test_sec03_untrusted_client_xff_spoofing_prevented(monkeypatch):
    """
    SEC-03: When request.client.host is NOT in TRUSTED_PROXIES, any X-Forwarded-For
    header provided by the client MUST be ignored, using request.client.host directly.
    """
    from routers.widget import extract_client_ip
    from starlette.datastructures import Headers, Address

    class MockRequest:
        def __init__(self, host: str, headers_dict: dict):
            self.client = Address(host, 12345)
            self.headers = Headers(headers_dict)

    # 1. Without TRUSTED_PROXIES set: untrusted direct client cannot spoof IP
    monkeypatch.delenv("TRUSTED_PROXIES", raising=False)
    req1 = MockRequest("198.51.100.2", {"x-forwarded-for": "203.0.113.195"})
    resolved_ip = extract_client_ip(req1)
    assert resolved_ip == "198.51.100.2", "Spoofed XFF from untrusted client must NOT change IP bucket"

    # 2. With TRUSTED_PROXIES="10.0.0.1, 192.168.0.0/16":
    monkeypatch.setenv("TRUSTED_PROXIES", "10.0.0.1, 192.168.0.0/16")

    # Untrusted client (203.0.113.10) sending XFF is still ignored
    req2 = MockRequest("203.0.113.10", {"x-forwarded-for": "1.1.1.1"})
    assert extract_client_ip(req2) == "203.0.113.10"

    # Trusted proxy (10.0.0.1) sending single untrusted client in XFF -> reads client IP
    req3 = MockRequest("10.0.0.1", {"x-forwarded-for": "203.0.113.195"})
    assert extract_client_ip(req3) == "203.0.113.195"

    # Trusted proxy sending multi-proxy chain: selects right-most untrusted entry
    # Chain: client (8.8.8.8), untrusted intermediate (203.0.113.50), trusted proxy (192.168.1.100)
    req4 = MockRequest("10.0.0.1", {"x-forwarded-for": "8.8.8.8, 203.0.113.50, 192.168.1.100"})
    assert extract_client_ip(req4) == "203.0.113.50"


# ---------------------------------------------------------------------------
# SEC-09: Guardrails fail-closed & Dialect isolation tests
# ---------------------------------------------------------------------------

def test_sec09_guardrail_failure_aborts_execution(monkeypatch, tmp_path):
    """
    SEC-09: If dialect guardrails (read-only or timeout) fail to apply,
    the query must NOT proceed with 'except Exception: pass'. It must abort.
    """
    import models
    from services.sql_engine import execute_safe_sql
    import sqlite3

    db_file = tmp_path / "test_sec09.db"
    conn_raw = sqlite3.connect(str(db_file))
    conn_raw.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);")
    conn_raw.execute("INSERT INTO users VALUES (1, 'Alice');")
    conn_raw.commit()
    conn_raw.close()

    db_conn = models.DatabaseConnection(
        id=1,
        name="Test SQLite",
        db_type="sqlite",
        database=str(db_file),
        host=None,
        port=None,
        username=None,
        password=None
    )

    # Monkeypatch text or connection execution during guardrails to simulate a failure
    from sqlalchemy.engine import Connection
    orig_execute = Connection.execute

    def failing_execute(self, statement, *args, **kwargs):
        stmt_str = str(statement)
        if "PRAGMA query_only" in stmt_str or "statement_timeout" in stmt_str or "READ ONLY" in stmt_str:
            raise RuntimeError("Simulated guardrail execution failure")
        return orig_execute(self, statement, *args, **kwargs)

    monkeypatch.setattr(Connection, "execute", failing_execute)

    # Must raise RuntimeError and abort execution, rather than silently catching and proceeding
    with pytest.raises(RuntimeError) as exc_info:
        execute_safe_sql(db_conn, "SELECT * FROM users;")

    assert "guardrail" in str(exc_info.value).lower() or "simulated guardrail" in str(exc_info.value).lower()


def test_sec09_sqlite_query_only_does_not_leak_to_separate_connection(tmp_path):
    """
    SEC-09: After a widget read-only query executes with PRAGMA query_only = ON,
    a subsequent write on a separate connection must succeed (confirming dedicated connection / NullPool).
    """
    import models
    from services.sql_engine import execute_safe_sql
    from sqlalchemy import create_engine, text

    db_file = tmp_path / "test_sec09_leak.db"
    engine_main = create_engine(f"sqlite:///{db_file}")
    with engine_main.connect() as c:
        c.execute(text("CREATE TABLE items (id INTEGER PRIMARY KEY, title TEXT);"))
        c.execute(text("INSERT INTO items VALUES (1, 'Widget');"))
        c.commit()

    db_conn = models.DatabaseConnection(
        id=2,
        name="Test SQLite Isolation",
        db_type="sqlite",
        database=str(db_file),
    )

    # Execute widget read query
    res = execute_safe_sql(db_conn, "SELECT * FROM items;")
    assert res["row_count"] == 1

    # Perform normal write on separate connection — must succeed without query_only error
    with engine_main.connect() as c:
        c.execute(text("INSERT INTO items VALUES (2, 'Gadget');"))
        c.commit()

        count = c.execute(text("SELECT COUNT(*) FROM items;")).scalar()
        assert count == 2


# ---------------------------------------------------------------------------
# SEC-07: Origin regex validation & frame-ancestors CSP safety tests
# ---------------------------------------------------------------------------

def test_sec07_allowed_origins_strict_regex_validation():
    """
    SEC-07: In schemas.py, validate allowed_origins with strict regex:
    ^https?://[A-Za-z0-9.-]+(?::[0-9]{1,5})?$
    Must reject:
    - Semicolons / CSP injection: "https://a.com; script-src *"
    - Trailing paths: "https://a.com/path"
    - Spaces: " https://a.com", "https://a. com", "https://a.com "
    - Quotes or commas: 'https://a.com"', "https://a.com, https://b.com"
    - Wildcard "*"
    Must accept:
    - Mixed-case scheme: "HTtPs://a.com" -> normalizes to "https://a.com"
    - Standard domain with port: "http://localhost:3000"
    Applies on BOTH WidgetKeyCreate and WidgetKeyUpdate.
    """
    from pydantic import ValidationError
    from schemas import WidgetKeyCreate, WidgetKeyUpdate

    invalid_origins = [
        "https://a.com; script-src *",
        "https://a.com/path",
        "https://a.com/path/",
        " https://a.com",
        "https://a.com ",
        "https://a. com",
        "https://a.com:8080?query=1",
        'https://a.com"',
        "https://a.com,https://b.com",
        "ftp://a.com",
        "javascript:alert(1)",
        "*",
    ]

    for bad in invalid_origins:
        # Test on WidgetKeyCreate
        with pytest.raises(ValidationError) as exc1:
            WidgetKeyCreate(name="Test", allowed_origins=[bad])
        assert "origin" in str(exc1.value).lower(), f"Expected origin validation error on create for: {bad}"

        # Test on WidgetKeyUpdate
        with pytest.raises(ValidationError) as exc2:
            WidgetKeyUpdate(allowed_origins=[bad])
        assert "origin" in str(exc2.value).lower(), f"Expected origin validation error on update for: {bad}"

    # Valid mixed-case origin normalizes cleanly
    created = WidgetKeyCreate(name="Test", allowed_origins=["HTtPs://Sub.Acme-Corp.Com:8443"])
    assert created.allowed_origins == ["https://sub.acme-corp.com:8443"]

    updated = WidgetKeyUpdate(allowed_origins=["HTtP://Localhost:3000"])
    assert updated.allowed_origins == ["http://localhost:3000"]


def test_sec07_frame_ancestors_rejects_malformed_stored_origins(tmp_path):
    """
    SEC-07: Never emit frame-ancestors header with invalid/malformed origin
    if stored data contains invalid characters or injection attempts.
    """
    import models
    from routers.widget import get_widget_embed_page
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from starlette.datastructures import Headers, URL
    from starlette.requests import Request

    engine = create_engine(f"sqlite:///{tmp_path}/sec07_embed.db")
    models.Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    # Seed key with invalid stored origin (e.g. bypass or legacy row)
    wk_malicious = models.WidgetKey(
        id=701,
        tenant_id=1,
        public_key="pk_live_malicious_origin_key_7777777",
        name="Malicious Stored Origin Key",
        allowed_origins=["https://a.com; script-src *"],
        enabled=True
    )
    db.add(wk_malicious)
    db.commit()

    class DummyReq:
        base_url = URL("https://api.dataspeak.ai")

    res = get_widget_embed_page(wk_malicious.public_key, DummyReq(), db)
    csp_header = res.headers.get("Content-Security-Policy", "")

    # Must NOT contain the injection string in frame-ancestors
    assert "; script-src *" not in csp_header.split(";")[0], "Injection string must not be present in frame-ancestors"
    # When any origin is invalid, frame-ancestors must be 'none' or fail closed
    assert "frame-ancestors 'none';" in csp_header or "frame-ancestors" not in csp_header
    db.close()


# ---------------------------------------------------------------------------
# SEC-04: Monthly cap per key and migration tests
# ---------------------------------------------------------------------------

def test_sec04_monthly_cap_per_key_isolation_and_migration(tmp_path, monkeypatch):
    """
    SEC-04:
    - Add widget_key_id column to QueryLog and migration in db_migration.py.
    - Count monthly usage per widget key (not tenant-wide).
    - Exhausting Key A must NOT block Key B on the same tenant.
    """
    import models, schemas
    from services.db_migration import run_schema_migrations, MIGRATION_COLUMNS
    from services.widget_session_service import create_widget_session_token
    from routers.widget import process_widget_chat
    from sqlalchemy import create_engine, inspect
    from sqlalchemy.orm import sessionmaker
    from starlette.requests import Request
    from fastapi import HTTPException

    # 1. Verify db_migration includes widget_key_id for query_logs
    assert any(
        table == "query_logs" and col == "widget_key_id"
        for table, col, *_ in MIGRATION_COLUMNS
    ), "MIGRATION_COLUMNS must include widget_key_id for query_logs"

    db_path = tmp_path / "sec04_test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    models.Base.metadata.create_all(bind=engine)
    run_schema_migrations(engine)

    # Confirm column and index exists
    inspector = inspect(engine)
    col_names = [c["name"] for c in inspector.get_columns("query_logs")]
    assert "widget_key_id" in col_names, "widget_key_id column must exist in query_logs"

    indexes = inspector.get_indexes("query_logs")
    idx_names = [idx["name"] for idx in indexes]
    assert any("widget_key" in str(name).lower() for name in idx_names), "Index on widget_key_id must exist"

    Session = sessionmaker(bind=engine)
    db = Session()

    # Create tenant
    tenant = models.Tenant(id=10, name="Cap Test Tenant")
    db.add(tenant)

    # Key A has cap of 2
    key_a = models.WidgetKey(
        id=101,
        tenant_id=10,
        public_key="pk_live_key_a_11111111111111111111",
        name="Key A",
        allowed_origins=["https://allowed-a.com"],
        enabled=True,
        monthly_message_cap=2,
        allow_sql=False
    )
    # Key B has cap of 5
    key_b = models.WidgetKey(
        id=102,
        tenant_id=10,
        public_key="pk_live_key_b_22222222222222222222",
        name="Key B",
        allowed_origins=["https://allowed-b.com"],
        enabled=True,
        monthly_message_cap=5,
        allow_sql=False
    )
    db.add_all([key_a, key_b])
    db.commit()

    token_a = create_widget_session_token(
        tenant_id=10,
        public_key=key_a.public_key,
        origin="https://allowed-a.com",
        conversation_id=1
    )
    token_b = create_widget_session_token(
        tenant_id=10,
        public_key=key_b.public_key,
        origin="https://allowed-b.com",
        conversation_id=2
    )

    class DummyReq:
        headers = {"x-widget-session": token_a, "origin": "https://allowed-a.com"}
        client = type("Client", (), {"host": "127.0.0.1"})()

    dummy_req_a = DummyReq()

    # Query 1 for Key A -> Success
    req_body1 = schemas.WidgetChatRequest(query="Hello from key A 1", session_token=token_a, stream=False)
    res_a1 = process_widget_chat(req_body1, dummy_req_a, db)
    assert res_a1.query == "Hello from key A 1"

    # Query 2 for Key A -> Success
    req_body2 = schemas.WidgetChatRequest(query="Hello from key A 2", session_token=token_a, stream=False)
    res_a2 = process_widget_chat(req_body2, dummy_req_a, db)
    assert res_a2.query == "Hello from key A 2"

    # Query 3 for Key A -> Must fail with 429 Quota Exceeded
    req_body3 = schemas.WidgetChatRequest(query="Hello from key A 3", session_token=token_a, stream=False)
    with pytest.raises(HTTPException) as exc_a:
        process_widget_chat(req_body3, dummy_req_a, db)
    assert exc_a.value.status_code == 429
    assert "quota exceeded" in exc_a.value.detail.lower()

    # Key A is exhausted. Now try Key B on the SAME tenant!
    class DummyReqB:
        headers = {"authorization": f"Bearer {token_b}", "origin": "https://allowed-b.com"}
        client = type("Client", (), {"host": "127.0.0.1"})()

    dummy_req_b = DummyReqB()
    req_body_b = schemas.WidgetChatRequest(query="Hello from key B 1", session_token=token_b, stream=False)

    # Key B must NOT be blocked!
    res_b1 = process_widget_chat(req_body_b, dummy_req_b, db)
    assert res_b1.query == "Hello from key B 1"

    # Verify query logs have widget_key_id set
    logs = db.query(models.QueryLog).filter(models.QueryLog.tenant_id == 10).all()
    assert len(logs) == 3
    a_logs = [l for l in logs if l.widget_key_id == 101]
    b_logs = [l for l in logs if l.widget_key_id == 102]
    assert len(a_logs) == 2
    assert len(b_logs) == 1

    db.close()


# ---------------------------------------------------------------------------
# SEC-06: Redis stream TTL, refresh, and disconnect/exception release tests
# ---------------------------------------------------------------------------

def test_sec06_redis_stream_ttl_refresh_and_disconnect_release():
    """
    SEC-06:
    - In Redis path, acquire_stream sets 120s TTL and refresh on stream key.
    - Slot is released on client disconnect (generator exit) and on exceptions.
    """
    from services.widget_rate_limiter import WidgetRateLimiter
    from unittest.mock import MagicMock

    limiter = WidgetRateLimiter()
    mock_redis = MagicMock()
    mock_redis.incr.return_value = 1
    mock_redis.decr.return_value = 0
    limiter.redis_client = mock_redis

    # 1. Acquire stream sets TTL (120s)
    acquired = limiter.acquire_stream("pk_live_test_redis_key", max_concurrent=5)
    assert acquired is True
    mock_redis.incr.assert_called_with("widget_streams:pk_live_test_redis_key")
    mock_redis.expire.assert_called_with("widget_streams:pk_live_test_redis_key", 120)

    # 2. Release stream decrements or cleans up
    limiter.release_stream("pk_live_test_redis_key")
    mock_redis.decr.assert_called_with("widget_streams:pk_live_test_redis_key")

    # 3. Test in-memory path: exception and disconnect (GeneratorExit) slot release
    inmem_limiter = WidgetRateLimiter()
    inmem_limiter.redis_client = None

    assert inmem_limiter.acquire_stream("pk_live_inmem", max_concurrent=1) is True
    assert inmem_limiter._active_streams.get("pk_live_inmem") == 1
    # Slot is full
    assert inmem_limiter.acquire_stream("pk_live_inmem", max_concurrent=1) is False

    # Simulate generator with try/finally releasing slot on client disconnect
    def simulated_sse_generator():
        try:
            yield "data: chunk1\n\n"
            yield "data: chunk2\n\n"
        finally:
            inmem_limiter.release_stream("pk_live_inmem")

    gen = simulated_sse_generator()
    first_chunk = next(gen)
    assert "chunk1" in first_chunk

    # Simulate client disconnect by closing generator early (GeneratorExit)
    gen.close()

    # Slot must have been released!
    assert inmem_limiter._active_streams.get("pk_live_inmem") == 0
    # Next connection can acquire slot immediately
    assert inmem_limiter.acquire_stream("pk_live_inmem", max_concurrent=1) is True
    inmem_limiter.release_stream("pk_live_inmem")


# ---------------------------------------------------------------------------
# SEC-05: Evict idle IP/session buckets (TTL ~10 min)
# ---------------------------------------------------------------------------

def test_sec05_idle_bucket_eviction():
    """
    SEC-05: Evict idle IP and session buckets (TTL ~10 min) so memory is bounded.
    """
    import time
    from services.widget_rate_limiter import WidgetRateLimiter, InMemoryTokenBucket

    limiter = WidgetRateLimiter()
    limiter.redis_client = None

    now = time.time()

    # Active bucket: updated 30 seconds ago
    active_b = InMemoryTokenBucket(30, 0.5)
    active_b.last_updated = now - 30
    limiter._ip_buckets["192.168.1.1"] = active_b

    # Idle IP bucket: updated 15 minutes (900 seconds) ago
    idle_ip = InMemoryTokenBucket(30, 0.5)
    idle_ip.last_updated = now - 900
    limiter._ip_buckets["10.0.0.99"] = idle_ip

    # Idle Session bucket: updated 20 minutes (1200 seconds) ago
    idle_sess = InMemoryTokenBucket(20, 0.33)
    idle_sess.last_updated = now - 1200
    limiter._session_buckets["sess_old_123"] = idle_sess

    # Run cleanup with 600s TTL (10 minutes)
    evicted_count = limiter.cleanup_idle_buckets(ttl_seconds=600)
    assert evicted_count == 2
    assert "192.168.1.1" in limiter._ip_buckets
    assert "10.0.0.99" not in limiter._ip_buckets
    assert "sess_old_123" not in limiter._session_buckets


# ---------------------------------------------------------------------------
# SEC-10: Rate-limit values read from env with documented defaults
# ---------------------------------------------------------------------------

def test_sec10_rate_limit_values_from_env(monkeypatch):
    """
    SEC-10: Rate limit values in code, docs and process_widget_chat identical,
    read from env with documented defaults (60 key, 30 IP, 20 sess, 5 streams).
    """
    from services.widget_rate_limiter import WidgetRateLimiter

    # Default values without env override
    monkeypatch.delenv("WIDGET_RATE_LIMIT_KEY_PER_MIN", raising=False)
    monkeypatch.delenv("WIDGET_RATE_LIMIT_IP_PER_MIN", raising=False)
    monkeypatch.delenv("WIDGET_RATE_LIMIT_SESSION_PER_MIN", raising=False)
    monkeypatch.delenv("WIDGET_MAX_CONCURRENT_STREAMS", raising=False)

    def_limiter = WidgetRateLimiter()
    assert def_limiter.key_limit == 60
    assert def_limiter.ip_limit == 30
    assert def_limiter.session_limit == 20
    assert def_limiter.max_concurrent_streams == 5

    # Configured values from env
    monkeypatch.setenv("WIDGET_RATE_LIMIT_KEY_PER_MIN", "120")
    monkeypatch.setenv("WIDGET_RATE_LIMIT_IP_PER_MIN", "60")
    monkeypatch.setenv("WIDGET_RATE_LIMIT_SESSION_PER_MIN", "40")
    monkeypatch.setenv("WIDGET_MAX_CONCURRENT_STREAMS", "10")

    custom_limiter = WidgetRateLimiter()
    assert custom_limiter.key_limit == 120
    assert custom_limiter.ip_limit == 60
    assert custom_limiter.session_limit == 40
    assert custom_limiter.max_concurrent_streams == 10





