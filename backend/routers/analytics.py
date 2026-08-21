from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from typing import List, Optional
import models, schemas
from database import get_db
from dependencies import get_current_user
from services.schema_profiler import profile_database_schema
from services.kpi_chart_engine import generate_kpis_and_chart_specs
from services.query_builder import build_aggregated_chart_query
from services.cache_service import cache_service
from services.ai_insights import generate_ai_business_insights

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

@router.post("/connections/{connection_id}/profile")
def trigger_schema_profile(
    connection_id: int,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")

    db_conn = db.query(models.DatabaseConnection).filter(
        models.DatabaseConnection.id == connection_id,
        models.DatabaseConnection.tenant_id == current_user.tenant_id
    ).first()

    if not db_conn:
        raise HTTPException(status_code=404, detail="Database connection not found")

    # Run profiling in background
    def run_profiling():
        profile_database_schema(db_conn, db)
        generate_kpis_and_chart_specs(current_user.tenant_id, connection_id, db)
        for r_range in ["7days", "30days", "90days", "1year"]:
            cache_service.invalidate(current_user.tenant_id, f"dash_view:{connection_id}:{r_range}")

    background_tasks.add_task(run_profiling)
    return {"message": "Schema profiling triggered", "connection_id": connection_id, "status": "processing"}


@router.get("/connections/{connection_id}/profile-status")
def get_profile_status(
    connection_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    entries = db.query(models.SchemaRegistry).filter(
        models.SchemaRegistry.connection_id == connection_id
    ).all()
    
    return {
        "connection_id": connection_id,
        "total_columns_profiled": len(entries),
        "status": "completed" if len(entries) > 0 else "pending"
    }

@router.get("/dashboard/{connection_id}")
def get_dashboard_data(
    connection_id: int,
    date_range: Optional[str] = "30days",
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")

    cache_key = f"dash_view:{connection_id}:{date_range}"

    def compute_dashboard():
        kpis = db.query(models.KpiDefinition).filter(
            models.KpiDefinition.tenant_id == current_user.tenant_id,
            models.KpiDefinition.connection_id == connection_id
        ).all()

        registries = db.query(models.SchemaRegistry).filter(
            models.SchemaRegistry.connection_id == connection_id
        ).all()

        tables = list(set([r.table_name for r in registries]))
        measures = [r for r in registries if r.is_measure]
        dimensions = [r for r in registries if r.is_dimension]

        db_conn = db.query(models.DatabaseConnection).filter(
            models.DatabaseConnection.id == connection_id,
            models.DatabaseConnection.tenant_id == current_user.tenant_id
        ).first()

        live_charts = []
        if db_conn:
            from routers.databases import get_connection_url
            url = get_connection_url(db_conn)
            if url:
                try:
                    from sqlalchemy import create_engine, text
                    engine = create_engine(url)
                    with engine.connect() as conn:
                        for k in kpis:
                            t_name = k.target_column.split(".")[0] if "." in (k.target_column or "") else (registries[0].table_name if registries else "users")
                            target_col = k.target_column.split(".")[1] if "." in (k.target_column or "") else k.target_column
                            group_col = k.dimension_column.split(".")[1] if k.dimension_column and "." in k.dimension_column else k.dimension_column

                            if group_col:
                                q = text(f'SELECT "{group_col}", SUM("{target_col}") AS val FROM "{t_name}" WHERE "{group_col}" IS NOT NULL GROUP BY "{group_col}" ORDER BY val DESC LIMIT 8')
                            else:
                                q = text(f'SELECT "{target_col}", SUM("{target_col}") AS val FROM "{t_name}" LIMIT 8')
                            
                            res = conn.execute(q).fetchall()
                            chart_data = [{"name": str(r[0] or "N/A")[:20], "value": round(float(r[1] or 0), 2)} for r in res]
                            live_charts.append({
                                "id": k.id,
                                "title": k.kpi_title,
                                "chart_type": k.default_chart_type,
                                "data": chart_data
                            })
                    engine.dispose()
                except Exception as ex:
                    logger.warning(f"Error computing live charts for connection {connection_id}: {ex}")

        return {
            "connection_id": connection_id,
            "table_count": len(tables),
            "measure_count": len(measures),
            "dimension_count": len(dimensions),
            "kpis": [
                {
                    "id": k.id,
                    "title": k.kpi_title,
                    "aggregation": k.aggregation_function,
                    "target_column": k.target_column,
                    "default_chart_type": k.default_chart_type
                } for k in kpis
            ],
            "live_charts": live_charts,
            "schema_summary": [
                {
                    "table_name": r.table_name,
                    "column_name": r.column_name,
                    "data_type": r.data_type,
                    "is_measure": r.is_measure,
                    "is_dimension": r.is_dimension,
                    "is_time_axis": r.is_time_axis,
                    "null_percentage": r.null_percentage
                } for r in registries
            ]
        }

    return cache_service.get_or_compute(current_user.tenant_id, cache_key, compute_dashboard)


@router.post("/dashboard/{connection_id}/query")
def execute_dashboard_query(
    connection_id: int,
    req: schemas.DashboardQueryRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")

    db_conn = db.query(models.DatabaseConnection).filter(
        models.DatabaseConnection.id == connection_id,
        models.DatabaseConnection.tenant_id == current_user.tenant_id
    ).first()

    if not db_conn:
        raise HTTPException(status_code=404, detail="Database connection not found")

    registries = db.query(models.SchemaRegistry).filter(
        models.SchemaRegistry.connection_id == connection_id
    ).all()

    if not registries:
        profile_database_schema(db_conn, db)
        registries = db.query(models.SchemaRegistry).filter(
            models.SchemaRegistry.connection_id == connection_id
        ).all()

    t_name = req.table_name or (registries[0].table_name if registries else "users")
    t_registries = [r for r in registries if r.table_name == t_name]
    
    measures = [r for r in t_registries if r.is_measure and not r.column_name.lower().endswith("id") and r.column_name.lower() != "id"]
    dimensions = [r for r in t_registries if r.is_dimension]

    # Select target column
    if req.target_column and req.target_column != "*":
        target_col = req.target_column
    elif measures:
        target_col = measures[0].column_name
    elif dimensions:
        target_col = dimensions[0].column_name
    else:
        target_col = t_registries[0].column_name if t_registries else "id"

    # Select dimension column
    dim_col = req.dimension_column
    if not dim_col and dimensions:
        dim_col = dimensions[0].column_name

    agg_func = (req.aggregation or ("COUNT" if not measures else "SUM")).upper()
    if agg_func not in ("SUM", "AVG", "COUNT", "MAX", "MIN"):
        agg_func = "COUNT" if not measures else "SUM"

    from routers.databases import get_connection_url
    url = get_connection_url(db_conn)
    if not url:
        raise HTTPException(status_code=400, detail="Database URL not available")

    chart_data = []
    kpi_stats = {"total": 0, "average": 0, "max": 0, "min": 0, "count": 0}

    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(url)
        with engine.connect() as conn:
            # 1. Fetch Summary Stats
            try:
                if agg_func == "COUNT" or target_col == "*":
                    s_q = text(f'SELECT COUNT(*), COUNT(DISTINCT "{dim_col}") IF "{dim_col}" IS NOT NULL ELSE COUNT(*), COUNT(*), COUNT(*), COUNT(*) FROM "{t_name}"') if False else text(f'SELECT COUNT(*), COUNT(*), COUNT(*), COUNT(*), COUNT(*) FROM "{t_name}"')
                    s_row = conn.execute(s_q).fetchone()
                    if s_row:
                        c_val = int(s_row[0] or 0)
                        kpi_stats = {"total": c_val, "average": 1.0, "max": c_val, "min": 1.0, "count": c_val}
                else:
                    s_q = text(f'SELECT SUM("{target_col}"), AVG("{target_col}"), MAX("{target_col}"), MIN("{target_col}"), COUNT(*) FROM "{t_name}"')
                    s_row = conn.execute(s_q).fetchone()
                    if s_row:
                        kpi_stats = {
                            "total": round(float(s_row[0] or 0), 2),
                            "average": round(float(s_row[1] or 0), 2),
                            "max": round(float(s_row[2] or 0), 2),
                            "min": round(float(s_row[3] or 0), 2),
                            "count": int(s_row[4] or 0)
                        }
            except Exception as ex_stat:
                logger.warning(f"Error fetching stats for {t_name}.{target_col}: {ex_stat}")

            # 2. Fetch Chart Data
            if dim_col:
                if agg_func == "COUNT" or target_col == "*":
                    q = text(f'SELECT "{dim_col}", COUNT(*) AS val FROM "{t_name}" WHERE "{dim_col}" IS NOT NULL GROUP BY "{dim_col}" ORDER BY val DESC LIMIT {int(req.limit or 10)}')
                else:
                    q = text(f'SELECT "{dim_col}", {agg_func}("{target_col}") AS val FROM "{t_name}" WHERE "{dim_col}" IS NOT NULL GROUP BY "{dim_col}" ORDER BY val DESC LIMIT {int(req.limit or 10)}')
            else:
                if agg_func == "COUNT" or target_col == "*":
                    q = text(f'SELECT "{target_col}", COUNT(*) AS val FROM "{t_name}" GROUP BY "{target_col}" LIMIT {int(req.limit or 10)}')
                else:
                    q = text(f'SELECT "{target_col}", {agg_func}("{target_col}") AS val FROM "{t_name}" LIMIT {int(req.limit or 10)}')
            
            res = conn.execute(q).fetchall()
            chart_data = [{"name": str(r[0] or "N/A")[:20], "value": round(float(r[1] or 0), 2)} for r in res]


            # 3. Fetch Scatter Data (Correlation between 2 numeric measures if available)
            scatter_data = []
            if len(measures) >= 2:
                m1 = measures[0].column_name
                m2 = measures[1].column_name
                try:
                    sc_label = dim_col if dim_col else m1
                    sc_q = text(f'SELECT "{m1}", "{m2}", "{sc_label}" FROM "{t_name}" WHERE "{m1}" IS NOT NULL AND "{m2}" IS NOT NULL LIMIT 40')
                    sc_res = conn.execute(sc_q).fetchall()
                    scatter_data = [{"x": round(float(r[0] or 0), 2), "y": round(float(r[1] or 0), 2), "name": str(r[2] or "")[:20]} for r in sc_res]
                except Exception as ex_sc:
                    logger.warning(f"Error building scatter data for {t_name}: {ex_sc}")

        engine.dispose()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query execution failed: {str(e)}")

    return {
        "status": "success",
        "table_name": t_name,
        "target_column": target_col,
        "dimension_column": dim_col,
        "aggregation": agg_func,
        "kpi_stats": kpi_stats,
        "chart_data": chart_data,
        "scatter_data": scatter_data
    }



@router.post("/dashboard/{connection_id}/refresh-cache")
def refresh_dashboard_cache(
    connection_id: int,
    current_user: models.User = Depends(get_current_user)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")

    cache_service.invalidate(current_user.tenant_id, f"dash_view:{connection_id}:7days")
    cache_service.invalidate(current_user.tenant_id, f"dash_view:{connection_id}:30days")
    return {"status": "success", "message": "Dashboard cache invalidated"}

@router.get("/connections/{connection_id}/ai-insights")
def get_connection_ai_insights(
    connection_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")

    db_conn = db.query(models.DatabaseConnection).filter(
        models.DatabaseConnection.id == connection_id,
        models.DatabaseConnection.tenant_id == current_user.tenant_id
    ).first()
    if not db_conn:
        raise HTTPException(status_code=404, detail="Database connection not found")

    registries = db.query(models.SchemaRegistry).filter(
        models.SchemaRegistry.connection_id == connection_id
    ).all()
    if not registries:
        from services.schema_profiler import profile_database_schema
        registries = profile_database_schema(db_conn, db)

    from services.ai_insights_service import generate_ai_insights_from_stats
    insights = generate_ai_insights_from_stats(db_conn, registries, db)
    return insights


from datetime import datetime, timedelta

INSIGHTS_COOLDOWN_SECONDS = 60
_LAST_INSIGHT_GEN_TIME: dict[int, datetime] = {}

@router.get("/insights", response_model=List[schemas.AiInsightResponse])
def get_ai_insights(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")

    insights = db.query(models.AiInsight).filter(
        models.AiInsight.tenant_id == current_user.tenant_id
    ).all()

    if not insights:
        insights = generate_ai_business_insights(current_user.tenant_id, db)

    return insights

@router.post("/insights/generate", response_model=List[schemas.AiInsightResponse])
def trigger_ai_insights_generation(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")

    last_gen = _LAST_INSIGHT_GEN_TIME.get(current_user.tenant_id)
    if last_gen:
        elapsed = (datetime.utcnow() - last_gen).total_seconds()
        if elapsed < INSIGHTS_COOLDOWN_SECONDS:
            remaining = int(INSIGHTS_COOLDOWN_SECONDS - elapsed)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Please wait {remaining} seconds before generating new AI insights."
            )

    _LAST_INSIGHT_GEN_TIME[current_user.tenant_id] = datetime.utcnow()
    return generate_ai_business_insights(current_user.tenant_id, db)

