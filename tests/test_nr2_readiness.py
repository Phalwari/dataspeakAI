"""NR-2 readiness regression tests. Assert acceptance behavior without xfail masking.

The CPU boundary is tested separately from in-process validation spies.
"""
import time

import numpy as np
import pandas as pd
import pytest
from langchain_core.embeddings import Embeddings

from schemas import TrainingSpecification
from services import automl_service


def regression_input():
    df = pd.DataFrame({"feature": np.arange(60, dtype=float), "target": np.arange(60, dtype=float) * 2})
    return df, {"problem_type": "regression", "target_column": "target", "feature_columns": ["feature"]}


def test_undated_rows_do_not_invent_period_growth():
    """Row order is not a business period, so growth must be unavailable."""
    df = pd.DataFrame({"revenue": [1.0, 1.0, 10.0, 10.0]})
    result = automl_service.compute_period_trend(df, "revenue", "sum")
    assert result["trend_pct"] is None, f"Undated transactions were reported as {result}"


def test_training_budget_releases_caller():
    """A real spawned, sleeping worker is killed within the caller's budget."""
    import multiprocessing
    from services.training_worker import run_bounded
    before = {p.pid for p in multiprocessing.active_children()}
    start = time.monotonic()
    result = run_bounded("time", "sleep", (20,), timeout=1)
    elapsed = time.monotonic() - start
    assert result["status"] == "timeout"
    assert elapsed < 2.5, f"1 second budget took {elapsed:.2f} seconds"
    assert {p.pid for p in multiprocessing.active_children()} <= before


def test_temporal_validation_never_trains_on_future_rows(monkeypatch):
    """A temporal holdout also needs temporal validation folds."""
    from sklearn.model_selection import check_cv
    df, info = regression_input()
    df["date"] = pd.date_range("2026-01-01", periods=len(df))
    observed_leaks = []
    observed_folds = []

    def inspect_cv(estimator, X, y, cv, **kwargs):
        splitter = check_cv(cv, y=y, classifier=False)
        for train, validation in splitter.split(X, y):
            observed_folds.append((train, validation))
            if int(max(train)) >= int(min(validation)):
                observed_leaks.append((int(max(train)), int(min(validation))))
        return np.array([0.5, 0.5, 0.5])

    monkeypatch.setattr(automl_service, "cross_val_score", inspect_cv)
    result = automl_service._run_automl_pipeline(df, info, TrainingSpecification(
        split_strategy="temporal", validation_strategy="time_series", time_column="date"
    ))
    assert result["split_strategy"] == "temporal"
    assert observed_folds
    assert not observed_leaks, f"Future training rows cross validation boundary: {observed_leaks}"


def test_only_selected_candidate_uses_final_holdout(monkeypatch):
    """The final holdout is evaluated once after candidate selection."""
    df, info = regression_input()
    original_r2 = automl_service.r2_score
    holdout_calls = []

    def count_holdout(y_true, y_pred, *args, **kwargs):
        holdout_calls.append(len(y_true))
        return original_r2(y_true, y_pred, *args, **kwargs)

    monkeypatch.setattr(automl_service, "r2_score", count_holdout)
    monkeypatch.setattr(automl_service, "cross_val_score", lambda *a, **kw: np.array([0.5, 0.5, 0.5]))
    result = automl_service._run_automl_pipeline(df, info)
    assert result["best_model"] is not None
    assert len(holdout_calls) == 1, f"Holdout evaluated for {len(holdout_calls)} candidates"


def test_embedding_initialization_failure_returns_unverified(monkeypatch):
    from routers import documents
    from services.citation_service import CitationService

    def fail_loading(*args, **kwargs):
        raise RuntimeError("Synthetic embedding initialization outage")

    monkeypatch.setattr(documents, "_load_hf_embeddings", fail_loading)
    result = CitationService().verify_grounding(
        response_text="Revenue was $10 million in 2025.",
        retrieved_chunks=[{"content": "Revenue was $10 million in 2025.", "score": 0.9,
                           "metadata": {"source": "report.txt", "document_id": 1, "chunk_id": 1}}],
    )
    assert result["grounding_status"] == "unverified"
    assert result["grounding_confidence"] == 0.0


