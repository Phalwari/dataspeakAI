"""
tests/test_nr1_platform_admin.py
--------------------------------
Verification tests for Task NR-1.1-A-T01:
Explicit Platform Administrator Authority & Security Boundary.

Acceptance Checks:
1. is_platform_admin defaults to False in models.User.
2. get_current_admin_user strictly requires is_platform_admin=True; users with
   tenant role="Admin" but is_platform_admin=False receive HTTP 403 Forbidden.
3. Registration endpoints (/api/auth/register) create users with is_platform_admin=False
   and ignore/forbid any client attempts to elevate to platform admin.
4. Tenant admin calling get_admin_tenants receives only their own tenant; other
   tenants' records are strictly withheld.
5. Platform superadmin (is_platform_admin=True) can list all tenants across organizations.
6. Diagnostics endpoint (/api/system/llm-metrics) returns 403 Forbidden to tenant admins,
   and 200 OK only to platform superadmins.
7. Alembic migration 002_add_platform_admin applies cleanly on top of baseline.
"""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine, inspect

import models
import schemas
from dependencies import get_current_admin_user, get_current_user
from database import get_db
from routers.analytics import get_admin_tenants
from main import app


def test_nr1_t01_default_authority_is_false(isolated_db: Session):
    """User instances default is_platform_admin to False."""
    user = models.User(
        email="test_default@acme.com",
        full_name="Default Tester",
        hashed_password="fake_hashed_pwd",
        role="Admin"
    )
    isolated_db.add(user)
    isolated_db.commit()
    isolated_db.refresh(user)
    
    assert user.is_platform_admin is False, "New users must default is_platform_admin to False"


def test_nr1_t01_dependency_rejects_tenant_admin(nr0_scenario):
    """get_current_admin_user rejects tenant admin with 403 Forbidden."""
    tenant_admin = nr0_scenario["users"]["u1_admin"]
    assert tenant_admin.role == "Admin"
    assert tenant_admin.is_platform_admin is False

    with pytest.raises(HTTPException) as exc_info:
        get_current_admin_user(current_user=tenant_admin)

    assert exc_info.value.status_code == 403
    assert "Platform administrator access required" in exc_info.value.detail


def test_nr1_t01_dependency_allows_platform_superadmin(nr0_scenario):
    """get_current_admin_user succeeds for user with is_platform_admin=True."""
    superadmin = nr0_scenario["users"]["u0_superadmin"]
    assert superadmin.is_platform_admin is True

    result = get_current_admin_user(current_user=superadmin)
    assert result.id == superadmin.id
    assert result.is_platform_admin is True


def test_nr1_t01_registration_cannot_elevate_platform_admin(isolated_app, isolated_db: Session):
    """Registering a new account cannot grant is_platform_admin authority."""
    payload = {
        "email": "new_org_admin@newco.com",
        "password": "SecurePassword123!",
        "full_name": "NewCo Admin",
        "company_name": "NewCo Inc",
        "is_platform_admin": True  # Malicious client injection attempt
    }
    
    resp = isolated_app.post("/api/auth/register", json=payload)
    assert resp.status_code == 200, f"Registration failed: {resp.text}"
    
    data = resp.json()
    assert data["email"] == "new_org_admin@newco.com"
    assert data["role"] == "Admin"
    assert data.get("is_platform_admin") is False, "Client registration must not elevate platform authority"

    # Verify directly in the database
    db_user = isolated_db.query(models.User).filter(models.User.email == "new_org_admin@newco.com").first()
    assert db_user is not None
    assert db_user.is_platform_admin is False, "DB record must have is_platform_admin=False"


