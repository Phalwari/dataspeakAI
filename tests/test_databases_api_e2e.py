import os
import sys
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import main
import models
import auth
from database import get_db, Base, engine


@pytest.fixture(scope="module")
def api_client():
    client = TestClient(main.app)
    return client


@pytest.fixture(scope="module")
def auth_headers(api_client):
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    tenant = db.query(models.Tenant).first()
    if not tenant:
        tenant = models.Tenant(name="E2E Tenant")
        db.add(tenant)
        db.commit()
        db.refresh(tenant)

    user = db.query(models.User).filter(models.User.email == "e2e_tester@dataspeak.ai").first()
    if not user:
        user = models.User(
            email="e2e_tester@dataspeak.ai",
            hashed_password=auth.get_password_hash("Password123!"),
            tenant_id=tenant.id,
            role="Admin",
            is_verified=True,
            is_platform_admin=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = auth.create_access_token(data={"sub": user.email, "tenant_id": user.tenant_id})
    db.close()
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.skipif(os.getenv("RUN_LIVE_DATABASE_TESTS") != "1", reason="External database integration: set RUN_LIVE_DATABASE_TESTS=1 in an authorized network environment")
def test_api_test_postgresql_connection(api_client, auth_headers):
    """E2E Test: POST /api/databases/test with live free PostgreSQL."""
    payload = {
        "name": "Live EBI Postgres",
        "db_type": "postgresql",
        "host": "hh-pgsql-public.ebi.ac.uk",
        "port": 5432,
        "database": "pfmegrnargs",
        "username": "reader",
        "password": "NWDMCE5xdipIjRrp"
    }
    resp = api_client.post("/api/databases/test", json=payload, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "success"


@pytest.mark.skipif(os.getenv("RUN_LIVE_DATABASE_TESTS") != "1", reason="External database integration: set RUN_LIVE_DATABASE_TESTS=1 in an authorized network environment")
def test_api_test_mysql_connection(api_client, auth_headers):
    """E2E Test: POST /api/databases/test with live free MySQL."""
    payload = {
        "name": "Live Ensembl MySQL",
        "db_type": "mysql",
        "host": "ensembldb.ensembl.org",
        "port": 3306,
        "database": "homo_sapiens_core_110_38",
        "username": "anonymous",
        "password": ""
    }
    resp = api_client.post("/api/databases/test", json=payload, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "success"


def test_api_test_mongodb_connection_string(api_client, auth_headers):
    """E2E Test: POST /api/databases/test with MongoDB connection string."""
    with patch("socket.getaddrinfo", return_value=[(2, 1, 6, '', ('93.184.216.34', 27017))]), \
         patch("pymongo.MongoClient") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        mock_instance.admin.command.return_value = {"ok": 1}

        payload = {
            "name": "Live Atlas Mongo",
            "db_type": "mongodb",
            "connection_string": "mongodb+srv://testuser:testpass@cluster0.mongodb.net/sample_mflix?retryWrites=true&w=majority"
        }
        resp = api_client.post("/api/databases/test", json=payload, headers=auth_headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "success"
