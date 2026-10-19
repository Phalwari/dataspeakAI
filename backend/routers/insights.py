"""
Database AI Insights Router (6-Layer Relational Analysis Engine)
Generates comprehensive executive playbooks, KPI recipes, smart charts, anomalies,
and multi-table relational insights.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse, HTMLResponse
from sqlalchemy.orm import Session, joinedload, selectinload
from typing import Optional, Dict, Any, List
import json
import html
import logging

import models
import schemas
from database import get_db
from dependencies import get_current_user
from services.db_pipeline_service import db_pipeline_service
from services.insights_engine import insights_engine

router = APIRouter(prefix="/api/insights", tags=["Database Insights"])
logger = logging.getLogger(__name__)


def _owned_connection(db: Session, connection_id: int, tenant_id: int) -> models.DatabaseConnection:
    connection = (
        db.query(models.DatabaseConnection)
        .filter(
            models.DatabaseConnection.id == connection_id,
            models.DatabaseConnection.tenant_id == tenant_id,
        )
        .first()
    )
    if not connection:
        raise HTTPException(status_code=404, detail="Database connection not found")
    return connection


# ── Phase 3: Dynamic AI Insights & Recommendation Engine ──────────────────

def _serialize_insight(insight: models.GeneratedInsight) -> schemas.GeneratedInsightItem:
    return schemas.GeneratedInsightItem(
        id=insight.id,
        tenant_id=insight.tenant_id,
        database_id=insight.database_id,
        database_name=insight.database.name if insight.database else None,
        title=insight.title,
        category=insight.category,
        severity=insight.severity,
        summary=insight.summary,
        impact_score=insight.impact_score,
        confidence_score=insight.confidence_score,
        status=insight.status,
        created_at=insight.created_at,
        recommendations=[
            schemas.RecommendationItem(
                id=rec.id,
                insight_id=rec.insight_id,
                action_step=rec.action_step,
                priority=rec.priority,
                action_type=rec.action_type,
                action_url=rec.action_url,
                status=rec.status,
            )
            for rec in insight.recommendations
        ]
    )


@router.get("", response_model=schemas.AIInsightsOverviewResponse)
@router.get("/", response_model=schemas.AIInsightsOverviewResponse)
def get_ai_insights(
    database_id: Optional[int] = Query(None, description="Optional database connection filter"),
    category: Optional[str] = Query(None, description="Category filter (All, Revenue, Performance, etc.)"),
    severity: Optional[str] = Query(None, description="Severity filter (critical, warning, alert, opportunity)"),
    status: Optional[str] = Query("active", description="Status filter (active, dismissed, all)"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves tenant-wide or database-scoped dynamic AI insights and recommendations.
    If no insights exist yet for the tenant, triggers initial synthesis.
    """
    if not current_user.tenant_id:
        raise HTTPException(status_code=403, detail="User must belong to a tenant.")

    tenant_id = current_user.tenant_id

    # Verify database ownership if scoped to prevent cross-tenant enumeration or leaks
    if database_id is not None:
        db_conn = db.query(models.DatabaseConnection).filter(
            models.DatabaseConnection.id == database_id,
            models.DatabaseConnection.tenant_id == tenant_id
        ).first()
        if not db_conn:
            raise HTTPException(status_code=404, detail="Database connection not found.")

    # Check if any insights exist for this tenant (scoped to database_id if provided)
    check_query = db.query(models.GeneratedInsight).filter(
        models.GeneratedInsight.tenant_id == tenant_id
    )
    if database_id is not None:
        check_query = check_query.filter(models.GeneratedInsight.database_id == database_id)

    # Opportunistically generate initial insights if empty and tenant has data
    if check_query.count() == 0:
        telemetry = insights_engine.collect_tenant_telemetry(tenant_id, database_id, db)
        if telemetry.get("has_data"):
            insights_engine.refresh_tenant_insights(tenant_id, database_id, db)

    # Base query for tenant
    base_query = db.query(models.GeneratedInsight).filter(
        models.GeneratedInsight.tenant_id == tenant_id
    )

    if database_id is not None:
        base_query = base_query.filter(
            (models.GeneratedInsight.database_id == database_id) | (models.GeneratedInsight.database_id.is_(None))
        )

    # Summary metrics across active insights
    active_insights = base_query.filter(models.GeneratedInsight.status == "active").all()
    total_active = len(active_insights)
    critical_count = sum(1 for i in active_insights if i.severity in ("critical", "warning"))
    opportunities_count = sum(1 for i in active_insights if i.severity == "opportunity")

    # Pending recommendations count
    active_insight_ids = [i.id for i in active_insights]
    pending_actions = 0
    if active_insight_ids:
        pending_actions = db.query(models.Recommendation).filter(
            models.Recommendation.insight_id.in_(active_insight_ids),
            models.Recommendation.status == "pending"
        ).count()

    summary_stats = schemas.AIInsightsSummaryStats(
        total_insights=total_active,
        critical_count=critical_count,
        opportunities_count=opportunities_count,
        pending_actions_count=pending_actions,
    )

    # Filtered query
    filtered_query = db.query(models.GeneratedInsight).filter(
        models.GeneratedInsight.tenant_id == tenant_id
    )
    if database_id is not None:
        filtered_query = filtered_query.filter(
            (models.GeneratedInsight.database_id == database_id) | (models.GeneratedInsight.database_id.is_(None))
        )

    if status and status.lower() != "all":
        filtered_query = filtered_query.filter(models.GeneratedInsight.status == status.lower())

    if category and category.lower() != "all":
        filtered_query = filtered_query.filter(models.GeneratedInsight.category.ilike(f"%{category}%"))

    if severity and severity.lower() != "all":
        filtered_query = filtered_query.filter(models.GeneratedInsight.severity == severity.lower())

    insights_records = (
        filtered_query
        .options(
            joinedload(models.GeneratedInsight.database),
            selectinload(models.GeneratedInsight.recommendations)
        )
        .order_by(models.GeneratedInsight.created_at.desc())
        .all()
    )

    # Check if tenant has any connected databases or query logs
    has_sources = (
        db.query(models.DatabaseConnection).filter(models.DatabaseConnection.tenant_id == tenant_id).count() > 0 or
        db.query(models.QueryLog).filter(models.QueryLog.tenant_id == tenant_id).count() > 0 or
        db.query(models.Document).filter(models.Document.tenant_id == tenant_id).count() > 0
    )

    return schemas.AIInsightsOverviewResponse(
        summary=summary_stats,
        insights=[_serialize_insight(i) for i in insights_records],
        available_categories=["All", "Revenue", "Performance", "Customer Success", "Operational"],
        has_connected_sources=has_sources,
    )


