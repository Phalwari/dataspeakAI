import sys
import os

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from database import SessionLocal
import models

def seed_fixture_key():
    db = SessionLocal()
    try:
        tenant = db.query(models.Tenant).first()
        if not tenant:
            tenant = models.Tenant(name="Test Tenant", plan="enterprise")
            db.add(tenant)
            db.commit()
            db.refresh(tenant)

        # Check or create ChatbotConfig
        cfg = db.query(models.ChatbotConfig).filter(models.ChatbotConfig.tenant_id == tenant.id).first()
        if not cfg:
            cfg = models.ChatbotConfig(
                tenant_id=tenant.id,
                widget_title="Fixture Support Bot",
                greeting_message="Hi! How can I help you?",
                theme_color="#3b82f6",
                position="bottom-right",
                welcome_delay=1,
                sound_enabled=False
            )
            db.add(cfg)
            db.commit()

        # Seed WidgetKey
        pub_key = "pk_live_testfixturekey1234567890123"
        wk = db.query(models.WidgetKey).filter(models.WidgetKey.public_key == pub_key).first()
        if not wk:
            wk = models.WidgetKey(
                tenant_id=tenant.id,
                public_key=pub_key,
                name="Fixture Test Key",
                allowed_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
                enabled=True,
                monthly_message_cap=1000,
                allow_sql=False,
                allowed_database_ids=[]
            )
            db.add(wk)
            db.commit()
            print(f"[SEED] Created fixture widget key: {pub_key}")
        else:
            wk.allowed_origins = ["http://localhost:8080", "http://127.0.0.1:8080"]
            wk.enabled = True
            db.commit()
            print(f"[SEED] Updated fixture widget key: {pub_key}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_fixture_key()
