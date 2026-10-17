"""
tests/conftest.py
-----------------
Master Pytest Configuration & Test Isolation Harness for DataSpeakAI.

Guarantees:
1. Strict pre-collection environment isolation: Overrides all persistence,
   caching, external provider, and background worker environment variables
   BEFORE test modules are imported or collected.
2. In-Memory SQLite isolation: Prevents any test from opening or altering `./app.db`.
3. Deterministic doubles: Eliminates live external API calls (Gemini/Groq/Resend/Redis)
   and HuggingFace model downloads in default test runs.
"""

import os
import sys
import tempfile
import pytest
from typing import Generator, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

# 1. Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# 2. Strict Pre-Collection Environment Setup (Executed at conftest load time)
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["EMBEDDING_WARMUP"] = "false"
os.environ["SECRET_KEY"] = "test-isolated-secret-key-32b-minimum-length-ok"
os.environ["WIDGET_HMAC_SECRET"] = "test-isolated-widget-hmac-secret-64b-minimum-length-ok"
os.environ["CELERY_BROKER_URL"] = ""
os.environ["CELERY_RESULT_BACKEND"] = ""
os.environ["REDIS_URL"] = ""
os.environ["ALLOW_PRIVATE_DB_HOSTS"] = "false"
os.environ["DEFAULT_ADMIN_EMAIL"] = "admin@dataspeak.ai"
os.environ["DEFAULT_ADMIN_PASSWORD"] = "AdminPassword123!"

# Provide synthetic dummy keys so LLMGateway initializes candidate pools without live calls
os.environ["GEMINI_API_KEY"] = "mock_gemini_test_key_001"
os.environ["GROQ_API_KEY"] = "mock_groq_test_key_001"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from database import Base, get_db, engine as global_db_engine
from scripts.seed_admin import seed_superadmin
from fixtures.nr0.synthetic_data import build_nr0_synthetic_scenario


@pytest.fixture(scope="session", autouse=True)
def setup_global_test_db():
    """Initializes in-memory database schema and seeds initial dev superadmin for tests."""
    Base.metadata.create_all(bind=global_db_engine)
    seed_superadmin()
    yield



@pytest.fixture(scope="function")
def isolated_db_engine():
    """Provides a fresh, isolated in-memory SQLite engine with StaticPool."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def isolated_db(isolated_db_engine) -> Generator[Session, None, None]:
    """Provides a clean SQLAlchemy Session attached to the isolated in-memory engine."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=isolated_db_engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture(scope="function")
def isolated_app(isolated_db: Session) -> Generator[TestClient, None, None]:
    """
    Provides a FastAPI TestClient with the get_db dependency overridden
    to use the isolated in-memory database session.
    """
    from main import app

    def override_get_db():
        try:
            yield isolated_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture(scope="function")
def nr0_scenario(isolated_db: Session) -> Dict[str, Any]:
    """Populates the isolated database with the canonical NR-0 multi-tenant scenario."""
    return build_nr0_synthetic_scenario(isolated_db)


@pytest.fixture(scope="function")
def mock_llm_gateway():
    """
    Provides a deterministic double for the LLMGateway, recording invocations
    and yielding predictable streaming chunks without network requests.
    """
    from services.llm_generation_service import llm_gateway

    original_generate_stream = llm_gateway.generate_stream
    original_generate_sync = llm_gateway.generate_sync

    call_records = []

    async def fake_generate_stream(prompt: str, *args, **kwargs):
        call_records.append({"type": "stream", "prompt": prompt})
        tokens = ["This ", "is ", "a ", "deterministic ", "streamed ", "response."]
        for t in tokens:
            yield t

    def fake_generate_sync(prompt: str, *args, **kwargs):
        call_records.append({"type": "sync", "prompt": prompt})
        return "Deterministic synthetic LLM answer."

    llm_gateway.generate_stream = fake_generate_stream
    llm_gateway.generate_sync = fake_generate_sync

    yield {
        "calls": call_records,
        "gateway": llm_gateway
    }

    llm_gateway.generate_stream = original_generate_stream
    llm_gateway.generate_sync = original_generate_sync
