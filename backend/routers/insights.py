"""
Database AI Insights Router (6-Layer Relational Analysis Engine)
Generates comprehensive executive playbooks, KPI recipes, smart charts, anomalies,
and multi-table relational insights.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse, HTMLResponse
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
import json

import models
from database import get_db
from dependencies import get_current_user
from services.db_pipeline_service import db_pipeline_service

router = APIRouter(prefix="/api/insights", tags=["Database Insights"])


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
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate database insights: {str(e)}")


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
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    connection = (
        db.query(models.DatabaseConnection)
        .filter(
            models.DatabaseConnection.id == connection_id,
            models.DatabaseConnection.tenant_id == current_user.tenant_id
        )
        .first()
    )
    if not connection:
        raise HTTPException(status_code=404, detail="Database connection not found")

    try:
        insights_data = db_pipeline_service.run_db_pipeline(
            db=db,
            connection_id=connection_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            force_refresh=False
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate insights for export: {str(e)}")

    business_name = connection.name or connection.database or connection.db_type.capitalize()
    observations = insights_data.get("observations", [])
    anomalies = insights_data.get("anomalies", [])
    recommendations = insights_data.get("insights", []) or insights_data.get("recommendations", [])

    metrics_html = ""
    key_metrics = insights_data.get("key_metrics", [])
    if not key_metrics and "business_summary" in insights_data:
        key_metrics = insights_data["business_summary"].get("key_metrics", [])

    for m in key_metrics:
        metrics_html += f"""
        <div class="metric-card">
            <div class="metric-title">{m.get('label', 'Metric')}</div>
            <div class="metric-value">{m.get('value', 'N/A')}</div>
            <div class="metric-desc">{m.get('description', '')}</div>
        </div>
        """

    obs_html = ""
    for o in observations:
        obs_html += f"""
        <div class="card obs-card">
            <strong>Observation:</strong> {o}
        </div>
        """
    if not observations:
        obs_html = "<p>No general observations compiled.</p>"

    anom_html = ""
    for a in anomalies:
        anom_html += f"""
        <div class="card anom-card">
            <strong>Anomaly in {a.get('field', 'Field')}:</strong> Value {a.get('value', 'N/A')} deviates by {a.get('deviation', 'N/A')} (Reason: {a.get('reason', 'N/A')})
        </div>
        """
    if not anomalies:
        anom_html = "<div class='card clean-card'>✓ No anomalies detected in current tables.</div>"

    rec_html = ""
    for r in recommendations:
        impact = str(r.get('impact', 'LOW')).upper()
        impact_class = f"badge-{impact.lower()}"
        rec_html += f"""
        <div class="card rec-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <strong style="font-size: 16px;">{r.get('title', 'Recommendation')}</strong>
                <span class="badge {impact_class}">{impact}</span>
            </div>
            <p>{r.get('description', '')}</p>
            <p style="font-style: italic; font-size: 13px; color: #555;">Suggested Action: {r.get('suggested_action', '')}</p>
        </div>
        """
    if not recommendations:
        rec_html = "<p>No recommendations available.</p>"

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>DataSpeakAI Insights Report - {business_name}</title>
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
            <p>Database: <strong>{business_name}</strong> | Type: {connection.db_type.upper()} | Status: {connection.status.upper()}</p>
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
