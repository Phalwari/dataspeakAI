"""
AutoML and AI Agent analysis service with 6-layer architecture.
Automatically detects ML problem type, runs preprocessing, trains multiple scikit-learn/XGBoost models,
selects the best model, and generates business insights using Gemini and Groq.
"""
import os
import io
import json
import re
import math
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split, cross_val_score, StratifiedShuffleSplit, TimeSeriesSplit, GroupKFold, GroupShuffleSplit
from sklearn.preprocessing import LabelEncoder, StandardScaler, OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from sklearn.ensemble import (
    RandomForestClassifier,
    RandomForestRegressor,
    GradientBoostingClassifier,
    GradientBoostingRegressor
)
from sklearn.metrics import (
    accuracy_score,
    r2_score,
    mean_absolute_error,
    silhouette_score,
    f1_score,
    confusion_matrix
)
from sklearn.cluster import KMeans
try:
    import xgboost as xgb
except ImportError:
    xgb = None

from services.multi_llm import get_intent_llm
from schemas import TrainingSpecification

def clean_float(val: Any) -> float:
    """Helper to convert a value to a JSON-serializable float, replacing NaN/Inf with 0.0."""
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return 0.0
        return f
    except (ValueError, TypeError):
        return 0.0

def detect_problem_type(df: pd.DataFrame) -> dict:
    """
    Use Gemini to analyze the dataframe and decide:
    - problem_type: "regression", "classification", or "clustering"
    - target_column: which column to predict
    - feature_columns: which columns to use as features
    - reasoning: why these choices were made
    """
    # Build compact data summary for Gemini
    from datetime import datetime
    sample_values = {}
    for col in df.columns:
        vals = df[col].dropna().head(5).tolist()
        sample_values[col] = [
            v.isoformat() if isinstance(v, (pd.Timestamp, datetime)) else v
            for v in vals
        ]
    summary = {
        "columns": list(df.columns),
        "dtypes": {col: str(df[col].dtype) for col in df.columns},
        "sample_values": sample_values,
        "unique_counts": {
            col: int(df[col].nunique()) for col in df.columns
        },
        "null_counts": {
            col: int(df[col].isnull().sum()) for col in df.columns
        },
        "shape": {"rows": len(df), "columns": len(df.columns)}
    }
    
    prompt = f"""You are an expert data scientist AI agent.
Analyze this dataset and determine the best ML problem to solve.

Dataset Summary:
{json.dumps(summary, indent=2)}

Your task:
1. Identify the most meaningful target column to predict
   - Prefer columns like: revenue, sales, price, churn, 
     status, category, score, amount, result, outcome
   - Avoid: id, timestamp, name, email, phone columns
2. Determine problem type:
   - "regression" if target is continuous numeric
   - "classification" if target has <= 10 unique categories
   - "clustering" if no clear target exists
3. Select feature columns (exclude target, IDs, and 
   high-cardinality text columns)
4. Explain your reasoning in 1-2 sentences

Return ONLY this JSON:
{{
  "problem_type": "regression|classification|clustering",
  "target_column": "column_name_or_null",
  "feature_columns": ["col1", "col2"],
  "reasoning": "Brief explanation",
  "business_question": "What business question does this answer?"
}}"""
    
    try:
        llm = get_intent_llm()
        response = llm.invoke(prompt)
        content = response.content.strip()
        content = re.sub(r"```json|```", "", content).strip()
        return json.loads(content)
    except Exception as e:
        print(f"Gemini auto-detect failed: {e}. Falling back to rule-based detection.")
        # Fallback: auto-detect without LLM
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
        
        target = None
        for keyword in ['revenue','sales','price','amount','score',
                        'churn','status','category','result']:
            for col in df.columns:
                if keyword in col.lower():
                    target = col
                    break
            if target:
                break
        
        if not target and numeric_cols:
            target = numeric_cols[-1]
        
        features = [c for c in (numeric_cols + categorical_cols) 
                   if c != target and df[c].nunique() < 100][:15]
        
        problem = "clustering"
        if target:
            if df[target].nunique() <= 10:
                problem = "classification"
            else:
                problem = "regression"
        
        return {
            "problem_type": problem,
            "target_column": target,
            "feature_columns": features,
            "reasoning": "Auto-detected based on column types",
            "business_question": f"What factors affect {target}?" if target else "How does the data group naturally?"
        }

# === LEAK-FREE PREPROCESSING & PARTITIONING (NR-2.1-B) ===

def partition_dataset(
    df: pd.DataFrame,
    feature_columns: list,
    target_column: Optional[str] = None,
    spec: Optional[TrainingSpecification] = None,
    problem_type: Optional[str] = None,
) -> dict:
    """
    Partitions the raw dataset into train and test sets BEFORE any fitting,
    imputation, scaling, or encoding to eliminate data leakage (Defect I-10).
    Supports random, stratified, and temporal splitting strategies.
    Detects class imbalance strictly on classification targets.
    """
    specification = spec or TrainingSpecification()
    
    # Restrict to available columns
    available_features = list(dict.fromkeys(c for c in feature_columns if c in df.columns and c not in (target_column, specification.group_column, specification.time_column)))
    cols_to_use = list(available_features)
    if target_column and target_column in df.columns:
        cols_to_use.append(target_column)

    df = df.reset_index(drop=True)
    clean_df = df[cols_to_use].dropna(how="all").copy()

    # Supervised learning requires valid, non-null target values (Fix F01)
    if target_column and target_column in clean_df.columns:
        clean_df = clean_df.dropna(subset=[target_column])

    # Resolve problem type
    resolved_problem_type = problem_type
    if not resolved_problem_type and target_column and target_column in clean_df.columns:
        t_series = clean_df[target_column]
        if t_series.dtype in ['object', 'category', 'string', 'bool'] or t_series.nunique() <= 10:
            resolved_problem_type = "classification"
        else:
            resolved_problem_type = "regression"

    imbalance_detected = False
    imbalance_warning = None
    min_class_ratio = 1.0
    majority_baseline = None
    class_distribution = None

    # Class imbalance analysis strictly for classification targets (Fix F06)
    if resolved_problem_type == "classification" and target_column and target_column in clean_df.columns:
        target_series = clean_df[target_column]
        if not target_series.empty:
            proportions = target_series.value_counts(normalize=True)
            if not proportions.empty:
                min_class_ratio = float(proportions.min())
                majority_ratio = float(proportions.max())
                majority_class = proportions.idxmax()
                majority_baseline = round(majority_ratio, 4)
                class_distribution = {str(k): round(float(v), 4) for k, v in proportions.items()}
                if min_class_ratio < specification.imbalance_threshold or majority_ratio >= 0.85:
                    imbalance_detected = True
                    minority_class = proportions.idxmin()
                    imbalance_warning = (
                        f"Class imbalance detected: Minority class '{minority_class}' represents "
                        f"{min_class_ratio*100:.1f}% of samples (threshold: {specification.imbalance_threshold*100:.1f}%), "
                        f"while majority class '{majority_class}' represents {majority_ratio*100:.1f}%. "
                        f"A trivial baseline model achieves {majority_ratio*100:.1f}% accuracy without learning."
                    )

    # Splitting strategy
    test_size = float(specification.test_size)
    random_state = int(specification.random_state)

    if not target_column or target_column not in clean_df.columns:
        # Unsupervised / Clustering
        return {
            "train_df": clean_df[available_features],
            "test_df": None,
            "y_train": None,
            "y_test": None,
            "feature_names": available_features,
            "target_column": None,
            "imbalance_detected": False,
            "imbalance_warning": None,
            "split_strategy": "unsupervised",
        }

    y_all = clean_df[target_column]
    X_all = clean_df[available_features]

    # Temporal split
    time_col = specification.time_column
    if not time_col:
        for c in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[c]) or any(k in str(c).lower() for k in ["date", "time", "created", "timestamp"]):
                time_col = c
                break

    train_groups = None
    train_times = None
    if specification.split_strategy == "temporal" or specification.validation_strategy == "time_series":
        if not time_col or time_col not in df.columns:
            raise ValueError("Temporal validation requires a time column")
        dates = pd.to_datetime(df.loc[clean_df.index, time_col], errors="raise", utc=True)
        if dates.isna().any():
            raise ValueError("Temporal validation requires complete timestamps")
        sorted_indices = dates.sort_values(kind="stable").index
        clean_df = clean_df.loc[sorted_indices]
        X_all = clean_df[available_features]
        y_all = clean_df[target_column]
        split_idx = int(len(clean_df) * (1.0 - test_size))
        cutoff = dates.loc[sorted_indices[split_idx]]
        before = dates.loc[sorted_indices] < cutoff
        X_train, X_test = X_all.loc[before], X_all.loc[~before]
        y_train, y_test = y_all.loc[before], y_all.loc[~before]
        train_times = dates.loc[X_train.index].to_numpy()
        actual_strategy = "temporal"
    elif specification.split_strategy == "grouped" or specification.validation_strategy == "grouped":
        group_col = specification.group_column
        if not group_col or group_col not in df.columns:
            raise ValueError("Grouped validation requires a group column")
        groups = df.loc[clean_df.index, group_col]
        if groups.isna().any() or groups.nunique() < 3:
            raise ValueError("Grouped validation needs at least three complete groups")
        train_idx, test_idx = next(GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state).split(X_all, y_all, groups))
        X_train, X_test = X_all.iloc[train_idx], X_all.iloc[test_idx]
        y_train, y_test = y_all.iloc[train_idx], y_all.iloc[test_idx]
        train_groups = groups.iloc[train_idx].to_numpy()
        actual_strategy = "grouped"
    elif resolved_problem_type == "classification" and (
        specification.split_strategy == "stratified" or (
            target_column and y_all.nunique() <= 20 and all(c >= 2 for c in y_all.value_counts())
        )
    ):
        try:
            X_train, X_test, y_train, y_test = train_test_split(
                X_all, y_all, test_size=test_size, random_state=random_state, stratify=y_all
            )
            actual_strategy = "stratified"
        except Exception:
            X_train, X_test, y_train, y_test = train_test_split(
                X_all, y_all, test_size=test_size, random_state=random_state
            )
            actual_strategy = "random_fallback"
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            X_all, y_all, test_size=test_size, random_state=random_state
        )
        actual_strategy = "random"

    return {
        "train_df": X_train,
        "test_df": X_test,
        "y_train": y_train,
        "y_test": y_test,
        "feature_names": available_features,
        "target_column": target_column,
        "imbalance_detected": imbalance_detected,
        "imbalance_warning": imbalance_warning,
        "majority_baseline": majority_baseline,
        "class_distribution": class_distribution,
        "split_strategy": actual_strategy,
        "train_groups": train_groups,
        "train_times": train_times,
    }


