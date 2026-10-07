"""
Files & Dataset Management Router for CSV/Excel Analytics.
Handles dataset uploads, metadata profiling, row querying, and dataset listing.
"""
import os
import shutil
import math
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import pandas as pd
import json

import models
import schemas
from database import get_db
from dependencies import get_current_user

router = APIRouter(prefix="/api/files", tags=["CSV Files"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _clean_json_val(val: Any) -> Any:
    """Sanitize float values for clean JSON output."""
    if val is None or pd.isna(val):
        return None
    if isinstance(val, (float, int)):
        if math.isnan(val) or math.isinf(val):
            return None
    return val


@router.post("/upload-dataset")
async def upload_dataset(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload and profile a CSV or Excel dataset for analytics."""
    if not current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant context required.")

    filename = file.filename or "uploaded_data.csv"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in [".csv", ".xlsx", ".xls"]:
        raise HTTPException(status_code=400, detail="Only CSV and Excel (.xlsx, .xls) files are supported.")

    file_type = "csv" if ext == ".csv" else "excel"
    safe_filename = f"{current_user.tenant_id}_{int(os.times().elapsed * 1000)}_{filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size_bytes = os.path.getsize(file_path)
    file_size_str = (
        f"{file_size_bytes / (1024 * 1024):.1f} MB"
        if file_size_bytes >= 1024 * 1024
        else f"{max(1, file_size_bytes // 1024)} KB"
    )

    # Read dataset with pandas
    try:
        if file_type == "csv":
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")

    row_count = len(df)
    columns = list(df.columns)

    dataset = models.Dataset(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        name=filename,
        file_type=file_type,
        file_path=file_path,
        file_size=file_size_str,
        columns=columns,
        row_count=row_count,
        indexing_status="ready"
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    return {
        "id": dataset.id,
        "name": dataset.name,
        "file_type": dataset.file_type,
        "file_size": dataset.file_size,
        "row_count": dataset.row_count,
        "columns": dataset.columns,
        "created_at": dataset.created_at.isoformat() if dataset.created_at else None,
        "message": "Dataset uploaded successfully"
    }


@router.get("/datasets")
def list_datasets(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all uploaded datasets for the current tenant."""
    if not current_user.tenant_id:
        return []

    datasets = (
        db.query(models.Dataset)
        .filter(models.Dataset.tenant_id == current_user.tenant_id)
        .order_by(models.Dataset.created_at.desc())
        .all()
    )

    return [
        {
            "id": d.id,
            "name": d.name,
            "file_type": d.file_type,
            "file_size": d.file_size,
            "row_count": d.row_count,
            "columns": d.columns,
            "indexing_status": d.indexing_status,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in datasets
    ]


@router.get("/{dataset_id}/data")
def get_dataset_rows(
    dataset_id: int,
    limit: int = Query(500, le=2000),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve raw rows from the uploaded dataset."""
    dataset = (
        db.query(models.Dataset)
        .filter(
            models.Dataset.id == dataset_id,
            models.Dataset.tenant_id == current_user.tenant_id
        )
        .first()
    )
    if not dataset or not os.path.exists(dataset.file_path):
        raise HTTPException(status_code=404, detail="Dataset not found.")

    try:
        if dataset.file_type == "csv":
            df = pd.read_csv(dataset.file_path, nrows=limit)
        else:
            df = pd.read_excel(dataset.file_path, nrows=limit)
        
        records = df.to_dict(orient="records")
        clean_records = []
        for row in records:
            clean_row = {}
            for k, v in row.items():
                if v is None or pd.isna(v):
                    clean_row[k] = None
                elif isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                    clean_row[k] = None
                else:
                    clean_row[k] = v
            clean_records.append(clean_row)
        return clean_records
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read dataset rows: {str(e)}")


@router.get("/datasets/{dataset_id}")
def get_dataset(
    dataset_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get single dataset details."""
    dataset = (
        db.query(models.Dataset)
        .filter(
            models.Dataset.id == dataset_id,
            models.Dataset.tenant_id == current_user.tenant_id
        )
        .first()
    )
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    return {
        "id": dataset.id,
        "name": dataset.name,
        "file_type": dataset.file_type,
        "file_size": dataset.file_size,
        "row_count": dataset.row_count,
        "columns": dataset.columns,
        "created_at": dataset.created_at.isoformat() if dataset.created_at else None,
    }


@router.delete("/datasets/{dataset_id}")
def delete_dataset(
    dataset_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a dataset and its physical file."""
    dataset = (
        db.query(models.Dataset)
        .filter(
            models.Dataset.id == dataset_id,
            models.Dataset.tenant_id == current_user.tenant_id
        )
        .first()
    )
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    if os.path.exists(dataset.file_path):
        try:
            os.remove(dataset.file_path)
        except Exception:
            pass

    db.delete(dataset)
    db.commit()
    return {"message": "Dataset deleted successfully."}


TEMPLATE_SLOTS = {
    "ecommerce_sales": ["month_col", "city_col", "product_col", "revenue_col", "units_col", "status_col"],
    "hr_analytics": ["department_col", "gender_col", "education_col", "salary_col", "performance_col", "tenure_col", "attrition_col"],
    "financial_performance": ["quarter_col", "region_col", "category_col", "amount_col", "budget_col", "variance_col", "growth_col"],
    "marketing_analytics": ["channel_col", "campaign_col", "month_col", "impressions_col", "clicks_col", "ctr_col", "conversions_col", "roi_col"],
    "supply_chain": ["supplier_col", "category_col", "status_col", "month_col", "quantity_col", "lead_time_col", "cost_col", "on_time_col"],
    "customer_analytics": ["segment_col", "region_col", "status_col", "month_col", "customers_col", "ltv_col", "retention_col", "nps_col"],
    "manufacturing_kpis": ["machine_col", "shift_col", "factory_col", "month_col", "units_col", "defect_rate_col", "efficiency_col", "downtime_col"]
}

SLOT_KEYWORDS = {
    "month_col": ["month", "date", "created_at", "order_date", "timestamp", "year", "period"],
    "revenue_col": ["revenue", "sales", "amount", "total", "price", "total_amount", "gross_sales", "income"],
    "units_col": ["units", "quantity", "qty", "count", "items", "units_sold", "volume"],
    "product_col": ["product", "item", "title", "sku", "product_name", "category", "item_name"],
    "city_col": ["city", "location", "region", "state", "country", "territory", "store_location"],
    "status_col": ["status", "order_status", "delivery_status", "fulfillment_status", "condition"],
    "department_col": ["department", "dept", "division", "team", "business_unit"],
    "gender_col": ["gender", "sex"],
    "education_col": ["education", "degree", "qualification"],
    "salary_col": ["salary", "compensation", "wage", "pay", "rate"],
    "performance_col": ["performance", "rating", "score", "evaluation"],
    "tenure_col": ["tenure", "years", "experience", "months"],
    "attrition_col": ["attrition", "left", "turnover", "terminated", "active"],
    "quarter_col": ["quarter", "qtr", "period", "fiscal_quarter"],
    "region_col": ["region", "territory", "area", "market", "zone"],
    "category_col": ["category", "type", "classification", "segment", "group"],
    "amount_col": ["amount", "value", "cost", "total", "spend"],
    "budget_col": ["budget", "target", "allocated", "forecast"],
    "variance_col": ["variance", "diff", "difference", "delta"],
    "growth_col": ["growth", "growth_rate", "pct_change", "yoy"],
    "channel_col": ["channel", "medium", "source", "platform"],
    "campaign_col": ["campaign", "ad_campaign", "initiative", "promotion"],
    "impressions_col": ["impressions", "views", "reach"],
    "clicks_col": ["clicks", "traffic", "visits"],
    "ctr_col": ["ctr", "click_through_rate"],
    "conversions_col": ["conversions", "leads", "signups", "orders"],
    "roi_col": ["roi", "roas", "return"],
    "supplier_col": ["supplier", "vendor", "partner"],
    "lead_time_col": ["lead_time", "delivery_days", "wait_time"],
    "cost_col": ["cost", "expense", "cogs", "unit_cost"],
    "on_time_col": ["on_time", "punctual", "ontime_delivery"],
    "segment_col": ["segment", "tier", "cluster"],
    "customers_col": ["customer", "clients", "users", "account_id"],
    "ltv_col": ["ltv", "customer_ltv", "lifetime_value"],
    "retention_col": ["retention", "churn", "churn_rate"],
    "nps_col": ["nps", "satisfaction", "csat"],
    "machine_col": ["machine", "equipment", "asset", "device"],
    "shift_col": ["shift", "working_shift", "batch"],
    "factory_col": ["factory", "plant", "site", "facility"],
    "defect_rate_col": ["defect", "defect_rate", "errors", "scrap_rate"],
    "efficiency_col": ["efficiency", "oee", "productivity"],
    "downtime_col": ["downtime", "idle_time", "breakdown_hours"]
}


@router.post("/analyze-for-template", response_model=schemas.TemplateAnalysisResponse)
def analyze_for_template(
    request: schemas.TemplateAnalysisRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Analyze a dataset to map columns to template slots (e.g. e-commerce, hr, etc.)."""
    dataset = (
        db.query(models.Dataset)
        .filter(
            models.Dataset.id == request.dataset_id,
            models.Dataset.tenant_id == current_user.tenant_id
        )
        .first()
    )
    if not dataset or not os.path.exists(dataset.file_path):
        raise HTTPException(status_code=404, detail="Dataset not found")

    try:
        if dataset.file_type == "csv":
            try:
                df = pd.read_csv(dataset.file_path, encoding='utf-8', encoding_errors='replace')
            except Exception:
                df = pd.read_csv(dataset.file_path, encoding='latin-1')
        else:
            df = pd.read_excel(dataset.file_path)

        columns_list = [str(col).strip() for col in df.columns.tolist()]
        column_info = []
        for col in df.columns:
            dtype = str(df[col].dtype)
            col_type = "numeric" if "int" in dtype or "float" in dtype else "categorical"
            if "date" in str(col).lower() or "time" in str(col).lower():
                col_type = "date"

            sample_vals = [str(s)[:50] for s in df[col].dropna().head(3).tolist()]
            column_info.append({
                "name": str(col),
                "type": col_type,
                "null_count": int(df[col].isnull().sum()),
                "unique_count": int(df[col].nunique()),
                "sample": sample_vals
            })

        template_type = request.template_type
        slots = TEMPLATE_SLOTS.get(template_type, [])
        if not slots:
            raise HTTPException(status_code=400, detail=f"Invalid template type: {template_type}")

        mapping = {}
        assigned_cols = set()

        # Step 1: keyword-based slot matching
        for slot in slots:
            keywords = SLOT_KEYWORDS.get(slot, [slot.replace("_col", "")])
            best_match = None
            best_score = 0
            for col in columns_list:
                if col in assigned_cols:
                    continue
                col_lower = col.lower()
                for kw in keywords:
                    if kw in col_lower:
                        score = len(kw) / max(len(col_lower), 1)
                        if score > best_score:
                            best_score = score
                            best_match = col
            if best_match:
                mapping[slot] = best_match
                assigned_cols.add(best_match)
            else:
                mapping[slot] = None

        confidence = sum(1 for v in mapping.values() if v is not None) / max(len(slots), 1)
        processing_summary = {
            "row_count": len(df),
            "column_count": len(columns_list),
            "null_handling": sum(c['null_count'] for c in column_info),
            "confidence": round(confidence, 2),
            "notes": f"Auto-mapped {len(assigned_cols)} of {len(slots)} slots for template {template_type}."
        }

        return {
            "mapping": mapping,
            "column_info": column_info,
            "processing_summary": processing_summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze template: {str(e)}")


@router.get("/datasets/{dataset_id}/download")
def download_dataset(
    dataset_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download the original or converted dataset file."""
    dataset = (
        db.query(models.Dataset)
        .filter(
            models.Dataset.id == dataset_id,
            models.Dataset.tenant_id == current_user.tenant_id
        )
        .first()
    )
    if not dataset or not os.path.exists(dataset.file_path):
        raise HTTPException(status_code=404, detail="Dataset not found on disk")

    return FileResponse(
        path=dataset.file_path,
        filename=dataset.name,
        media_type="application/octet-stream"
    )


@router.get("/datasets/{dataset_id}/analysis")
def get_dataset_analysis(
    dataset_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get stored analysis profile for a dataset."""
    dataset = (
        db.query(models.Dataset)
        .filter(
            models.Dataset.id == dataset_id,
            models.Dataset.tenant_id == current_user.tenant_id
        )
        .first()
    )
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    return {
        "dataset_id": dataset.id,
        "name": dataset.name,
        "summary": dataset.summary,
        "indexing_status": dataset.indexing_status,
        "row_count": dataset.row_count,
        "columns": dataset.columns
    }
