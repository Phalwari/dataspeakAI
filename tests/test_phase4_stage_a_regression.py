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
from services.sql_engine import sync_database_catalog, get_db_schema_context
from scripts.seed_admin import seed_superadmin

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


def test_tenant_settings_crud_and_cascade(db_session):
    """Verify TenantSettings model creation, relationship, and cascade deletion."""
    tenant = models.Tenant(name="Acme Corp", industry="Tech")
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)

    settings = models.TenantSettings(
        tenant_id=tenant.id,
        theme_mode="dark",
        custom_domain="portal.acme.com",
        notifications_enabled=True,
        branding_logo_url="https://acme.com/logo.png"
    )
    db_session.add(settings)
    db_session.commit()
    db_session.refresh(settings)

    assert settings.id is not None
    assert settings.tenant.name == "Acme Corp"
    assert tenant.settings.theme_mode == "dark"

    # Schema serialization check
    response_dto = schemas.TenantSettingsResponse.model_validate(settings)
    assert response_dto.theme_mode == "dark"
    assert response_dto.custom_domain == "portal.acme.com"

    # Cascade deletion check
    db_session.delete(tenant)
    db_session.commit()
    assert db_session.query(models.TenantSettings).filter_by(id=settings.id).first() is None


def test_rbac_roles_permissions_and_cascade(db_session):
    """Verify Role and Permission models, back-population, and cascade deletion."""
    role = models.Role(name="DataAnalyst", description="Analytics query access")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)

    p1 = models.Permission(role_id=role.id, action="read", resource="analytics")
    p2 = models.Permission(role_id=role.id, action="execute", resource="queries")
    db_session.add_all([p1, p2])
    db_session.commit()

    assert len(role.permissions) == 2
    assert {p.action for p in role.permissions} == {"read", "execute"}

    # Schema validation check
    role_dto = schemas.RoleResponse.model_validate(role)
    assert role_dto.name == "DataAnalyst"
    assert len(role_dto.permissions) == 2

    # Cascade deletion check
    db_session.delete(role)
    db_session.commit()
    assert db_session.query(models.Permission).filter_by(role_id=role.id).count() == 0


def test_membership_association_and_user_backward_compatibility(db_session):
    """Verify Membership connects User, Tenant, and Role while preserving User.role."""
    tenant = models.Tenant(name="SaaS Tenant")
    db_session.add(tenant)
    db_session.commit()

    user = models.User(
        email="member@saas.com",
        hashed_password="hash",
        full_name="Alice Smith",
        role="Developer",  # Existing backward-compatible string role
        tenant_id=tenant.id
    )
    db_session.add(user)
    db_session.commit()

    role = models.Role(name="DeveloperRole")
    db_session.add(role)
    db_session.commit()

    membership = models.Membership(
        user_id=user.id,
        tenant_id=tenant.id,
        role_id=role.id,
        is_owner=False
    )
    db_session.add(membership)
    db_session.commit()
    db_session.refresh(membership)

    assert membership.user.email == "member@saas.com"
    assert membership.tenant.name == "SaaS Tenant"
    assert membership.role.name == "DeveloperRole"
    assert len(user.memberships) == 1
    assert user.role == "Developer"  # Legacy column remains untouched

    # Schema serialization check
    membership_dto = schemas.MembershipResponse.model_validate(membership)
    assert membership_dto.user_id == user.id
    assert membership_dto.role.name == "DeveloperRole"


def test_database_secrets_model_and_cascade(db_session):
    """Verify Secret stores encrypted credentials and cascades with DatabaseConnection."""
    tenant = models.Tenant(name="Secret Tenant")
    db_session.add(tenant)
    db_session.commit()

    conn = models.DatabaseConnection(
        tenant_id=tenant.id,
        name="Prod Postgres",
        db_type="postgresql",
        database="prod_db"
    )
    db_session.add(conn)
    db_session.commit()

    secret = models.Secret(
        connection_id=conn.id,
        provider="local",
        encrypted_credentials="enc_credential_payload_token",
        key_version="v1"
    )
    db_session.add(secret)
    db_session.commit()
    db_session.refresh(secret)

    assert secret.id is not None
    assert len(conn.secrets) == 1
    assert conn.secrets[0].provider == "local"

    secret_dto = schemas.SecretResponse.model_validate(secret)
    assert secret_dto.key_version == "v1"

    # Cascade deletion check
    db_session.delete(conn)
    db_session.commit()
    assert db_session.query(models.Secret).filter_by(id=secret.id).first() is None


