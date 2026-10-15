"""
Automated unit & regression test suite for Phase 7 Task 7.2.2:
Hierarchical Semantic Document Chunking & Parent Context Expansion.
"""

import os
import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add backend directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import models
from database import Base
from ingestion.semantic_chunker import SemanticHierarchicalChunker
from routers.chat import build_grounded_rag_context


@pytest.fixture
def test_db():
    """In-memory SQLite database session for model relationship testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_semantic_hierarchical_chunking_creates_parents_and_children():
    """Verifies that SemanticHierarchicalChunker creates Level 0 parents and linked Level 1 children."""
    chunker = SemanticHierarchicalChunker(target_chunk_size=150, chunk_overlap=30)
    
    sample_text = (
        "# Executive Summary\n"
        "DataSpeakAI is a next-generation enterprise Conversational AI platform. "
        "It provides automated natural language queries over relational databases.\n\n"
        "## Architecture Overview\n"
        "The system uses a FastAPI backend with SQLAlchemy and LangChain. "
        "For unstructured data, it indexes PDF and text documents into FAISS vector stores. "
        "Each document is split into parent and child chunks for grounded citations.\n\n"
        "| Dialect | Status | Timeout |\n"
        "| --- | --- | --- |\n"
        "| PostgreSQL | Active | 10000ms |\n"
        "| MySQL | Active | 10000ms |\n"
        "| SQLite | Active | 10000ms |\n\n"
        "## Security Specifications\n"
        "All queries are strictly parameterised. Dynamic identifier whitelisting prevents SQL injection. "
        "Tokens expire within 60 minutes and Origin headers are strictly checked on widget endpoints.\n"
    )

    parents, children = chunker.chunk_document(sample_text, source_name="system_spec.md", page_number=1)

    assert len(parents) >= 2, "Expected multiple Level 0 parent sections"
    assert len(children) >= 2, "Expected multiple Level 1 child chunks"

    # Verify Level 0 attributes
    for p in parents:
        assert p.hierarchy_level == 0
        assert p.metadata.get("source") == "system_spec.md"
        assert p.page_number == 1
        assert len(p.content) > 0

    # Verify Level 1 attributes & valid parent linking
    for c in children:
        assert c.hierarchy_level == 1
        assert c.parent_local_index is not None
        assert 0 <= c.parent_local_index < len(parents)
        parent_chunk = parents[c.parent_local_index]
        # Child section heading should match or inherit from parent
        assert c.section_heading == parent_chunk.section_heading


def test_table_extraction_in_hierarchical_chunker():
    """Verifies that markdown tables are parsed with content_type == 'table'."""
    chunker = SemanticHierarchicalChunker()
    table_text = (
        "# Data Metrics\n"
        "| Metric | Q1 | Q2 |\n"
        "| --- | --- | --- |\n"
        "| Revenue | $10M | $12M |\n"
        "| Churn | 1.2% | 0.9% |\n"
    )
    parents, children = chunker.chunk_document(table_text, source_name="financials.md")
    table_parents = [p for p in parents if p.content_type == "table"]
    assert len(table_parents) >= 1
    assert "Revenue" in table_parents[0].content


def test_db_document_chunk_hierarchy_relationship(test_db):
    """Verifies that DocumentChunk parent_chunk_id self-referential relationship functions in SQL."""
    # 1. Create a dummy tenant and document
    tenant = models.Tenant(name="Acme Corp")
    test_db.add(tenant)
    test_db.commit()

    doc = models.Document(
        tenant_id=tenant.id,
        name="guide.pdf",
        file_type="pdf",
        size=1024,
        status="Completed"
    )
    test_db.add(doc)
    test_db.commit()

    # 2. Insert Level 0 Parent Chunk
    parent = models.DocumentChunk(
        document_id=doc.id,
        content="Section 1: General Overview of DataSpeakAI Architecture and Components.",
        chunk_index=0,
        page_number=1,
        content_type="text",
        section_heading="Overview",
        parent_chunk_id=None,
        hierarchy_level=0
    )
    test_db.add(parent)
    test_db.commit()
    test_db.refresh(parent)

    # 3. Insert Level 1 Child Chunks referencing parent.id
    child1 = models.DocumentChunk(
        document_id=doc.id,
        content="Child Passage 1: Covers FastAPI microservice and router structure.",
        chunk_index=1,
        page_number=1,
        content_type="text",
        section_heading="Overview",
        parent_chunk_id=parent.id,
        hierarchy_level=1
    )
    child2 = models.DocumentChunk(
        document_id=doc.id,
        content="Child Passage 2: Covers FAISS vector indexing and sentence embeddings.",
        chunk_index=2,
        page_number=1,
        content_type="text",
        section_heading="Overview",
        parent_chunk_id=parent.id,
        hierarchy_level=1
    )
    test_db.add_all([child1, child2])
    test_db.commit()

    test_db.refresh(parent)
    test_db.refresh(child1)
    test_db.refresh(child2)

    # Verify relationships
    assert len(parent.child_chunks) == 2
    assert child1.parent_chunk.id == parent.id
    assert child2.parent_chunk.id == parent.id


def test_build_grounded_rag_context_parent_deduplication(test_db):
    """
    Verifies that build_grounded_rag_context expands parent context without duplicating
    parent section text when multiple children come from the same parent.
    """
    tenant = models.Tenant(name="Context Test")
    test_db.add(tenant)
    test_db.commit()

    doc = models.Document(tenant_id=tenant.id, name="handbook.pdf", file_type="pdf", size=500)
    test_db.add(doc)
    test_db.commit()

    parent = models.DocumentChunk(
        document_id=doc.id,
        content="Full Parent Chapter: This chapter details user access policies and role matrices.",
        chunk_index=0,
        page_number=5,
        section_heading="Access Policies",
        parent_chunk_id=None,
        hierarchy_level=0
    )
    test_db.add(parent)
    test_db.commit()
    test_db.refresh(parent)

    child1 = models.DocumentChunk(
        document_id=doc.id,
        content="Admin role grants full database schema introspection.",
        chunk_index=1,
        page_number=5,
        parent_chunk_id=parent.id,
        hierarchy_level=1
    )
    child2 = models.DocumentChunk(
        document_id=doc.id,
        content="Viewer role is restricted to natural language querying.",
        chunk_index=2,
        page_number=5,
        parent_chunk_id=parent.id,
        hierarchy_level=1
    )
    test_db.add_all([child1, child2])
    test_db.commit()
    test_db.refresh(child1)
    test_db.refresh(child2)

    retrieved_chunks = [
        {
            "content": child1.content,
            "metadata": {
                "source": "handbook.pdf",
                "page_number": 5,
                "content_type": "text",
                "chunk_id": child1.id,
                "parent_chunk_id": parent.id
            },
            "score": 0.88
        },
        {
            "content": child2.content,
            "metadata": {
                "source": "handbook.pdf",
                "page_number": 5,
                "content_type": "text",
                "chunk_id": child2.id,
                "parent_chunk_id": parent.id
            },
            "score": 0.82
        }
    ]

    context_text, citations = build_grounded_rag_context(retrieved_chunks, test_db)

    # 1. Citations must preserve both children
    assert len(citations) == 2
    assert "Admin role" in citations[0].snippet
    assert "Viewer role" in citations[1].snippet

    # 2. Parent context text must be included
    assert "Full Parent Chapter" in context_text

    # 3. Deduplication check: parent section header appears only ONCE in the expanded prompt
    parent_mention_count = context_text.count("(Parent Context)")
    assert parent_mention_count == 1, f"Expected parent context to be deduplicated (found {parent_mention_count})"
