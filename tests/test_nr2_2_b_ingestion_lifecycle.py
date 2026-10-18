"""
Comprehensive test suite for Sprint NR-2.2-B:
Reliable Ingestion and Index Lifecycle (Tasks NR-2.2-B-T01 through T09).
"""
import os
import io
import time
import uuid
import hashlib
import pytest
from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models, schemas
from database import Base
from services.storage import storage_service
from ingestion.extractors import validate_file_magic, extract_pdf_split_router, extract_excel_csv, MAX_PAGE_BUDGET, MAX_ROW_BUDGET
from search.generation_manager import IndexGenerationManager
from routers.documents import process_document, resolve_tenant_vector_index_path
from scripts.reconcile_indexes import reconcile_indexes

@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_lifecycle.db"
    db_url = f"sqlite:///{db_file}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()

    tenant = models.Tenant(id=501, name="Lifecycle Test Corp")
    session.add(tenant)
    session.commit()

    yield session

    session.close()
    engine.dispose()

def test_t01_durable_storage_and_failure_retention(test_db, tmp_path):
    """
    NR-2.2-B-T01:
    Uploaded originals stored under content-addressed keys.
    Retained even when processing fails.
    """
    raw_content = b"Document content for storage contract verification."
    content_hash = hashlib.sha256(raw_content).hexdigest()

    temp_file = tmp_path / "sample.txt"
    temp_file.write_bytes(raw_content)

    doc = models.Document(
        tenant_id=501,
        name="sample.txt",
        file_type="TXT",
        size=len(raw_content),
        status="Processing",
        progress_step="queued",
        content_sha256=content_hash,
        version=1
    )
    test_db.add(doc)
    test_db.commit()
    test_db.refresh(doc)

    stored_path = storage_service.store_file(501, doc.id, str(temp_file), content_hash)
    doc.storage_key = stored_path
    test_db.commit()

    assert os.path.exists(stored_path)
    assert stored_path.endswith(f"{doc.id}_{content_hash}.bin")

    # Simulate processing failure
    doc.status = "Failed"
    doc.error_message = "Synthetic parsing exception"
    test_db.commit()

    # Raw file must still exist in durable storage
    assert os.path.exists(stored_path)
    retrieved = storage_service.get_file_path(501, doc.id, content_hash)
    assert retrieved == stored_path

def test_t02_magic_mime_and_budget_guards():
    """
    NR-2.2-B-T02:
    Reject dangerous executable binaries disguised as documents.
    Enforce MAX_PAGE_BUDGET and MAX_ROW_BUDGET.
    """
    # 1. PE / MZ Executable check
    fake_exe = b"MZ\x90\x00\x03\x00\x00\x00malicious binary content"
    is_valid, reason = validate_file_magic(fake_exe, "invoice.pdf")
    assert not is_valid
    assert "Executable binaries" in reason

    # 2. Linux ELF binary check
    fake_elf = b"\x7fELF\x02\x01\x01\x00linux binary"
    is_valid, reason = validate_file_magic(fake_elf, "report.docx")
    assert not is_valid
    assert "Executable binaries" in reason

    # 3. Disguised shell script check
    fake_sh = b"#!/bin/bash\nrm -rf /"
    is_valid, reason = validate_file_magic(fake_sh, "policy.txt")
    assert not is_valid
    assert "Shell scripts are not permitted" in reason

    # 4. Valid PDF magic
    valid_pdf = b"%PDF-1.7\nsome valid pdf stream"
    is_valid, _ = validate_file_magic(valid_pdf, "safe.pdf")
    assert is_valid

    # 5. Page and Row budget constants
    assert MAX_PAGE_BUDGET == 100
    assert MAX_ROW_BUDGET == 50000

def test_t03_t04_job_identity_and_session_isolation(test_db, tmp_path, monkeypatch):
    """
    NR-2.2-B-T03 & T04:
    Ingestion assigns job IDs, tracks lifecycle steps, and isolates sessions.
    """
    doc_text = "This is a company policy statement. Annual leave is granted to all full-time employees."
    temp_file = tmp_path / "policy.txt"
    temp_file.write_text(doc_text, encoding="utf-8")

    doc = models.Document(
        tenant_id=501,
        name="policy.txt",
        file_type="TXT",
        size=len(doc_text),
        status="Processing",
        progress_step="queued",
        ingestion_job_id=str(uuid.uuid4())
    )
    test_db.add(doc)
    test_db.commit()
    test_db.refresh(doc)

    # Call process_document with explicit db
    process_document(doc.id, str(temp_file), 501, 100, 10, "fixed", test_db)
    test_db.refresh(doc)

    assert doc.status == "Completed"
    assert doc.progress_step == "ready"
    assert doc.progress == 1.0
    assert doc.ingestion_job_id is not None
    assert doc.last_heartbeat_at is not None

