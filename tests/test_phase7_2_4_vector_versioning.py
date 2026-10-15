"""
Automated unit & regression test suite for Phase 7 Task 7.2.4:
Versioned Vector Indexing & Multi-Model Safe Storage.
"""

import os
import sys
import shutil
import pytest
import numpy as np
from unittest.mock import MagicMock, patch

# Add backend directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from routers.documents import resolve_tenant_vector_index_path
from routers.chat import retrieve_rag_chunks


@pytest.fixture
def clean_vector_store():
    """Ensures test vector store paths are isolated and cleaned up."""
    test_paths = []
    def _register(p):
        test_paths.append(p)
        return p
    yield _register
    for p in test_paths:
        if os.path.exists(p):
            shutil.rmtree(p, ignore_errors=True)


def test_resolve_tenant_vector_index_path_nonexistent(clean_vector_store):
    """Verifies default slugged path is returned with exists=False when no index directory exists."""
    tenant_id = 99991
    model_name = "all-MiniLM-L6-v2"
    path, exists = resolve_tenant_vector_index_path(tenant_id, model_name)
    assert exists is False
    assert path == f"vector_store/tenant_{tenant_id}_all-MiniLM-L6-v2"


def test_resolve_tenant_vector_index_path_legacy_fallback(clean_vector_store):
    """Verifies seamless fallback to legacy un-slugged path if legacy exists and versioned does not."""
    tenant_id = 99992
    legacy_dir = clean_vector_store(f"vector_store/tenant_{tenant_id}")
    os.makedirs(legacy_dir, exist_ok=True)

    path, exists = resolve_tenant_vector_index_path(tenant_id, "all-MiniLM-L6-v2")
    assert exists is True
    assert path == legacy_dir


def test_resolve_tenant_vector_index_path_prefers_versioned(clean_vector_store):
    """Verifies that versioned path takes precedence when both versioned and legacy directories exist."""
    tenant_id = 99993
    model_name = "BAAI/bge-small-en-v1.5"
    model_slug = "BAAI_bge-small-en-v1.5"

    legacy_dir = clean_vector_store(f"vector_store/tenant_{tenant_id}")
    versioned_dir = clean_vector_store(f"vector_store/tenant_{tenant_id}_{model_slug}")
    os.makedirs(legacy_dir, exist_ok=True)
    os.makedirs(versioned_dir, exist_ok=True)

    path, exists = resolve_tenant_vector_index_path(tenant_id, model_name)
    assert exists is True
    assert path == versioned_dir


def test_retrieve_rag_chunks_dimension_mismatch_guard():
    """
    Verifies that retrieve_rag_chunks safely catches vector dimension mismatches
    (e.g., index is 768d but query embedding is 384d) and returns empty list
    without crashing FAISS or raising an unhandled server error.
    """
    tenant_id = 99994

    # Mock FAISS vectorstore with index.d = 768
    mock_vectorstore = MagicMock()
    mock_vectorstore.index.d = 768

    # Mock embedding model returning 384-dimensional vector
    mock_emb = MagicMock()
    mock_emb.embed_query.return_value = [0.1] * 384

    mock_db = MagicMock()

    with patch("routers.documents.resolve_tenant_vector_index_path", return_value=("fake_dir", True)), \
         patch("os.path.exists", return_value=True), \
         patch("routers.chat.get_embeddings", return_value=mock_emb), \
         patch("langchain_community.vectorstores.FAISS.load_local", return_value=mock_vectorstore):

        results = retrieve_rag_chunks("test query", tenant_id=tenant_id, db=mock_db)

        # Must return empty list safely instead of crashing
        assert results == []
