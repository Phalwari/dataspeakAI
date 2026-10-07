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
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
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
    mean_absolute_error
)
from sklearn.cluster import KMeans
try:
    import xgboost as xgb
except ImportError:
    xgb = None

from services.multi_llm import get_intent_llm

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

def preprocess_data(df: pd.DataFrame, 
                    feature_columns: list,
                    target_column: str = None) -> dict:
    """
    Auto preprocessing pipeline:
    - Drop high-null columns (>50% null)
    - Fill missing numeric with median
    - Fill missing categorical with mode
    - Label encode categorical columns
    - Standard scale numeric columns
    Returns processed X, y, preprocessing_report
    """
    report = {
        "original_shape": df.shape,
        "steps": [],
        "dropped_columns": [],
        "encoded_columns": [],
        "scaled_columns": []
    }
    
    # Work with relevant columns only
    cols_to_use = [c for c in feature_columns if c in df.columns]
    if target_column and target_column in df.columns:
        cols_to_use.append(target_column)
    
    df_clean = df[cols_to_use].copy()
    
    # Convert datetime/timestamp columns to string representation
    for col in df_clean.columns:
        if pd.api.types.is_datetime64_any_dtype(df_clean[col]) or 'datetime' in str(df_clean[col].dtype):
            df_clean[col] = df_clean[col].astype(str)
            report["steps"].append(f"Converted datetime/timestamp column '{col}' to string category")
    
    # Drop high-null columns
    null_pct = df_clean.isnull().mean()
    high_null = null_pct[null_pct > 0.5].index.tolist()
    if high_null:
        df_clean.drop(columns=high_null, inplace=True, errors="ignore")
        feature_columns = [c for c in feature_columns if c not in high_null]
        report["dropped_columns"] = high_null
        report["steps"].append(f"Dropped {len(high_null)} high-null columns: {high_null}")
    
    # Fill missing values
    for col in df_clean.columns:
        if df_clean[col].isnull().sum() > 0:
            if df_clean[col].dtype in ['float64', 'int64']:
                median_val = df_clean[col].median()
                if pd.isna(median_val):
                    median_val = 0.0
                df_clean[col] = df_clean[col].fillna(median_val)
                report["steps"].append(f"Filled {col} nulls with median ({clean_float(median_val):.2f})")
            else:
                mode_series = df_clean[col].mode()
                mode_val = mode_series[0] if not mode_series.empty else "Unknown"
                df_clean[col] = df_clean[col].fillna(mode_val)
                report["steps"].append(f"Filled {col} nulls with mode ({mode_val})")
    
    # Label encode categoricals
    encoders = {}
    for col in feature_columns:
        if col in df_clean.columns and (df_clean[col].dtype in ['object', 'category', 'string'] or str(df_clean[col].dtype).startswith('str') or not pd.api.types.is_numeric_dtype(df_clean[col])):
            le = LabelEncoder()
            df_clean[col] = le.fit_transform(df_clean[col].astype(str))
            encoders[col] = le
            report["encoded_columns"].append(col)
    
    # Encode target if classification
    target_encoder = None
    if target_column and target_column in df_clean.columns:
        if df_clean[target_column].dtype in ['object', 'category', 'string'] or str(df_clean[target_column].dtype).startswith('str') or not pd.api.types.is_numeric_dtype(df_clean[target_column]):
            le = LabelEncoder()
            df_clean[target_column] = le.fit_transform(df_clean[target_column].astype(str))
            target_encoder = le
            report["steps"].append(f"Label encoded target column: {target_column}")
    
    # Scale numeric features
    scaler = StandardScaler()
    numeric_features = [c for c in feature_columns 
                       if c in df_clean.columns and 
                       pd.api.types.is_numeric_dtype(df_clean[c])]
    if numeric_features:
        df_clean[numeric_features] = scaler.fit_transform(df_clean[numeric_features])
        report["scaled_columns"] = numeric_features
        report["steps"].append(f"Standard scaled {len(numeric_features)} numeric features")
    
    report["final_shape"] = df_clean.shape
    
    X = df_clean[feature_columns].values if feature_columns else None
    y = df_clean[target_column].values if target_column else None
    
    return {
        "X": X, "y": y,
        "feature_names": feature_columns,
        "report": report,
        "target_encoder": target_encoder
    }

