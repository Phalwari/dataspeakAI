"""Opt-in NR-2 readiness probes. Assert acceptance behavior without xfail masking.

Run through .agents/nr2-readiness/run_verification.py for offline isolation.
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


def test_training_budget_releases_caller(monkeypatch):
    """A timed-out fitting operation must not keep the caller waiting."""
    df, info = regression_input()

    def slow_cv(*args, **kwargs):
        time.sleep(2.5)
        return np.array([0.5, 0.5, 0.5])

    monkeypatch.setattr(automl_service, "cross_val_score", slow_cv)
    start = time.monotonic()
    result = automl_service.run_automl_pipeline(df, info, TrainingSpecification(training_timeout_seconds=1))
    elapsed = time.monotonic() - start
    assert any("timeout" in row.get("error", "").lower() for row in result["all_models"])
    assert elapsed < 2.0, f"1 second budget took {elapsed:.2f} seconds"


def test_temporal_validation_never_trains_on_future_rows(monkeypatch):
    """A temporal holdout also needs temporal validation folds."""
    from sklearn.model_selection import check_cv
    df, info = regression_input()
    df["date"] = pd.date_range("2026-01-01", periods=len(df))
    observed_leaks = []

    def inspect_cv(estimator, X, y, cv, **kwargs):
        splitter = check_cv(cv, y=y, classifier=False)
        for train, validation in splitter.split(X, y):
            if int(max(train)) >= int(min(validation)):
                observed_leaks.append((int(max(train)), int(min(validation))))
        return np.array([0.5, 0.5, 0.5])

    monkeypatch.setattr(automl_service, "cross_val_score", inspect_cv)
    result = automl_service.run_automl_pipeline(df, info, TrainingSpecification(
        split_strategy="temporal", validation_strategy="time_series", time_column="date"
    ))
    assert result["split_strategy"] == "temporal"
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
    result = automl_service.run_automl_pipeline(df, info)
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