def test_failed_ingestion_is_not_reported_as_successful_worker_job(isolated_db, tmp_path, monkeypatch):
    import models
    from ingestion import task_queue
    from routers import documents

    tenant = models.Tenant(name="Readiness audit")
    isolated_db.add(tenant)
    isolated_db.flush()
    doc = models.Document(tenant_id=tenant.id, name="outage.pdf", file_type="PDF", status="Processing", size=10)
    isolated_db.add(doc)
    isolated_db.commit()
    doc_id, tenant_id = doc.id, tenant.id
    path = tmp_path / "outage.pdf"
    path.write_bytes(b"%PDF-synthetic")

    def transient_failure(*args, **kwargs):
        raise TimeoutError("Synthetic temporary extractor outage")

    monkeypatch.setattr(documents, "extract_pdf_split_router", transient_failure)
    monkeypatch.setattr(task_queue, "SessionLocal", lambda: isolated_db)
    with pytest.raises(Exception):
        task_queue.process_document_task.run(doc_id, str(path), tenant_id, 512, 50, "fixed")


class OfflineEmbeddings(Embeddings):
    def embed_query(self, text):
        return [0.2, 0.4, 0.6, 0.8]

    def embed_documents(self, texts):
        return [self.embed_query(text) for text in texts]


def test_serialized_publication_preserves_dense_sparse_membership(tmp_path):
    """Two workers can prepare SQL snapshots before either acquires the lock."""
    from langchain_community.vectorstores import FAISS
    from search.generation_manager import IndexGenerationManager
    from search.bm25_index import BM25IndexManager

    manager = IndexGenerationManager(tenant_id=765, model_name="offline-4", base_dir=str(tmp_path))
    embeddings = OfflineEmbeddings()
    # Valid interleaving: both jobs see the other's document as Processing,
    # prepare snapshots, then publish sequentially under the real manager lock.
    snapshots = [
        [{"id": 1, "content": "alpha revenue report", "metadata": {"document_id": 1, "source": "a.txt"}}],
        [{"id": 2, "content": "beta expenses report", "metadata": {"document_id": 2, "source": "b.txt"}}],
    ]
    for snapshot in snapshots:
        manager.build_and_publish_generation(
            embeddings_model=embeddings,
            new_chunks=[entry["content"] for entry in snapshot],
            new_metadatas=[entry["metadata"] for entry in snapshot],
            all_bm25_chunks=snapshot,
        )
    active, exists = manager.get_active_generation_path()
    assert exists
    dense = FAISS.load_local(active, embeddings, allow_dangerous_deserialization=True)
    dense_ids = {entry.metadata["document_id"] for entry in dense.docstore._dict.values()}
    sparse = BM25IndexManager(tenant_id=765, index_dir=active)
    sparse_ids = {entry["metadata"]["document_id"] for entry in sparse.search("alpha beta", top_k=10)}
    assert dense_ids == {1, 2}
    assert sparse_ids == dense_ids, f"Dense contains {dense_ids}, sparse contains {sparse_ids}"


def test_explicit_business_periods_are_timezone_aware():
    df = pd.DataFrame({"date": ["2026-01-31T18:00:00Z", "2026-01-31T20:00:00Z"], "revenue": [10, 25]})
    comparison = {"prior_start": "2026-01-01", "prior_end": "2026-02-01",
                  "current_start": "2026-02-01", "current_end": "2026-03-01", "timezone": "Asia/Karachi"}
    result = automl_service.compute_period_trend(df, "revenue", date_col="date", comparison=comparison)
    assert result["trend_pct"] == 150
    comparison["current_start"] = "2026-01-15"
    assert automl_service.compute_period_trend(df, "revenue", date_col="date", comparison=comparison)["trend_pct"] is None


def test_group_validation_separates_repeated_entities(monkeypatch):
    df, info = regression_input()
    df["customer"] = np.repeat(np.arange(12), 5)
    spec = TrainingSpecification(split_strategy="grouped", validation_strategy="grouped", group_column="customer")
    partition = automl_service.partition_dataset(df, info["feature_columns"], "target", spec, "regression")
    assert set(df.loc[partition["train_df"].index, "customer"]).isdisjoint(df.loc[partition["test_df"].index, "customer"])
    folds_seen = []

    def inspect_cv(estimator, X, y, cv, **kwargs):
        for train, validation in cv:
            groups = df.loc[X.index, "customer"].to_numpy()
            assert set(groups[train]).isdisjoint(groups[validation])
            folds_seen.append((train, validation))
        return np.array([0.5] * len(cv))

    monkeypatch.setattr(automl_service, "cross_val_score", inspect_cv)
    result = automl_service._run_automl_pipeline(df, info, spec)
    assert result["best_model"] is not None
    assert folds_seen


