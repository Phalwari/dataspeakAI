"""
File Insights Router for CSV & Excel Dataset ML Analysis.
Provides AutoML pipeline execution, quick statistics, SSE streaming, and dataset chat.
Strictly enforces tenant isolation.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import asyncio
import json
import os
import jwt
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

import models
import auth
from database import get_db
from dependencies import get_current_user
from services.automl_service import run_full_pipeline, detect_problem_type
from services.redis_service import cache_get, cache_set, make_cache_key

router = APIRouter(prefix="/api/file-insights", tags=["File Insights"])


def _parse_dataset_id(file_id: str) -> int:
    try:
        return int(file_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid dataset ID format; expected integer ID.")


def _get_dataset_with_tenant(db: Session, file_id: str, tenant_id: int) -> models.Dataset:
    dataset_id = _parse_dataset_id(file_id)
    dataset = db.query(models.Dataset).filter(
        models.Dataset.id == dataset_id,
        models.Dataset.tenant_id == tenant_id
    ).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.get("/ml-analysis/{file_id}")
async def get_ml_analysis(
    file_id: str,
    template_type: Optional[str] = None,
    refresh: bool = False,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Run or fetch cached AutoML pipeline results for a dataset."""
    dataset = _get_dataset_with_tenant(db, file_id, current_user.tenant_id)

    # Check L1 Cache
    redis_key = make_cache_key("ml", str(current_user.tenant_id), str(dataset.id))
    if not refresh:
        redis_cached = cache_get(redis_key)
        if redis_cached:
            if not template_type or redis_cached.get("template_type") == template_type:
                return {**redis_cached, "cached": True, "cache_source": "redis"}

    # Check L2 Cache (DB) - 24 hours expiry
    use_cache = False
    if not refresh and dataset.ml_insights_cache and dataset.ml_insights_cached_at:
        age = datetime.utcnow() - dataset.ml_insights_cached_at
        if age < timedelta(hours=24):
            use_cache = True
            if template_type and dataset.ml_insights_cache.get("template_type") != template_type:
                use_cache = False

    if use_cache:
        cache_set(redis_key, dataset.ml_insights_cache, ttl_seconds=86400)
        return dataset.ml_insights_cache

    if not os.path.exists(dataset.file_path):
        raise HTTPException(status_code=404, detail="Underlying dataset file not found on disk.")

    pipeline_results = await asyncio.to_thread(
        run_full_pipeline, dataset.file_path, dataset.file_type, template_type
    )

    if not pipeline_results.get("success"):
        raise HTTPException(
            status_code=500,
            detail=f"AutoML pipeline failed: {pipeline_results.get('error', 'Unknown error')}"
        )

    try:
        pipeline_results["template_type"] = template_type
        clean_json_str = json.dumps(pipeline_results, default=str)
        clean_json_obj = json.loads(clean_json_str)

        cache_set(redis_key, clean_json_obj, ttl_seconds=86400)
        dataset.ml_insights_cache = clean_json_obj
        dataset.ml_insights_cached_at = datetime.utcnow()
        db.commit()
        return clean_json_obj
    except Exception as e:
        db.rollback()
        print(f"Failed to cache AutoML results: {e}")

    return pipeline_results


def _detect_domain(df, problem_info, template_type=None):
    try:
        from services.automl_service import (
            deep_profile, ai_domain_strategy, ai_chart_planner,
            compute_chart_data, compute_kpis
        )
        profile = deep_profile(df)
        strategy = ai_domain_strategy(profile)
        chart_specs = ai_chart_planner(profile, strategy)
        charts = compute_chart_data(df, chart_specs, profile)
        kpis = compute_kpis(df, strategy, profile)
        return {
            "charts": charts,
            "key_metrics": kpis,
            "detected_domain": strategy.get("domain", "general")
        }
    except Exception as e:
        print(f"[_detect_domain] Fallback: {e}")
        return {"charts": [], "key_metrics": [], "detected_domain": "general"}