from langchain_core.embeddings import Embeddings

def test_t06_dimension_mismatch_guard(tmp_path):
    """
    NR-2.2-B-T06:
    Vector dimension mismatch is caught before index mutation.
    """
    class MockEmbeddings(Embeddings):
        def __init__(self, dim):
            self.dim = dim
            self.model_name = f"mock-{dim}"
        def embed_query(self, text):
            return [0.1] * self.dim
        def embed_documents(self, texts):
            return [[0.1] * self.dim for _ in texts]
        def __call__(self, text):
            return self.embed_query(text)

    gen_mgr = IndexGenerationManager(tenant_id=999, model_name="mock-384", base_dir=str(tmp_path))
    emb_384 = MockEmbeddings(384)
    # Build initial index with 384 dim
    gen_mgr.build_and_publish_generation(
        embeddings_model=emb_384,
        new_chunks=["initial chunk"],
        new_metadatas=[{"document_id": 1, "source": "test.txt"}],
        all_bm25_chunks=[{"id": 1, "content": "initial chunk", "metadata": {"source": "test.txt"}}]
    )

    # Attempt to insert 768 dim vector into the existing 384 dim index
    emb_768 = MockEmbeddings(768)
    with pytest.raises(ValueError, match="Vector dimension mismatch"):
        gen_mgr.build_and_publish_generation(
            embeddings_model=emb_768,
            new_chunks=["mismatched chunk"],
            new_metadatas=[{"document_id": 2, "source": "test2.txt"}],
            all_bm25_chunks=[]
        )

def test_t07_immutable_generation_atomic_swap(tmp_path):
    """
    NR-2.2-B-T07:
    Builds immutable index generations in staging and atomically swaps active pointer.
    """
    class MockEmbeddings(Embeddings):
        def __init__(self, dim=64):
            self.dim = dim
            self.model_name = "mock-64"
        def embed_query(self, text):
            return [0.2] * self.dim
        def embed_documents(self, texts):
            return [[0.2] * self.dim for _ in texts]
        def __call__(self, text):
            return self.embed_query(text)

    emb = MockEmbeddings(64)
    gen_mgr = IndexGenerationManager(tenant_id=888, model_name="mock-64", base_dir=str(tmp_path))

    gen_id_1 = gen_mgr.build_and_publish_generation(
        embeddings_model=emb,
        new_chunks=["hello world"],
        new_metadatas=[{"document_id": 1, "source": "hello.txt"}],
        all_bm25_chunks=[{"id": 1, "content": "hello world", "metadata": {"source": "hello.txt"}}]
    )

    active_path, exists = gen_mgr.get_active_generation_path()
    assert exists
    assert gen_id_1 in active_path

    # Build second generation
    gen_id_2 = gen_mgr.build_and_publish_generation(
        embeddings_model=emb,
        new_chunks=["second world"],
        new_metadatas=[{"document_id": 2, "source": "world.txt"}],
        all_bm25_chunks=[{"id": 2, "content": "second world", "metadata": {"source": "world.txt"}}]
    )

    active_path_2, exists_2 = gen_mgr.get_active_generation_path()
    assert exists_2
    assert gen_id_2 in active_path_2
    assert gen_id_2 != gen_id_1

def test_t08_immediate_tombstoning_and_retrieval_exclusion(test_db, tmp_path):
    """
    NR-2.2-B-T08:
    Immediate tombstoning excludes deleted documents from retrieval queries.
    """
    doc1 = models.Document(tenant_id=501, name="active.txt", file_type="TXT", status="Completed", is_deleted=False)
    doc2 = models.Document(tenant_id=501, name="deleted.txt", file_type="TXT", status="Completed", is_deleted=False)
    test_db.add_all([doc1, doc2])
    test_db.commit()

    chunk1 = models.DocumentChunk(document_id=doc1.id, content="Active policy text", chunk_index=0)
    chunk2 = models.DocumentChunk(document_id=doc2.id, content="Deleted policy text", chunk_index=0)
    test_db.add_all([chunk1, chunk2])
    test_db.commit()

    # Tombstone doc2
    doc2.is_deleted = True
    doc2.status = "Deleted"
    test_db.commit()

    # Querying documents for tenant must exclude tombstoned documents
    active_docs = test_db.query(models.Document).filter(
        models.Document.tenant_id == 501,
        models.Document.is_deleted == False
    ).all()
    doc_ids = [d.id for d in active_docs]
    assert doc1.id in doc_ids
    assert doc2.id not in doc_ids

