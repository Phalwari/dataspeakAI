import os
import sys
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import models, schemas
from database import Base, engine, SessionLocal
from main import app
from services.sql_engine import validate_widget_sql, extract_sql_referenced_tables
from services.widget_rate_limiter import WidgetRateLimiter, InMemoryTokenBucket
from routers.widget import get_client_ip
from pydantic import ValidationError

client = TestClient(app)


# ==============================================================================
# SEC-01: Exact Table Matching Tests (Task 2.1.1)
# ==============================================================================
def test_sec01_exact_table_matching_blocks_cross_schema_bypass():
    # 1. Unqualified allowed table allows unqualified query
    valid, msg = validate_widget_sql("SELECT * FROM products;", allowed_tables=["products"])
    assert valid is True

    # 2. Schema-qualified bypass attempt on unqualified allowlist is rejected
    valid, msg = validate_widget_sql("SELECT * FROM other_schema.products;", allowed_tables=["products"])
    assert valid is False
    assert "other_schema.products" in msg

    # 3. Cross-schema bypass attempt
    valid, msg = validate_widget_sql("SELECT * FROM evil_db.products;", allowed_tables=["products"])
    assert valid is False
    assert "evil_db.products" in msg

    # 4. Explicit qualified allowlist allows exact match
    valid, msg = validate_widget_sql("SELECT * FROM public.products;", allowed_tables=["public.products"])
    assert valid is True

    # 5. Explicit qualified allowlist rejects other schema
    valid, msg = validate_widget_sql("SELECT * FROM private.products;", allowed_tables=["public.products"])
    assert valid is False
    assert "private.products" in msg


# ==============================================================================
# SEC-02: AST Fail-Closed Parsing Tests (Task 2.1.2)
# ==============================================================================
def test_sec02_ast_fail_closed_parsing():
    # 1. Malformed syntax that cannot be parsed by sqlglot fails closed
    malformed_queries = [
        "SELECT * FROM WHERE;",
        "SELECT * FROM (SELECT ;",
        "SELECT FROM WHERE products;",
        "SELECT 1 FROM 'unclosed_quote",
    ]
    for mq in malformed_queries:
        valid, msg = validate_widget_sql(mq, allowed_tables=["products"])
        assert valid is False
        assert "SQL parsing failed" in msg or "Forbidden keyword" in msg or "Only read-only" in msg

    # 2. Extract referenced tables directly raises ValueError on parse failure
    with pytest.raises(ValueError) as excinfo:
        extract_sql_referenced_tables("SELECT * FROM (((( unparsable garbage")
    assert "SQL parsing failed" in str(excinfo.value)

    # 3. Valid complex CTE parses and extracts physical tables cleanly
    tables = extract_sql_referenced_tables("WITH my_cte AS (SELECT id FROM orders) SELECT * FROM my_cte, products;")
    assert "orders" in tables
    assert "products" in tables
    assert "my_cte" not in tables


# ==============================================================================
# SEC-03: Trusted Proxy IP Validation Tests (Task 2.1.3)
# ==============================================================================
def test_sec03_trusted_proxy_ip_validation():
    # Mock FastAPI Request
    mock_req = MagicMock()

    # Case 1: Client host is 127.0.0.1 (trusted loopback proxy) -> trust X-Forwarded-For
    mock_req.client.host = "127.0.0.1"
    mock_req.headers = {"x-forwarded-for": "203.0.113.195, 10.0.0.1"}
    assert get_client_ip(mock_req) == "203.0.113.195"

    # Case 2: Client host is ::1 (trusted loopback) -> trust X-Forwarded-For
    mock_req.client.host = "::1"
    mock_req.headers = {"x-forwarded-for": "198.51.100.22"}
    assert get_client_ip(mock_req) == "198.51.100.22"

    # Case 3: Client host is UNTRUSTED external IP trying to spoof X-Forwarded-For
    mock_req.client.host = "198.51.100.77"
    mock_req.headers = {"x-forwarded-for": "1.1.1.1"}
    assert get_client_ip(mock_req) == "198.51.100.77"  # Spoofed header strictly IGNORED

    # Case 4: Custom TRUSTED_PROXIES env var
    with patch.dict(os.environ, {"TRUSTED_PROXIES": "10.0.0.1, 10.0.0.2"}):
        mock_req.client.host = "10.0.0.1"
        mock_req.headers = {"x-forwarded-for": "192.0.2.1"}
        assert get_client_ip(mock_req) == "192.0.2.1"

        # Host not in custom list
        mock_req.client.host = "127.0.0.1"
        mock_req.headers = {"x-forwarded-for": "192.0.2.1"}
        assert get_client_ip(mock_req) == "127.0.0.1"