def test_temporal_validation_rejects_missing_timestamps():
    df, info = regression_input()
    df["date"] = pd.date_range("2026-01-01", periods=len(df)).astype(str)
    df.loc[4, "date"] = None
    with pytest.raises(ValueError, match="timestamps"):
        automl_service.partition_dataset(df, info["feature_columns"], "target",
            TrainingSpecification(split_strategy="temporal", time_column="date"), "regression")


def test_retry_policy_is_transient_bounded_and_exponential(isolated_db):
    from types import SimpleNamespace
    from unittest.mock import Mock
    from celery.exceptions import Retry
    import models
    from ingestion.task_queue import _retry_transient
    tenant = models.Tenant(name="Retries")
    isolated_db.add(tenant)
    isolated_db.flush()
    doc = models.Document(tenant_id=tenant.id, name="retry.txt", file_type="TXT", status="Failed")
    isolated_db.add(doc)
    isolated_db.commit()
    task = SimpleNamespace(request=SimpleNamespace(retries=1), max_retries=3, retry=Mock(return_value=Retry()))
    with pytest.raises(Retry):
        _retry_transient(task, TimeoutError("temporary"), isolated_db, doc.id)
    assert task.retry.call_args.kwargs["countdown"] == 60
    assert doc.progress_step == "retrying"
    task.retry.reset_mock()
    with pytest.raises(ValueError):
        _retry_transient(task, ValueError("malformed"), isolated_db, doc.id)
    task.retry.assert_not_called()
    task.request.retries = 3
    with pytest.raises(TimeoutError):
        _retry_transient(task, TimeoutError("exhausted"), isolated_db, doc.id)
    task.retry.assert_not_called()


def test_generation_tombstones_retry_and_failed_publish(tmp_path, monkeypatch):
    from langchain_community.vectorstores import FAISS
    from search.generation_manager import IndexGenerationManager
    from search.bm25_index import BM25IndexManager
    manager = IndexGenerationManager(901, "offline", base_dir=str(tmp_path))
    emb = OfflineEmbeddings()
    def publish(ids):
        return manager.build_and_publish_generation(emb, [f"document {i}" for i in ids],
            [{"document_id": i, "chunk_id": i} for i in ids], [], live_document_ids=lambda: set(ids))
    publish([1, 2])
    pinned, _ = manager.get_active_generation_path()
    publish([2])
    publish([2])
    active, _ = manager.get_active_generation_path()
    dense = FAISS.load_local(active, emb, allow_dangerous_deserialization=True)
    assert dense.index.ntotal == 1
    assert BM25IndexManager(901, active).chunk_metadatas == [{"document_id": 2, "chunk_id": 2}]
    original = BM25IndexManager.build_index
    monkeypatch.setattr(BM25IndexManager, "build_index", lambda *args: (_ for _ in ()).throw(RuntimeError("failed staging")))
    with pytest.raises(RuntimeError, match="failed staging"):
        publish([3])
    assert manager.get_active_generation_path()[0] == active
    monkeypatch.setattr(BM25IndexManager, "build_index", original)
    publish([])
    empty, _ = manager.get_active_generation_path()
    assert FAISS.load_local(empty, emb, allow_dangerous_deserialization=True).index.ntotal == 0
    assert BM25IndexManager(901, empty).search("document") == []
    assert FAISS.load_local(pinned, emb, allow_dangerous_deserialization=True).index.ntotal == 2


def test_publication_file_lock_fails_closed(tmp_path):
    from search.generation_manager import ProcessTenantLock
    path = str(tmp_path / "publication.lock")
    with ProcessTenantLock(path):
        with pytest.raises(TimeoutError):
            with ProcessTenantLock(path, timeout=0.05):
                pytest.fail("Contended writer entered publication")


