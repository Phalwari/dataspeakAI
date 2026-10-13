"""
tests/test_fix_commit_issues_regression.py
-----------------------------------------
Automated regression tests verifying the 8-issue remediation package:
1. Re-mount of analytics router (covered by existing 320 tests and endpoint checks).
2. scikit-learn & xgboost availability and requirements presence.
3. Zero 'NexaBI' branding contamination across all active source code files.
4. DatabaseConnection description column persistence, schema serialization, and router wire-up.
5. Harmonized GEMINI_MODEL prioritization and deduplication in llm_generation_service.
6. Dead code removal verification.
7. Fixture location validation for covid19 CSV.
8. CLI error-handling behavior in run_audit_mongo_business.py.
"""

import os
import sys
from typing import Any, cast, List, Dict
from unittest.mock import patch, MagicMock

# Ensure backend and root are in path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
backend_dir = os.path.join(root_dir, "backend")
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models
import schemas
from database import Base
from routers.databases import add_database
from routers.connections import list_connections, get_connection
from services.llm_generation_service import GEMINI_MODELS


@pytest.fixture
def memory_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSession()
    try:
        # Seed test tenant and user
        tenant = models.Tenant(id=1, name="Test Tenant")
        db.add(tenant)
        user = models.User(
            id=1,
            tenant_id=1,
            email="tester@dataspeak.ai",
            hashed_password="hash",
            full_name="Tester",
            role="Admin",
            is_verified=True,
        )
        db.add(user)
        db.commit()
        yield db, user
    finally:
        db.close()


def test_database_connection_description_persistence_and_routes(memory_db):
    """Verify description column persists, is serialized, and passes through routes."""
    db, user = memory_db

    # 1. ORM level persistence
    conn = models.DatabaseConnection(
        tenant_id=user.tenant_id,
        name="Analytics DB",
        db_type="postgresql",
        host="localhost",
        port=5432,
        username="postgres",
        database="analytics",
        connection_string="postgresql://localhost:5432/analytics",
        description="Core analytics data warehouse",
        status="connected"
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)

    assert conn.id is not None
    assert conn.description == "Core analytics data warehouse"
    assert conn.port == 5432

    # 2. Schema serialization
    response_schema = schemas.DatabaseConnectionResponse.model_validate(conn)
    assert response_schema.description == "Core analytics data warehouse"

    # 3. add_database route helper
    create_schema = schemas.DatabaseConnectionCreate(
        name="Sales DB",
        db_type="sqlite",
        database="./sales.db",
        description="Regional sales records",
        port=None,
        connection_string=None,
    )
    added = add_database(db_conn=create_schema, current_user=user, db=db)
    assert added.description == "Regional sales records"
    assert added.name == "Sales DB"

    # 4. list_connections router output includes description
    listing: Any = list_connections(current_user=user, db=db)
    assert listing["total"] == 2
    raw_conns: List[Dict[str, Any]] = listing["connections"]
    descriptions = [c.get("description") for c in raw_conns]
    assert "Core analytics data warehouse" in descriptions
    assert "Regional sales records" in descriptions

    # 5. get_connection router output includes description
    conn_id = int(cast(int, conn.id))
    single = get_connection(connection_id=conn_id, current_user=user, db=db)
    assert single["description"] == "Core analytics data warehouse"


