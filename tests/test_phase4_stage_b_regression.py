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


def test_query_templates_crud_and_cascade(db_session):
    """Verify QueryTemplate model, serialization, and cascade deletion."""
    tenant = models.Tenant(name="Template Corp")
    db_session.add(tenant)
    db_session.commit()

    template = models.QueryTemplate(
        tenant_id=tenant.id,
        name="Monthly Revenue Summary",
        sql_template="SELECT date_trunc('month', created_at), sum(amount) FROM orders GROUP BY 1",
        description="Aggregates monthly revenue from orders table"
    )
    db_session.add(template)
    db_session.commit()
    db_session.refresh(template)

    assert template.id is not None
    assert template.tenant.name == "Template Corp"
    assert len(tenant.query_templates) == 1

    # Schema serialization check
    dto = schemas.QueryTemplateResponse.model_validate(template)
    assert dto.name == "Monthly Revenue Summary"
    assert "sum(amount)" in dto.sql_template

    # Cascade deletion check
    db_session.delete(tenant)
    db_session.commit()
    assert db_session.query(models.QueryTemplate).filter_by(id=template.id).first() is None


def test_intent_classification_and_message_relationship(db_session):
    """Verify Intent model links to Message and cascades properly."""
    tenant = models.Tenant(name="Chat Tenant")
    db_session.add(tenant)
    db_session.commit()

    convo = models.Conversation(tenant_id=tenant.id, title="Support Session")
    db_session.add(convo)
    db_session.commit()

    msg = models.Message(
        conversation_id=convo.id,
        sender_role="user",
        content="Show me all customers from New York"
    )
    db_session.add(msg)
    db_session.commit()
    db_session.refresh(msg)

    intent = models.Intent(
        message_id=msg.id,
        intent_name="nl_to_sql_exploration",
        confidence=0.98
    )
    db_session.add(intent)
    db_session.commit()
    db_session.refresh(intent)

    assert intent.id is not None
    assert intent.message.content == "Show me all customers from New York"
    assert len(msg.intents) == 1
    assert msg.intents[0].confidence == 0.98

    # Schema serialization
    dto = schemas.IntentResponse.model_validate(intent)
    assert dto.intent_name == "nl_to_sql_exploration"
    assert dto.confidence == 0.98

    # Cascade deletion check
    db_session.delete(msg)
    db_session.commit()
    assert db_session.query(models.Intent).filter_by(id=intent.id).first() is None


def test_executed_queries_and_safety_logs(db_session):
    """Verify ExecutedQuery and QuerySafetyLog models, validation tracking, and cascade."""
    tenant = models.Tenant(name="Audit Tenant")
    user = models.User(email="analyst@audit.com", hashed_password="pwd", tenant_id=tenant.id)
    db_session.add_all([tenant, user])
    db_session.commit()

    exec_query = models.ExecutedQuery(
        tenant_id=tenant.id,
        user_id=user.id,
        raw_query="Top 10 products by revenue",
        sql_generated="SELECT product_name, sum(revenue) FROM sales GROUP BY product_name ORDER BY 2 DESC LIMIT 10",
        execution_time_ms=42.5,
        rows_returned=10,
        status="success",
        was_successful=True
    )
    db_session.add(exec_query)
    db_session.commit()
    db_session.refresh(exec_query)

    safety_log = models.QuerySafetyLog(
        query_id=exec_query.id,
        passed_validation=True,
        violation_details=None
    )
    db_session.add(safety_log)
    db_session.commit()
    db_session.refresh(safety_log)

    assert len(exec_query.safety_logs) == 1
    assert exec_query.safety_logs[0].passed_validation is True

    # Schema serialization
    audit_dto = schemas.ExecutedQueryAuditResponse.model_validate(exec_query)
    assert audit_dto.execution_time_ms == 42.5
    assert len(audit_dto.safety_logs) == 1
    assert audit_dto.safety_logs[0].passed_validation is True

    # Cascade deletion check
    db_session.delete(exec_query)
    db_session.commit()
    assert db_session.query(models.QuerySafetyLog).filter_by(id=safety_log.id).first() is None


def test_collections_and_vector_records(db_session):
    """Verify Collection and VectorRecord models for multi-collection knowledge bases."""
    tenant = models.Tenant(name="Vector Tenant")
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)

    doc = models.Document(tenant_id=tenant.id, name="CompanyHandbook.pdf", file_type="pdf")
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    chunk = models.DocumentChunk(
        document_id=doc.id,
        content="Vacation policy: Employees receive 20 days paid leave.",
        chunk_index=0
    )
    db_session.add(chunk)
    db_session.commit()

    collection = models.Collection(
        tenant_id=tenant.id,
        name="HR Policies",
        description="Human resources company policies and guidelines",
        vector_provider="faiss"
    )
    db_session.add(collection)
    db_session.commit()
    db_session.refresh(collection)

    assert len(tenant.collections) == 1
    assert tenant.collections[0].name == "HR Policies"

    vec_record = models.VectorRecord(
        chunk_id=chunk.id,
        collection_id=collection.id,
        vector_external_id="vec_chunk_001_hr"
    )
    db_session.add(vec_record)
    db_session.commit()
    db_session.refresh(vec_record)

    assert len(collection.vector_records) == 1
    assert collection.vector_records[0].vector_external_id == "vec_chunk_001_hr"
    assert vec_record.chunk.content.startswith("Vacation policy")

    # Schema serialization
    col_dto = schemas.CollectionResponse.model_validate(collection)
    assert col_dto.name == "HR Policies"
    rec_dto = schemas.VectorRecordResponse.model_validate(vec_record)
    assert rec_dto.vector_external_id == "vec_chunk_001_hr"

    # Cascade deletion check
    db_session.delete(collection)
    db_session.commit()
    assert db_session.query(models.VectorRecord).filter_by(id=vec_record.id).first() is None
