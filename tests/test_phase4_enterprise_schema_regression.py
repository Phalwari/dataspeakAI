import os
import sys
import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import models
import schemas
from database import Base

# Use isolated in-memory SQLite database for regression tests
TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_custom_dashboards_and_widgets(db_session):
    """Verify Dashboard and Widget models, config serialization, and cascade deletion."""
    tenant = models.Tenant(name="BI Enterprise")
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)

    dashboard = models.Dashboard(
        tenant_id=tenant.id,
        title="Executive KPI Overview",
        layout_json={"columns": 12, "row_height": 100}
    )
    db_session.add(dashboard)
    db_session.commit()
    db_session.refresh(dashboard)

    w1 = models.Widget(
        dashboard_id=dashboard.id,
        type="metric_kpi",
        config_json={"title": "Monthly Recurring Revenue", "metric": "MRR", "format": "$0,0"}
    )
    w2 = models.Widget(
        dashboard_id=dashboard.id,
        type="line_chart",
        config_json={"x_axis": "month", "y_axis": "active_users"}
    )
    db_session.add_all([w1, w2])
    db_session.commit()
    db_session.refresh(dashboard)

    assert len(dashboard.widgets) == 2
    assert {w.type for w in dashboard.widgets} == {"metric_kpi", "line_chart"}

    # Schema serialization check
    dto = schemas.DashboardResponse.model_validate(dashboard)
    assert dto.title == "Executive KPI Overview"
    assert len(dto.widgets) == 2
    assert dto.widgets[0].config_json["metric"] == "MRR"

    # Cascade deletion check
    db_session.delete(dashboard)
    db_session.commit()
    assert db_session.query(models.Widget).filter_by(dashboard_id=dashboard.id).count() == 0


def test_billing_and_metering_infrastructure(db_session):
    """Verify Subscription, Invoice, Payment, and MeteredUsage models and relationships."""
    tenant = models.Tenant(name="SaaS Subscriber")
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)

    sub = models.Subscription(
        tenant_id=tenant.id,
        stripe_id="sub_live_stripe_9921",
        plan_tier="pro",
        status="active"
    )
    db_session.add(sub)
    db_session.commit()
    db_session.refresh(sub)

    invoice = models.Invoice(
        subscription_id=sub.id,
        amount_due=149.00,
        status="paid"
    )
    db_session.add(invoice)
    db_session.commit()
    db_session.refresh(invoice)

    payment = models.Payment(
        invoice_id=invoice.id,
        payment_method="stripe_card",
        status="succeeded",
        transaction_id="tx_stripe_88192"
    )
    db_session.add(payment)

    usage = models.MeteredUsage(
        tenant_id=tenant.id,
        feature="nl_queries",
        quantity=350
    )
    db_session.add(usage)
    db_session.commit()
    db_session.refresh(sub)
    db_session.refresh(usage)

    assert len(sub.invoices) == 1
    assert sub.invoices[0].amount_due == 149.00
    assert len(sub.invoices[0].payments) == 1
    assert usage.quantity == 350

    # Schema validation
    sub_dto = schemas.SubscriptionResponse.model_validate(sub)
    assert sub_dto.plan_tier == "pro"
    inv_dto = schemas.InvoiceResponse.model_validate(invoice)
    assert inv_dto.amount_due == 149.00
    pay_dto = schemas.PaymentResponse.model_validate(payment)
    assert pay_dto.transaction_id == "tx_stripe_88192"
    use_dto = schemas.MeteredUsageResponse.model_validate(usage)
    assert use_dto.feature == "nl_queries"


