"""
Automated unit & regression test suite for Phase 7 Task 7.2.3:
Verifiable Source Citation & Grounding Engine (CitationService).
"""

import os
import sys
import pytest
import numpy as np
from unittest.mock import MagicMock

# Add backend directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from services.citation_service import CitationService, GROUNDING_SIMILARITY_THRESHOLD, LOW_CONFIDENCE_THRESHOLD


@pytest.fixture
def citation_service():
    return CitationService()


def test_extract_claims_filters_fluff_and_tables(citation_service):
    """Verifies that extract_claims discards conversational pleasantries, markdown tables, and code."""
    raw_response = (
        "Hello! Certainly, I can help you with that.\n\n"
        "| ID | Status |\n"
        "| --- | --- |\n"
        "| 1 | Active |\n\n"
        "```python\n"
        "print('code block')\n"
        "```\n\n"
        "The company was founded in September 2021 by a team of researchers. "
        "Total revenue for the fiscal year reached 12.4 million dollars with a 40 percent margin. "
        "In conclusion, the company demonstrated solid financial growth."
    )

    claims = citation_service.extract_claims(raw_response)

    # Conversational pleasantries and markdown tables/code should not be present
    for c in claims:
        assert "Hello!" not in c
        assert "Certainly" not in c
        assert "print('code block')" not in c
        assert "Active" not in c

    # Factual statements should be extracted
    found_founded = any("founded in September 2021" in c for c in claims)
    found_revenue = any("12.4 million dollars" in c for c in claims)
    assert found_founded, "Expected founding date claim to be extracted"
    assert found_revenue, "Expected revenue claim to be extracted"


def test_verify_grounding_high_confidence(citation_service):
    """
    Verifies that claims with high semantic match against chunks receive
    is_grounded = True and no disclaimer.
    """
    response_text = "PostgreSQL statement timeout is configured to 10000 milliseconds for safety."
    retrieved_chunks = [
        {
            "content": "Engine level timeout: PostgreSQL uses options statement_timeout=10000ms to terminate runaway queries.",
            "metadata": {"source": "database_guide.md", "page_number": 2, "content_type": "text"},
            "score": 0.89
        }
    ]

    # Create mock embedding model that produces high cosine similarity for matching content
    mock_emb = MagicMock()
    # Normalize vectors so dot product equals cosine similarity
    vec = [1.0, 0.0, 0.0]
    mock_emb.embed_documents.return_value = [vec]

    res = citation_service.verify_grounding(
        response_text=response_text,
        retrieved_chunks=retrieved_chunks,
        embedding_model=mock_emb
    )

    assert res["grounding_confidence"] >= GROUNDING_SIMILARITY_THRESHOLD
    assert res["has_low_confidence"] is False
    assert res["disclaimer"] is None
    assert len(res["citations"]) >= 1
    assert res["citations"][0].document_name == "database_guide.md"
    assert res["citations"][0].page_number == 2


def test_verify_grounding_low_confidence_triggers_disclaimer(citation_service):
    """
    Verifies that claims with low semantic match against chunks trigger
    has_low_confidence = True and generate an actionable disclaimer.
    """
    response_text = "The satellite is scheduled to launch into low Earth orbit aboard a heavy rocket."
    retrieved_chunks = [
        {
            "content": "Our employee handbook details standard paid time off and vacation leave policies.",
            "metadata": {"source": "hr_handbook.pdf", "page_number": 1, "content_type": "text"},
            "score": 0.35
        }
    ]

    # Mock orthogonal/low-similarity vectors
    mock_emb = MagicMock()
    # First call for chunks, second call for claims
    mock_emb.embed_documents.side_effect = [
        [[1.0, 0.0, 0.0]],  # chunk vec
        [[0.0, 1.0, 0.0]]   # claim vec (cosine similarity = 0.0)
    ]

    res = citation_service.verify_grounding(
        response_text=response_text,
        retrieved_chunks=retrieved_chunks,
        embedding_model=mock_emb
    )

    assert res["grounding_confidence"] < LOW_CONFIDENCE_THRESHOLD
    assert res["has_low_confidence"] is True
    assert res["disclaimer"] is not None
    assert "low grounding confidence" in res["disclaimer"]


def test_verify_grounding_empty_graceful_handling(citation_service):
    """Verifies graceful return when response_text or retrieved_chunks are empty."""
    res_empty_text = citation_service.verify_grounding("", [{"content": "sample"}])
    assert res_empty_text["grounding_confidence"] == 0.0
    assert len(res_empty_text["citations"]) == 0

    res_empty_chunks = citation_service.verify_grounding("Some response text", [])
    assert res_empty_chunks["grounding_confidence"] == 0.0
    assert len(res_empty_chunks["citations"]) == 0
