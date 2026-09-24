import os
import sys

# Ensure backend dir is on path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import models
from database import Base, engine, SessionLocal
from services.query_router import classify_query_route, auto_select_database

def test_models_and_router():
    # 1. Create tables
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Check tenant exists or create mock tenant
        tenant = db.query(models.Tenant).first()
        if not tenant:
            tenant = models.Tenant(name="Test Corp", industry="Tech")
            db.add(tenant)
            db.commit()
            db.refresh(tenant)

        print(f"[OK] Verified Tenant ID: {tenant.id}")

        # 2. Test Conversation & Message Model CRUD
        test_conv = models.Conversation(
            tenant_id=tenant.id,
            title="Test Conversation",
            platform="web"
        )
        db.add(test_conv)
        db.commit()
        db.refresh(test_conv)
        print(f"[OK] Created Conversation ID: {test_conv.id}")

        test_msg = models.Message(
            conversation_id=test_conv.id,
            sender_role="user",
            content="What are our total Q3 revenues according to the annual report?",
            query_type="rag"
        )
        db.add(test_msg)
        db.commit()
        db.refresh(test_msg)
        print(f"[OK] Created Message ID: {test_msg.id}")

        # 3. Test Query Router Heuristics
        sql_query = "SELECT count(*) FROM users WHERE is_active = true"
        decision_sql = classify_query_route(sql_query, tenant.id, db, source_preference="auto")
        print(f"[OK] Query '{sql_query}' -> Route: {decision_sql.route_type} (Confidence: {decision_sql.confidence})")

        rag_query = "Summarize the leave policy and guidelines described in the employee handbook"
        decision_rag = classify_query_route(rag_query, tenant.id, db, source_preference="auto")
        print(f"[OK] Query '{rag_query}' -> Route: {decision_rag.route_type} (Confidence: {decision_rag.confidence})")

        # 4. Clean up test data
        db.delete(test_conv)
        db.commit()
        print("[OK] Cleanup successful. All Conversation & Router tests passed!")

    finally:
        db.close()

if __name__ == "__main__":
    test_models_and_router()