@router.post("/refresh", response_model=schemas.AIInsightsRefreshResponse)
def refresh_ai_insights(
    database_id: Optional[int] = Query(None, description="Optional database connection filter"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Triggers fresh synthesis of AI business insights and recommendations using Google Gemini 2.5 Flash
    (or deterministic fallback) based on real telemetry.
    """
    if not current_user.tenant_id:
        raise HTTPException(status_code=403, detail="User must belong to a tenant.")

    # Verify database ownership if scoped to prevent cross-tenant enumeration or leaks
    if database_id is not None:
        db_conn = db.query(models.DatabaseConnection).filter(
            models.DatabaseConnection.id == database_id,
            models.DatabaseConnection.tenant_id == current_user.tenant_id
        ).first()
        if not db_conn:
            raise HTTPException(status_code=404, detail="Database connection not found.")

    refreshed = insights_engine.refresh_tenant_insights(
        tenant_id=current_user.tenant_id,
        database_id=database_id,
        db=db,
    )

    return schemas.AIInsightsRefreshResponse(
        message="AI insights and recommendations successfully synthesized.",
        refreshed_count=len(refreshed),
        insights=[_serialize_insight(i) for i in refreshed],
    )


@router.put("/recommendations/{recommendation_id}/status", response_model=schemas.RecommendationItem)
def update_recommendation_status(
    recommendation_id: int,
    payload: schemas.RecommendationStatusUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Updates a recommendation's status (pending vs completed).
    Ensures strict tenant ownership verification via join with GeneratedInsight.
    """
    if not current_user.tenant_id:
        raise HTTPException(status_code=403, detail="User must belong to a tenant.")

    rec = (
        db.query(models.Recommendation)
        .join(models.GeneratedInsight)
        .filter(
            models.Recommendation.id == recommendation_id,
            models.GeneratedInsight.tenant_id == current_user.tenant_id
        )
        .first()
    )
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found.")

    valid_statuses = {"pending", "completed"}
    if payload.status.lower() not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {valid_statuses}")

    rec.status = payload.status.lower()
    db.commit()
    db.refresh(rec)

    return schemas.RecommendationItem.model_validate(rec)


@router.put("/{insight_id}/status", response_model=schemas.GeneratedInsightItem)
def update_insight_status(
    insight_id: int,
    payload: schemas.GeneratedInsightStatusUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Updates an insight's status (active vs dismissed vs actioned).
    Ensures strict tenant ownership verification.
    """
    if not current_user.tenant_id:
        raise HTTPException(status_code=403, detail="User must belong to a tenant.")

    insight = db.query(models.GeneratedInsight).filter(
        models.GeneratedInsight.id == insight_id,
        models.GeneratedInsight.tenant_id == current_user.tenant_id
    ).first()
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found.")

    valid_statuses = {"active", "dismissed", "actioned"}
    if payload.status.lower() not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {valid_statuses}")

    insight.status = payload.status.lower()
    db.commit()
    db.refresh(insight)

    return _serialize_insight(insight)


# ── Existing Database AI Insights Endpoints ────────────────────────────────


@router.get("/generate/{connection_id}")
def generate_database_insights(
    connection_id: int,
    table: Optional[str] = Query(None, description="Filter insights to a specific table"),
    refresh: bool = Query(False, description="Bypass cache and force re-generation"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate 6-Layer Enterprise Database AI Insights for a connected database.
    Produces executive summary, KPI metrics, charts, anomaly flags, and strategic playbook.
    """
    if not current_user.tenant_id:
        raise HTTPException(status_code=403, detail="User must belong to a tenant.")

    try:
        result = db_pipeline_service.run_db_pipeline(
            db=db,
            connection_id=connection_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            selected_table=table,
            date_from=date_from,
            date_to=date_to,
            force_refresh=refresh,
        )
        return result
    except ValueError:
        logger.exception("Database insights request could not resolve an owned connection")
        raise HTTPException(status_code=404, detail="Database connection not found")
    except Exception:
        logger.exception("Database insights generation failed")
        raise HTTPException(status_code=500, detail="Failed to generate database insights")


@router.post("/pipeline/{connection_id}")
def run_database_pipeline_post(
    connection_id: int,
    payload: Dict[str, Any] = {},
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """POST alias for running the 6-layer database analysis pipeline."""
    if not current_user.tenant_id:
        raise HTTPException(status_code=403, detail="User must belong to a tenant.")

    table = payload.get("table")
    refresh = payload.get("refresh", False)
    date_from = payload.get("date_from")
    date_to = payload.get("date_to")

    try:
        result = db_pipeline_service.run_db_pipeline(
            db=db,
            connection_id=connection_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            selected_table=table,
            date_from=date_from,
            date_to=date_to,
            force_refresh=refresh,
        )
        return result
    except ValueError:
        logger.exception("Database pipeline request could not resolve an owned connection")
        raise HTTPException(status_code=404, detail="Database connection not found")
    except Exception:
        logger.exception("Database pipeline execution failed")
        raise HTTPException(status_code=500, detail="Database pipeline execution failed")


@router.get("/pipeline/{connection_id}/stream")
def stream_database_pipeline(
    connection_id: int,
    table: Optional[str] = Query(None),
    refresh: bool = Query(False),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """SSE streaming endpoint for 6-layer pipeline progress animation."""
    if not current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Resolve tenant ownership before the generator can read the Redis or DB cache.
    _owned_connection(db, connection_id, current_user.tenant_id)

    def event_generator():
        gen = db_pipeline_service.run_db_pipeline_stream(
            db=db,
            connection_id=connection_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            selected_table=table,
            date_from=date_from,
            date_to=date_to,
            force_refresh=refresh,
        )
        for event in gen:
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/export/{connection_id}", response_class=HTMLResponse)
def export_insights(
    connection_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export cached or freshly generated business insights as an HTML report."""
    connection = _owned_connection(db, connection_id, current_user.tenant_id)

    try:
        insights_data = db_pipeline_service.run_db_pipeline(
            db=db,
            connection_id=connection_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            force_refresh=False
        )
    except Exception:
        logger.exception("Insights export generation failed")
        raise HTTPException(status_code=500, detail="Failed to generate insights for export")

    def esc(value: Any) -> str:
        return html.escape("" if value is None else str(value), quote=True)

    business_name = connection.name or connection.database or connection.db_type.capitalize()
    observations = insights_data.get("observations", [])
    anomalies = insights_data.get("anomalies", [])
    recommendations = insights_data.get("insights", []) or insights_data.get("recommendations", [])

    metrics_html = ""
    key_metrics = insights_data.get("key_metrics", [])
    if not key_metrics and "business_summary" in insights_data:
        key_metrics = insights_data["business_summary"].get("key_metrics", [])

    for m in key_metrics:
        metric_value = m.get("value")
        if m.get("status") in ("unavailable", "error") or metric_value is None:
            metric_value = "N/A"
        metrics_html += f"""
        <div class="metric-card">
            <div class="metric-title">{esc(m.get('label', 'Metric'))}</div>
            <div class="metric-value">{esc(metric_value)}</div>
            <div class="metric-desc">{esc(m.get('description', ''))}</div>
        </div>
        """

    obs_html = ""
    for o in observations:
        obs_html += f"""
        <div class="card obs-card">
            <strong>Observation:</strong> {esc(o)}
        </div>
        """
    if not observations:
        obs_html = "<p>No general observations compiled.</p>"

    anom_html = ""
    for a in anomalies:
        anom_html += f"""
        <div class="card anom-card">
            <strong>Anomaly in {esc(a.get('field', 'Field'))}:</strong> Value {esc(a.get('value', 'N/A'))} deviates by {esc(a.get('deviation', 'N/A'))} (Reason: {esc(a.get('reason', 'N/A'))})
        </div>
        """
    if not anomalies:
        anom_html = "<div class='card clean-card'>✓ No anomalies detected in current tables.</div>"

    rec_html = ""
    for r in recommendations:
        impact = esc(str(r.get('impact', 'LOW')).upper())
        impact_class = esc(f"badge-{impact.lower()}")
        rec_html += f"""
        <div class="card rec-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <strong style="font-size: 16px;">{esc(r.get('title', 'Recommendation'))}</strong>
                <span class="badge {impact_class}">{impact}</span>
            </div>
            <p>{esc(r.get('description', ''))}</p>
            <p style="font-style: italic; font-size: 13px; color: #555;">Suggested Action: {esc(r.get('suggested_action', ''))}</p>
        </div>
        """
    if not recommendations:
        rec_html = "<p>No recommendations available.</p>"

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
    <title>DataSpeakAI Insights Report - {esc(business_name)}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            color: #333;
            background-color: #f8fafc;
            margin: 0;
            padding: 40px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: #fff;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }}
        .header {{
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 24px;
            margin-bottom: 30px;
        }}
        .header h1 {{ margin: 0; font-size: 28px; color: #1e293b; }}
        .header p {{ margin: 8px 0 0 0; color: #64748b; font-size: 14px; }}
        .section-title {{
            font-size: 20px;
            color: #1e293b;
            border-bottom: 1px solid #e2e8f0;
            padding-bottom: 8px;
            margin-top: 40px;
            margin-bottom: 20px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: #f1f5f9;
            border-radius: 8px;
            padding: 20px;
            border: 1px solid #e2e8f0;
        }}
        .metric-title {{ font-size: 14px; color: #64748b; text-transform: uppercase; font-weight: 600; margin-bottom: 8px; }}
        .metric-value {{ font-size: 28px; font-weight: bold; color: #0f172a; margin-bottom: 4px; }}
        .metric-desc {{ font-size: 12px; color: #94a3b8; }}
        .card {{
            background: #fff;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 12px;
        }}
        .obs-card {{ border-left: 4px solid #3b82f6; }}
        .anom-card {{ border-left: 4px solid #ef4444; background: #fff5f5; }}
        .rec-card {{ border-left: 4px solid #10b981; }}
        .clean-card {{ border-left: 4px solid #10b981; color: #065f46; font-weight: 500; background: #f0fdf4; }}
        .badge {{ padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }}
        .badge-high {{ background: #fee2e2; color: #991b1b; }}
        .badge-medium {{ background: #fef3c7; color: #92400e; }}
        .badge-low {{ background: #e0e7ff; color: #3730a3; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>DataSpeakAI Intelligence Report</h1>
            <p>Database: <strong>{esc(business_name)}</strong> | Type: {esc(connection.db_type.upper())} | Status: {esc(connection.status.upper())}</p>
        </div>
        <div class="section-title">Key Executive Performance Metrics</div>
        <div class="grid">{metrics_html}</div>
        <div class="section-title">Strategic Observations & Insights</div>
        <div>{obs_html}</div>
        <div class="section-title">Statistical Anomaly Detections</div>
        <div>{anom_html}</div>
        <div class="section-title">AI Prescriptive Action Playbook</div>
        <div>{rec_html}</div>
    </div>
</body>
</html>"""
    return HTMLResponse(content=html_content)