# ==============================================================================
# SEC-04 & SEC-05 & SEC-06: Quotas, Bucket Cleanup & Stream TTL (Task 2.1.4)
# ==============================================================================
def test_sec04_key_scoped_monthly_quota():
    db = SessionLocal()
    try:
        tenant = db.query(models.Tenant).first()
        if not tenant:
            tenant = models.Tenant(name="Quota Test Tenant")
            db.add(tenant)
            db.commit()
            db.refresh(tenant)

        # Create two distinct widget keys
        key_a = models.WidgetKey(
            tenant_id=tenant.id,
            public_key="pk_live_quota_test_key_a",
            name="Key A",
            allowed_origins=["https://example.com"],
            monthly_message_cap=5
        )
        key_b = models.WidgetKey(
            tenant_id=tenant.id,
            public_key="pk_live_quota_test_key_b",
            name="Key B",
            allowed_origins=["https://example.com"],
            monthly_message_cap=10
        )
        db.add_all([key_a, key_b])
        db.commit()
        db.refresh(key_a)
        db.refresh(key_b)

        # Insert 5 QueryLogs specifically for Key A
        now = datetime.now(timezone.utc)
        for i in range(5):
            qlog = models.QueryLog(
                tenant_id=tenant.id,
                widget_key_id=key_a.id,
                source="widget",
                natural_query=f"Query {i}",
                status="success",
                created_at=now
            )
            db.add(qlog)
        db.commit()

        # Key A should have 5 queries in current month
        month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        key_a_usage = db.query(models.QueryLog).filter(
            models.QueryLog.widget_key_id == key_a.id,
            models.QueryLog.source == "widget",
            models.QueryLog.created_at >= month_start
        ).count()
        assert key_a_usage == 5

        # Key B should have 0 queries despite sharing the same tenant!
        key_b_usage = db.query(models.QueryLog).filter(
            models.QueryLog.widget_key_id == key_b.id,
            models.QueryLog.source == "widget",
            models.QueryLog.created_at >= month_start
        ).count()
        assert key_b_usage == 0

        # Cleanup
        db.query(models.QueryLog).filter(models.QueryLog.widget_key_id.in_([key_a.id, key_b.id])).delete(synchronize_session=False)
        db.delete(key_a)
        db.delete(key_b)
        db.commit()
    finally:
        db.close()


def test_sec05_rate_limiter_in_memory_bucket_pruning():
    limiter = WidgetRateLimiter()

    # Populate 10 fake IP buckets
    old_time = 1000000.0
    for i in range(10):
        b = InMemoryTokenBucket(capacity=30, fill_rate_per_sec=0.5)
        b.last_accessed = old_time
        limiter._ip_buckets[f"10.0.0.{i}"] = b

    # Add 2 fresh buckets
    fresh_b1 = InMemoryTokenBucket(capacity=30, fill_rate_per_sec=0.5)
    limiter._ip_buckets["192.168.1.1"] = fresh_b1
    fresh_b2 = InMemoryTokenBucket(capacity=30, fill_rate_per_sec=0.5)
    limiter._ip_buckets["192.168.1.2"] = fresh_b2

    assert len(limiter._ip_buckets) == 12

    # Prune inactive buckets with threshold 600s
    limiter._prune_inactive_buckets(max_idle_seconds=600, max_entries=5000)

    # All 10 stale buckets should be removed, leaving only the 2 fresh ones
    assert len(limiter._ip_buckets) == 2
    assert "192.168.1.1" in limiter._ip_buckets
    assert "192.168.1.2" in limiter._ip_buckets

    # Test max capacity trimming
    for i in range(20):
        limiter._ip_buckets[f"172.16.0.{i}"] = InMemoryTokenBucket(capacity=30, fill_rate_per_sec=0.5)
    limiter._prune_inactive_buckets(max_idle_seconds=9999999, max_entries=5)
    assert len(limiter._ip_buckets) == 5


