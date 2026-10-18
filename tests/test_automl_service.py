"""
Unit and regression test suite for Milestone NR-2.1:
Sprint NR-2.1-A (Tasks T03-T07): Clean dataframe policies, full aggregates, honest trend calculation, typed baselines.
Sprint NR-2.1-B (Tasks T01-T07): Leak-free partitioning, scikit-learn pipelines, CV model selection, untouched holdout, silhouette scoring, and training timeout.
"""

import math
import os
import sys
import time
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from schemas import TrainingSpecification
from services.automl_service import (
    clean_dataframe,
    compute_period_trend,
    compute_kpis,
    AutoMLPipeline,
    partition_dataset,
    build_feature_preprocessor,
    run_automl_pipeline,
)


# ============================================================================
# SPRINT NR-2.1-A TESTS: DEDUPLICATION & METRIC CORRECTNESS
# ============================================================================

def test_clean_dataframe_preserves_duplicates_by_default():
    """NR-2.1-A-T04: By default, deduplication_policy='preserve_all' preserves duplicates."""
    df = pd.DataFrame({
        "order_id": [1, 1, 2, 3],
        "amount": [100.0, 100.0, 200.0, 300.0],
    })

    cleaned_df, report = clean_dataframe(df, deduplication_policy="preserve_all")

    assert len(cleaned_df) == 4
    assert report["dropped_duplicates_count"] == 0
    assert report["duplicates_detected_count"] == 1
    assert report["duplicates_removed"] == 0


def test_clean_dataframe_exact_row_policy():
    """NR-2.1-A-T04: When deduplication_policy='exact_row', exact duplicates are dropped."""
    df = pd.DataFrame({
        "order_id": [1, 1, 2, 3],
        "amount": [100.0, 100.0, 200.0, 300.0],
    })

    cleaned_df, report = clean_dataframe(df, deduplication_policy="exact_row")

    assert len(cleaned_df) == 3
    assert report["dropped_duplicates_count"] == 1
    assert report["duplicates_removed"] == 1


def test_clean_dataframe_subset_keys_policy():
    """NR-2.1-A-T04: When deduplication_policy='subset_keys', duplicates on keys are dropped."""
    df = pd.DataFrame({
        "order_id": [1, 1, 2, 3],
        "amount": [100.0, 150.0, 200.0, 300.0],
    })

    cleaned_df, report = clean_dataframe(df, deduplication_policy="subset_keys", subset_keys=["order_id"])

    assert len(cleaned_df) == 3
    assert report["dropped_duplicates_count"] == 1


def test_compute_period_trend_does_not_compare_sum_to_mean():
    """NR-2.1-A-T05: Defect I-09 / FYP-09 Elimination: 10 rows of 100 produce 0.0% trend, not 900%."""
    df = pd.DataFrame({"revenue": [100.0] * 10})
    trend = compute_period_trend(df, "revenue", "sum")

    assert trend["trend_pct"] == 0.0
    assert trend["trend_pct"] != 900.0
    assert trend["trend_status"] == "ok" or trend["trend_status"] == "flat"


def test_compute_period_trend_typed_zero_baseline():
    """NR-2.1-A-T06: When prior period aggregate is zero and current > 0, return unavailable_zero_baseline."""
    df = pd.DataFrame({
        "period": ["2026-Q1", "2026-Q1", "2026-Q2", "2026-Q2"],
        "revenue": [0.0, 0.0, 100.0, 200.0],
    })

    trend = compute_period_trend(df, "revenue", "sum", date_col="period")

    assert trend["trend_status"] == "unavailable_zero_baseline"
    assert trend["trend_pct"] is None
    assert trend["trend_label"] == "Baseline 0"


def test_compute_period_trend_no_prior_data():
    """NR-2.1-A-T06: When dataset has only 1 row, return no_prior_data."""
    df = pd.DataFrame({"revenue": [100.0]})
    trend = compute_period_trend(df, "revenue", "sum")

    assert trend["trend_status"] == "no_prior_data"
    assert trend["trend_pct"] is None


def test_compute_kpis_attaches_provenance_and_exact_aggregates():
    """NR-2.1-A-T03 & T07: compute_kpis computes exact aggregates with provenance."""
    df = pd.DataFrame({
        "revenue": [100.0, 200.0, 300.0, 400.0],
        "date": ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"],
    })
    strategy = {
        "kpi_columns": [{"column": "revenue", "aggregation": "sum", "format": "currency"}]
    }
    profile = {"columns": {"revenue": {"mean": 250.0}}}

    kpis = compute_kpis(df, strategy, profile)

    assert len(kpis) == 1
    kpi = kpis[0]
    assert kpi["raw_value"] == 1000.0
    assert kpi["is_sampled"] is False
    assert "provenance" in kpi
    assert kpi["provenance"]["total_rows_evaluated"] == 4
    assert kpi["provenance"]["is_sampled"] is False