def test_nr1_t01_system_metrics_denied_to_tenant_admin(isolated_app, nr0_scenario):
    """GET /api/system/llm-metrics returns 403 Forbidden to tenant admin."""
    tenant_admin = nr0_scenario["users"]["u1_admin"]

    # When authenticated as tenant admin (role=Admin, is_platform_admin=False)
    app.dependency_overrides[get_current_user] = lambda: tenant_admin
    try:
        resp = isolated_app.get("/api/system/llm-metrics")
        assert resp.status_code == 403
        assert "Platform administrator access required" in resp.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_nr1_t01_system_metrics_allowed_for_platform_superadmin(isolated_app, nr0_scenario):
    """GET /api/system/llm-metrics returns 200 OK to platform superadmin."""
    superadmin = nr0_scenario["users"]["u0_superadmin"]

    app.dependency_overrides[get_current_user] = lambda: superadmin
    try:
        resp = isolated_app.get("/api/system/llm-metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_requests" in data
        assert "keys" in data
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_nr1_t01_tenant_admin_cannot_access_other_tenants(nr0_scenario, isolated_db: Session):
    """Tenant admin calling get_admin_tenants receives only their own organization."""
    u1_admin = nr0_scenario["users"]["u1_admin"]
    t1 = nr0_scenario["tenants"]["t1"]
    t2 = nr0_scenario["tenants"]["t2"]

    results = get_admin_tenants(current_user=u1_admin, db=isolated_db)
    returned_ids = [item["id"] for item in results]

    assert t1.id in returned_ids, "Tenant admin must see their own organization"
    assert t2.id not in returned_ids, "Tenant admin MUST NOT see other organizations (I-01)"


def test_nr1_t01_platform_superadmin_sees_all_tenants(nr0_scenario, isolated_db: Session):
    """Platform superadmin calling get_admin_tenants receives all organizations."""
    superadmin = nr0_scenario["users"]["u0_superadmin"]
    t1 = nr0_scenario["tenants"]["t1"]
    t2 = nr0_scenario["tenants"]["t2"]

    results = get_admin_tenants(current_user=superadmin, db=isolated_db)
    returned_ids = [item["id"] for item in results]

    assert t1.id in returned_ids
    assert t2.id in returned_ids


# ---------------------------------------------------------------------------
# Task NR-1.1-A-T06 Tests: Seeding & Production Credential Safeguards
# ---------------------------------------------------------------------------

def test_seeding_production_gate(monkeypatch):
    """Calling seed_superadmin when ENVIRONMENT=production must raise RuntimeError."""
    from scripts.seed_admin import seed_superadmin
    monkeypatch.setenv("ENVIRONMENT", "production")

    with pytest.raises(RuntimeError) as exc_info:
        seed_superadmin()

    assert "Development seeding is strictly disabled when ENVIRONMENT=production" in str(exc_info.value)


def test_seeding_preserves_existing_password(monkeypatch, isolated_db: Session):
    """Development seeding must never reset an existing administrator password."""
    from scripts.seed_admin import seed_superadmin, DEFAULT_ADMIN_EMAIL
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("ENABLE_DEV_STARTUP_DDL", "false")

    # Ensure a tenant exists
    tenant = isolated_db.query(models.Tenant).first()
    if not tenant:
        tenant = models.Tenant(name="Test Org", plan="enterprise")
        isolated_db.add(tenant)
        isolated_db.commit()

    # Pre-create admin user with a custom password hash
    existing_hash = "$2b$12$eXistingPreCustomHashNotToOverWrite123456789012345678"
    admin = isolated_db.query(models.User).filter(models.User.email == DEFAULT_ADMIN_EMAIL).first()
    if not admin:
        admin = models.User(
            email=DEFAULT_ADMIN_EMAIL,
            full_name="Custom Admin",
            hashed_password=existing_hash,
            role="Admin",
            is_platform_admin=True,
            is_active=True,
            is_verified=True,
            tenant_id=tenant.id
        )
        isolated_db.add(admin)
        isolated_db.commit()
    else:
        admin.hashed_password = existing_hash
        isolated_db.commit()

    # Create fresh sessions from the isolated db bind so seed_admin's db.close() does not terminate isolated_db
    bind = isolated_db.get_bind()
    TestSession = sessionmaker(bind=bind)
    import scripts.seed_admin as sa
    monkeypatch.setattr(sa, "SessionLocal", TestSession)

    # Run seed_superadmin
    seeded_admin = seed_superadmin()

    # Verify password was preserved
    assert seeded_admin.hashed_password == existing_hash, "Seeding must NOT overwrite existing administrator password!"
    with TestSession() as verify_session:
        db_admin = verify_session.query(models.User).filter(models.User.email == DEFAULT_ADMIN_EMAIL).first()
        assert db_admin.hashed_password == existing_hash, "DB password hash must remain unchanged!"


def test_otp_not_logged_in_production(monkeypatch, capsys):
    """When ENVIRONMENT=production, send_otp_email must NOT print the OTP code to logs."""
    from routers.users import send_otp_email
    monkeypatch.setenv("ENVIRONMENT", "production")
    # Clear email credentials so fallback log path is exercised
    monkeypatch.delenv("EMAIL_USER", raising=False)
    monkeypatch.delenv("EMAIL_PASS", raising=False)
    monkeypatch.delenv("RESEND_API_KEY", raising=False)

    secret_otp = "739201"
    send_otp_email("user@company.com", secret_otp, "Password Reset", "Your code is")

    captured = capsys.readouterr()
    assert secret_otp not in captured.out, "Plaintext OTP code must never be logged in production!"
    assert secret_otp not in captured.err, "Plaintext OTP code must never be logged to stderr in production!"
    assert "Failed to deliver OTP to user@company.com" in captured.out