def build_feature_preprocessor(feature_columns: list, df_sample: pd.DataFrame) -> tuple:
    """
    Builds a scikit-learn ColumnTransformer containing SimpleImputer, StandardScaler,
    and OneHotEncoder(handle_unknown='ignore').
    Guarantees no data leakage since it is fit strictly inside a Pipeline on training data.
    """
    numeric_cols = []
    categorical_cols = []

    for col in feature_columns:
        if col not in df_sample.columns:
            continue
        if pd.api.types.is_numeric_dtype(df_sample[col]):
            numeric_cols.append(col)
        else:
            categorical_cols.append(col)

    transformers = []
    if numeric_cols:
        num_pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ])
        transformers.append(("num", num_pipeline, numeric_cols))

    if categorical_cols:
        cat_pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ])
        transformers.append(("cat", cat_pipeline, categorical_cols))

    if not transformers:
        # Fallback dummy transformer
        transformers.append(("num", Pipeline([("imputer", SimpleImputer(strategy="median"))]), feature_columns))

    preprocessor = ColumnTransformer(transformers=transformers, remainder="drop")
    return preprocessor, numeric_cols, categorical_cols


def run_automl_pipeline(df: pd.DataFrame, problem_info: dict, spec: Optional[TrainingSpecification] = None) -> dict:
    """Run all preprocessing and fitting in a killable, capacity-limited worker."""
    from services.training_worker import run_bounded
    specification = spec or TrainingSpecification()
    return run_bounded(__name__, "_run_automl_pipeline", (df, problem_info, specification), specification.training_timeout_seconds)


