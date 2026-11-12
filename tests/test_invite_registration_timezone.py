from datetime import datetime, timedelta, timezone

import models
from routers.users import register_user


def test_invite_registration_accepts_database_naive_expiry(isolated_db, monkeypatch):
    """SQLite may return DateTime values without tzinfo; invite registration must still work."""
    role = models.Role(name="Viewer", description="Read-only")
    tenant = models.Tenant(name="Timezone Fixture")
    isolated_db.add_all([role, tenant])
    isolated_db.commit()

    invite = models.TenantInvite(
        email="invitee@example.test",
        token="offline-invite-token",
        tenant_id=tenant.id,
        role="Viewer",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    isolated_db.add(invite)
    isolated_db.commit()

    monkeypatch.setattr("routers.users.send_otp_email", lambda *args, **kwargs: None)

    class Invitee:
        email = "invitee@example.test"
        password = "offline-test-password"
        full_name = "Invitee Test"
        company_name = None
        invite_token = "offline-invite-token"

    result = register_user(user=Invitee(), db=isolated_db)

    assert result["email"] == "invitee@example.test"
    assert result["tenant_id"] == tenant.id