def test_concurrent_document_retries_serialize_and_keep_source(isolated_db, tmp_path, monkeypatch):
    import threading
    from concurrent.futures import ThreadPoolExecutor
    from sqlalchemy.orm import sessionmaker
    import database
    import models
    from routers import documents
    from langchain_community.vectorstores import FAISS
    from search.generation_manager import IndexGenerationManager
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(documents, "embeddings_model", OfflineEmbeddings())
    monkeypatch.setattr(database, "SessionLocal", sessionmaker(bind=isolated_db.bind))
    tenant = models.Tenant(name="Concurrent retries")
    isolated_db.add(tenant)
    isolated_db.flush()
    path = tmp_path / "source.txt"
    path.write_text("The annual policy requires every employee to complete safety training.")
    doc = models.Document(tenant_id=tenant.id, name="source.txt", file_type="TXT", status="Processing", storage_key=str(path))
    isolated_db.add(doc)
    isolated_db.commit()
    doc_id, tenant_id = doc.id, tenant.id
    first_started, release = threading.Event(), threading.Event()
    original = documents._process_document
    calls = []
    def paused(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            first_started.set()
            assert release.wait(10)
        return original(*args, **kwargs)
    monkeypatch.setattr(documents, "_process_document", paused)
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(documents.process_document, doc_id, str(path), tenant_id)
        assert first_started.wait(10)
        second = executor.submit(documents.process_document, doc_id, str(path), tenant_id)
        assert len(calls) == 1
        release.set()
        first.result(timeout=30)
        second.result(timeout=30)
    isolated_db.refresh(doc)
    assert doc.status == "Completed"
    assert path.exists()
    active, _ = IndexGenerationManager(tenant_id).get_active_generation_path()
    dense = FAISS.load_local(active, OfflineEmbeddings(), allow_dangerous_deserialization=True)
    assert dense.index.ntotal == doc.embeddings_count
    assert len({entry.metadata["chunk_id"] for entry in dense.docstore._dict.values()}) == dense.index.ntotal


def test_reconciliation_detects_and_repairs_pointer_and_sql_drift(isolated_db, tmp_path, monkeypatch):
    import json
    from pathlib import Path
    import models
    from routers import documents
    from scripts.reconcile_indexes import reconcile_indexes
    from search.generation_manager import IndexGenerationManager
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(documents, "_document_embeddings", lambda model: OfflineEmbeddings())
    tenant = models.Tenant(name="Reconciliation")
    isolated_db.add(tenant)
    isolated_db.flush()
    doc = models.Document(tenant_id=tenant.id, name="policy.txt", file_type="TXT", status="Completed")
    isolated_db.add(doc)
    isolated_db.flush()
    chunk = models.DocumentChunk(document_id=doc.id, chunk_index=0, content="The policy requires safety training.")
    isolated_db.add(chunk)
    isolated_db.commit()
    manager = IndexGenerationManager(tenant.id)
    report = reconcile_indexes(dry_run=True, db=isolated_db)
    assert report["generation_reports"][0]["issues"] == ["missing_or_invalid_generation"]
    assert not Path(manager.pointer_file).exists()
    fixed = reconcile_indexes(dry_run=False, db=isolated_db)
    assert fixed["generation_reports"][0]["repaired"]
    pinned, _ = manager.get_active_generation_path()
    assert reconcile_indexes(dry_run=True, db=isolated_db)["generation_reports"][0]["issues"] == []
    chunk.content = "The policy now requires privacy training."
    isolated_db.commit()
    assert reconcile_indexes(dry_run=True, db=isolated_db)["generation_reports"][0]["issues"] == ["sql_index_drift"]
    Path(manager.pointer_file).write_text(json.dumps({"active_generation": "../outside"}))
    assert reconcile_indexes(dry_run=False, db=isolated_db)["generation_reports"][0]["repaired"]
    assert Path(pinned).is_dir()
    assert reconcile_indexes(dry_run=True, db=isolated_db)["generation_reports"][0]["issues"] == []
    doc.status = "Processing"
    isolated_db.commit()
    before = Path(manager.pointer_file).read_bytes()
    assert "deferred" in reconcile_indexes(dry_run=False, db=isolated_db)["generation_reports"][0]
    assert Path(manager.pointer_file).read_bytes() == before


def test_document_embedding_selection_does_not_reuse_another_model(monkeypatch):
    from types import SimpleNamespace
    from routers import documents
    default = SimpleNamespace(model_name="default")
    alternate = SimpleNamespace(model_name="alternate")
    monkeypatch.setattr(documents, "embeddings_model", default)
    monkeypatch.setattr(documents, "_load_hf_embeddings", lambda name: alternate)
    assert documents._document_embeddings("alternate") is alternate
    assert documents.embeddings_model is default