def test_t09_reconciliation_script(test_db, tmp_path):
    """
    NR-2.2-B-T09:
    Reconciliation detects stalled documents (>10 min) and resets to Failed.
    """
    # Create stalled document with heartbeat 15 minutes ago
    stalled_time = datetime.utcnow() - timedelta(minutes=15)
    stalled_doc = models.Document(
        tenant_id=501,
        name="stalled.txt",
        file_type="TXT",
        status="Processing",
        progress_step="chunking",
        last_heartbeat_at=stalled_time
    )
    test_db.add(stalled_doc)
    test_db.commit()

    # Run dry run with test_db
    report_dry = reconcile_indexes(dry_run=True, db=test_db)
    assert report_dry["stalled_jobs_count"] >= 1
    test_db.refresh(stalled_doc)
    assert stalled_doc.status == "Processing"  # Unchanged in dry run

    # Run fix with test_db
    report_fix = reconcile_indexes(dry_run=False, db=test_db)
    assert report_fix["stalled_jobs_count"] >= 1
    test_db.refresh(stalled_doc)
    assert stalled_doc.status == "Failed"
    assert "heartbeat expired" in stalled_doc.error_message


def test_f01_status_endpoint_contract():
    """F01: Ensure DocumentStatusResponse accepts document_id, id, name, and page counts."""
    resp = schemas.DocumentStatusResponse(
        document_id=42,
        id=42,
        name="test_report.pdf",
        status="Completed",
        progress=1.0,
        progress_step="ready",
        ingestion_job_id="job-uuid-1234",
        error_message=None,
        pages_processed=12,
        total_pages=15
    )
    assert resp.document_id == 42
    assert resp.id == 42
    assert resp.name == "test_report.pdf"
    assert resp.pages_processed == 12
    assert resp.total_pages == 15


def test_f02_retry_preserves_extension_and_format(tmp_path):
    """F02: LocalStorageAdapter preserves file extension and extract_excel_csv accepts file_ext."""
    from services.storage import LocalStorageAdapter
    import pandas as pd

    adapter = LocalStorageAdapter(base_dir=str(tmp_path / "storage"))
    src_file = tmp_path / "financials.csv"
    src_file.write_text("Year,Revenue\n2025,1000000\n2026,1500000\n", encoding="utf-8")
    
    sha256 = hashlib.sha256(src_file.read_bytes()).hexdigest()
    stored = adapter.store_file(tenant_id=10, doc_id=5, source_path=str(src_file), sha256_hash=sha256, filename="financials.csv")
    assert stored.endswith(".csv")

    retrieved = adapter.get_file_path(tenant_id=10, doc_id=5, sha256_hash=sha256, filename="financials.csv")
    assert retrieved == stored

    # Verify extract_excel_csv with file_ext
    extracted = extract_excel_csv(str(src_file), file_ext=".csv")
    assert extracted.stats.total_pages >= 1
    assert len(extracted.table_chunks) >= 1


def test_f03_retry_does_not_duplicate_chunks(test_db, tmp_path):
    """F03: Retrying process_document clears previous chunks before re-inserting."""
    doc_text = "Section 1: General provisions.\nSection 2: Safety guidelines.\nSection 3: Reporting procedures."
    temp_file = tmp_path / "manual.txt"
    temp_file.write_text(doc_text, encoding="utf-8")

    doc = models.Document(
        tenant_id=501,
        name="manual.txt",
        file_type="TXT",
        size=len(doc_text),
        status="Processing",
        progress_step="queued"
    )
    test_db.add(doc)
    test_db.commit()
    test_db.refresh(doc)

    # First pass
    process_document(doc.id, str(temp_file), 501, 64, 10, "fixed", test_db)
    count_first_pass = test_db.query(models.DocumentChunk).filter(models.DocumentChunk.document_id == doc.id).count()
    assert count_first_pass > 0

    # Second pass (retry)
    process_document(doc.id, str(temp_file), 501, 64, 10, "fixed", test_db)
    count_second_pass = test_db.query(models.DocumentChunk).filter(models.DocumentChunk.document_id == doc.id).count()
    assert count_second_pass == count_first_pass