def test_persistent_schema_catalog_and_pii_flagging(db_session, tmp_path):
    """Verify persistent schema catalog models and sync_database_catalog helper."""
    # Create a dummy physical SQLite database to introspect
    sample_db_file = tmp_path / "test_sample.db"
    sample_engine = create_engine(f"sqlite:///{sample_db_file}")
    with sample_engine.begin() as c:
        c.exec_driver_sql("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT, password_hash TEXT, full_name TEXT);")
        c.exec_driver_sql("CREATE TABLE audit_logs (id INTEGER PRIMARY KEY, action TEXT, created_at TEXT);")
    sample_engine.dispose()

    tenant = models.Tenant(name="Catalog Tenant")
    db_session.add(tenant)
    db_session.commit()

    db_conn = models.DatabaseConnection(
        tenant_id=tenant.id,
        name="Sample SQLite",
        db_type="sqlite",
        database=str(sample_db_file)
    )
    db_session.add(db_conn)
    db_session.commit()

    # Call catalog sync helper
    db_schema = sync_database_catalog(db_conn, db_session)
    assert db_schema is not None
    assert db_schema.connection_id == db_conn.id

    # Verify tables were recorded
    tables = db_session.query(models.TableMetadata).filter_by(schema_id=db_schema.id).all()
    table_names = {t.table_name for t in tables}
    assert "users" in table_names
    assert "audit_logs" in table_names

    # Check PII column detection
    users_table = next(t for t in tables if t.table_name == "users")
    user_columns = {c.column_name: c.is_pii for c in users_table.columns}
    assert user_columns["email"] is True
    assert user_columns["password_hash"] is True
    assert user_columns["full_name"] is False

    # Check fact table heuristic detection
    audit_table = next(t for t in tables if t.table_name == "audit_logs")
    assert audit_table.is_fact_table is True

    # Check Schema serialization
    schema_dto = schemas.DatabaseSchemaResponse.model_validate(db_schema)
    assert len(schema_dto.tables) == 2

    # Check that get_db_schema_context uses the persistent catalog
    context_str = get_db_schema_context(db_conn, db_session)
    assert "--- SCHEMA DETAILS (PERSISTENT CATALOG) ---" in context_str
    assert "[PII]" in context_str


def test_seed_superadmin_idempotency_and_rbac(db_session, monkeypatch):
    """Verify seed_superadmin creates standard roles, permissions, settings, and membership cleanly."""
    monkeypatch.setattr("scripts.seed_admin.SessionLocal", lambda: db_session)
    monkeypatch.setattr("scripts.seed_admin.engine", engine)

    # First run
    seed_superadmin()
    admin_user = db_session.query(models.User).filter_by(email="admin@dataspeak.ai").first()
    assert admin_user is not None

    # Verify 4 standard roles exist
    roles = db_session.query(models.Role).all()
    role_names = {r.name for r in roles}
    assert {"Admin", "Developer", "Business Owner", "Viewer"}.issubset(role_names)

    # Verify Admin has membership
    membership = db_session.query(models.Membership).filter_by(user_id=admin_user.id).first()
    assert membership is not None
    assert membership.is_owner is True
    assert membership.role.name == "Admin"

    # Verify TenantSettings exists
    settings = db_session.query(models.TenantSettings).filter_by(tenant_id=admin_user.tenant_id).first()
    assert settings is not None
    assert settings.theme_mode == "light"

    # Second run (Idempotency check - must not raise duplicate key errors)
    second_admin = seed_superadmin()
    assert second_admin is not None
    assert db_session.query(models.Role).count() == 4