def test_security_policies_rate_limits_and_audit(db_session):
    """Verify RateLimit, SecurityPolicy, AuditLog, and SystemMetric models."""
    tenant = models.Tenant(name="Security Tenant")
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)

    user = models.User(email="sec_admin@security.com", hashed_password="pwd", tenant_id=tenant.id)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    conn = models.DatabaseConnection(
        tenant_id=tenant.id,
        name="Telemetry Postgres",
        db_type="postgresql",
        database="telemetry_db"
    )
    db_session.add(conn)
    db_session.commit()
    db_session.refresh(conn)

    # Rate limits
    rl = models.RateLimit(
        tenant_id=tenant.id,
        endpoint_group="widget_chat",
        max_requests_per_min=40
    )
    db_session.add(rl)

    # Security policy
    policy = models.SecurityPolicy(
        tenant_id=tenant.id,
        enforce_2fa=True,
        allowed_ip_ranges="192.168.1.0/24, 10.0.0.0/8",
        pii_redaction_rules={"mask_ssn": True, "mask_credit_card": True}
    )
    db_session.add(policy)

    # Audit log
    audit = models.AuditLog(
        tenant_id=tenant.id,
        user_id=user.id,
        action="database.connection.created",
        ip_address="192.168.1.50",
        details={"connection_name": "Telemetry Postgres"}
    )
    db_session.add(audit)

    # System metrics
    metric = models.SystemMetric(
        connection_id=conn.id,
        cpu_usage=24.5,
        memory_usage=68.2,
        active_connections=12
    )
    db_session.add(metric)
    db_session.commit()
    db_session.refresh(rl)
    db_session.refresh(policy)
    db_session.refresh(audit)
    db_session.refresh(metric)

    assert rl.max_requests_per_min == 40
    assert policy.enforce_2fa is True
    assert policy.pii_redaction_rules["mask_ssn"] is True
    assert audit.action == "database.connection.created"
    assert metric.cpu_usage == 24.5

    # Schema validation
    rl_dto = schemas.RateLimitResponse.model_validate(rl)
    assert rl_dto.endpoint_group == "widget_chat"
    pol_dto = schemas.SecurityPolicyResponse.model_validate(policy)
    assert pol_dto.enforce_2fa is True
    aud_dto = schemas.AuditLogResponse.model_validate(audit)
    assert aud_dto.user_id == user.id
    met_dto = schemas.SystemMetricResponse.model_validate(metric)
    assert met_dto.memory_usage == 68.2


def test_full_35_table_schema_integrity_and_cascade(db_session):
    """Verify that all 35 canonical tables from Full_Project_Schemas.sql co-exist and cascade cleanly."""
    from sqlalchemy import inspect
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    canonical_35_tables = {
        "tenants", "tenant_settings", "users", "roles", "permissions", "memberships",
        "database_connections", "secrets", "database_schemas", "table_metadata", "column_metadata",
        "chatbot_configs", "conversations", "messages", "intents", "query_templates",
        "executed_queries", "query_safety_logs", "documents", "document_chunks",
        "collections", "vector_records", "generated_insights", "recommendations",
        "dashboards", "widgets", "subscriptions", "invoices", "payments", "metered_usage",
        "api_keys", "rate_limits", "security_policies", "audit_logs", "system_metrics"
    }

    missing_tables = canonical_35_tables - table_names
    assert len(missing_tables) == 0, f"Missing canonical tables in database: {missing_tables}"

    # 1. Test Tenant CASCADE across dependent models
    tenant = models.Tenant(name="Cascade Test Tenant")
    db_session.add(tenant)
    db_session.commit()

    user = models.User(email="cascade@example.com", hashed_password="pw", tenant_id=tenant.id)
    db_session.add(user)
    db_session.commit()

    t_settings = models.TenantSettings(tenant_id=tenant.id, theme_mode="dark")
    t_membership = models.Membership(user_id=user.id, tenant_id=tenant.id, is_owner=True)
    t_col = models.Collection(tenant_id=tenant.id, name="KB Docs")
    t_dash = models.Dashboard(tenant_id=tenant.id, title="Main Dash")
    t_sub = models.Subscription(tenant_id=tenant.id, stripe_id="sub_cascade")
    db_session.add_all([t_settings, t_membership, t_col, t_dash, t_sub])
    db_session.commit()

    # Verify children exist
    assert db_session.query(models.TenantSettings).filter_by(tenant_id=tenant.id).count() == 1
    assert db_session.query(models.Membership).filter_by(tenant_id=tenant.id).count() == 1
    assert db_session.query(models.Collection).filter_by(tenant_id=tenant.id).count() == 1
    assert db_session.query(models.Dashboard).filter_by(tenant_id=tenant.id).count() == 1
    assert db_session.query(models.Subscription).filter_by(tenant_id=tenant.id).count() == 1

    # Delete Tenant via ORM
    db_session.delete(tenant)
    db_session.commit()

    # Verify all children were cascade deleted
    assert db_session.query(models.TenantSettings).filter_by(tenant_id=tenant.id).count() == 0
    assert db_session.query(models.Membership).filter_by(tenant_id=tenant.id).count() == 0
    assert db_session.query(models.Collection).filter_by(tenant_id=tenant.id).count() == 0
    assert db_session.query(models.Dashboard).filter_by(tenant_id=tenant.id).count() == 0
    assert db_session.query(models.Subscription).filter_by(tenant_id=tenant.id).count() == 0

    # 2. Test Role CASCADE across permissions
    role = models.Role(name="TestRole", description="Test Role")
    db_session.add(role)
    db_session.commit()

    perm1 = models.Permission(role_id=role.id, action="read", resource="databases")
    perm2 = models.Permission(role_id=role.id, action="write", resource="databases")
    db_session.add_all([perm1, perm2])
    db_session.commit()

    assert db_session.query(models.Permission).filter_by(role_id=role.id).count() == 2

    # Delete Role via ORM
    db_session.delete(role)
    db_session.commit()

    # Verify child permissions were deleted
    assert db_session.query(models.Permission).filter_by(role_id=role.id).count() == 0


