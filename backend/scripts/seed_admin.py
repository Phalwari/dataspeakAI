import os
import sys

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import models
from database import SessionLocal, engine, Base
from auth import get_password_hash

DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@dataspeak.ai")
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "AdminPassword123!")
DEFAULT_ADMIN_NAME = os.getenv("DEFAULT_ADMIN_NAME", "Super Admin")
DEFAULT_ORG_NAME = os.getenv("DEFAULT_ORG_NAME", "DataSpeak Enterprise")

def seed_superadmin():
    # Only run DDL if explicitly in non-production development mode
    if os.getenv("ENVIRONMENT", "development").lower() != "production" and os.getenv("ENABLE_DEV_STARTUP_DDL", "true").lower() == "true":
        Base.metadata.create_all(bind=engine)
        try:
            from services.db_migration import run_schema_migrations
            run_schema_migrations(engine)
        except Exception as err:
            print(f"[MIGRATION] Note during seed: {err}")
    db = SessionLocal()
    try:
        # 1. Ensure default tenant exists
        tenant = db.query(models.Tenant).first()
        if not tenant:
            tenant = models.Tenant(
                name=DEFAULT_ORG_NAME,
                industry="Artificial Intelligence & Analytics",
                website="https://dataspeak.ai",
                address="Enterprise HQ"
            )
            db.add(tenant)
            db.commit()
            db.refresh(tenant)
            print(f"[SEED] Created default Tenant: '{tenant.name}' (ID: {tenant.id})")

        # 2. Check if default superadmin user exists
        admin_user = db.query(models.User).filter(models.User.email == DEFAULT_ADMIN_EMAIL).first()
        if not admin_user:
            admin_user = models.User(
                email=DEFAULT_ADMIN_EMAIL,
                full_name=DEFAULT_ADMIN_NAME,
                hashed_password=get_password_hash(DEFAULT_ADMIN_PASSWORD),
                role="Admin",
                is_active=True,
                is_verified=True,
                tenant_id=tenant.id
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            print(f"[SEED] Successfully created Superadmin User:")
            print(f"       Email:    {DEFAULT_ADMIN_EMAIL}")
            print(f"       Password: {DEFAULT_ADMIN_PASSWORD}")
            print(f"       Role:     Admin (Verified: True)")
        else:
            # Ensure admin is active and verified
            admin_user.is_active = True
            admin_user.is_verified = True
            if not admin_user.tenant_id:
                admin_user.tenant_id = tenant.id
            db.commit()
            print(f"[SEED] Superadmin User '{DEFAULT_ADMIN_EMAIL}' already exists. Status verified & active.")

        # 3. Ensure default ChatbotConfig exists for tenant
        cb_config = db.query(models.ChatbotConfig).filter(models.ChatbotConfig.tenant_id == tenant.id).first()
        if not cb_config:
            cb_config = models.ChatbotConfig(
                tenant_id=tenant.id,
                theme_color="#3b82f6",
                widget_title="DataSpeak Assistant",
                greeting_message="Hi there! How can I help you explore your data today?"
            )
            db.add(cb_config)
            db.commit()

        # 4. Ensure default TenantSettings exists for tenant (Stage 4A)
        settings = db.query(models.TenantSettings).filter(models.TenantSettings.tenant_id == tenant.id).first()
        if not settings:
            settings = models.TenantSettings(
                tenant_id=tenant.id,
                theme_mode="light",
                notifications_enabled=True
            )
            db.add(settings)
            db.commit()

        # 5. Ensure standard RBAC Roles & Permissions exist (Stage 4A)
        standard_roles = [
            ("Admin", "Full enterprise administrative control across all resources and configurations.", [
                ("manage", "all"), ("read", "all"), ("write", "all"), ("delete", "all")
            ]),
            ("Developer", "Database connections, SQL querying, schema introspection, and API key management.", [
                ("read", "databases"), ("write", "databases"), ("execute", "queries"),
                ("read", "documents"), ("write", "documents"), ("manage", "api_keys")
            ]),
            ("Business Owner", "Business dashboards, executive analytics, and AI insights management.", [
                ("read", "analytics"), ("read", "insights"), ("read", "dashboards"), ("write", "dashboards"),
                ("execute", "queries"), ("read", "reports")
            ]),
            ("Viewer", "Read-only access to published dashboards and performance insights.", [
                ("read", "dashboards"), ("read", "insights"), ("read", "analytics")
            ]),
        ]

        for role_name, description, permissions in standard_roles:
            role = db.query(models.Role).filter(models.Role.name == role_name).first()
            if not role:
                role = models.Role(name=role_name, description=description)
                db.add(role)
                db.flush()
                for action, resource in permissions:
                    perm = models.Permission(role_id=role.id, action=action, resource=resource)
                    db.add(perm)
                db.commit()

        # 6. Ensure default Admin user has Membership record (Stage 4A)
        admin_role = db.query(models.Role).filter(models.Role.name == "Admin").first()
        membership = db.query(models.Membership).filter(
            models.Membership.user_id == admin_user.id,
            models.Membership.tenant_id == tenant.id
        ).first()
        if not membership:
            membership = models.Membership(
                user_id=admin_user.id,
                tenant_id=tenant.id,
                role_id=admin_role.id if admin_role else None,
                is_owner=True
            )
            db.add(membership)
            db.commit()

        db.expunge_all()
        return admin_user
    finally:
        db.close()

if __name__ == "__main__":
    seed_superadmin()