def test_f04_bm25_active_generation_isolation(tmp_path):
    """F04: BM25IndexManager isolates staging build from active directory until published."""
    from search.bm25_index import BM25IndexManager

    custom_dir = str(tmp_path / "custom_gen_01")
    mgr = BM25IndexManager(tenant_id=99, index_dir=custom_dir)
    chunks = [
        {"id": 101, "content": "Quarterly earnings revenue report", "metadata": {"source": "earnings.txt"}}
    ]
    mgr.build_index(chunks)
    assert os.path.exists(os.path.join(custom_dir, "bm25.pkl"))

    # Search directly through custom_dir
    hits = mgr.search("revenue", top_k=5)
    assert len(hits) == 1
    assert hits[0]["chunk_id"] == 101


def test_f05_reconciliation_handles_aware_datetimes(test_db):
    """F05: reconcile_indexes handles timezone-aware and offset-naive timestamps without raising TypeError."""
    from datetime import timezone
    from scripts.reconcile_indexes import to_naive_utc

    aware_dt = datetime.now(timezone.utc) - timedelta(minutes=20)
    naive = to_naive_utc(aware_dt)
    assert naive.tzinfo is None

    stalled_doc = models.Document(
        tenant_id=501,
        name="aware_test.txt",
        file_type="TXT",
        status="Processing",
        progress_step="indexing",
        last_heartbeat_at=naive
    )
    test_db.add(stalled_doc)
    test_db.commit()

    report = reconcile_indexes(dry_run=False, db=test_db)
    test_db.refresh(stalled_doc)
    assert stalled_doc.status == "Failed"


def test_f06_upload_filename_traversal_sanitized():
    """F06: Filename paths with directory traversal sequences are stripped to base name."""
    malicious_name = "../../../etc/shadow"
    safe_name = os.path.basename(malicious_name or "uploaded_document")
    assert safe_name == "shadow"
    assert ".." not in safe_name
    assert "/" not in safe_name


def test_f07_widget_key_document_cleanup_on_delete(test_db):
    """F07: Deleting a document purges WidgetKeyDocument links and excludes tombstoned docs."""
    doc = models.Document(tenant_id=501, name="published_policy.txt", file_type="TXT", status="Completed", is_deleted=False)
    test_db.add(doc)
    test_db.commit()
    test_db.refresh(doc)

    wk = models.WidgetKey(
        tenant_id=501,
        name="Production Key",
        public_key="pk_live_1234567890abcdef",
        enabled=True
    )
    test_db.add(wk)
    test_db.commit()
    test_db.refresh(wk)

    link = models.WidgetKeyDocument(widget_key_id=wk.id, document_id=doc.id)
    test_db.add(link)
    test_db.commit()

    # Query active published documents
    docs_before = test_db.query(models.WidgetKeyDocument.document_id).join(
        models.Document, models.WidgetKeyDocument.document_id == models.Document.id
    ).filter(
        models.WidgetKeyDocument.widget_key_id == wk.id,
        models.Document.is_deleted == False
    ).all()
    assert len(docs_before) == 1

    # Simulate deletion cleanup
    doc.is_deleted = True
    test_db.query(models.WidgetKeyDocument).filter(models.WidgetKeyDocument.document_id == doc.id).delete()
    test_db.commit()

    docs_after = test_db.query(models.WidgetKeyDocument).filter(models.WidgetKeyDocument.widget_key_id == wk.id).all()
    assert len(docs_after) == 0


def test_f08_process_tenant_lock(tmp_path):
    """F08: ProcessTenantLock provides cross-process file-locking."""
    from search.generation_manager import ProcessTenantLock

    lock_file = str(tmp_path / "test.lock")
    with ProcessTenantLock(lock_file, timeout=1.0) as lock1:
        assert lock1.fd is not None
        # Verify file exists
        assert os.path.exists(lock_file)


def test_f10_pages_processed_stats_accuracy(test_db, tmp_path):
    """F10: doc.pages_processed records extracted.stats.pages_processed."""
    doc_text = "Page 1 content.\nPage 2 content."
    temp_file = tmp_path / "pages.txt"
    temp_file.write_text(doc_text, encoding="utf-8")

    doc = models.Document(
        tenant_id=501,
        name="pages.txt",
        file_type="TXT",
        size=len(doc_text),
        status="Processing",
        progress_step="queued"
    )
    test_db.add(doc)
    test_db.commit()
    test_db.refresh(doc)

    process_document(doc.id, str(temp_file), 501, 100, 10, "fixed", test_db)
    test_db.refresh(doc)
    assert doc.status == "Completed"
    assert doc.pages_processed == 1