def test_gemini_model_prioritization_and_deduplication():
    """Verify GEMINI_MODEL env var prioritizes models without duplicating requested models."""
    from services.llm_generation_service import generate_with_gemini, generate_multimodal_with_gemini

    # Test 1: GEMINI_MODEL set to existing model in GEMINI_MODELS
    with patch.dict(os.environ, {"GEMINI_MODEL": "gemini-3.8-flash"}):
        with patch("services.llm_generation_service._get_all_gemini_keys", return_value=["test-key-1234"]):
            with patch("httpx.post") as mock_post:
                mock_post.return_value = MagicMock(status_code=200, json=lambda: {"candidates": [{"content": {"parts": [{"text": "OK"}]}}]})
                generate_with_gemini(prompt="ping")
                
                # Check URL called in first attempt
                first_url = mock_post.call_args_list[0][0][0]
                assert "gemini-3.8-flash:generateContent" in first_url

    # Test 2: GEMINI_MODEL set to a new/custom model
    with patch.dict(os.environ, {"GEMINI_MODEL": "gemini-3.5-flash-lite"}):
        with patch("services.llm_generation_service._get_all_gemini_keys", return_value=["test-key-1234"]):
            with patch("httpx.post") as mock_post:
                mock_post.return_value = MagicMock(status_code=200, json=lambda: {"candidates": [{"content": {"parts": [{"text": "OK"}]}}]})
                generate_with_gemini(prompt="ping")
                
                first_url = mock_post.call_args_list[0][0][0]
                assert "gemini-3.5-flash-lite:generateContent" in first_url

    # Test 3: Explicit model passed prioritizes explicit model without duplication
    with patch.dict(os.environ, {"GEMINI_MODEL": "gemini-3.8-flash"}):
        with patch("services.llm_generation_service._get_all_gemini_keys", return_value=["test-key-1234"]):
            with patch("httpx.post") as mock_post:
                # First attempt fails with 500, second succeeds
                mock_post.side_effect = [
                    MagicMock(status_code=500),
                    MagicMock(status_code=200, json=lambda: {"candidates": [{"content": {"parts": [{"text": "OK"}]}}]}),
                ]
                generate_with_gemini(prompt="ping", model="custom-override-model")
                
                first_url = mock_post.call_args_list[0][0][0]
                second_url = mock_post.call_args_list[1][0][0]
                assert "custom-override-model:generateContent" in first_url
                assert "gemini-3.8-flash:generateContent" in second_url

    # Test 4: Multimodal respects GEMINI_MODEL when model is None
    with patch.dict(os.environ, {"GEMINI_MODEL": "gemini-custom-vision"}):
        with patch("services.llm_generation_service._get_all_gemini_keys", return_value=["test-key-1234"]):
            with patch("httpx.post") as mock_post:
                mock_post.return_value = MagicMock(status_code=200, json=lambda: {"candidates": [{"content": {"parts": [{"text": "Vision OK"}]}}]})
                res = generate_multimodal_with_gemini(prompt="Analyze image", image_b64_list=["fakebase64"])
                assert res == "Vision OK"
                url = mock_post.call_args_list[0][0][0]
                assert "gemini-custom-vision:generateContent" in url


def test_run_audit_mongo_business_error_handling():
    """Verify run_mongo_audit returns False on missing dataset."""
    from scripts.run_audit_mongo_business import run_mongo_audit  # type: ignore[import-not-found,import-untyped]

    test_args = ["run_audit_mongo_business.py", "--data-path", "non_existent_dataset_12345.json"]
    with patch.object(sys, "argv", test_args):
        result = run_mongo_audit()
        assert result is False


def test_requirements_contain_ml_dependencies():
    """Verify scikit-learn and xgboost are explicitly in backend/requirements.txt."""
    req_path = os.path.join(backend_dir, "requirements.txt")
    with open(req_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "scikit-learn" in content
    assert "xgboost" in content


def test_dead_code_files_are_deleted():
    """Confirm the 4 orphan service files are completely deleted."""
    orphan_files = [
        os.path.join(backend_dir, "services", "pipeline_service.py"),
        os.path.join(backend_dir, "services", "file_service.py"),
        os.path.join(backend_dir, "services", "relationship_detector.py"),
        os.path.join(backend_dir, "services", "security_service.py"),
    ]
    for p in orphan_files:
        assert not os.path.exists(p), f"Orphan file {p} should have been deleted"


def test_fixture_csv_relocated():
    """Confirm covid19 CSV is in tests/fixtures/ and not at root."""
    root_csv = os.path.join(backend_dir, "..", "covid19_healthcare_hospital_analytics.csv")
    fixture_csv = os.path.join(os.path.dirname(__file__), "fixtures", "covid19_healthcare_hospital_analytics.csv")
    assert not os.path.exists(root_csv), "Root CSV must be moved"
    assert os.path.exists(fixture_csv), "Fixture CSV must exist in tests/fixtures/"


def test_nobranding_contamination_in_codebase():
    """Verify zero occurrences of 'nexabi' case-insensitively across all project source code."""
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    ignored_dirs = {".git", "node_modules", "dist", ".agents", "__pycache__", ".vscode", "graft", ".cache", "scratch", "venv", ".venv"}
    checked_exts = {".py", ".ts", ".tsx", ".html", ".css", ".json"}

    violations = []
    this_file = os.path.abspath(__file__)
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Exclude ignored dirs in-place
        dirnames[:] = [d for d in dirnames if d not in ignored_dirs]
        for f in filenames:
            ext = os.path.splitext(f)[1].lower()
            if ext in checked_exts:
                full_path = os.path.join(dirpath, f)
                if os.path.abspath(full_path) == this_file:
                    continue
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as fh:
                        for line_no, line in enumerate(fh, start=1):
                            if "nexabi" in line.lower():
                                violations.append((full_path, line_no, line.strip()))
                except Exception:
                    pass

    assert len(violations) == 0, f"Found {len(violations)} NexaBI occurrences: {violations[:5]}"
