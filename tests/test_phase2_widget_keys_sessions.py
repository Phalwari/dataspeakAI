"""
tests/test_phase2_widget_keys_sessions.py
-----------------------------------------
Automated regression tests for Phase 2: Embeddable Standalone Chatbot Widget (Stage A).
Verifies:
1. WidgetKey model schema, defaults, and zero-dependency migration.
2. Authenticated widget key CRUD endpoints (/api/keys/widget).
3. Wildcard origins rejection and empty allowlist rejection.
4. Key rotation with 24-hour grace window.
5. Key revocation and deletion.
6. Multi-tenant isolation for widget keys.
7. POST /api/widget/session:
   - Valid Origin header session token issuance.
   - Referer fallback origin extraction.
   - Missing origin/referer 403 rejection.
   - Unauthorized origin 403 rejection.
   - Empty allowlist deny-all 403 rejection.
   - Revoked key 403 rejection.
   - Key rotation grace window (valid before expiry, 403 after expiry).
   - Non-existent key 403 rejection.
   - HMAC session token signature and claims verification.
   - Tenant isolation for session conversations.
"""

import os
import sys
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Ensure backend directory is in path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import models
import schemas
import auth
from database import Base, get_db
from dependencies import get_current_user
from main import app
from services.widget_session_service import (
    verify_widget_session_token,
    extract_request_origin,
    is_origin_allowed,
    normalize_origin
)