def test_catalog_resync_and_relational_context_preservation(db_session):
    """Verify that sync_database_catalog preserves PK/FK context and prevents orphan column duplication."""
    import tempfile
    import sqlite3
    from services.sql_engine import sync_database_catalog, get_db_schema_context

    # Create temporary physical SQLite database with foreign keys and PII
    temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_path = temp_file.name
    temp_file.close()

    try:
        raw_conn = sqlite3.connect(temp_path)
        raw_conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT, name TEXT);")
        raw_conn.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER, amount REAL, FOREIGN KEY(user_id) REFERENCES users(id));")
        raw_conn.commit()
        raw_conn.close()

        tenant = models.Tenant(name="Catalog QA Tenant")
        db_session.add(tenant)
        db_session.commit()

        db_conn = models.DatabaseConnection(
            tenant_id=tenant.id,
            name="Physical SQLite DB",
            db_type="sqlite",
            database=temp_path,
            host="",
            username="",
            password=""
        )
        db_session.add(db_conn)
        db_session.commit()

        # 1. Initial sync
        schema_1 = sync_database_catalog(db_conn, db_session)
        assert schema_1 is not None

        # Inspect ColumnMetadata constraints
        user_email_col = db_session.query(models.ColumnMetadata).filter(
            models.ColumnMetadata.column_name == "email"
        ).first()
        assert user_email_col is not None
        assert user_email_col.is_pii is True

        order_user_id_col = db_session.query(models.ColumnMetadata).filter(
            models.ColumnMetadata.column_name == "user_id"
        ).first()
        assert order_user_id_col is not None
        assert order_user_id_col.is_foreign_key is True
        assert order_user_id_col.foreign_key_target == "users.id"

        order_id_col = db_session.query(models.ColumnMetadata).filter(
            models.ColumnMetadata.column_name == "id",
            models.ColumnMetadata.table_id == order_user_id_col.table_id
        ).first()
        assert order_id_col is not None
        assert order_id_col.is_primary_key is True

        # Check formatted schema prompt context
        ctx = get_db_schema_context(db_conn, db_session)
        assert "[PRIMARY KEY]" in ctx
        assert "[FOREIGN KEY -> users.id]" in ctx
        assert "[PII]" in ctx

        initial_col_count = db_session.query(models.ColumnMetadata).count()
        assert initial_col_count == 6

        # 2. Re-sync (must NOT duplicate columns)
        schema_2 = sync_database_catalog(db_conn, db_session)
        assert schema_2 is not None

        after_resync_col_count = db_session.query(models.ColumnMetadata).count()
        assert after_resync_col_count == 6, f"Expected 6 columns after re-sync, found {after_resync_col_count}"

        # Re-check formatted prompt
        ctx_2 = get_db_schema_context(db_conn, db_session)
        assert "[PRIMARY KEY]" in ctx_2
        assert "[FOREIGN KEY -> users.id]" in ctx_2
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


def test_user_registration_creates_membership_and_settings(db_session):
    """Verify that user registration auto-initializes TenantSettings and Membership records."""
    from routers.users import register_user as register

    # Ensure Admin role exists
    admin_role = models.Role(name="Admin", description="Administrator")
    db_session.add(admin_role)
    db_session.commit()

    class DummyReq:
        email = "founder@startup.com"
        password = "SecurePassword123!"
        full_name = "Founder Bob"
        company_name = "Acme Corp"
        invite_token = None

    res = register(user=DummyReq(), db=db_session)
    assert res["email"] == "founder@startup.com"
    created_tenant_id = res["tenant_id"]

    # Verify TenantSettings created
    settings = db_session.query(models.TenantSettings).filter_by(tenant_id=created_tenant_id).first()
    assert settings is not None
    assert settings.theme_mode == "light"

    # Verify Membership created with is_owner=True
    membership = db_session.query(models.Membership).filter_by(
        user_id=res["id"],
        tenant_id=created_tenant_id
    ).first()
    assert membership is not None
    assert membership.is_owner is True
    assert membership.role_id == admin_role.id