def _run_automl_pipeline(
    df: pd.DataFrame,
    problem_info: dict,
    spec: Optional[TrainingSpecification] = None,
) -> dict:
    """
    Runs the honest, leak-free AutoML pipeline (NR-2.1-B):
    1. Pre-split partitioning into train/test before any fitting.
    2. Enforces ColumnTransformer inside Pipeline.
    3. Model selection via Cross-Validation on the training split.
    4. Evaluates winning model ONCE on untouched holdout test set.
    5. Calculates true silhouette score for clustering.
    6. Enforces training timeout watchdog.
    """
    start_time = time.time()
    specification = spec or TrainingSpecification()
    timeout = specification.training_timeout_seconds
    problem_type = problem_info.get("problem_type", "clustering")
    target = problem_info.get("target_column")
    features = problem_info.get("feature_columns", [])

    if not features:
        return {"error": "No feature columns found for model training"}

    if len(df) < 20:
        return {
            "error": "Dataset too small (< 20 rows) for reliable machine learning",
            "insufficient_data": True,
            "row_count": len(df),
            "all_models": [],
            "best_model": None,
            "problem_type": problem_type
        }

    # 1. Partition dataset
    partition = partition_dataset(
        df=df,
        feature_columns=features,
        target_column=target if problem_type != "clustering" else None,
        spec=specification,
        problem_type=problem_type,
    )

    X_train = partition["train_df"]
    X_test = partition["test_df"]
    y_train = partition["y_train"]
    y_test = partition["y_test"]
    available_features = partition["feature_names"]

    preprocessor, num_cols, cat_cols = build_feature_preprocessor(available_features, X_train)

    results = []

    def _train_and_eval_model(
        candidate_name,
        candidate_model,
        preproc,
        X_tr,
        y_tr,
        X_te,
        y_te,
        folds,
        metric_score_name,
        p_type,
        numeric_columns,
        categorical_columns,
        feat_names,
    ):
        pipeline = Pipeline([
            ("preprocessor", preproc),
            ("model", candidate_model),
        ])

        # Model selection on train data strictly via Cross Validation
        mean_cv = folds  # Selected using training-only validation before this final fit.

        # Fit once on train and evaluate on holdout test
        pipeline.fit(X_tr, y_tr)
        y_pred = pipeline.predict(X_te)

        if p_type == "regression":
            if len(y_te) < 2:
                raise ValueError("R² requires at least two holdout observations")
            test_score = float(r2_score(y_te, y_pred))
            if not math.isfinite(test_score):
                raise ValueError("Holdout R² is undefined")
            mae = clean_float(mean_absolute_error(y_te, y_pred))
            metric_label = "R² Score"
        else:
            test_score = clean_float(accuracy_score(y_te, y_pred))
            mae = None
            metric_label = "Accuracy"

        # Extract feature importance if available and map back to parent features (Fix F04)
        feat_imp = []
        inner_model = pipeline.named_steps["model"]
        if hasattr(inner_model, "feature_importances_"):
            importances = inner_model.feature_importances_
            try:
                fitted_pre = pipeline.named_steps["preprocessor"]
                transformed_names = fitted_pre.get_feature_names_out()
                feature_map = {}
                for feat_name, imp in zip(transformed_names, importances):
                    raw_name = feat_name
                    for prefix in ["num__", "cat__", "remainder__"]:
                        if raw_name.startswith(prefix):
                            raw_name = raw_name[len(prefix):]
                            break
                    parent = raw_name
                    for c in categorical_columns:
                        if raw_name == c or raw_name.startswith(f"{c}_"):
                            parent = c
                            break
                    feature_map[parent] = feature_map.get(parent, 0.0) + float(imp)
                feat_imp = [
                    {"feature": f, "importance": round(clean_float(score), 4)}
                    for f, score in sorted(feature_map.items(), key=lambda x: x[1], reverse=True)[:10]
                ]
            except Exception:
                # Fallback to direct mapping
                feat_imp = [
                    {"feature": f, "importance": round(clean_float(i), 4)}
                    for f, i in sorted(
                        zip(feat_names[:len(importances)], importances.tolist()),
                        key=lambda x: x[1], reverse=True
                    )[:10]
                ]

        candidate_res = {
            "model": candidate_name,
            "score": round(float(test_score), 4),
            "test_score": round(float(test_score), 4),
            "cv_score": round(float(mean_cv), 4),
            "metric": metric_label,
            "feature_importance": feat_imp,
            "predictions_sample": [clean_float(v) for v in y_pred[:20]],
            "actual_sample": [clean_float(v) for v in y_te[:20]],
        }
        if mae is not None:
            candidate_res["mae"] = round(float(mae), 4)
            candidate_res["r2_score"] = round(float(test_score), 4)
        else:
            candidate_res["accuracy"] = round(float(test_score), 4)
            f1_val = f1_score(y_te, y_pred, average="weighted", zero_division=0)
            candidate_res["f1_score"] = round(float(f1_val), 4)
            candidate_res["confusion_matrix"] = confusion_matrix(y_te, y_pred).tolist()

        return candidate_res

    if problem_type in ["regression", "classification"]:
        if y_train is None or len(X_train) < 5:
            return {"error": "Not enough training samples for supervised learning"}

        # Encode target for classification if non-numeric
        target_encoder = None
        if problem_type == "classification":
            if y_train.dtype in ['object', 'category', 'string', 'bool'] or not pd.api.types.is_numeric_dtype(y_train):
                target_encoder = LabelEncoder()
                y_train = target_encoder.fit_transform(y_train.astype(str))
                y_test = target_encoder.transform(y_test.astype(str))
            else:
                y_train = y_train.values
                y_test = y_test.values

            if len(np.unique(y_train)) < 2:
                return {"error": "Target column has fewer than 2 unique classes in training data"}

            candidate_models = {
                "Logistic Regression": LogisticRegression(max_iter=500, random_state=specification.random_state),
                "Decision Tree": DecisionTreeClassifier(max_depth=5, random_state=specification.random_state),
                "Random Forest": RandomForestClassifier(n_estimators=50, max_depth=10, random_state=specification.random_state, n_jobs=1),
            }
            scoring_metric = "accuracy"
        else:
            y_train = y_train.values
            y_test = y_test.values
            candidate_models = {
                "Linear Regression": LinearRegression(),
                "Decision Tree": DecisionTreeRegressor(max_depth=5, random_state=specification.random_state),
                "Random Forest": RandomForestRegressor(n_estimators=50, max_depth=10, random_state=specification.random_state, n_jobs=1),
            }
            scoring_metric = "r2"

        cv_folds = min(3, max(2, len(X_train) // 5))
        if partition["split_strategy"] == "temporal":
            times = partition["train_times"]
            folds = []
            for train_idx, validation_idx in TimeSeriesSplit(n_splits=cv_folds).split(X_train):
                train_idx = train_idx[times[train_idx] < times[validation_idx[0]]]
                if len(train_idx) and len(validation_idx) >= 2:
                    folds.append((train_idx, validation_idx))
            if not folds:
                return {"error": "Insufficient distinct periods for temporal validation", "best_model": None, "all_models": []}
        elif partition["split_strategy"] == "grouped":
            groups = partition["train_groups"]
            folds = list(GroupKFold(n_splits=min(cv_folds, len(np.unique(groups)))).split(X_train, y_train, groups))
        elif specification.validation_strategy == "holdout":
            tr, va = train_test_split(np.arange(len(X_train)), test_size=specification.test_size,
                                      random_state=specification.random_state,
                                      stratify=y_train if problem_type == "classification" else None)
            folds = [(tr, va)]
        else:
            folds = cv_folds

        for name, model in candidate_models.items():
            try:
                pipeline = Pipeline([("preprocessor", preprocessor), ("model", model)])
                scores = cross_val_score(pipeline, X_train, y_train, cv=folds, scoring=scoring_metric, error_score="raise")
                if not np.isfinite(scores).all():
                    raise ValueError("Validation metric is undefined for these folds")
                mean_cv = round(float(np.mean(scores)), 4)
                results.append({"model": name, "score": mean_cv, "cv_score": mean_cv,
                                "test_score": None, "metric": "Validation R²" if problem_type == "regression" else "Validation Accuracy",
                                "evaluation_scope": "training_validation"})
            except Exception as exc:
                results.append({"model": name, "error": str(exc), "score": None})
        eligible = [r for r in results if "error" not in r]
        if eligible:
            selected = max(eligible, key=lambda r: r["cv_score"])
            try:
                final = _train_and_eval_model(selected["model"], candidate_models[selected["model"]], preprocessor,
                    X_train, y_train, X_test, y_test, selected["cv_score"], scoring_metric, problem_type,
                    num_cols, cat_cols, available_features)
                final["evaluation_scope"] = "final_holdout"
                selected.update(final)
            except Exception as exc:
                selected.update(error=str(exc), score=None)

    elif problem_type == "clustering":
        best_k = 3
        try:
            # Fit preprocessor on X_train
            X_proc = preprocessor.fit_transform(X_train)

            inertias = []
            for k in range(2, min(7, len(X_train))):
                if time.time() - start_time > timeout:
                    break
                try:
                    km = KMeans(n_clusters=k, random_state=specification.random_state, n_init=10)
                    km.fit(X_proc)
                    inertias.append({"k": k, "inertia": clean_float(km.inertia_)})
                except Exception:
                    pass

            km_best = KMeans(n_clusters=best_k, random_state=specification.random_state, n_init=10)
            labels = km_best.fit_predict(X_proc)

            # Genuine silhouette score (Defect I-11 eliminated)
            n_unique_labels = len(np.unique(labels))
            if n_unique_labels > 1 and len(X_proc) > n_unique_labels:
                if len(X_proc) > 2000:
                    sample_idx = np.random.RandomState(42).choice(len(X_proc), 2000, replace=False)
                    sil_val = float(silhouette_score(X_proc[sample_idx], labels[sample_idx]))
                else:
                    sil_val = float(silhouette_score(X_proc, labels))
            else:
                raise ValueError("Silhouette score is unavailable for fewer than two distinct clusters")

            results.append({
                "model": "K-Means Clustering",
                "n_clusters": best_k,
                "score": round(clean_float(sil_val), 4),
                "silhouette_score": round(clean_float(sil_val), 4),
                "metric": "Silhouette",
                "cluster_labels": labels[:100].tolist(),
                "inertia_curve": inertias,
                "cluster_sizes": {
                    str(i): int(np.sum(labels == i))
                    for i in range(best_k)
                }
            })
        except Exception as e:
            results.append({"model": "K-Means Clustering", "error": str(e), "score": None})

    valid = [r for r in results if "error" not in r]
    # Model selection priority: train CV score when available, otherwise score
    evaluated = [r for r in valid if r.get("evaluation_scope") == "final_holdout" or problem_type == "clustering"]
    best = max(evaluated, key=lambda x: x.get("cv_score", x.get("score", -1.0))) if evaluated else None

    return {
        "problem_type": problem_type,
        "all_models": results,
        "best_model": best,
        "train_size": len(X_train),
        "test_size": len(X_test) if X_test is not None else 0,
        "split_strategy": partition.get("split_strategy", "random"),
        "class_imbalance_detected": partition.get("imbalance_detected", False),
        "class_imbalance_warning": partition.get("imbalance_warning"),
        "majority_baseline": partition.get("majority_baseline"),
        "class_distribution": partition.get("class_distribution"),
        "training_time_seconds": round(time.time() - start_time, 2),
    }


# === BACKWARD COMPATIBILITY ADAPTERS ===

def preprocess_data(df: pd.DataFrame, 
                    feature_columns: list,
                    target_column: str = None) -> dict:
    """Backward compatibility adapter returning X, y, report, target_encoder."""
    cols_to_use = [c for c in feature_columns if c in df.columns]
    if target_column and target_column in df.columns:
        cols_to_use.append(target_column)
    clean_df = df[cols_to_use].dropna(how="all").copy()

    preprocessor, num_cols, cat_cols = build_feature_preprocessor(feature_columns, clean_df)
    X = preprocessor.fit_transform(clean_df[feature_columns]) if feature_columns else None
    
    target_encoder = None
    y = None
    if target_column and target_column in clean_df.columns:
        t_series = clean_df[target_column]
        if t_series.dtype in ['object', 'category', 'string'] or not pd.api.types.is_numeric_dtype(t_series):
            target_encoder = LabelEncoder()
            y = target_encoder.fit_transform(t_series.astype(str))
        else:
            y = t_series.values

    return {
        "X": X,
        "y": y,
        "feature_names": feature_columns,
        "report": {
            "original_shape": df.shape,
            "steps": ["Partitioned and transformed using ColumnTransformer"],
            "dropped_columns": [],
            "encoded_columns": cat_cols,
            "scaled_columns": num_cols,
            "final_shape": (len(clean_df), len(feature_columns) + (1 if target_column else 0)),
        },
        "target_encoder": target_encoder,
    }


def run_automl(X, y, problem_type: str, feature_names: list) -> dict:
    """Backward compatibility adapter for array-based AutoML execution."""
    if X is None or len(X) < 10:
        return {"error": "Not enough data to train models"}
    df_dict = {f: X[:, i] for i, f in enumerate(feature_names[:X.shape[1]])}
    if y is not None:
        df_dict["__target__"] = y
    df = pd.DataFrame(df_dict)
    problem_info = {
        "problem_type": problem_type,
        "target_column": "__target__" if y is not None else None,
        "feature_columns": feature_names[:X.shape[1]],
    }
    return run_automl_pipeline(df, problem_info)


# === LAYER 1: DEEP DATA PROFILER ===

def deep_profile(df: pd.DataFrame) -> dict:
    """
    Pure pandas profiling — no LLM calls.
    Fast, runs first before any AI.
    """
    import math
    sample_records = df.head(100).to_dict('records')
    clean_sample_rows = []
    for r in sample_records:
        clean_row = {}
        for k, v in r.items():
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                clean_row[k] = None
            elif pd.isna(v):
                clean_row[k] = None
            else:
                clean_row[k] = v
        clean_sample_rows.append(clean_row)

    profile = {
        "shape": {"rows": len(df), "cols": len(df.columns)},
        "columns": {},
        "correlations": [],
        "sample_rows": clean_sample_rows
    }
    
    for col in df.columns:
        series = df[col]
        missing_pct = round(series.isnull().mean() * 100, 2)
        
        # Detect type
        if pd.api.types.is_datetime64_any_dtype(series):
            col_type = "datetime"
        elif pd.api.types.is_bool_dtype(series):
            col_type = "boolean"
        elif pd.api.types.is_numeric_dtype(series):
            col_type = "numeric"
        elif series.nunique() <= 20:
            col_type = "categorical"
        else:
            col_type = "text"
        
        info = {
            "type": col_type,
            "missing_pct": missing_pct,
            "unique_count": int(series.nunique())
        }
        
        if col_type == "numeric":
            clean = series.dropna()
            q1, q3 = clean.quantile(0.25), clean.quantile(0.75)
            iqr = q3 - q1
            outliers = ((clean < q1 - 1.5*iqr) | 
                       (clean > q3 + 1.5*iqr)).sum()
            info.update({
                "mean": round(float(clean.mean()), 4),
                "std": round(float(clean.std()), 4),
                "min": round(float(clean.min()), 4),
                "max": round(float(clean.max()), 4),
                "median": round(float(clean.median()), 4),
                "skewness": round(float(clean.skew()), 4),
                "outlier_pct": round(float(outliers/len(clean)*100) if len(clean) > 0 else 0.0, 2),
                "sum": round(float(clean.sum()), 4)
            })
        
        elif col_type == "categorical":
            top = series.value_counts().head(8)
            info["top_values"] = {
                str(k): int(v) for k, v in top.items()
            }
            info["sample_values"] = [
                str(x) for x in series.dropna().unique()[:5]
            ]
        
        elif col_type == "datetime":
            clean = series.dropna()
            info["date_range"] = [
                str(clean.min()), str(clean.max())
            ]
        
        profile["columns"][col] = info
    
    # Top correlations between numeric columns
    numeric_cols = [c for c, i in profile["columns"].items() 
                   if i["type"] == "numeric"]
    if len(numeric_cols) >= 2:
        corr_matrix = df[numeric_cols].corr()
        pairs = []
        for i in range(len(numeric_cols)):
            for j in range(i+1, len(numeric_cols)):
                c1, c2 = numeric_cols[i], numeric_cols[j]
                val = corr_matrix.loc[c1, c2]
                if not pd.isna(val):
                    pairs.append({
                        "col_a": c1, "col_b": c2,
                        "correlation": round(float(val), 4)
                    })
        pairs.sort(key=lambda x: abs(x["correlation"]), reverse=True)
        profile["correlations"] = pairs[:10]
    
    return profile


# === LAYER 2: GEMINI DOMAIN STRATEGIST ===

def ai_domain_strategy(profile: dict) -> dict:
    """
    Gemini analyzes full profile and decides 
    what this data is about and how to analyze it.
    """
    compact = {
        "shape": profile["shape"],
        "columns": {
            col: {
                "type": info["type"],
                "missing_pct": info["missing_pct"],
                "unique_count": info["unique_count"],
                "sample_values": info.get(
                    "sample_values", 
                    list(info.get("top_values", {}).keys())[:3]
                ),
                **({"mean": info["mean"], 
                    "max": info["max"],
                    "skewness": info["skewness"]} 
                   if info["type"] == "numeric" else {})
            }
            for col, info in profile["columns"].items()
        },
        "top_correlations": profile["correlations"][:5]
    }
    
    prompt = f"""You are a senior data scientist.
Analyze this dataset profile and return a strategy.

Profile:
{json.dumps(compact, indent=2)}

Return ONLY this JSON (no markdown, no explanation):
{{
  "domain": "one of: manufacturing/ecommerce/hr/financial/marketing/supply_chain/healthcare/education/general",
  "business_context": "1 sentence: what this data represents",
  "target_column": "most important column to analyze or predict (the main metric)",
  "key_columns": ["5-8 most analytically important columns"],
  "noise_columns": ["columns to ignore: IDs, free text, high-cardinality strings"],
  "analysis_type": "one of: descriptive/diagnostic/predictive/comparative",
  "primary_question": "The main business question this data can answer",
  "kpi_columns": [
    {{"column": "col_name", "label": "Human label", "aggregation": "sum/avg/count/max", "format": "number/currency/percent", "icon_type": "positive/negative/neutral"}}
  ]
}}

Rules:
- kpi_columns: pick 4-6 numeric columns that are most meaningful as KPIs
- target_column: prefer columns with business meaning (revenue, defect, salary, conversion)
- noise_columns: definitely exclude ID columns, email, phone, UUID columns"""

    try:
        from services.multi_llm import get_intent_llm
        llm = get_intent_llm()
        response = llm.invoke(prompt)
        content = response.content.strip()
        content = re.sub(r"```json|```", "", content).strip()
        result = json.loads(content)
        return result
    except Exception as e:
        print(f"[Layer2] Strategy failed: {e}")
        # Fallback
        numeric_cols = [c for c, i in profile["columns"].items() 
                       if i["type"] == "numeric"]
        return {
            "domain": "general",
            "business_context": "Dataset analysis",
            "target_column": numeric_cols[0] if numeric_cols else None,
            "key_columns": numeric_cols[:6],
            "noise_columns": [],
            "analysis_type": "descriptive",
            "primary_question": "What are the key patterns in this dataset?",
            "kpi_columns": [
                {"column": c, "label": c.replace("_"," ").title(),
                 "aggregation": "sum", "format": "number",
                 "icon_type": "neutral"}
                for c in numeric_cols[:5]
            ]
        }


# === LAYER 3: GEMINI CHART PLANNER ===

def ai_chart_planner(profile: dict, strategy: dict) -> list:
    """
    Gemini selects the best charts for this 
    specific dataset based on profile + strategy.
    Returns 6-12 chart specifications.
    """
    col_types = {
        col: info["type"] 
        for col, info in profile["columns"].items()
        if col not in strategy.get("noise_columns", [])
    }
    
    categorical_cols = [c for c, t in col_types.items() 
                       if t == "categorical"]
    numeric_cols = [c for c, t in col_types.items() 
                   if t == "numeric"]
    datetime_cols = [c for c, t in col_types.items() 
                    if t == "datetime"]
    
    prompt = f"""You are a senior data visualization expert.
Design the best dashboard charts for this dataset.

Domain: {strategy.get('domain')}
Primary Question: {strategy.get('primary_question')}
Target Column: {strategy.get('target_column')}
Key Columns: {strategy.get('key_columns')}

Available columns by type:
- Categorical (for grouping/filtering): {categorical_cols}
- Numeric (for measuring): {numeric_cols}
- DateTime (for trends): {datetime_cols}

Top correlations: {profile.get('correlations', [])[:5]}

Design 6-10 charts. Each chart must use ONLY columns 
from the lists above. Return ONLY this JSON array:
[
  {{
    "title": "Descriptive chart title",
    "subtitle": "One sentence: what to notice here",
    "type": "bar|horizontal_bar|line|area|donut|scatter|heatmap|gauge|treemap",
    "x_column": "column name for x axis or grouping",
    "y_column": "column name for values",
    "aggregation": "sum|avg|count|max|min",
    "color_key": "primary|secondary|warning|danger|success",
    "priority": 1
  }}
]

Rules:
1. Priority 1 = most important chart (always show first)
2. Include at least:
   - 1 trend chart (use datetime col if exists, else top categorical)
   - 1 distribution/breakdown chart (donut/treemap)
   - 2 comparison charts (bar/horizontal_bar)
   - 1 correlation chart if 2+ numeric cols exist (scatter/heatmap)
3. For heatmap: x_column and y_column = comma-separated numeric cols
4. For gauge: y_column = target_column, x_column = null
5. For treemap: x_column = categorical col, y_column = numeric col
6. NEVER use noise columns
7. color_key meaning:
   - danger: defects, errors, costs, downtime, scrap, loss
   - success: revenue, efficiency, performance, conversion  
   - warning: average metrics, neutral comparisons
   - primary: main comparison charts
   - secondary: trend charts"""

    try:
        from services.multi_llm import get_intent_llm
        llm = get_intent_llm()
        response = llm.invoke(prompt)
        content = response.content.strip()
        content = re.sub(r"```json|```", "", content).strip()
        charts = json.loads(content)
        
        # Safely handle wrapped dictionary responses (e.g. {"charts": [...]})
        if isinstance(charts, dict):
            for key, val in charts.items():
                if isinstance(val, list):
                    charts = val
                    break
            else:
                charts = []
                
        if isinstance(charts, list) and len(charts) > 0:
            charts.sort(key=lambda x: x.get("priority", 99))
            return charts
        return _deterministic_chart_plan(profile, strategy)
    except Exception as e:
        print(f"[Layer3] Chart planning failed ({e}), using deterministic planner fallback.")
        return _deterministic_chart_plan(profile, strategy)


def _deterministic_chart_plan(profile: dict, strategy: dict) -> list:
    """Deterministic fallback chart generator based on profile columns."""
    col_types = {
        col: info["type"]
        for col, info in profile.get("columns", {}).items()
        if col not in strategy.get("noise_columns", [])
    }
    categorical_cols = [c for c, t in col_types.items() if t == "categorical"]
    numeric_cols = [c for c, t in col_types.items() if t == "numeric"]
    datetime_cols = [c for c, t in col_types.items() if t == "datetime"]
    target = strategy.get("target_column") or (numeric_cols[0] if numeric_cols else None)

    fallback = []
    # 1. Primary trend or categorical comparison
    if datetime_cols and target:
        fallback.append({
            "id": "chart_trend",
            "title": f"{target.replace('_', ' ').title()} Over Time",
            "type": "area",
            "x_column": datetime_cols[0],
            "y_column": target,
            "aggregation": "sum",
            "color_key": "secondary",
            "priority": 1
        })
    elif categorical_cols and target:
        fallback.append({
            "id": "chart_cat_trend",
            "title": f"{target.replace('_', ' ').title()} by {categorical_cols[0].replace('_', ' ').title()}",
            "type": "bar",
            "x_column": categorical_cols[0],
            "y_column": target,
            "aggregation": "sum",
            "color_key": "primary",
            "priority": 1
        })

    # 2. Distribution / Donut
    if len(categorical_cols) > 1 and target:
        fallback.append({
            "id": "chart_dist",
            "title": f"Distribution by {categorical_cols[1].replace('_', ' ').title()}",
            "type": "donut",
            "x_column": categorical_cols[1],
            "y_column": target,
            "aggregation": "sum",
            "color_key": "secondary",
            "priority": 2
        })
    elif categorical_cols:
        fallback.append({
            "id": "chart_dist",
            "title": f"Distribution by {categorical_cols[0].replace('_', ' ').title()}",
            "type": "donut",
            "x_column": categorical_cols[0],
            "y_column": target or categorical_cols[0],
            "aggregation": "count",
            "color_key": "secondary",
            "priority": 2
        })

    # 3. Correlation scatter if 2+ numeric
    if len(numeric_cols) >= 2:
        fallback.append({
            "id": "chart_scatter",
            "title": f"{numeric_cols[0].replace('_', ' ').title()} vs {numeric_cols[1].replace('_', ' ').title()}",
            "type": "scatter",
            "x_column": numeric_cols[0],
            "y_column": numeric_cols[1],
            "aggregation": "avg",
            "color_key": "warning",
            "priority": 3
        })

    # 4. Secondary categorical breakdown
    if len(numeric_cols) > 1 and categorical_cols:
        fallback.append({
            "id": "chart_bar_2",
            "title": f"{numeric_cols[1].replace('_', ' ').title()} Breakdown",
            "type": "horizontal_bar",
            "x_column": categorical_cols[0],
            "y_column": numeric_cols[1],
            "aggregation": "sum",
            "color_key": "success",
            "priority": 4
        })

    return fallback


# === LAYER 4: DATA COMPUTER ===

def compute_chart_data(
    df: pd.DataFrame, 
    chart_specs: list,
    profile: dict
) -> list:
    """
    Pure pandas — no LLM.
    Executes each chart spec. If a spec doesn't fit the dataset,
    automatically substitutes a valid chart using available columns.
    Charts that still can't be built are dropped entirely (never shown broken).
    """
    COLOR_MAP = {
        "primary": "#6c47ff", "secondary": "#00c2cb", "warning": "#f59e0b",
        "danger": "#e24b4a", "success": "#10b981"
    }
    CHART_COLORS = ["#6c47ff", "#00c2cb", "#f59e0b", "#e24b4a", "#10b981", "#9b7dff"]

    numeric_cols = [c for c, i in profile["columns"].items() if i["type"] == "numeric"]
    categorical_cols = [c for c, i in profile["columns"].items() if i["type"] == "categorical"]
    datetime_cols = [c for c, i in profile["columns"].items() if i["type"] == "datetime"]

    normalized_map = {str(c).strip().lower().replace(" ", "_"): c for c in df.columns}

    def resolve_col(name):
        """Case/whitespace-tolerant column resolution."""
        if not name:
            return None
        if name in df.columns:
            return name
        return normalized_map.get(str(name).strip().lower().replace(" ", "_"))

    used_pairs = set()  # avoid generating duplicate substitute charts
    computed = []

    def try_build(chart_type, x_col_raw, y_col_raw, agg, color):
        """Attempt to build one chart. Returns chart dict with data, or None if impossible."""
        x_col = resolve_col(x_col_raw)
        y_col = resolve_col(y_col_raw)
        try:
            if chart_type == "heatmap":
                cols = [c for c in numeric_cols][:6]
                if len(cols) < 2:
                    return None
                corr = df[cols].corr().round(3)
                data = [{"x": c1, "y": c2, "value": float(corr.loc[c1, c2]) if not pd.isna(corr.loc[c1, c2]) else 0.0}
                        for c1 in cols for c2 in cols]
                return {"type": "heatmap", "data": data, "columns": cols, "color": color}

            if chart_type == "scatter":
                if x_col and y_col and x_col in df.columns and y_col in df.columns:
                    sample = df[[x_col, y_col]].dropna()
                    if len(sample) < 3:
                        return None
                    if len(sample) > 200:
                        sample = sample.sample(200)
                    return {"type": "scatter", "x_column": x_col, "y_column": y_col,
                            "data": [{"x": round(float(r[x_col]), 4), "y": round(float(r[y_col]), 4)} for _, r in sample.iterrows()],
                            "color": color}
                return None

            if chart_type == "gauge":
                if y_col and y_col in df.columns:
                    col_info = profile["columns"].get(y_col, {})
                    val = float(df[y_col].mean())
                    return {"type": "gauge", "y_column": y_col,
                            "value": round(val, 2), "min": col_info.get("min", 0), "max": col_info.get("max", 100),
                            "data": [{"value": round(val, 2)}], "color": color}
                return None

            # bar / line / area / donut / horizontal_bar / treemap
            if not x_col or x_col not in df.columns:
                return None
            if y_col_raw and (not y_col or y_col not in df.columns):
                return None

            if y_col:
                grouped = df.groupby(x_col)[y_col].agg(agg if agg in ["sum","mean","count","max","min"] else "sum")
                if chart_type in ["line", "area"] or x_col in datetime_cols:
                    grouped = grouped.sort_index()
                else:
                    grouped = grouped.sort_values(ascending=False)
                max_points = 30 if chart_type in ["line", "area"] else 12
                grouped = grouped.head(max_points)
                if grouped.empty:
                    return None
                data = [{"x": str(k), "y": round(float(v), 4), "name": str(k), "value": round(float(v), 4)} for k, v in grouped.items()]
            else:
                counts = df[x_col].value_counts().head(10)
                if counts.empty:
                    return None
                data = [{"x": str(k), "y": int(v), "name": str(k), "value": int(v)} for k, v in counts.items()]

            if chart_type in ["donut", "pie", "treemap"]:
                for i, point in enumerate(data):
                    point["color"] = CHART_COLORS[i % len(CHART_COLORS)]

            return {"type": chart_type, "x_column": x_col, "y_column": y_col, "data": data, "color": color}
        except Exception:
            return None

    # STEP 1: Try each Gemini-suggested spec as-is
    for spec in chart_specs:
        chart_type = spec.get("type", "bar")
        x_col = spec.get("x_column")
        y_col = spec.get("y_column")
        agg = spec.get("aggregation", "sum")
        color = COLOR_MAP.get(spec.get("color_key", "primary"), "#6c47ff")

        result = try_build(chart_type, x_col, y_col, agg, color)

        if result:
            chart = {**spec, **result}
            computed.append(chart)
            if result.get("x_column") and result.get("y_column"):
                used_pairs.add((result["x_column"], result["y_column"]))
            continue

        # STEP 2: Original spec failed — auto-substitute using available column types
        substitute = None

        # Type-specific substitution logic
        if chart_type == "scatter" and len(numeric_cols) >= 2:
            for i in range(len(numeric_cols)):
                for j in range(len(numeric_cols)):
                    if i == j:
                        continue
                    nx, ny = numeric_cols[i], numeric_cols[j]
                    if (nx, ny) in used_pairs:
                        continue
                    substitute = try_build("scatter", nx, ny, agg, color)
                    if substitute:
                        used_pairs.add((nx, ny))
                        break
                if substitute:
                    break

        elif chart_type == "heatmap":
            substitute = try_build("heatmap", None, None, agg, color)

        elif chart_type == "gauge" and numeric_cols:
            for num in numeric_cols:
                if (None, num) in used_pairs:
                    continue
                substitute = try_build("gauge", None, num, agg, color)
                if substitute:
                    used_pairs.add((None, num))
                    break

        # Fallback: try a bar chart using available categorical+numeric columns
        if not substitute and categorical_cols and numeric_cols:
            for cat in categorical_cols:
                for num in numeric_cols:
                    if (cat, num) in used_pairs:
                        continue
                    substitute = try_build("bar", cat, num, "sum", color)
                    if substitute:
                        used_pairs.add((cat, num))
                        break
                if substitute:
                    break

            # Reuse fallback if all unique pairs were exhausted
            if not substitute:
                for cat in categorical_cols:
                    for num in numeric_cols:
                        substitute = try_build("bar", cat, num, "sum", color)
                        if substitute:
                            break
                    if substitute:
                        break

        if substitute:
            computed.append({
                **spec,
                **substitute,
                "title": spec.get("title", "Auto-generated chart"),
                "subtitle": "Automatically adapted to fit this dataset",
                "auto_substituted": True
            })
        # STEP 3: Nothing worked — silently drop this chart slot entirely (no broken card)

    return computed


# === LAYER 5: GROQ INSIGHT GENERATOR ===

def ai_generate_insights(
    profile: dict,
    strategy: dict, 
    computed_charts: list
) -> list:
    """
    Groq (fast) generates specific, quantified 
    business insights based on actual data.
    """
    chart_summaries = []
    for chart in computed_charts[:6]:
        if chart.get("data"):
            top3 = chart["data"][:3]
            chart_summaries.append({
                "title": chart["title"],
                "type": chart["type"],
                "top_values": top3
            })
    
    prompt = f"""You are a senior business analyst.
Write specific, actionable insights for a business owner.

Domain: {strategy.get('domain')}
Primary Question: {strategy.get('primary_question')}
Business Context: {strategy.get('business_context')}
Target Column: {strategy.get('target_column')}

Chart data (actual values):
{json.dumps(chart_summaries, indent=2)}

Write exactly 4 insights. Each insight must:
1. Mention specific numbers from the chart data
2. Explain what it means for the business
3. Suggest one concrete action
4. Be 1-2 sentences max

Return ONLY this JSON array:
[
  {{
    "text": "Specific insight with numbers and action",
    "severity": "high|medium|low",
    "icon_type": "alert|trend|info|success"
  }}
]"""

    try:
        from services.multi_llm import get_response_llm
        llm = get_response_llm()
        response = llm.invoke(prompt)
        content = response.content.strip()
        content = re.sub(r"```json|```", "", content).strip()
        return json.loads(content)
    except Exception as e:
        print(f"[Layer5] Insights failed: {e}")
        return [
            {"text": "Analysis complete. Review charts for patterns.",
             "severity": "low", "icon_type": "info"}
        ]


# === DATA CLEANING LAYER ===

def clean_dataframe(
    df: pd.DataFrame,
    deduplication_policy: str = "preserve_all",
    subset_keys: Optional[List[str]] = None,
) -> tuple:
    """
    Cleans any real-world messy dataset before analysis.
    Preserves duplicates by default unless explicitly asked.
    Returns (cleaned_df, cleaning_report).
    """
    report = {
        "original_rows": len(df),
        "original_cols": len(df.columns),
        "deduplication_policy": deduplication_policy,
        "dropped_duplicates_count": 0,
        "duplicates_detected_count": int(df.duplicated().sum()),
        "duplicates_removed": 0,
        "nulls_imputed_count": 0,
        "outliers_detected_count": 0,
        "missing_value_pct_by_column": {},
    }

    # 1. Drop fully empty rows & columns
    df = df.dropna(how="all")
    df = df.dropna(axis=1, how="all")

    # 2. Strip whitespace from column names
    df.columns = [str(c).strip() for c in df.columns]

    # 3. Deduplication according to policy (default: preserve_all)
    if deduplication_policy == "exact_row":
        dup_count = int(df.duplicated().sum())
        df = df.drop_duplicates()
        report["dropped_duplicates_count"] = dup_count
        report["duplicates_removed"] = dup_count
    elif deduplication_policy == "subset_keys" and subset_keys:
        valid_keys = [k for k in subset_keys if k in df.columns]
        if valid_keys:
            dup_count = int(df.duplicated(subset=valid_keys).sum())
            df = df.drop_duplicates(subset=valid_keys)
            report["dropped_duplicates_count"] = dup_count
            report["duplicates_removed"] = dup_count

    # 4. Per-column type coercion — convert "numeric-looking" strings to numbers
    for col in df.columns:
        if df[col].dtype == object or pd.api.types.is_string_dtype(df[col]):
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace(
                {"": None, "nan": None, "None": None, "N/A": None, "null": None, "NULL": None}
            )
            coerced = pd.to_numeric(
                df[col].str.replace(",", "", regex=False).str.replace("$", "", regex=False),
                errors="coerce"
            )
            non_null = df[col].notna().sum()
            if non_null > 0 and (coerced.notna().sum() / non_null) >= 0.8:
                df[col] = coerced

    # 5. Detect date columns
    for col in df.columns:
        if df[col].dtype == object or pd.api.types.is_string_dtype(df[col]):
            name_hint = any(k in col.lower() for k in ["date", "time", "created", "updated"])
            if name_hint:
                parsed = pd.to_datetime(df[col], errors="coerce")
                if parsed.notna().sum() / max(len(df[col]), 1) >= 0.6:
                    df[col] = parsed

    # 6. Track missing value percentage and outliers per column
    missing_report = {}
    outliers_total = 0
    for col in df.columns:
        missing_pct = round(df[col].isna().mean() * 100, 1)
        if missing_pct > 0:
            missing_report[col] = missing_pct
        if pd.api.types.is_numeric_dtype(df[col]):
            col_series = df[col].dropna()
            if len(col_series) >= 10:
                q25, q75 = col_series.quantile(0.25), col_series.quantile(0.75)
                iqr = q75 - q25
                if iqr > 0:
                    outliers_count = int(((col_series < (q25 - 1.5 * iqr)) | (col_series > (q75 + 1.5 * iqr))).sum())
                    outliers_total += outliers_count

    report["missing_value_pct_by_column"] = missing_report
    report["outliers_detected_count"] = outliers_total
    report["cleaned_rows"] = len(df)
    report["cleaned_cols"] = len(df.columns)
    return df, report


# === LAYER 6: KPI COMPUTER ===

def compute_period_trend(
    df: pd.DataFrame,
    col: str,
    agg: str = "sum",
    date_col: Optional[str] = None,
    comparison: Optional[dict] = None,
) -> dict:
    """Compare dated, non-overlapping business periods; never infer time from row order."""
    unavailable = {"trend_pct": None, "trend_direction": "flat",
                   "trend_status": "no_prior_data", "trend_label": "Comparison periods unavailable"}
    if df.empty or col not in df.columns or not date_col or date_col not in df.columns:
        return unavailable
    if not comparison:
        return unavailable
    try:
        zone = comparison.get("timezone", "UTC")
        dates = pd.to_datetime(df[date_col], errors="raise")
        dates = dates.dt.tz_localize(zone, ambiguous="raise", nonexistent="raise") if dates.dt.tz is None else dates.dt.tz_convert(zone)
        boundaries = []
        for key in ("prior_start", "prior_end", "current_start", "current_end"):
            boundary = pd.Timestamp(comparison[key])
            boundary = boundary.tz_localize(zone) if boundary.tzinfo is None else boundary.tz_convert(zone)
            boundaries.append(boundary)
        ps, pe, cs, ce = boundaries
        if not (ps < pe <= cs < ce) or dates.isna().any():
            return unavailable
        prior_df = df.loc[(dates >= ps) & (dates < pe)]
        curr_df = df.loc[(dates >= cs) & (dates < ce)]
    except (ValueError, TypeError, KeyError):
        return unavailable

    def _eval_agg(sub_df, column, ag):
        s = sub_df[column].dropna()
        if s.empty:
            return None
        ag_lower = str(ag).lower()
        if ag_lower in ["sum", "total"]:
            return float(s.sum())
        elif ag_lower in ["avg", "mean", "average"]:
            return float(s.mean())
        elif ag_lower in ["count"]:
            return float(len(s))
        elif ag_lower == "max":
            return float(s.max())
        elif ag_lower == "min":
            return float(s.min())
        return float(s.sum())

    curr_val = _eval_agg(curr_df, col, agg)
    prior_val = _eval_agg(prior_df, col, agg)

    if prior_val is None or curr_val is None:
        return {
            "trend_pct": None,
            "trend_direction": "flat",
            "trend_status": "no_prior_data",
            "trend_label": "No prior data",
        }

    if prior_val == 0:
        if curr_val == 0:
            return {
                "trend_pct": 0.0,
                "trend_direction": "flat",
                "trend_status": "flat",
                "trend_label": "0.0%",
            }
        return {
            "trend_pct": None,
            "trend_direction": "up" if curr_val > 0 else "down",
            "trend_status": "unavailable_zero_baseline",
            "trend_label": "Baseline 0",
        }

    pct = round((curr_val - prior_val) / abs(prior_val) * 100.0, 1)
    direction = "up" if pct > 0 else ("down" if pct < 0 else "flat")
    return {
        "trend_pct": pct,
        "trend_direction": direction,
        "trend_status": "ok",
        "trend_label": f"{pct:+.1f}%",
    }


def compute_kpis(df: pd.DataFrame, 
                 strategy: dict,
                 profile: dict) -> list:
    """
    Compute actual KPI values from data generically for ANY dataset.
    Uses strategy.kpi_columns defined by AI with normalized column matching.
    Attaches provenance metadata and typed baseline statuses.
    """
    kpis = []
    kpi_cols = strategy.get("kpi_columns", [])

    # Build a normalized lookup: "post_code" -> "Postcode" (actual df column)
    normalized_map = {str(c).strip().lower().replace(" ", "_"): c for c in df.columns}
    
    for kpi_spec in kpi_cols[:6]:
        raw_col = kpi_spec.get("column", "")
        if not raw_col:
            continue

        # Case & space tolerant matching
        col = raw_col if raw_col in df.columns else normalized_map.get(
            str(raw_col).strip().lower().replace(" ", "_")
        )
        
        if not col or col not in df.columns:
            print(f"[Layer6] KPI column '{raw_col}' not found in dataframe columns: {list(df.columns)}")
            continue
        
        try:
            label = kpi_spec.get("label", col.replace("_", " ").title())
            agg = kpi_spec.get("aggregation")
            col_lower = str(col).lower()
            label_lower = str(label).lower()
            
            # Infer aggregation if not explicitly defined or inappropriately defaulted
            if not agg or agg == "sum":
                if any(kw in col_lower for kw in ['age', 'rating', 'score', 'tenure', 'temp', 'prob', 'ratio', 'rate', 'pct', 'percent', 'satisfaction']) or any(kw in label_lower for kw in ['avg', 'average', 'mean', 'rate', 'ratio', 'score', 'rating']):
                    agg = "avg"
                else:
                    agg = "sum"

            series = df[col].dropna()
            
            if series.empty:
                continue

            if agg == "sum":
                val = float(series.sum())
            elif agg in ["avg", "mean", "average"]:
                val = float(series.mean())
            elif agg == "count":
                val = float(len(series))
            elif agg == "max":
                val = float(series.max())
            elif agg == "min":
                val = float(series.min())
            else:
                val = float(series.sum())
            
            # Format value
            fmt = kpi_spec.get("format", "number")
            if fmt == "currency":
                if val >= 1e9:
                    formatted = f"${val/1e9:.2f}B"
                elif val >= 1e6:
                    formatted = f"${val/1e6:.2f}M"
                elif val >= 1e3:
                    formatted = f"${val/1e3:.1f}K"
                else:
                    formatted = f"${val:,.2f}"
            elif fmt == "percent":
                formatted = f"{val:.1f}%"
            else:
                if val >= 1e9:
                    formatted = f"{val/1e9:.2f}B"
                elif val >= 1e6:
                    formatted = f"{val/1e6:.2f}M"
                elif val >= 1e3 and agg == "sum":
                    formatted = f"{val/1e3:.1f}K"
                elif val == int(val):
                    formatted = f"{int(val):,}"
                else:
                    formatted = f"{val:,.1f}"
            
            # Honest period trend computation (Defect I-09 / FYP-09 eliminated)
            trend_info = compute_period_trend(df, col, agg, kpi_spec.get("date_column"), kpi_spec.get("comparison"))
            
            kpis.append({
                "label": kpi_spec.get(
                    "label", 
                    col.replace("_"," ").title()
                ),
                "value": formatted,
                "raw_value": val,
                "column": col,
                "format": fmt,
                "icon_type": kpi_spec.get("icon_type", "neutral"),
                "trend_pct": trend_info["trend_pct"],
                "trend_direction": trend_info["trend_direction"],
                "trend_status": trend_info["trend_status"],
                "trend_label": trend_info["trend_label"],
                "is_sampled": False,
                "provenance": {
                    "definition_version": "2.0",
                    "date_column": kpi_spec.get("date_column"),
                    "comparison": kpi_spec.get("comparison"),
                    "source_type": "dataframe",
                    "calculated_at": datetime.now(timezone.utc).isoformat(),
                    "total_rows_evaluated": len(df),
                    "is_sampled": False,
                    "sample_ratio": 1.0,
                }
            })
        except Exception as e:
            print(f"[Layer6] KPI '{col}' failed: {e}")
    
    # Auto-fallback: if no KPIs could be computed from strategy, generate from numeric columns
    if not kpis:
        print("[Layer6] No strategy KPIs matched — auto-generating numeric KPIs")
        numeric_cols = [c for c, info in profile.get("columns", {}).items() if info.get("type") == "numeric"][:5]
        for col in numeric_cols:
            try:
                series = df[col].dropna()
                if series.empty:
                    continue
                val = float(series.sum())
                formatted = f"{val/1e6:.2f}M" if abs(val) >= 1e6 else f"{val/1e3:.1f}K" if abs(val) >= 1e3 else f"{val:,.2f}"
                trend_info = compute_period_trend(df, col, "sum")
                kpis.append({
                    "label": col.replace("_", " ").title(),
                    "value": formatted,
                    "raw_value": val,
                    "column": col,
                    "format": "number",
                    "icon_type": "neutral",
                    "trend_pct": trend_info["trend_pct"],
                    "trend_direction": trend_info["trend_direction"],
                    "trend_status": trend_info["trend_status"],
                    "trend_label": trend_info["trend_label"],
                    "is_sampled": False,
                    "provenance": {
                        "definition_version": "1.0",
                        "source_type": "dataframe",
                        "calculated_at": datetime.now(timezone.utc).isoformat(),
                        "total_rows_evaluated": len(df),
                        "is_sampled": False,
                        "sample_ratio": 1.0,
                    }
                })
            except Exception:
                continue

    return kpis


class AutoMLPipeline:
    """
    AutoML Pipeline wrapper providing structured configuration (TrainingSpecification),
    honest KPI generation, and model training interfaces.
    """
    def __init__(self, spec: Optional[TrainingSpecification] = None):
        self.spec = spec or TrainingSpecification()

    def _generate_kpis(
        self,
        df: pd.DataFrame,
        profile: dict,
        source_type: str = "database",
        strategy: Optional[dict] = None
    ) -> list[dict]:
        strat = strategy or {}
        if not strat.get("kpi_columns"):
            numeric_cols = [c for c, info in profile.get("columns", {}).items() if info.get("type") == "numeric"]
            if not numeric_cols:
                numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            strat["kpi_columns"] = [{"column": c, "aggregation": "sum"} for c in numeric_cols]
        return compute_kpis(df, strat, profile)


# === MASTER PIPELINE ===

def run_full_pipeline(
    file_path: str,
    file_type: str,
    template_type: str = None
) -> dict:
    """
    Master function — runs all 6 layers.
    Layers 2,3,5 run Gemini/Groq.
    Layers 1,4,6 run pure pandas (fast).
    ML runs in parallel via asyncio.to_thread.
    """
    # Load file
    try:
        if file_type.lower() in ["csv"]:
            df = pd.read_csv(file_path, skip_blank_lines=True)
        elif file_type.lower() in ["xlsx","xls","excel"]:
            df = pd.read_excel(file_path)
        else:
            return {"success": False, "error": f"Unsupported: {file_type}"}
        
        if df.empty:
            return {"success": False, "error": "Uploaded file is empty."}
            
        # Clean data before profiling & analysis
        df, cleaning_report = clean_dataframe(df)

        if df.empty:
            return {"success": False, "error": "After removing empty/invalid rows, no usable data remained."}

        total_rows_full = len(df)
        original_row_count = total_rows_full

        # Exact aggregates (KPIs, profiling stats) MUST be computed over full dataset (NR-2.1-A-T03)
        full_df = df

        # Sampling is strictly for high-volume chart payloads (NR-2.1-A-T03)
        is_sampled_charts = len(df) > 5000
        chart_df = df.sample(5000, random_state=42) if is_sampled_charts else df

        df_stats = {
            "total_rows": total_rows_full,
            "original_row_count": original_row_count,
            "total_columns": len(df.columns),
            "columns": list(df.columns),
            "cleaning_report": cleaning_report,
            "is_sampled": False,
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}
    
    # ── LAYER 1: Profile (fast, always first) ──
    print("[Pipeline] Layer 1: Profiling...")
    profile = deep_profile(full_df)
    
    # ── LAYER 2 & ML Detection (Parallelized for speed) ──
    print("[Pipeline] Layer 2 & ML Problem Detection (Parallel)...")
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_strategy = executor.submit(ai_domain_strategy, profile)
        future_problem = executor.submit(detect_problem_type, full_df)
        strategy = future_strategy.result()
        problem_info = future_problem.result()
    
    # ── LAYER 3: Chart Plan (Gemini) ──
    print("[Pipeline] Layer 3: Chart planning...")
    chart_specs = ai_chart_planner(profile, strategy)
    
    # ── LAYER 4: Compute Data (fast) ──
    print("[Pipeline] Layer 4: Computing chart data...")
    computed_charts = compute_chart_data(chart_df, chart_specs, profile)
    for c in computed_charts:
        if isinstance(c, dict):
            c["is_sampled"] = is_sampled_charts
            c["sample_size"] = len(chart_df)
            c["total_rows"] = total_rows_full
    
    # ── LAYER 5 & LAYER 6: Insights & KPIs (Parallelized) ──
    print("[Pipeline] Layer 5 & 6: Insights & KPIs (Parallel)...")
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_insights = executor.submit(ai_generate_insights, profile, strategy, computed_charts)
        future_kpis = executor.submit(compute_kpis, full_df, strategy, profile)
        insights = future_insights.result()
        kpis = future_kpis.result()
    
    # ── ML Pipeline (optimized for speed & leak-free NR-2.1-B) ──
    print("[Pipeline] ML: Training models...")
    try:
        if problem_info and problem_info.get("feature_columns"):
            train_df = full_df if len(full_df) <= 5000 else full_df.sample(5000, random_state=42)
            ml_results = run_automl_pipeline(train_df, problem_info)
        else:
            ml_results = None
    except Exception as e:
        print(f"[Pipeline] ML failed: {e}")
        ml_results = None
    
    print("[Pipeline] Complete!")
    
    return {
        "success": True,
        "df_stats": {
            **df_stats,
            "column_stats": profile["columns"],
            "correlations": profile["correlations"],
            "sample_rows": profile["sample_rows"]
        },
        "profile": profile,
        "strategy": strategy,
        "charts": computed_charts,
        "key_metrics": kpis,
        "ml_insights": {
            "key_findings": [i["text"] for i in insights],
            "insights_full": insights
        },
        "automl_results": ml_results,
        "problem_info": problem_info if ml_results else None,
        "recommended_templates": [
            {"template": strategy.get("domain","general"), "match_score": 95}
        ]
    }

def background_run_automl(dataset_id: str, file_path: str, file_type: str):
    """Fallback handler for backward compatibility if background cache starts up."""
    pass
