"""
tests/fixtures/nr0/synthetic_data.py
-----------------------------------
Synthetic data fixtures for Phase NR-0 regression tests and boundary verification.
Establishes two isolated tenants, multiple users with distinct permission roles,
private dashboard conversations, distinct widget keys & visitor sessions, and synthetic documents.
Contains zero real production secrets or credentials.
"""

from typing import Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timezone

import models
from auth import get_password_hash


def build_nr0_synthetic_scenario(db: Session) -> Dict[str, Any]:
    """
    Populates an isolated, disposable database with a multi-tenant test matrix.
    
    Structure:
    - Tenant 1: "Acme Corp" (plan: "Starter")
      - User 1: admin@acme.com (role: "Admin", is_active=True, is_verified=True)
      - User 2: analyst@acme.com (role: "Developer", is_active=True, is_verified=True)
      - User 3: inactive@acme.com (role: "Business Owner", is_active=False, is_verified=True)
      - User 4: unverified@acme.com (role: "Developer", is_active=True, is_verified=False)
      - Conversation 1 (Private to analyst): "Acme Internal Financials" (platform="web", user_id=analyst.id)
      - Conversation 2 (Private to admin): "Acme Exec Strategy" (platform="web", user_id=admin.id)
      - WidgetKey 1: public_key="pk_live_acme_widget_11111111111111", allowed_origins=["https://acme.com"], allow_sql=True, allowed_database_ids=[101]
      - Visitor Conversation 1: "Visitor A Query" (platform="widget", tenant_id=Tenant 1)
      - Visitor Conversation 2: "Visitor B Query" (platform="widget", tenant_id=Tenant 1)
      - DatabaseConnection 1: id=101, db_type="sqlite", name="Acme Sales", connection_string="sqlite:///:memory:"
      - Document 1 (Published): id=201, title="Acme Public FAQ", filename="faq.pdf"
      - Document 2 (Internal/Unpublished): id=202, title="Acme Confidential Q3", filename="confidential.pdf"
      - Chunks for Document 1 & Document 2
      
    - Tenant 2: "Globex Corporation" (plan: "Pro")
      - User 5: admin@globex.com (role: "Admin", is_active=True, is_verified=True)
      - User 6: member@globex.com (role: "Developer", is_active=True, is_verified=True)
      - Conversation 3 (Private to globex admin): "Globex Roadmap" (platform="web", user_id=globex_admin.id)
      - WidgetKey 2: public_key="pk_live_globex_widget_222222222222", allowed_origins=["https://globex.com"], allow_sql=False
      - DatabaseConnection 2: id=102, db_type="sqlite", name="Globex Ops", connection_string="sqlite:///:memory:"
      - Document 3: id=203, title="Globex Internal Architecture", filename="globex_arch.pdf"
    """
    now = datetime.now(timezone.utc)
    
    # 1. Tenants
    t1 = models.Tenant(id=1, name="Acme Corp", plan="Starter", website="https://acme.com")
    t2 = models.Tenant(id=2, name="Globex Corporation", plan="Pro", website="https://globex.com")
    db.add_all([t1, t2])
    db.flush()
    
    # 2. Users for Tenant 1
    u0_superadmin = models.User(
        id=99,
        email="superadmin@dataspeak.ai",
        full_name="Platform Superadmin",
        hashed_password=get_password_hash("SuperAdminPassword123!"),
        role="Admin",
        is_platform_admin=True,
        is_active=True,
        is_verified=True,
        tenant_id=None
    )
    u1_admin = models.User(
        id=1,
        email="admin@acme.com",
        full_name="Acme Admin",
        hashed_password=get_password_hash("AcmePassword123!"),
        role="Admin",
        is_platform_admin=False,
        is_active=True,
        is_verified=True,
        tenant_id=t1.id
    )
    u2_analyst = models.User(
        id=2,
        email="analyst@acme.com",
        full_name="Acme Analyst",
        hashed_password=get_password_hash("AnalystPassword123!"),
        role="Developer",
        is_platform_admin=False,
        is_active=True,
        is_verified=True,
        tenant_id=t1.id
    )
    u3_inactive = models.User(
        id=3,
        email="inactive@acme.com",
        full_name="Acme Inactive",
        hashed_password=get_password_hash("InactivePassword123!"),
        role="Business Owner",
        is_platform_admin=False,
        is_active=False,
        is_verified=True,
        tenant_id=t1.id
    )
    u4_unverified = models.User(
        id=4,
        email="unverified@acme.com",
        full_name="Acme Unverified",
        hashed_password=get_password_hash("UnverifiedPassword123!"),
        role="Developer",
        is_platform_admin=False,
        is_active=True,
        is_verified=False,
        tenant_id=t1.id
    )
    
    # Users for Tenant 2
    u5_globex_admin = models.User(
        id=5,
        email="admin@globex.com",
        full_name="Globex Admin",
        hashed_password=get_password_hash("GlobexPassword123!"),
        role="Admin",
        is_platform_admin=False,
        is_active=True,
        is_verified=True,
        tenant_id=t2.id
    )
    u6_globex_member = models.User(
        id=6,
        email="member@globex.com",
        full_name="Globex Member",
        hashed_password=get_password_hash("MemberPassword123!"),
        role="Developer",
        is_platform_admin=False,
        is_active=True,
        is_verified=True,
        tenant_id=t2.id
    )
    db.add_all([u0_superadmin, u1_admin, u2_analyst, u3_inactive, u4_unverified, u5_globex_admin, u6_globex_member])
    db.flush()
    
    # 3. Conversations
    c1_analyst = models.Conversation(
        id=10,
        tenant_id=t1.id,
        user_id=u2_analyst.id,
        title="Acme Internal Financials",
        platform="web"
    )
    c2_admin = models.Conversation(
        id=11,
        tenant_id=t1.id,
        user_id=u1_admin.id,
        title="Acme Exec Strategy",
        platform="web"
    )
    c3_globex = models.Conversation(
        id=12,
        tenant_id=t2.id,
        user_id=u5_globex_admin.id,
        title="Globex Roadmap",
        platform="web"
    )
    # Visitor Conversations
    c4_visitor_a = models.Conversation(
        id=13,
        tenant_id=t1.id,
        user_id=None,
        title="Visitor A Widget Session",
        platform="widget"
    )
    c5_visitor_b = models.Conversation(
        id=14,
        tenant_id=t1.id,
        user_id=None,
        title="Visitor B Widget Session",
        platform="widget"
    )
    db.add_all([c1_analyst, c2_admin, c3_globex, c4_visitor_a, c5_visitor_b])
    db.flush()

    # Messages inside private conversation c1
    m1 = models.Message(
        id=1,
        conversation_id=c1_analyst.id,
        sender_role="user",
        content="What was our Q3 EBITDA?",
        created_at=now
    )
    m2 = models.Message(
        id=2,
        conversation_id=c1_analyst.id,
        sender_role="assistant",
        content="Confidential: Acme Q3 EBITDA was $4.2M.",
        created_at=now
    )
    db.add_all([m1, m2])
    db.flush()
    
    # 4. Widget Keys
    wk1 = models.WidgetKey(
        id=1,
        tenant_id=t1.id,
        name="Acme Marketing Site Widget",
        public_key="pk_live_acme_widget_11111111111111",
        allowed_origins=["https://acme.com"],
        enabled=True,
        monthly_message_cap=1000,
        allow_sql=True,
        allowed_database_ids=[101]
    )
    wk2 = models.WidgetKey(
        id=2,
        tenant_id=t2.id,
        name="Globex Helpdesk Widget",
        public_key="pk_live_globex_widget_222222222222",
        allowed_origins=["https://globex.com"],
        enabled=True,
        monthly_message_cap=500,
        allow_sql=False,
        allowed_database_ids=[]
    )
    db.add_all([wk1, wk2])
    db.flush()
    
    # 5. Database Connections
    dbc1 = models.DatabaseConnection(
        id=101,
        tenant_id=t1.id,
        name="Acme Sales SQLite",
        db_type="sqlite",
        host="localhost",
        port=0,
        username="sa",
        database=":memory:",
        connection_string="sqlite:///:memory:",
        description="Acme operational sales dataset",
        status="connected"
    )
    dbc2 = models.DatabaseConnection(
        id=102,
        tenant_id=t2.id,
        name="Globex Ops SQLite",
        db_type="sqlite",
        host="localhost",
        port=0,
        username="sa",
        database=":memory:",
        connection_string="sqlite:///:memory:",
        description="Globex supply chain dataset",
        status="connected"
    )
    db.add_all([dbc1, dbc2])
    db.flush()
    
    # 6. Documents and Chunks
    doc1 = models.Document(
        id=201,
        tenant_id=t1.id,
        name="faq.pdf",
        file_type="pdf",
        status="Completed",
        total_pages=2,
        pages_processed=2
    )
    doc2 = models.Document(
        id=202,
        tenant_id=t1.id,
        name="confidential_q3.pdf",
        file_type="pdf",
        status="Completed",
        total_pages=5,
        pages_processed=5
    )
    doc3 = models.Document(
        id=203,
        tenant_id=t2.id,
        name="globex_manual.pdf",
        file_type="pdf",
        status="Completed",
        total_pages=10,
        pages_processed=10
    )
    db.add_all([doc1, doc2, doc3])
    db.flush()
    
    chunk1 = models.DocumentChunk(
        id=301,
        document_id=doc1.id,
        content="Acme business hours are Monday through Friday, 9am to 6pm EST.",
        chunk_index=0,
        hierarchy_level=1
    )
    chunk2 = models.DocumentChunk(
        id=302,
        document_id=doc2.id,
        content="RESTRICTED ACME INTERNAL: Target acquisition code name Project Falcon.",
        chunk_index=0,
        hierarchy_level=1
    )
    chunk3 = models.DocumentChunk(
        id=303,
        document_id=doc3.id,
        content="Globex standard operating procedure for international supply line logistics.",
        chunk_index=0,
        hierarchy_level=1
    )
    db.add_all([chunk1, chunk2, chunk3])
    db.commit()
    
    return {
        "tenants": {"t1": t1, "t2": t2},
        "users": {
            "u0_superadmin": u0_superadmin,
            "u1_admin": u1_admin,
            "u2_analyst": u2_analyst,
            "u3_inactive": u3_inactive,
            "u4_unverified": u4_unverified,
            "u5_globex_admin": u5_globex_admin,
            "u6_globex_member": u6_globex_member,
        },
        "conversations": {
            "c1_analyst": c1_analyst,
            "c2_admin": c2_admin,
            "c3_globex": c3_globex,
            "c4_visitor_a": c4_visitor_a,
            "c5_visitor_b": c5_visitor_b,
        },
        "widget_keys": {"wk1": wk1, "wk2": wk2},
        "db_connections": {"dbc1": dbc1, "dbc2": dbc2},
        "documents": {"doc1": doc1, "doc2": doc2, "doc3": doc3},
        "chunks": {"chunk1": chunk1, "chunk2": chunk2, "chunk3": chunk3},
    }
