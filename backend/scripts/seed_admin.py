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
    Base.metadata.create_all(bind=engine)
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
            # Reset password to default if specified
            admin_user.hashed_password = get_password_hash(DEFAULT_ADMIN_PASSWORD)
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

        return admin_user
    finally:
        db.close()

if __name__ == "__main__":
    seed_superadmin()