# ============================================================================
# SPRINT NR-2.1-B TESTS: HONEST AUTOML & PIPELINE SEPARATION
# ============================================================================

def test_partition_dataset_before_fitting_stratified():
    """NR-2.1-B-T02 & T03: Partition raw data into train and test without data leakage."""
    np.random.seed(42)
    df = pd.DataFrame({
        "feat_num": np.random.randn(100),
        "feat_cat": ["A", "B", "C", "D"] * 25,
        "target": [0] * 80 + [1] * 20,
    })

    spec = TrainingSpecification(split_strategy="stratified", test_size=0.2, random_state=42)
    partition = partition_dataset(df, ["feat_num", "feat_cat"], "target", spec)

    X_train = partition["train_df"]
    X_test = partition["test_df"]
    y_train = partition["y_train"]
    y_test = partition["y_test"]

    assert len(X_train) == 80
    assert len(X_test) == 20
    # Stratified split preserves target ratio (20% ones in both train and test)
    assert sum(y_train) == 16
    assert sum(y_test) == 4


def test_partition_dataset_temporal_split():
    """NR-2.1-B-T03: Temporal split sorts chronologically without future leakage."""
    dates = pd.date_range("2026-01-01", periods=100, freq="D")
    df = pd.DataFrame({
        "date": dates,
        "feat": range(100),
        "target": range(100),
    })

    spec = TrainingSpecification(split_strategy="temporal", test_size=0.2, time_column="date")
    partition = partition_dataset(df, ["feat"], "target", spec)

    X_train = partition["train_df"]
    X_test = partition["test_df"]

    assert len(X_train) == 80
    assert len(X_test) == 20
    # Train indices must strictly precede test indices
    assert X_train["feat"].max() < X_test["feat"].min()


def test_class_imbalance_detection():
    """NR-2.1-B-T08: Detect class imbalance when minority class is < threshold."""
    df = pd.DataFrame({
        "feat": range(100),
        "target": ["normal"] * 95 + ["fraud"] * 5,  # 5% minority
    })

    spec = TrainingSpecification(imbalance_threshold=0.10)
    partition = partition_dataset(df, ["feat"], "target", spec)

    assert partition["imbalance_detected"] is True
    assert "fraud" in partition["imbalance_warning"]


def test_build_feature_preprocessor_pipeline_structure():
    """NR-2.1-B-T02: Feature preprocessor wraps OneHotEncoder(handle_unknown='ignore') and SimpleImputer."""
    df = pd.DataFrame({
        "age": [25, 30, np.nan, 45],
        "city": ["NY", "SF", "NY", np.nan],
    })

    preprocessor, num_cols, cat_cols = build_feature_preprocessor(["age", "city"], df)

    assert "age" in num_cols
    assert "city" in cat_cols

    # Transform training data
    transformed = preprocessor.fit_transform(df)
    assert transformed.shape[0] == 4

    # New unseen category in test data must not raise error due to handle_unknown='ignore'
    df_test = pd.DataFrame({
        "age": [50],
        "city": ["Tokyo"],  # Unseen city
    })
    transformed_test = preprocessor.transform(df_test)
    assert transformed_test.shape[0] == 1


def test_run_automl_pipeline_cv_model_selection_regression():
    """NR-2.1-B-T04 & T05: Model selection performed via CV on train, with single untouched test evaluation."""
    np.random.seed(42)
    n = 100
    X1 = np.random.randn(n)
    X2 = np.random.choice(["A", "B", "C"], n)
    y = 3.0 * X1 + (X2 == "A").astype(float) * 2.0 + np.random.randn(n) * 0.1

    df = pd.DataFrame({"feat1": X1, "feat2": X2, "target": y})
    problem_info = {
        "problem_type": "regression",
        "target_column": "target",
        "feature_columns": ["feat1", "feat2"],
    }

    spec = TrainingSpecification(test_size=0.2, random_state=42)
    res = run_automl_pipeline(df, problem_info, spec)

    assert "all_models" in res
    assert len(res["all_models"]) > 0
    best = res["best_model"]
    assert best is not None
    assert "cv_score" in best
    assert "test_score" in best
    assert res["train_size"] == 80
    assert res["test_size"] == 20