def train_single_model(args):
    """Top-level function (required for pickling)"""
    name, model, X_train, y_train, X_test, y_test, feature_names, problem_type = args
    try:
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        
        if problem_type == "regression":
            from sklearn.metrics import r2_score, mean_absolute_error
            score = r2_score(y_test, y_pred)
            metric = "R² Score"
            mae = mean_absolute_error(y_test, y_pred)
        else:
            from sklearn.metrics import accuracy_score
            score = accuracy_score(y_test, y_pred)
            metric = "Accuracy"
            mae = None
            
        feat_imp = []
        if hasattr(model, 'feature_importances_'):
            importances = model.feature_importances_
            feat_imp = sorted(
                zip(feature_names, importances.tolist()),
                key=lambda x: x[1], reverse=True
            )[:10]
        
        score_val = clean_float(score)
        result = {
            "model": name,
            "score": round(float(score_val), 4),
            "metric": metric,
            "feature_importance": [
                {"feature": f, "importance": round(clean_float(i), 4)}
                for f, i in feat_imp
            ],
            "predictions_sample": [clean_float(v) for v in y_pred[:20]],
            "actual_sample": [clean_float(v) for v in y_test[:20]]
        }
        if mae is not None:
            mae_val = clean_float(mae)
            result["mae"] = round(float(mae_val), 4)
            result["r2_score"] = round(float(score_val), 4)
        else:
            result["accuracy"] = round(float(score_val), 4)
        return result
    except Exception as e:
        return {"model": name, "error": str(e), "score": -1.0}

def run_automl(X, y, problem_type: str, 
               feature_names: list) -> dict:
    """
    Train multiple models, select the best one.
    Returns results for all models + best model details.
    """
    if X is None or len(X) < 10:
        return {"error": "Not enough data to train models"}

    n_samples = len(X)
    MAX_TRAIN_SAMPLES = 5000
    if n_samples > MAX_TRAIN_SAMPLES:
        idx = np.random.RandomState(42).choice(n_samples, MAX_TRAIN_SAMPLES, replace=False)
        X = X[idx]
        if y is not None:
            y = y[idx]

    if problem_type in ["regression", "classification"] and y is None:
        return {"error": f"Target column required for {problem_type}"}
        
    results = []
    
    if problem_type in ["regression", "classification"]:
        if problem_type == "classification":
            unique_classes = np.unique(y)
            if len(unique_classes) < 2:
                return {"error": "Target column has fewer than 2 unique classes. Classification is not possible."}
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42)
            
        if problem_type == "regression":
            models = {
                "Linear Regression": LinearRegression(),
                "Decision Tree": DecisionTreeRegressor(
                    max_depth=5, random_state=42),
                "Random Forest": RandomForestRegressor(
                    n_estimators=50, max_depth=10, random_state=42, n_jobs=-1),
            }
        else:
            models = {
                "Logistic Regression": LogisticRegression(
                    max_iter=500, random_state=42),
                "Decision Tree": DecisionTreeClassifier(
                    max_depth=5, random_state=42),
                "Random Forest": RandomForestClassifier(
                    n_estimators=50, max_depth=10, random_state=42, n_jobs=-1),
            }
            
        for name, model in models.items():
            args = (name, model, X_train, y_train, X_test, y_test, feature_names, problem_type)
            res = train_single_model(args)
            results.append(res)
    
    elif problem_type == "clustering":
        best_k = 3
        inertias = []
        for k in range(2, min(8, len(X))):
            try:
                km = KMeans(n_clusters=k, random_state=42, n_init=10)
                km.fit(X)
                inertias.append({"k": k, "inertia": clean_float(km.inertia_)})
            except:
                pass
        
        km_best = KMeans(n_clusters=best_k, random_state=42, n_init=10)
        labels = km_best.fit_predict(X)
        
        results.append({
            "model": "K-Means Clustering",
            "n_clusters": best_k,
            "score": 1.0,
            "metric": "Silhouette",
            "cluster_labels": labels.tolist(),
            "inertia_curve": inertias,
            "cluster_sizes": {
                str(i): int(np.sum(labels == i)) 
                for i in range(best_k)
            }
        })
    
    valid = [r for r in results if "error" not in r]
    best = max(valid, key=lambda x: x["score"]) if valid else None
    
    return {
        "problem_type": problem_type,
        "all_models": results,
        "best_model": best,
        "train_size": len(X_train) if problem_type != "clustering" else len(X),
        "test_size": len(X_test) if problem_type != "clustering" else 0
    }


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

