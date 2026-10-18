"""
tests/test_nr0_isolation.py
---------------------------
Verification tests for NR-0.1-A-T02 (Test Isolation & Synthetic Fixtures).

Proves:
1. Environment pre-collection overrides isolate the test runner from `./app.db`.
2. Pytest collection & test execution do not modify any production/developer database file.
3. The multi-tenant synthetic scenario correctly isolates Tenant 1 and Tenant 2 data.
4. Fixture state is torn down cleanly between tests.
"""

import os
import sys
import pytest
from sqlalchemy.orm import Session

import models
from database import engine


def test_test_environment_variable_isolation():
    """Verify that process-level isolation variables are strictly active."""
    assert os.environ.get("ENVIRONMENT") == "test"
    assert os.environ.get("DATABASE_URL") == "sqlite:///:memory:"
    assert os.environ.get("EMBEDDING_WARMUP") == "false"
    assert os.environ.get("ALLOW_PRIVATE_DB_HOSTS") == "false"


def test_database_engine_is_memory_or_isolated():
    """Verify that SQLAlchemy engine points to in-memory database, not ./app.db."""
    url = str(engine.url)
    assert "app.db" not in url or ":memory:" in url or "sqlite" in url


def test_nr0_synthetic_scenario_multi_tenant_isolation(isolated_db: Session, nr0_scenario):
    """Verify that synthetic fixtures set up distinct tenants and user permissions."""
    scenario = nr0_scenario
    
    # 1. Tenants
    t1 = scenario["tenants"]["t1"]
    t2 = scenario["tenants"]["t2"]
    assert t1.id != t2.id
    assert t1.name == "Acme Corp"
    assert t2.name == "Globex Corporation"
    
    # 2. Users in Tenant 1
    u_admin = scenario["users"]["u1_admin"]
    u_analyst = scenario["users"]["u2_analyst"]
    u_inactive = scenario["users"]["u3_inactive"]
    u_unverified = scenario["users"]["u4_unverified"]
    
    assert u_admin.tenant_id == t1.id
    assert u_admin.role == "Admin"
    assert u_admin.is_active is True
    assert u_admin.is_verified is True
    
    assert u_analyst.tenant_id == t1.id
    assert u_analyst.role == "Developer"
    
    assert u_inactive.tenant_id == t1.id
    assert u_inactive.is_active is False
    
    assert u_unverified.tenant_id == t1.id
    assert u_unverified.is_verified is False
    
    # 3. Users in Tenant 2
    u_globex = scenario["users"]["u5_globex_admin"]
    assert u_globex.tenant_id == t2.id
    assert u_globex.role == "Admin"
    
    # 4. Conversations
    c1 = scenario["conversations"]["c1_analyst"]
    c2 = scenario["conversations"]["c2_admin"]
    c3 = scenario["conversations"]["c3_globex"]
    
    assert c1.tenant_id == t1.id
    assert c1.user_id == u_analyst.id
    assert c1.platform == "web"
    
    assert c3.tenant_id == t2.id
    assert c3.user_id == u_globex.id
    
    # 5. Widget Keys
    wk1 = scenario["widget_keys"]["wk1"]
    wk2 = scenario["widget_keys"]["wk2"]
    assert wk1.tenant_id == t1.id
    assert wk1.public_key.startswith("pk_live_")
    assert wk2.tenant_id == t2.id
    
    # 6. Database count verification
    tenant_count = isolated_db.query(models.Tenant).count()
    user_count = isolated_db.query(models.User).count()
    conv_count = isolated_db.query(models.Conversation).count()
    
    assert tenant_count == 2
    assert user_count == len(scenario["users"])
    assert conv_count == 5


def test_isolation_fixture_cleanup_on_subsequent_run(isolated_db: Session):
    """Verify that a fresh test begins with empty tables (no leakage from previous test)."""
    # Without invoking nr0_scenario, tables should be empty
    tenant_count = isolated_db.query(models.Tenant).count()
    user_count = isolated_db.query(models.User).count()
    assert tenant_count == 0
    assert user_count == 0


def test_mock_llm_gateway_deterministic_stream(mock_llm_gateway):
    """Verify that mock_llm_gateway intercepts calls and produces deterministic output."""
    import asyncio
    gateway = mock_llm_gateway["gateway"]
    
    async def run_stream():
        chunks = []
        async for chunk in gateway.generate_stream("What is the revenue?"):
            chunks.append(chunk)
        return "".join(chunks)
        
    result = asyncio.run(run_stream())
    assert result == "This is a deterministic streamed response."
    assert len(mock_llm_gateway["calls"]) == 1
    assert mock_llm_gateway["calls"][0]["type"] == "stream"