@router.get("/quick-stats/{file_id}")
async def get_quick_stats(
    file_id: str,
    template_type: Optional[str] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Compute and return quick statistical profile, key KPIs, charts, and recommendations."""
    dataset = _get_dataset_with_tenant(db, file_id, current_user.tenant_id)

    redis_key = f"quick:{current_user.tenant_id}:{dataset.id}:{template_type}"
    redis_cached = cache_get(redis_key)
    if redis_cached:
        return {**redis_cached, "cached": True, "cache_source": "redis"}

    if not os.path.exists(dataset.file_path):
        raise HTTPException(status_code=404, detail="Dataset file not found on disk.")

    try:
        import pandas as pd
        file_path = dataset.file_path
        file_type = dataset.file_type.lower()
        if file_type in ["csv"]:
            df = pd.read_csv(file_path)
        elif file_type in ["xlsx", "xls", "excel"]:
            df = pd.read_excel(file_path)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_type}")

        if df.empty:
            raise HTTPException(status_code=400, detail="Uploaded dataset file is empty.")

        if len(df) > 10000:
            df = df.sample(10000, random_state=42)

        df_stats = {
            "total_rows": int(len(df)),
            "total_columns": int(len(df.columns)),
            "columns": list(df.columns),
            "memory_mb": round(float(df.memory_usage().sum()) / 1e6, 2)
        }

        try:
            problem_info = await asyncio.to_thread(detect_problem_type, df)
        except Exception as _pt_err:
            print(f"[quick-stats] detect_problem_type fallback ({_pt_err})")
            problem_info = {
                "problem_type": "regression",
                "target_column": None,
                "feature_columns": [],
                "business_question": "General exploration of data"
            }

        domain_res = _detect_domain(df, problem_info, template_type=None)
        charts = domain_res.get("charts", [])
        key_metrics = domain_res.get("key_metrics", [])
        detected_domain = domain_res.get("detected_domain", "general")

        # Business summary via Multi-LLM caller
        from services.multi_llm import get_intent_llm
        import re

        describe_str = df.describe(include='all').to_string()
        if len(describe_str) > 3000:
            describe_str = describe_str[:3000] + "\n...[truncated]"

        prompt = f"""You are a top-tier business intelligence and data analyst.
Analyze these dataset statistics for the domain: {template_type or detected_domain}.

Dataset Statistics:
- Columns: {list(df.columns)}
- Statistics Summary:
{describe_str}

Provide analysis in this EXACT JSON format:
{{
  "executive_summary": "2-3 sentence business summary of what the data indicates",
  "key_findings": [
    "Key finding 1 with realistic business numbers/percentages from the data",
    "Key finding 2 with realistic business numbers/percentages from the data",
    "Key finding 3 with realistic business numbers/percentages from the data"
  ],
  "business_recommendations": [
    {{
      "title": "Actionable recommendation title",
      "description": "Detailed strategic business action",
      "impact": "HIGH",
      "action": "Specific implementation step"
    }}
  ]
}}"""

        try:
            llm = get_intent_llm()
            response = llm.invoke(prompt)
            content = response.content.strip()
            content = re.sub(r"```json|```", "", content).strip()
            ml_insights = json.loads(content)
        except Exception as _llm_e:
            ml_insights = {
                "executive_summary": f"Dataset contains {len(df)} records across {len(df.columns)} dimensions with high analytical utility.",
                "key_findings": [
                    f"Analyzed {len(df)} rows across {len(df.columns)} feature columns.",
                    f"Primary detected domain profile: {detected_domain.replace('_', ' ').title()}."
                ],
                "business_recommendations": [
                    {
                        "title": "Leverage High-Coverage Dimensions",
                        "description": "Establish continuous automated segment tracking across high cardinality features.",
                        "impact": "HIGH",
                        "action": "Configure scheduled ingestion and threshold alerting."
                    }
                ]
            }

        def build_recommendations(df_cols):
            cols_lower = [str(c).lower() for c in df_cols]
            templates_kw = {
                "ecommerce":     ["revenue", "sales", "order", "product", "city", "customer", "payment", "price"],
                "manufacturing": ["defect", "machine", "shift", "efficiency", "downtime", "production"],
                "hr":            ["employee", "salary", "department", "attrition", "performance", "hire"],
                "financial":     ["revenue", "profit", "expense", "budget", "cost", "margin"],
                "marketing":     ["campaign", "impression", "click", "ctr", "conversion", "channel"],
                "supply_chain":  ["supplier", "inventory", "lead_time", "quantity", "shipment", "sku"]
            }
            recs = []
            for tmpl, kws in templates_kw.items():
                score = sum(1 for kw in kws if any(kw in c for c in cols_lower))
                pct = round((score / max(1, len(kws))) * 100)
                recs.append({"template": tmpl, "match_score": pct})
            recs.sort(key=lambda x: x["match_score"], reverse=True)
            return recs[:3]

        result = {
            "success": True,
            "df_stats": df_stats,
            "problem_info": problem_info,
            "detected_domain": detected_domain,
            "requested_template": template_type,
            "preprocessing_report": {
                "steps": ["Loaded dataset", "AI detected problem type", "Column-first domain detection", "Computed KPIs & charts"],
                "report": {}
            },
            "automl_results": None,
            "ml_insights": ml_insights,
            "charts": charts,
            "key_metrics": key_metrics,
            "predictions_sample": {
                "predicted": [],
                "actual": []
            },
            "recommended_templates": build_recommendations(list(df.columns))
        }

        cache_set(redis_key, result, ttl_seconds=86400)
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate quick stats: {str(e)}")


@router.get("/ml-analysis/{file_id}/stream")
async def stream_ml_analysis(
    file_id: str,
    request: Request,
    token: Optional[str] = Query(None),
    refresh: bool = False,
    db: Session = Depends(get_db)
):
    """Stream ML analysis progress via Server-Sent Events."""
    user = None
    auth_header = request.headers.get("Authorization")
    raw_token = token
    if not raw_token and auth_header and auth_header.startswith("Bearer "):
        raw_token = auth_header.split(" ")[1]

    if raw_token:
        try:
            payload = jwt.decode(raw_token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
            email = payload.get("sub")
            if email:
                user = db.query(models.User).filter(models.User.email == email).first()
        except Exception:
            user = None

    if not user:
        raise HTTPException(status_code=401, detail="Authentication required for SSE stream")

    dataset = _get_dataset_with_tenant(db, file_id, user.tenant_id)

    async def event_generator():
        try:
            redis_key = make_cache_key("ml", str(user.tenant_id), str(dataset.id))
            if not refresh:
                redis_cached = cache_get(redis_key)
                if redis_cached:
                    yield f"data: {json.dumps({'type': 'result', 'data': redis_cached, 'cached': True})}\n\n"
                    return

            if not refresh and dataset.ml_insights_cache and dataset.ml_insights_cached_at:
                age = datetime.utcnow() - dataset.ml_insights_cached_at
                if age < timedelta(hours=24):
                    cache_set(redis_key, dataset.ml_insights_cache, ttl_seconds=86400)
                    yield f"data: {json.dumps({'type': 'result', 'data': dataset.ml_insights_cache, 'cached': True})}\n\n"
                    return

            yield f"data: {json.dumps({'type': 'progress', 'message': 'Reading dataset structure...', 'step': 1, 'total': 6})}\n\n"
            await asyncio.sleep(0.05)

            yield f"data: {json.dumps({'type': 'progress', 'message': 'Detecting target & problem taxonomy...', 'step': 2, 'total': 6})}\n\n"
            await asyncio.sleep(0.05)

            yield f"data: {json.dumps({'type': 'progress', 'message': 'Training machine learning models & evaluating feature importance...', 'step': 3, 'total': 6})}\n\n"

            result = await asyncio.to_thread(run_full_pipeline, dataset.file_path, dataset.file_type)

            if result.get("success"):
                clean_json_str = json.dumps(result, default=str)
                clean_json_obj = json.loads(clean_json_str)
                cache_set(redis_key, clean_json_obj, ttl_seconds=86400)
                dataset.ml_insights_cache = clean_json_obj
                dataset.ml_insights_cached_at = datetime.utcnow()
                db.commit()
                yield f"data: {json.dumps({'type': 'result', 'data': clean_json_obj, 'cached': False})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'error', 'message': result.get('error', 'ML Ingestion pipeline failed.')})}\n\n"
        except Exception as e:
            print(f"[ML Stream Error] {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


class DatasetChatRequest(BaseModel):
    message: str
    chat_history: List[Dict[str, str]] = []


@router.post("/chat/{file_id}")
async def chat_with_dataset(
    file_id: str,
    payload: DatasetChatRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Chat with conversational AI about a specific dataset."""
    dataset = _get_dataset_with_tenant(db, file_id, current_user.tenant_id)

    import pandas as pd
    try:
        if dataset.file_type.lower() in ["csv"]:
            df = pd.read_csv(dataset.file_path)
        else:
            df = pd.read_excel(dataset.file_path)

        df_subset = df.head(100) if len(df) > 100 else df
        df_stats_str = (
            f"Columns: {list(df.columns)}\n"
            f"Shape: {df.shape}\n"
            f"Sample Rows:\n{json.dumps(df_subset.head(5).to_dict(orient='records'), indent=2, default=str)}"
        )
    except Exception as e:
        df_stats_str = f"Could not read dataset file content: {str(e)}"

    prompt = f"""You are DataSpeakAI Analyst, an executive AI assistant specialized in analyzing business datasets.
A user is chatting with you about their dataset '{dataset.name}'.

Dataset Summary:
{df_stats_str}

Chat History:
{json.dumps(payload.chat_history, indent=2)}

User Question: {payload.message}

Please analyze the user's question, inspect the dataset details, and provide a clear, concise, and professional answer:
- Answer in simple, direct language.
- Highlight specific insights, percentages, or numbers based on the columns/values.
- Recommend suitable charts if relevant.
- Do not make up facts; if you cannot answer from the dataset details, explain why.

Answer:"""

    try:
        from services.multi_llm import get_intent_llm
        llm = get_intent_llm()
        res = llm.invoke(prompt)
        return {"response": res.content.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Chat failed: {str(e)}")