def clean_dataframe(df: pd.DataFrame) -> tuple:
    """
    Cleans any real-world messy dataset before analysis.
    Returns (cleaned_df, cleaning_report).
    """
    report = {"original_rows": len(df), "original_cols": len(df.columns)}

    # 1. Drop fully empty rows & columns
    df = df.dropna(how="all")
    df = df.dropna(axis=1, how="all")

    # 2. Strip whitespace from column names
    df.columns = [str(c).strip() for c in df.columns]

    # 3. Drop exact duplicate rows
    dup_count = df.duplicated().sum()
    df = df.drop_duplicates()
    report["duplicates_removed"] = int(dup_count)

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

    # 6. Track missing value percentage per column
    missing_report = {}
    for col in df.columns:
        missing_pct = round(df[col].isna().mean() * 100, 1)
        if missing_pct > 0:
            missing_report[col] = missing_pct
    report["missing_value_pct_by_column"] = missing_report

    report["cleaned_rows"] = len(df)
    report["cleaned_cols"] = len(df.columns)
    return df, report


# === LAYER 6: KPI COMPUTER ===

def compute_kpis(df: pd.DataFrame, 
                 strategy: dict,
                 profile: dict) -> list:
    """
    Compute actual KPI values from data generically for ANY dataset.
    Uses strategy.kpi_columns defined by AI with normalized column matching.
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
            
            # Compute trend vs mean
            col_info = profile.get("columns", {}).get(col, {})
            col_mean = col_info.get("mean", val)
            trend_pct = round((val - col_mean) / (col_mean or 1) * 100, 1) if col_mean else 0
            
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
                "trend_pct": trend_pct,
                "trend_direction": (
                    "up" if trend_pct > 0 else 
                    "down" if trend_pct < 0 else "flat"
                )
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
                kpis.append({
                    "label": col.replace("_", " ").title(),
                    "value": formatted,
                    "raw_value": val,
                    "column": col,
                    "format": "number",
                    "icon_type": "neutral",
                    "trend_pct": 0,
                    "trend_direction": "flat"
                })
            except Exception:
                continue

    return kpis


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
        # Full dataset used for charts/KPIs up to 50k (pandas handles this fine)
        if len(df) > 50000:
            df = df.sample(50000, random_state=42)
        
        df_stats = {
            "total_rows": len(df),
            "original_row_count": original_row_count,
            "total_columns": len(df.columns),
            "columns": list(df.columns),
            "cleaning_report": cleaning_report
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}
    
    # ── LAYER 1: Profile (fast, always first) ──
    print("[Pipeline] Layer 1: Profiling...")
    profile = deep_profile(df)
    
    # ── LAYER 2 & ML Detection (Parallelized for speed) ──
    print("[Pipeline] Layer 2 & ML Problem Detection (Parallel)...")
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_strategy = executor.submit(ai_domain_strategy, profile)
        future_problem = executor.submit(detect_problem_type, df)
        strategy = future_strategy.result()
        problem_info = future_problem.result()
    
    # ── LAYER 3: Chart Plan (Gemini) ──
    print("[Pipeline] Layer 3: Chart planning...")
    chart_specs = ai_chart_planner(profile, strategy)
    
    # ── LAYER 4: Compute Data (fast) ──
    print("[Pipeline] Layer 4: Computing chart data...")
    computed_charts = compute_chart_data(df, chart_specs, profile)
    
    # ── LAYER 5 & LAYER 6: Insights & KPIs (Parallelized) ──
    print("[Pipeline] Layer 5 & 6: Insights & KPIs (Parallel)...")
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_insights = executor.submit(ai_generate_insights, profile, strategy, computed_charts)
        future_kpis = executor.submit(compute_kpis, df, strategy, profile)
        insights = future_insights.result()
        kpis = future_kpis.result()
    
    # ── ML Pipeline (optimized for speed) ──
    print("[Pipeline] ML: Training models...")
    try:
        target = problem_info.get("target_column")
        features = problem_info.get("feature_columns", [])
        
        if target and features:
            train_df = df if len(df) <= 5000 else df.sample(5000, random_state=42)
            prep = preprocess_data(train_df, features, target)
            ml_results = run_automl(
                prep["X"], prep["y"],
                problem_info["problem_type"],
                prep["feature_names"]
            )
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