def test_clustering_genuine_silhouette_score():
    """NR-2.1-B-T06: Defect I-11 Elimination: Silhouette score must be genuine, never hardcoded 1.0."""
    np.random.seed(42)
    # Generate 3 distinct blobs
    c1 = np.random.randn(30, 2) + [0, 0]
    c2 = np.random.randn(30, 2) + [10, 10]
    c3 = np.random.randn(30, 2) + [-10, 10]
    data = np.vstack([c1, c2, c3])
    df = pd.DataFrame(data, columns=["x", "y"])

    problem_info = {
        "problem_type": "clustering",
        "target_column": None,
        "feature_columns": ["x", "y"],
    }

    res = run_automl_pipeline(df, problem_info)

    assert "all_models" in res
    km_res = next((m for m in res["all_models"] if m["model"] == "K-Means Clustering"), None)
    assert km_res is not None
    assert km_res["metric"] == "Silhouette"
    # Genuine silhouette score for 3 distinct clusters should be high (> 0.5) but not hardcoded 1.0
    assert 0.0 < km_res["score"] < 1.0
    assert km_res["score"] == km_res["silhouette_score"]


# ============================================================================
# REGRESSION DEFECT TESTS (REV-NR2.1-QA-01)
# ============================================================================

def test_partition_dataset_drops_target_nans():
    """Fix F01: partition_dataset must drop missing targets to avoid sklearn NaN errors."""
    df = pd.DataFrame({
        "feat1": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0] * 3,
        "target": [1, np.nan, 0, 1, np.nan, 0, 1, 0, 1, 0] * 3,
    })
    partition = partition_dataset(
        df=df,
        feature_columns=["feat1"],
        target_column="target",
        problem_type="classification",
    )
    assert not partition["y_train"].isna().any()
    assert not partition["y_test"].isna().any()
    assert len(partition["train_df"]) + len(partition["test_df"]) == 24  # 30 - 6 NaNs


def test_compute_period_trend_odd_row_flat_series():
    """Fix F02: Odd row count on a flat series must calculate 0.0% trend instead of +100%."""
    df = pd.DataFrame({
        "revenue": [100.0, 100.0, 100.0],
    })
    trend = compute_period_trend(df, "revenue", "sum")
    assert trend["trend_status"] in ("ok", "flat")
    assert trend["trend_pct"] == 0.0
    assert trend["trend_direction"] == "flat"


def test_compute_period_trend_temporal_midpoint_split():
    """Fix F02: Datetime columns should split on temporal midpoint."""
    df = pd.DataFrame({
        "revenue": [10.0, 20.0, 30.0, 40.0],
        "date": ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-31"],
    })
    trend = compute_period_trend(df, "revenue", "sum", date_col="date")
    assert trend["trend_status"] == "ok"
    assert trend["trend_pct"] is not None


def test_feature_importance_aligned_with_categorical_onehot():
    """Fix F04: Feature importance must aggregate back to original parent features."""
    np.random.seed(42)
    n = 60
    age = np.random.randint(20, 60, size=n)
    category = np.random.choice(["Electronics", "Clothing", "Home"], size=n)
    # Target strongly depends on age
    target = (age > 40).astype(int)

    df = pd.DataFrame({"age": age, "category": category, "target": target})
    problem_info = {
        "problem_type": "classification",
        "target_column": "target",
        "feature_columns": ["age", "category"],
    }
    res = run_automl_pipeline(df, problem_info)
    assert "best_model" in res and res["best_model"] is not None
    rf_model = next((m for m in res["all_models"] if "Random Forest" in m["model"]), None)
    if rf_model and rf_model.get("feature_importance"):
        features = [item["feature"] for item in rf_model["feature_importance"]]
        # Parent feature 'age' must be preserved and not replaced by dummy category names
        assert "age" in features
        for item in rf_model["feature_importance"]:
            assert item["feature"] in ["age", "category"]


def test_regression_target_no_class_imbalance_warning():
    """Fix F06: Continuous regression target must not trigger classification class imbalance warning."""
    np.random.seed(42)
    df = pd.DataFrame({
        "x": np.random.randn(50),
        "y_continuous": np.linspace(10.0, 500.0, 50),
    })
    partition = partition_dataset(
        df=df,
        feature_columns=["x"],
        target_column="y_continuous",
        problem_type="regression",
    )
    assert partition["imbalance_detected"] is False
    assert partition["imbalance_warning"] is None