# ==============================================================================
# SEC-07: Origin URL Validation Tests (Task 2.1.5)
# ==============================================================================
def test_sec07_origin_url_validation():
    # 1. Valid URLs normalize cleanly
    valid_origins = [
        "https://example.com",
        "https://example.com/",
        "http://localhost:3000",
        "https://app.subdomain.io:8080",
    ]
    data = schemas.WidgetKeyCreate(
        name="Test Key",
        allowed_origins=valid_origins
    )
    assert "https://example.com" in data.allowed_origins
    assert "http://localhost:3000" in data.allowed_origins
    assert "https://app.subdomain.io:8080" in data.allowed_origins

    # 2. Semicolon injection attempts fail validation
    with pytest.raises(ValidationError) as exc:
        schemas.WidgetKeyCreate(
            name="Evil Semicolon",
            allowed_origins=["https://example.com; script-src 'unsafe-inline'"]
        )
    assert "forbidden character ';'" in str(exc.value)

    # 3. Newline / CRLF injection attempts fail validation
    with pytest.raises(ValidationError):
        schemas.WidgetKeyCreate(
            name="Evil CRLF",
            allowed_origins=["https://example.com\r\nX-Injected: true"]
        )

    # 4. Path segments are rejected (origins are scheme + host + optional port)
    with pytest.raises(ValidationError) as exc:
        schemas.WidgetKeyCreate(
            name="Evil Path",
            allowed_origins=["https://example.com/api/v1"]
        )
    assert "must not include path segments" in str(exc.value)

    # 5. Wildcard origin '*' is strictly blocked
    with pytest.raises(ValidationError) as exc:
        schemas.WidgetKeyCreate(
            name="Evil Wildcard",
            allowed_origins=["*"]
        )
    assert "Wildcard origins" in str(exc.value)


# ==============================================================================
# SEC-08: Revoke Key API & Disabled State Tests (Task 2.1.5)
# ==============================================================================
def test_sec08_revoke_key_endpoint_and_disabled_state():
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == "admin@dataspeak.ai").first()
        assert user is not None

        # Create active test key
        wkey = models.WidgetKey(
            tenant_id=user.tenant_id,
            public_key="pk_live_test_revoke_sec08",
            name="Key to Revoke",
            allowed_origins=["https://myapp.com"],
            enabled=True
        )
        db.add(wkey)
        db.commit()
        db.refresh(wkey)

        from auth import create_access_token
        auth_token = create_access_token(data={"sub": user.email, "tenant_id": user.tenant_id})

        # Call PUT /api/keys/widget/{id}/revoke
        response = client.put(
            f"/api/keys/widget/{wkey.id}/revoke",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        revoked_data = response.json()
        assert revoked_data["enabled"] is False

        # Attempting handshake with revoked key must yield HTTP 403
        hs_res = client.post(
            "/api/widget/session",
            json={"public_key": "pk_live_test_revoke_sec08"},
            headers={"Origin": "https://myapp.com"}
        )
        assert hs_res.status_code == 403
        assert "disabled or revoked" in hs_res.json()["detail"]

        # Call PUT /api/keys/widget/{id} to re-enable
        enable_res = client.put(
            f"/api/keys/widget/{wkey.id}",
            json={"enabled": True},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert enable_res.status_code == 200
        assert enable_res.json()["enabled"] is True

        # Now handshake succeeds again
        hs_res2 = client.post(
            "/api/widget/session",
            json={"public_key": "pk_live_test_revoke_sec08"},
            headers={"Origin": "https://myapp.com"}
        )
        assert hs_res2.status_code == 200
        assert "session_token" in hs_res2.json()

        # Cleanup
        db.delete(wkey)
        db.commit()
    finally:
        db.close()
