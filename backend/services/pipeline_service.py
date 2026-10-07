import pandas as pd
import numpy as np
from datetime import datetime
from sqlalchemy.orm import Session
from models import Dataset, Document
from typing import Any
import os

def update_dataset_status(db: Session, dataset_id: str, status: str):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if dataset:
        dataset.indexing_status = status
        db.commit()
        return
    
    # Also check Document model for PDF/DOC/DOCX uploads
    document = db.query(Document).filter(Document.id == dataset_id).first()
    if document:
        document.status = status
        db.commit()

async def process_file_pipeline(db: Session, dataset_id: str, file_path: str, file_type: str, user_id: str):
    """
    Full ML pipeline runs automatically after upload
    Steps: Load → Clean → EDA → Cluster → Anomaly → Save
    """
    try:
        # Update status to processing
        update_dataset_status(db, dataset_id, "processing")
        
        # STEP 1: LOAD DATA
        if file_type not in ['csv', 'xlsx', 'xls']:
            # Skip ML pipeline for PDFs and JSONs, just do RAG indexing
            try:
                from services.rag_service import index_file
                index_file(db, dataset_id, user_id, file_path, file_type)
                update_dataset_status(db, dataset_id, "ready")
                print(f"✅ RAG Pipeline complete for {file_type} dataset {dataset_id}")
            except Exception as e:
                print(f"RAG indexing error: {e}")
                update_dataset_status(db, dataset_id, "error")
            return
            
        if file_type == 'csv':
            try:
                df = pd.read_csv(file_path, encoding='utf-8', encoding_errors='replace')
            except:
                df = pd.read_csv(file_path, encoding='latin-1')
        else:
            df = pd.read_excel(file_path)
        
        original_shape = df.shape
        
        # STEP 2: PREPROCESSING
        # Remove null bytes from string columns
        for col in df.select_dtypes(include=['object', 'string']).columns:
            df[col] = df[col].astype(str).str.replace('\x00', '', regex=False)
        
        # Handle missing values
        null_counts = df.isnull().sum().to_dict()
        null_cols = {k: int(v) for k, v in null_counts.items() if v > 0}
        
        for col in df.columns:
            if df[col].dtype in ['int64', 'float64']:
                median_val = df[col].median()
                if not pd.isna(median_val):
                    df[col] = df[col].fillna(median_val)
                else:
                    df[col] = df[col].fillna(0)
            else:
                mode_res = df[col].mode()
                fill_val = mode_res[0] if len(mode_res) > 0 else 'Unknown'
                df[col] = df[col].fillna(fill_val)
        
        # Remove duplicates
        duplicates_removed = int(df.duplicated().sum())
        df = df.drop_duplicates()
        
        preprocessing_report = {
            "original_rows": original_shape[0],
            "original_cols": original_shape[1],
            "null_values_handled": null_cols,
            "duplicates_removed": duplicates_removed,
            "final_rows": len(df),
            "final_cols": len(df.columns)
        }
        
        # STEP 3: EDA
        numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'string']).columns.tolist()
        
        numeric_stats = {}
        for col in numeric_cols:
            numeric_stats[col] = {
                "mean": round(float(df[col].mean()), 2) if not pd.isna(df[col].mean()) else 0,
                "median": round(float(df[col].median()), 2) if not pd.isna(df[col].median()) else 0,
                "std": round(float(df[col].std()), 2) if not pd.isna(df[col].std()) else 0,
                "min": round(float(df[col].min()), 2) if not pd.isna(df[col].min()) else 0,
                "max": round(float(df[col].max()), 2) if not pd.isna(df[col].max()) else 0,
                "skewness": round(float(df[col].skew()), 3) if not pd.isna(df[col].skew()) else 0
            }
        
        categorical_stats = {}
        for col in categorical_cols:
            value_counts = df[col].value_counts()
            categorical_stats[col] = {
                "unique_count": int(df[col].nunique()),
                "top_values": value_counts.head(5).to_dict(),
                "missing_pct": round(float(df[col].isnull().sum() / len(df) * 100), 2)
            }
        
        correlations = []
        if len(numeric_cols) >= 2:
            corr_matrix = df[numeric_cols].corr()
            for i in range(len(numeric_cols)):
                for j in range(i+1, len(numeric_cols)):
                    val = corr_matrix.iloc[i, j]
                    if not pd.isna(val) and abs(val) > 0.5:
                        correlations.append({
                            "col1": numeric_cols[i],
                            "col2": numeric_cols[j],
                            "value": round(float(val), 3)
                        })
        
        eda_report = {
            "numeric_columns": numeric_cols,
            "categorical_columns": categorical_cols,
            "numeric_stats": numeric_stats,
            "categorical_stats": categorical_stats,
            "correlations": correlations,
            "total_rows": len(df),
            "total_cols": len(df.columns)
        }
        
        # STEP 4: CLUSTERING
        clustering_report = {}
        if len(numeric_cols) >= 2:
            from sklearn.cluster import KMeans
            from sklearn.preprocessing import StandardScaler
            
            # Use top 5 numeric cols
            target_cols = numeric_cols[:5]
            X = df[target_cols].copy()
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            n_clusters = min(3, len(df) // 10)
            n_clusters = max(2, n_clusters)
            
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            clusters = kmeans.fit_predict(X_scaled)
            
            cluster_summaries = []
            for i in range(n_clusters):
                mask = clusters == i
                cluster_df = df[mask]
                cluster_summaries.append({
                    "cluster_id": i,
                    "size": int(mask.sum()),
                    "percentage": round(float(mask.sum()) / len(df) * 100, 1),
                    "avg_values": {
                        col: round(float(cluster_df[col].mean()), 2) if not pd.isna(cluster_df[col].mean()) else 0
                        for col in target_cols
                    }
                })
            
            clustering_report = {
                "n_clusters": n_clusters,
                "columns_used": target_cols,
                "cluster_summaries": cluster_summaries
            }
        
        # STEP 5: ANOMALY DETECTION
        anomaly_report = {}
        if len(numeric_cols) >= 1:
            from sklearn.ensemble import IsolationForest
            
            X_anomaly = df[numeric_cols].fillna(df[numeric_cols].mean()).fillna(0)
            iso = IsolationForest(contamination=0.1, random_state=42)
            predictions = iso.fit_predict(X_anomaly)
            anomaly_indices = [int(i) for i, p in enumerate(predictions) if p == -1]
            
            anomaly_report = {
                "total_anomalies": len(anomaly_indices),
                "anomaly_percentage": round(float(len(anomaly_indices) / len(df) * 100), 1),
                "anomaly_rows": anomaly_indices[:20]
            }
        
        # STEP 6: RECOMMENDATIONS
        recommendations = []
        for col in numeric_cols:
            mean = df[col].mean()
            std = df[col].std()
            if not pd.isna(mean) and not pd.isna(std) and mean != 0 and std > abs(mean) * 2:
                recommendations.append({
                    "type": "high_variance",
                    "priority": "medium",
                    "column": col,
                    "message": f"{col} has high variance - check for outliers"
                })
            
            skew = df[col].skew()
            if not pd.isna(skew) and abs(skew) > 2:
                recommendations.append({
                    "type": "skewness",
                    "priority": "low",
                    "column": col,
                    "message": f"{col} is skewed ({round(float(skew), 2)}) - consider transformation"
                })
        
        for col in categorical_cols:
            if df[col].nunique() < 10:
                vc = df[col].value_counts()
                if len(vc) > 1:
                    ratio = vc.iloc[0] / vc.iloc[-1]
                    if ratio > 5:
                        recommendations.append({
                            "type": "imbalance",
                            "priority": "medium",
                            "column": col,
                            "message": f"{col} is imbalanced - '{vc.index[0]}' dominates"
                        })
        
        # STEP 7: SAVE ALL TO DATABASE
        analysis_results = {
            "preprocessing": preprocessing_report,
            "eda": eda_report,
            "clustering": clustering_report,
            "anomalies": anomaly_report,
            "recommendations": recommendations[:10],
            "processed_at": datetime.utcnow().isoformat()
        }
        
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if dataset:
            dataset.analysis_results = analysis_results
            dataset.indexing_status = "ready"
            db.commit()
            
        # Datasets are processed for analytics only.
        # RAG indexing is reserved for document uploads (PDF / DOCX) via /upload-document.
        print(f"✅ Pipeline complete for dataset {dataset_id}")
        
    except Exception as e:
        import traceback
        print(f"❌ Pipeline error: {e}")
        traceback.print_exc()
        update_dataset_status(db, dataset_id, "error")
