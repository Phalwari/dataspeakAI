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