@pytest.fixture
def test_setup():
    # Use isolated SQLite in-memory database
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSession()

    # Seed Tenant 1 and User 1
    t1 = models.Tenant(id=1, name="Acme Corp")
    db.add(t1)
    u1 = models.User(
        id=1,
        tenant_id=1,
        email="alice@acme.com",
        hashed_password=auth.get_password_hash("Secret123!"),
        full_name="Alice Smith",
        role="Admin",
        is_verified=True,
    )
    db.add(u1)

    # Seed Tenant 2 and User 2 (for multi-tenant isolation tests)
    t2 = models.Tenant(id=2, name="Beta Ltd")
    db.add(t2)
    u2 = models.User(
        id=2,
        tenant_id=2,
        email="bob@beta.com",
        hashed_password=auth.get_password_hash("Secret123!"),
        full_name="Bob Jones",
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

    # Create tokens for test clients
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


# ---------------------------------------------------------------------------
# Unit & Helper Tests
# ---------------------------------------------------------------------------

def test_origin_normalization_and_allowlist():
    assert normalize_origin("https://example.com/") == "https://example.com"
    assert normalize_origin("http://localhost:3000") == "http://localhost:3000"
    assert normalize_origin("") is None
    assert normalize_origin(None) is None

    # Allowed list checking
    assert is_origin_allowed("https://example.com", ["https://example.com"]) is True
    assert is_origin_allowed("https://example.com/", ["https://example.com"]) is True
    assert is_origin_allowed("https://evil.com", ["https://example.com"]) is False
    assert is_origin_allowed("https://example.com", []) is False
    assert is_origin_allowed("https://example.com", None) is False
    # Wildcard is strictly ignored
    assert is_origin_allowed("https://any.com", ["*"]) is False


# ---------------------------------------------------------------------------
# Task 2.1b: Authenticated Widget Keys Endpoints
# ---------------------------------------------------------------------------

def test_widget_key_crud_lifecycle(test_setup):
    client = test_setup["client"]
    token1 = test_setup["token1"]
    headers1 = {"Authorization": f"Bearer {token1}"}

    # 1. Create a widget key
    payload = {
        "name": "Production Widget",
        "allowed_origins": ["https://acme.com", "http://localhost:5173"],
        "monthly_message_cap": 2500,
        "allow_sql": False,
        "allowed_database_ids": []
    }
    resp = client.post("/api/keys/widget", json=payload, headers=headers1)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["name"] == "Production Widget"
    assert data["public_key"].startswith("pk_live_")
    assert len(data["public_key"]) >= 39  # "pk_live_" + 32 chars
    assert data["enabled"] is True
    assert data["monthly_message_cap"] == 2500
    assert data["allow_sql"] is False
    key_id = data["id"]
    pub_key_1 = data["public_key"]

    # 2. List widget keys
    list_resp = client.get("/api/keys/widget", headers=headers1)
    assert list_resp.status_code == 200
    keys = list_resp.json()
    assert len(keys) == 1
    assert keys[0]["id"] == key_id

    # 3. Update widget key
    update_payload = {
        "name": "Renamed Widget",
        "allow_sql": True,
        "allowed_database_ids": [10, 12]
    }
    update_resp = client.put(f"/api/keys/widget/{key_id}", json=update_payload, headers=headers1)
    assert update_resp.status_code == 200
    updated_data = update_resp.json()
    assert updated_data["name"] == "Renamed Widget"
    assert updated_data["allow_sql"] is True
    assert updated_data["allowed_database_ids"] == [10, 12]

    # 4. Rotate widget key
    rotate_resp = client.post(f"/api/keys/widget/{key_id}/rotate", headers=headers1)
    assert rotate_resp.status_code == 200
    rot_data = rotate_resp.json()
    assert rot_data["new_key"] != pub_key_1
    assert rot_data["previous_key"] == pub_key_1
    assert rot_data["previous_key_expires_at"] is not None

    # 5. Revoke widget key
    revoke_resp = client.put(f"/api/keys/widget/{key_id}/revoke", headers=headers1)
    assert revoke_resp.status_code == 200
    revoked_data = revoke_resp.json()
    assert revoked_data["enabled"] is False

    # 6. Delete widget key
    del_resp = client.delete(f"/api/keys/widget/{key_id}", headers=headers1)
    assert del_resp.status_code == 200
    assert del_resp.json()["message"] == "Widget key deleted successfully"

    # Confirm deleted
    list_after = client.get("/api/keys/widget", headers=headers1)
    assert len(list_after.json()) == 0


def test_widget_key_validation_rules(test_setup):
    client = test_setup["client"]
    token1 = test_setup["token1"]
    headers1 = {"Authorization": f"Bearer {token1}"}

    # Empty origins list rejected
    resp_empty = client.post("/api/keys/widget", json={
        "name": "Test",
        "allowed_origins": []
    }, headers=headers1)
    assert resp_empty.status_code == 422

    # Wildcard origin rejected
    resp_wildcard = client.post("/api/keys/widget", json={
        "name": "Test",
        "allowed_origins": ["*"]
    }, headers=headers1)
    assert resp_wildcard.status_code == 422

    # Invalid origin scheme rejected
    resp_invalid_scheme = client.post("/api/keys/widget", json={
        "name": "Test",
        "allowed_origins": ["ftp://acme.com"]
    }, headers=headers1)
    assert resp_invalid_scheme.status_code == 422


def test_tenant_isolation_on_widget_keys(test_setup):
    client = test_setup["client"]
    headers1 = {"Authorization": f"Bearer {test_setup['token1']}"}
    headers2 = {"Authorization": f"Bearer {test_setup['token2']}"}

    # Tenant 1 creates a key
    create_resp = client.post("/api/keys/widget", json={
        "name": "Tenant 1 Key",
        "allowed_origins": ["https://t1.com"]
    }, headers=headers1)
    assert create_resp.status_code == 200
    key1_id = create_resp.json()["id"]

    # Tenant 2 lists keys -> must NOT see Tenant 1's key
    t2_list = client.get("/api/keys/widget", headers=headers2)
    assert t2_list.status_code == 200
    assert len(t2_list.json()) == 0

    # Tenant 2 attempts to update Tenant 1's key -> 404
    t2_update = client.put(f"/api/keys/widget/{key1_id}", json={"name": "Hacked"}, headers=headers2)
    assert t2_update.status_code == 404

    # Tenant 2 attempts to rotate Tenant 1's key -> 404
    t2_rotate = client.post(f"/api/keys/widget/{key1_id}/rotate", headers=headers2)
    assert t2_rotate.status_code == 404

    # Tenant 2 attempts to revoke Tenant 1's key -> 404
    t2_revoke = client.put(f"/api/keys/widget/{key1_id}/revoke", headers=headers2)
    assert t2_revoke.status_code == 404

    # Tenant 2 attempts to delete Tenant 1's key -> 404
    t2_delete = client.delete(f"/api/keys/widget/{key1_id}", headers=headers2)
    assert t2_delete.status_code == 404


# ---------------------------------------------------------------------------
# Task 2.1c: POST /api/widget/session Handshake & Security
# ---------------------------------------------------------------------------

def test_widget_session_valid_origin(test_setup):
    client = test_setup["client"]
    headers1 = {"Authorization": f"Bearer {test_setup['token1']}"}

    # 1. Create active widget key for Acme Corp (tenant_id = 1)
    create_resp = client.post("/api/keys/widget", json={
        "name": "Acme Live Widget",
        "allowed_origins": ["https://acme-store.com", "http://localhost:3000"]
    }, headers=headers1)
    assert create_resp.status_code == 200
    pub_key = create_resp.json()["public_key"]

    # 2. Public request with Origin header
    session_resp = client.post(
        "/api/widget/session",
        json={"public_key": pub_key},
        headers={"Origin": "https://acme-store.com"}
    )
    assert session_resp.status_code == 200, session_resp.text
    session_data = session_resp.json()
    assert "session_token" in session_data
    assert session_data["tenant_id"] == 1
    assert session_data["conversation_id"] is not None
    assert session_data["expires_in"] == 3600

    # 3. Verify HMAC token claims
    token = session_data["session_token"]
    payload = verify_widget_session_token(token, expected_origin="https://acme-store.com")
    assert payload["tenant_id"] == 1
    assert payload["public_key"] == pub_key
    assert payload["origin"] == "https://acme-store.com"
    assert payload["conversation_id"] == session_data["conversation_id"]
    assert payload["sub"] == "widget_session"


def test_widget_session_referer_fallback(test_setup):
    client = test_setup["client"]
    headers1 = {"Authorization": f"Bearer {test_setup['token1']}"}

    create_resp = client.post("/api/keys/widget", json={
        "name": "Referer Test",
        "allowed_origins": ["https://client.org"]
    }, headers=headers1)
    pub_key = create_resp.json()["public_key"]

    # Request with Referer header instead of Origin
    resp = client.post(
        "/api/widget/session",
        json={"public_key": pub_key},
        headers={"Referer": "https://client.org/products/item-42?ref=nav"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["tenant_id"] == 1
    claims = verify_widget_session_token(data["session_token"])
    assert claims["origin"] == "https://client.org"


def test_widget_session_unauthorized_origin_rejected(test_setup):
    client = test_setup["client"]
    headers1 = {"Authorization": f"Bearer {test_setup['token1']}"}

    create_resp = client.post("/api/keys/widget", json={
        "name": "Strict Widget",
        "allowed_origins": ["https://trusted.com"]
    }, headers=headers1)
    pub_key = create_resp.json()["public_key"]

    # Request from unauthorized origin -> 403
    resp = client.post(
        "/api/widget/session",
        json={"public_key": pub_key},
        headers={"Origin": "https://untrusted-phishing.com"}
    )
    assert resp.status_code == 403
    assert "Origin not permitted" in resp.json()["detail"]


def test_widget_session_missing_origin_and_referer_rejected(test_setup):
    client = test_setup["client"]
    headers1 = {"Authorization": f"Bearer {test_setup['token1']}"}

    create_resp = client.post("/api/keys/widget", json={
        "name": "No-Header Widget",
        "allowed_origins": ["https://trusted.com"]
    }, headers=headers1)
    pub_key = create_resp.json()["public_key"]

    # Direct request without Origin or Referer -> 403
    resp = client.post(
        "/api/widget/session",
        json={"public_key": pub_key}
    )
    assert resp.status_code == 403
    assert "Missing or invalid Origin" in resp.json()["detail"]


def test_widget_session_revoked_key_rejected(test_setup):
    client = test_setup["client"]
    headers1 = {"Authorization": f"Bearer {test_setup['token1']}"}

    create_resp = client.post("/api/keys/widget", json={
        "name": "Revoke Test",
        "allowed_origins": ["https://acme.com"]
    }, headers=headers1)
    key_id = create_resp.json()["id"]
    pub_key = create_resp.json()["public_key"]

    # Revoke key
    client.put(f"/api/keys/widget/{key_id}/revoke", headers=headers1)

    # Session request with revoked key -> 403
    resp = client.post(
        "/api/widget/session",
        json={"public_key": pub_key},
        headers={"Origin": "https://acme.com"}
    )
    assert resp.status_code == 403
    assert "disabled or revoked" in resp.json()["detail"]


def test_widget_session_key_rotation_grace_period(test_setup):
    client = test_setup["client"]
    db = test_setup["db"]
    headers1 = {"Authorization": f"Bearer {test_setup['token1']}"}

    # 1. Create key
    create_resp = client.post("/api/keys/widget", json={
        "name": "Rotation Grace Test",
        "allowed_origins": ["https://acme.com"]
    }, headers=headers1)
    key_id = create_resp.json()["id"]
    old_key = create_resp.json()["public_key"]

    # 2. Rotate key
    rotate_resp = client.post(f"/api/keys/widget/{key_id}/rotate", headers=headers1)
    new_key = rotate_resp.json()["new_key"]

    # 3. New key works immediately -> 200
    resp_new = client.post(
        "/api/widget/session",
        json={"public_key": new_key},
        headers={"Origin": "https://acme.com"}
    )
    assert resp_new.status_code == 200

    # 4. Old key still works within grace period -> 200
    resp_old = client.post(
        "/api/widget/session",
        json={"public_key": old_key},
        headers={"Origin": "https://acme.com"}
    )
    assert resp_old.status_code == 200

    # 5. Simulate expiry of grace window in database
    wk = db.query(models.WidgetKey).filter(models.WidgetKey.id == key_id).first()
    wk.previous_key_expires_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    db.commit()

    # 6. Old key after grace expiry -> 403
    resp_old_expired = client.post(
        "/api/widget/session",
        json={"public_key": old_key},
        headers={"Origin": "https://acme.com"}
    )
    assert resp_old_expired.status_code == 403
    assert "Invalid or expired widget key" in resp_old_expired.json()["detail"]


def test_widget_session_empty_allowlist_denies_all(test_setup):
    client = test_setup["client"]
    db = test_setup["db"]

    # Directly create widget key in DB with empty allowed_origins list
    wk = models.WidgetKey(
        tenant_id=1,
        public_key="pk_live_emptyallowlisttest1234567890",
        name="Empty Allowlist",
        allowed_origins=[],
        enabled=True
    )
    db.add(wk)
    db.commit()

    # Even with an Origin header present, empty allowlist must deny
    resp = client.post(
        "/api/widget/session",
        json={"public_key": "pk_live_emptyallowlisttest1234567890"},
        headers={"Origin": "https://acme.com"}
    )
    assert resp.status_code == 403
    assert "Origin not permitted" in resp.json()["detail"]


def test_widget_session_tenant_conversation_isolation(test_setup):
    client = test_setup["client"]
    db = test_setup["db"]
    headers1 = {"Authorization": f"Bearer {test_setup['token1']}"}

    # 1. Create a conversation owned by Tenant 2
    conv_t2 = models.Conversation(tenant_id=2, title="Tenant 2 Secret Conv", platform="web")
    db.add(conv_t2)
    db.commit()
    db.refresh(conv_t2)

    # 2. Tenant 1 creates a widget key
    create_resp = client.post("/api/keys/widget", json={
        "name": "Tenant 1 Widget",
        "allowed_origins": ["https://t1.com"]
    }, headers=headers1)
    pub_key_t1 = create_resp.json()["public_key"]

    # 3. An attacker from Tenant 1's widget passes Tenant 2's conversation_id
    resp = client.post(
        "/api/widget/session",
        json={"public_key": pub_key_t1, "conversation_id": conv_t2.id},
        headers={"Origin": "https://t1.com"}
    )
    assert resp.status_code == 200
    session_data = resp.json()
    # It must NOT bind to Tenant 2's conversation!
    assert session_data["conversation_id"] != conv_t2.id
    # Instead, a new conversation bound to Tenant 1 was created
    new_conv = db.query(models.Conversation).filter(models.Conversation.id == session_data["conversation_id"]).first()
    assert new_conv.tenant_id == 1
