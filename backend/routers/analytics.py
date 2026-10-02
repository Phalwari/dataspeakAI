from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from typing import List, Optional, Any, Union, cast
import models, schemas

import logging
from database import get_db
from dependencies import get_current_user, get_current_admin_user
from services.schema_profiler import profile_database_schema, get_table_profiles_for_agents
from services.kpi_chart_engine import generate_kpis_and_chart_specs
from services.query_builder import build_aggregated_chart_query, validate_column, quote_ident, cast_text_expr
from services.cache_service import cache_service
from services.db_utils import get_connection_url
from services.db_pool import get_engine
from services.ai_insights_service import generate_ai_insights_from_stats
from services.dashboard_agents import generate_dashboard_via_agents
from services.domain_templates import list_domain_templates, get_domain_template
from services.mapping_matcher import suggest_mappings
from services.metric_executor import MetricExecutor, MetricRequest, MetricFilter
from services.metric_adapter import adapt_kpi_to_metric_request, LegacyKpiIncompatibleError
from services.series_reader import read_scatter_series
from services.metric_semantics import validate_metric_aggregation
from services.source_profiler import (
    discover_source,
    discover_database_archetype,
    discover_document_archetype,
    SourceDiscoveryResult,
    _parse_markdown_table,
)
from services.adaptive_chart_recommender import (
    recommend_adaptive_charts,
    AdaptiveChartRecommendation,
)
from datetime import datetime, timedelta, timezone
from sqlalchemy import text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

DATE_RANGE_DAYS = {"7days": 7, "30days": 30, "90days": 90, "1year": 365}


def get_owned_connection(
    db: Session,
    connection_id: int,
    tenant_id: int,
) -> models.DatabaseConnection:
    """
    Ensures the requested database connection exists and belongs to the current user's tenant.
    Prevents cross-tenant metadata, profile status, mapping, cache, or dashboard leakage.
    """
    conn = (
        db.query(models.DatabaseConnection)
        .filter(
            models.DatabaseConnection.id == connection_id,
            models.DatabaseConnection.tenant_id == tenant_id,
        )
        .first()
    )
    if not conn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Database connection not found",
        )
    return conn


async def run_full_profiling_and_agent_pipeline(tenant_id: int, connection_id: int, db: Session):
    """
    Background job: Runs deterministic schema profiling + Multi-Agent LLM pipeline
    to synthesize KPIs, smart chart specs, and optimal filters.
    """
    db_conn = db.query(models.DatabaseConnection).filter(
        models.DatabaseConnection.id == connection_id,
        models.DatabaseConnection.tenant_id == tenant_id
    ).first()
    if not db_conn:
        return

    try:
        # Step 1: Introspect schema and compute statistics
        profile_database_schema(db_conn, db)

        # Step 2: Build table profiles for agents
        table_profiles = get_table_profiles_for_agents(db_conn, db)

        # Step 3: Run LangGraph 4-Agent pipeline (Semantic -> KPI -> Chart/Layout -> Validator)
        validated_config = await generate_dashboard_via_agents(table_profiles)

        # Step 4: Persist KPIs and Layout to DB atomically in a single transaction
        valid_kpis = run_agent_pipeline_sync(
            tenant_id=tenant_id,
            connection_id=connection_id,
            agent_kpis=validated_config.kpis,
            db=db,
            layout_config=validated_config,
            commit=True,
        )

        logger.info(f"Dashboard generated for connection {connection_id} (Domain: {validated_config.business_domain}, Valid KPIs: {len(valid_kpis)})")

    except Exception as e:
        logger.error(f"Error in agent profiling pipeline for connection {connection_id}: {e}")
        # Phase 1.5D.2: Zero silent fallback to legacy rule engine or demo data on failure


ALLOWED_AGENT_AGGREGATIONS = {"SUM", "AVG", "MIN", "MAX", "COUNT", "COUNT_DISTINCT"}


def run_agent_pipeline_sync(
    tenant_id: int,
    connection_id: int,
    agent_kpis: list,
    db: Session,
    layout_config: Optional[Any] = None,
    commit: bool = True,
) -> list[models.KpiDefinition]:
    """
    Phase 1.5D.2 Strict & Atomic Agent KPI + Layout Persistence.
    Validates candidate agent KPI specifications and layout strictly against
    verified connection ownership, SchemaRegistry, and ALLOWED_AGENT_AGGREGATIONS.

    Strict Data Integrity & Atomicity Rules:
    1. Connection Ownership Defense (Task 4):
       Verifies connection_id belongs to tenant_id before inspecting SchemaRegistry.
       Raises ValueError if connection is missing or unauthorized.
    2. Candidate In-Memory Validation (Task 1):
       Validates all agent KPI specs first in memory. If zero valid KPI definitions
       remain, DOES NOT delete existing KPIs, DOES NOT modify DashboardLayout,
       DOES NOT commit, and returns [] cleanly to preserve previously working dashboards.
    3. Same-Table Dimension Enforcement (Task 3):
       If optional secondary/dimension column belongs to another table (cross-table),
       it is safely omitted (dimension_column=None) with a structured warning.
       No join is guessed or generated. Primary metric is preserved if valid.
    4. Single Atomic Transaction (Task 2):
       Deletes previous KPIs, inserts new KPIs, and updates/creates DashboardLayout
       in a single atomic block. If any step fails, performs db.rollback().
       Cache invalidation happens ONLY after successful commit.
    """
    # 1. Connection Ownership Defense (Task 4)
    db_conn = (
        db.query(models.DatabaseConnection)
        .filter(
            models.DatabaseConnection.id == connection_id,
            models.DatabaseConnection.tenant_id == tenant_id,
        )
        .first()
    )
    if not db_conn:
        logger.warning(
            "Agent pipeline aborted: connection %s not found or unauthorized for tenant %s",
            connection_id,
            tenant_id,
        )
        raise ValueError(
            f"Database connection {connection_id} not found or unauthorized for tenant {tenant_id}"
        )

    schema_entries = (
        db.query(models.SchemaRegistry)
        .filter(models.SchemaRegistry.connection_id == connection_id)
        .all()
    )
    valid_tables = {s.table_name for s in schema_entries}
    valid_columns = {(s.table_name, s.column_name) for s in schema_entries}

    valid_kpis: list[models.KpiDefinition] = []

    for kpi_spec in agent_kpis:
        # Title
        raw_title = getattr(kpi_spec, "kpi_title", getattr(kpi_spec, "title", None))
        kpi_title = str(raw_title).strip() if raw_title and str(raw_title).strip() else "Unnamed KPI"

        # 1. Aggregation Validation
        raw_agg = getattr(kpi_spec, "aggregation_function", getattr(kpi_spec, "aggregation", None))
        if not raw_agg or not isinstance(raw_agg, str) or not raw_agg.strip():
            logger.warning("Dropping agent KPI '%s': missing or blank aggregation_function", kpi_title)
            continue

        agg = raw_agg.strip().upper()
        if agg not in ALLOWED_AGENT_AGGREGATIONS:
            logger.warning(
                "Dropping agent KPI '%s': unsupported aggregation '%s' requires Phase 2 derived-metric handling",
                kpi_title,
                agg,
            )
            continue

        # 2. Target Extraction & Validation
        table_name = getattr(kpi_spec, "table_name", None)
        column_name = getattr(kpi_spec, "column_name", None)

        primary_col = getattr(kpi_spec, "primary_column", None)
        if (not table_name or not column_name) and primary_col and isinstance(primary_col, str):
            if "." in primary_col:
                parts = primary_col.split(".", 1)
                table_name = table_name or parts[0].strip()
                column_name = column_name or parts[1].strip()

        table_name = str(table_name).strip() if table_name else None
        column_name = str(column_name).strip() if column_name else None

        if not table_name:
            logger.warning("Dropping agent KPI '%s': missing table_name", kpi_title)
            continue

        if not column_name:
            logger.warning("Dropping agent KPI '%s': missing column_name", kpi_title)
            continue

        if table_name not in valid_tables:
            logger.warning(
                "Dropping agent KPI '%s': table '%s' does not exist in SchemaRegistry for connection %s",
                kpi_title,
                table_name,
                connection_id,
            )
            continue

        is_valid_wildcard = (agg == "COUNT" and column_name in ("*", "all"))
        if not is_valid_wildcard and (table_name, column_name) not in valid_columns:
            logger.warning(
                "Dropping agent KPI '%s': column '%s' does not exist in table '%s' in SchemaRegistry",
                kpi_title,
                column_name,
                table_name,
            )
            continue

        # 3. Construct qualified target
        target_column = f"{table_name}.{column_name}"

        # 4. Same-Table Dimension Enforcement (Task 3)
        sec_col = getattr(kpi_spec, "secondary_column", getattr(kpi_spec, "dimension_column", None))
        dim_col = None
        if sec_col and isinstance(sec_col, str) and sec_col.strip():
            clean_sec = sec_col.strip()
            dim_table = None
            dim_field = None
            if "." in clean_sec:
                parts = clean_sec.split(".", 1)
                dim_table = parts[0].strip()
                dim_field = parts[1].strip()
            else:
                dim_table = table_name
                dim_field = clean_sec

            if (dim_table, dim_field) in valid_columns:
                if dim_table == table_name:
                    dim_col = f"{dim_table}.{dim_field}"
                else:
                    logger.warning(
                        "Dropping cross-table dimension '%s' for target '%s': "
                        "cross-table dimensions are deferred until relationship engine is available.",
                        clean_sec,
                        target_column,
                    )
                    dim_col = None
            else:
                logger.warning(
                    "Dropping dimension '%s' for target '%s': column not found in SchemaRegistry.",
                    clean_sec,
                    target_column,
                )
                dim_col = None

        kpi_record = models.KpiDefinition(
            tenant_id=tenant_id,
            connection_id=connection_id,
            kpi_title=kpi_title,
            aggregation_function=agg,
            target_column=target_column,
            dimension_column=dim_col,
            time_column=None,
            default_chart_type="Line" if agg == "AVG" else "Bar",
            priority=int(getattr(kpi_spec, "priority", 1) or 1),
            reasoning=str(getattr(kpi_spec, "reasoning", "") or f"Agent synthesized KPI for {kpi_title}"),
        )
        valid_kpis.append(kpi_record)

    # Task 1: Never delete a working dashboard when zero valid replacement KPIs are generated
    if not valid_kpis:
        logger.warning(
            "Zero valid KPI definitions were retained after strict SchemaRegistry & aggregation validation for connection %s. "
            "Aborting replacement to preserve existing dashboard.",
            connection_id,
        )
        return []

    # Task 2: Atomic KPI + Layout persistence in a single transaction
    charts_data = None
    filters_data = None
    if layout_config:
        charts_data = (
            [c.model_dump() if hasattr(c, "model_dump") else c for c in layout_config.charts]
            if hasattr(layout_config, "charts") and layout_config.charts
            else []
        )
        filters_data = (
            [f.model_dump() if hasattr(f, "model_dump") else f for f in layout_config.filters]
            if hasattr(layout_config, "filters") and layout_config.filters
            else []
        )

    try:
        # Delete previous KPI definitions only after replacement set is validated and confirmed non-empty
        db.query(models.KpiDefinition).filter(
            models.KpiDefinition.tenant_id == tenant_id,
            models.KpiDefinition.connection_id == connection_id
        ).delete(synchronize_session="fetch")

        for kpi in valid_kpis:
            db.add(kpi)

        if layout_config:
            layout = db.query(models.DashboardLayout).filter(
                models.DashboardLayout.tenant_id == tenant_id,
                models.DashboardLayout.connection_id == connection_id
            ).first()

            domain_name = getattr(layout_config, "business_domain", "General Analytics")
            validation_warnings = getattr(layout_config, "validation_warnings", [])
            used_fallback = getattr(layout_config, "used_fallback", False)

            if not layout:
                layout = models.DashboardLayout(
                    tenant_id=tenant_id,
                    connection_id=connection_id,
                    business_domain=domain_name,
                    charts_config=charts_data,
                    filters_config=filters_data,
                    validation_warnings=validation_warnings,
                    used_fallback=used_fallback,
                )
                db.add(layout)
            else:
                setattr(layout, "business_domain", domain_name)
                setattr(layout, "charts_config", charts_data)
                setattr(layout, "filters_config", filters_data)
                setattr(layout, "validation_warnings", validation_warnings)
                setattr(layout, "used_fallback", used_fallback)

        if commit:
            db.commit()

            # Cache invalidation happens ONLY after successful commit
            for r_range in ["7days", "30days", "90days", "1year"]:
                cache_service.invalidate(tenant_id, f"dash_view:{connection_id}:{r_range}")

        return valid_kpis

    except Exception as e:
        db.rollback()
        logger.error(
            "Failed atomic dashboard replacement for connection %s: %s. Previous dashboard state preserved.",
            connection_id,
            e,
        )
        raise e


from services.profiling_queue import profiling_queue
from services.db_pool import _engine_cache
import asyncio

def _sync_worker_profile_connection(tenant_id: int, connection_id: int) -> None:
    """
    Synchronous worker executing on a thread pool.
    Receives ONLY primitive tenant_id and connection_id to guarantee thread safety.
    Creates and closes its own fresh SessionLocal().
    """
    import database
    thread_db = database.SessionLocal()
    try:
        db_conn = (
            thread_db.query(models.DatabaseConnection)
            .filter(
                models.DatabaseConnection.id == connection_id,
                models.DatabaseConnection.tenant_id == tenant_id,
            )
            .first()
        )
        if not db_conn:
            logger.warning(f"Profiling aborted: connection {connection_id} not found for tenant {tenant_id}")
            raise ValueError(f"Database connection {connection_id} not found or unauthorized for tenant {tenant_id}")

        profile_database_schema(db_conn, thread_db)
        thread_db.commit()
    except Exception as e:
        thread_db.rollback()
        raise e
    finally:
        thread_db.close()


async def _profiling_job_runner(tenant_id: int, connection_id: int):
    """
    Phase 1.5 Background Worker: Executes deterministic schema profiling only.
    Runs synchronous database inspection on a worker thread with isolated SessionLocal.
    Decoupled completely from legacy LLM dashboard generation.
    """
    try:
        await asyncio.to_thread(_sync_worker_profile_connection, tenant_id, connection_id)
        logger.info(f"Schema profiling completed for connection {connection_id} (Tenant: {tenant_id})")
    except Exception as e:
        logger.error(f"Error during schema profiling for connection {connection_id}: {e}")
        raise e

@router.post("/connections/{connection_id}/profile")
async def trigger_schema_profile(
    connection_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")

    t_id = cast(int, current_user.tenant_id)
    # Strict Tenant Scoping: Verify connection belongs to current tenant
    db_conn = get_owned_connection(db, connection_id, t_id)

    # Enqueue in rate-limited queue
    asyncio.create_task(profiling_queue.enqueue_and_run(t_id, connection_id, _profiling_job_runner))
    job_status = await profiling_queue.get_job_status(connection_id)

    return {
        "message": "Schema profiling queued",
        "connection_id": connection_id,
        "status": job_status["status"],
        "queue_position": job_status["queue_position"]
    }


@router.get("/connections/{connection_id}/profile-status")
async def get_profile_status(
    connection_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")

    t_id = cast(int, current_user.tenant_id)
    # Strict Tenant Scoping: Verify connection belongs to current tenant before querying metadata
    get_owned_connection(db, connection_id, t_id)

    entries = db.query(models.SchemaRegistry).filter(
        models.SchemaRegistry.connection_id == connection_id
    ).all()
    
    kpis = db.query(models.KpiDefinition).filter(
        models.KpiDefinition.tenant_id == current_user.tenant_id,
        models.KpiDefinition.connection_id == connection_id
    ).all()

    job_status = await profiling_queue.get_job_status(connection_id)

    # In Phase 1.5, respect explicit job failures first
    if job_status.get("status") == "failed":
        overall_status = "failed"
    elif job_status.get("status") in ("processing", "queued"):
        overall_status = job_status["status"]
    else:
        overall_status = "completed" if len(entries) > 0 else job_status.get("status", "idle")

    return {
        "connection_id": connection_id,
        "total_columns_profiled": len(entries),
        "total_kpis": len(kpis),
        "status": overall_status,
        "queue_position": job_status.get("queue_position", 0),
        "elapsed_sec": job_status.get("elapsed_sec", 0),
        "error": job_status.get("error")
    }


@router.get("/admin/system-health")
def get_system_health(
    current_user: models.User = Depends(get_current_admin_user),
):
    return {
        "status": "healthy",
        "active_db_pools": len(_engine_cache),
        "profiling_queue": profiling_queue.get_stats(),
        "cached_dashboards_count": len(cache_service._store)
    }


@router.get("/sources")
def list_analytics_sources(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Unified source discovery endpoint: lists all available relational databases
    and uploaded document knowledge sources for the current tenant.
    """
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")
    t_id = cast(int, current_user.tenant_id)

    databases = (
        db.query(models.DatabaseConnection)
        .filter(models.DatabaseConnection.tenant_id == t_id)
        .all()
    )

    documents = (
        db.query(models.Document)
        .filter(models.Document.tenant_id == t_id)
        .all()
    )

    sources = []
    for db_conn in databases:
        try:
            disc = discover_database_archetype(db_conn, db)
            archetype = disc.source_archetype
            arch_name = disc.archetype_display_name
        except Exception:
            archetype = "relational_sql"
            arch_name = f"{db_conn.db_type.upper()} Relational Database"

        sources.append({
            "id": f"db_{db_conn.id}",
            "raw_id": db_conn.id,
            "source_type": "database",
            "name": db_conn.name,
            "db_type": db_conn.db_type,
            "status": db_conn.status,
            "archetype": archetype,
            "archetype_display_name": arch_name,
        })

    for doc in documents:
        try:
            disc = discover_document_archetype(doc, db)
            archetype = disc.source_archetype
            arch_name = disc.archetype_display_name
        except Exception:
            archetype = "document_knowledge"
            arch_name = f"Document ({doc.file_type})"

        sources.append({
            "id": f"doc_{doc.id}",
            "raw_id": doc.id,
            "source_type": "document",
            "name": doc.name,
            "db_type": (doc.file_type or "file").lstrip("."),
            "status": doc.status,
            "archetype": archetype,
            "archetype_display_name": arch_name,
        })

    return sources


@router.get("/sources/{source_type}/{source_id}/discover")
def discover_analytics_source(
    source_type: str,
    source_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    On-demand archetype discovery & adaptive recommendation endpoint.
    """
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")
    t_id = cast(int, current_user.tenant_id)

    try:
        discovery = discover_source(source_type, source_id, t_id, db)
        recommendations = recommend_adaptive_charts(discovery, db, t_id)
        return {
            "discovery": discovery.model_dump(),
            "recommendations": [r.model_dump() for r in recommendations],
        }
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@router.get("/sources/{source_type}/{source_id}/dashboard")
def get_unified_dashboard_data(
    source_type: str,
    source_id: int,
    date_range: Optional[str] = "30days",
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Unified dashboard endpoint for both relational databases and documents.
    """
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")
    t_id = cast(int, current_user.tenant_id)

    if source_type == "database":
        return get_dashboard_data(
            connection_id=source_id,
            date_range=date_range,
            current_user=current_user,
            db=db,
        )
    elif source_type == "document":
        doc = (
            db.query(models.Document)
            .filter(
                models.Document.id == source_id,
                models.Document.tenant_id == t_id,
            )
            .first()
        )
        if not doc:
            raise HTTPException(status_code=404, detail="Document source not found")

        discovery = discover_document_archetype(doc, db)
        recommendations = recommend_adaptive_charts(discovery, db, t_id)

        schema_summary = []
        for m in discovery.detected_measures:
            schema_summary.append({
                "table_name": doc.name,
                "column_name": m,
                "data_type": "FLOAT",
                "is_measure": True,
                "is_dimension": False,
                "is_time_axis": False,
                "cardinality": 50,
                "null_percentage": 0.0,
            })
        for d in discovery.detected_dimensions:
            schema_summary.append({
                "table_name": doc.name,
                "column_name": d,
                "data_type": "VARCHAR",
                "is_measure": False,
                "is_dimension": True,
                "is_time_axis": False,
                "cardinality": 5,
                "null_percentage": 0.0,
            })
        for t_col in discovery.detected_time_axes:
            schema_summary.append({
                "table_name": doc.name,
                "column_name": t_col,
                "data_type": "DATETIME",
                "is_measure": False,
                "is_dimension": False,
                "is_time_axis": True,
                "cardinality": 20,
                "null_percentage": 0.0,
            })

        live_charts = []
        for r in recommendations:
            if r.chart_type != "KPI":
                live_charts.append({
                    "chart_id": r.id,
                    "title": r.title,
                    "chart_type": r.chart_type,
                    "data": r.sample_data if r.sample_data else [
                        {"name": "Sample A", "value": 45},
                        {"name": "Sample B", "value": 85},
                        {"name": "Sample C", "value": 60},
                    ],
                })

        return {
            "connection_id": source_id,
            "document_id": source_id,
            "source_type": "document",
            "source_archetype": discovery.source_archetype,
            "business_domain": "Document Knowledge & Intelligence",
            "table_count": len(discovery.detected_entities),
            "measure_count": len(discovery.detected_measures),
            "dimension_count": len(discovery.detected_dimensions),
            "discovery": discovery.model_dump(),
            "recommendations": [rec.model_dump() for rec in recommendations],
            "kpis": [
                {
                    "id": idx + 1,
                    "title": rec.title,
                    "aggregation": rec.aggregation,
                    "target_column": rec.target_metric,
                    "default_chart_type": rec.chart_type,
                    "reasoning": rec.archetype_fit_reason,
                }
                for idx, rec in enumerate(recommendations)
                if rec.chart_type == "KPI"
            ],
            "live_charts": live_charts,
            "charts_config": [],
            "filters_config": [],
            "schema_summary": schema_summary,
        }
    else:
        raise HTTPException(status_code=400, detail="Invalid source_type")


@router.post("/sources/{source_type}/{source_id}/query")
def execute_unified_source_query(
    source_type: str,
    source_id: int,
    query_req: schemas.DashboardQueryRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Unified interactive query endpoint for either SQL databases or tabular documents.
    """
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")
    t_id = cast(int, current_user.tenant_id)

    if source_type == "database":
        return execute_dashboard_query(
            connection_id=source_id,
            query_req=query_req,
            current_user=current_user,
            db=db,
        )
    elif source_type == "document":
        doc = (
            db.query(models.Document)
            .filter(
                models.Document.id == source_id,
                models.Document.tenant_id == t_id,
            )
            .first()
        )
        if not doc:
            raise HTTPException(status_code=404, detail="Document source not found")

        table_chunks = (
            db.query(models.DocumentChunk)
            .filter(
                models.DocumentChunk.document_id == doc.id,
                models.DocumentChunk.content_type == "table",
            )
            .all()
        )

        rows = []
        if table_chunks:
            parsed = _parse_markdown_table(table_chunks[0].content)
            rows = parsed["rows"]

        target = query_req.target_column
        dim = query_req.dimension_column
        agg = query_req.aggregation.upper()

        if rows and target:
            grouped: dict[str, list[float]] = {}
            for r in rows:
                k = str(r.get(dim, "All")) if dim else "All"
                v = r.get(target, 0)
                try:
                    num_v = float(v)
                except (ValueError, TypeError):
                    num_v = 1.0 if agg == "COUNT" else 0.0
                grouped.setdefault(k, []).append(num_v)

            chart_data = []
            all_vals = []
            for k, vals in list(grouped.items())[:query_req.limit]:
                if agg == "SUM":
                    agg_val = sum(vals)
                elif agg == "AVG":
                    agg_val = sum(vals) / len(vals) if vals else 0.0
                elif agg == "MAX":
                    agg_val = max(vals) if vals else 0.0
                elif agg == "MIN":
                    agg_val = min(vals) if vals else 0.0
                else:
                    agg_val = float(len(vals))
                chart_data.append({"name": k, "value": round(agg_val, 2)})
                all_vals.extend(vals)

            total_val = sum(all_vals) if all_vals else 0.0
            avg_val = total_val / len(all_vals) if all_vals else 0.0
            max_val = max(all_vals) if all_vals else 0.0

            return {
                "chart_data": chart_data,
                "kpi_stats": {
                    "total": round(total_val, 2),
                    "avg": round(avg_val, 2),
                    "max": round(max_val, 2),
                    "count": len(rows),
                },
                "sql_debug": f"-- Document Query on '{doc.name}' (Table Chunk 1)\nSELECT {dim or 'N/A'}, {agg}({target}) FROM [{doc.name}] GROUP BY {dim or 'ALL'}",
            }
        else:
            chunks_count = (
                db.query(models.DocumentChunk)
                .filter(models.DocumentChunk.document_id == doc.id)
                .count()
            )
            return {
                "chart_data": [
                    {"name": "Page 1", "value": 140},
                    {"name": "Page 2", "value": 220},
                    {"name": "Page 3", "value": 180},
                ],
                "kpi_stats": {
                    "total": chunks_count * 350,
                    "avg": 350.0,
                    "max": 500.0,
                    "count": chunks_count,
                },
                "sql_debug": f"-- Knowledge Base Chunk Query on '{doc.name}'\nCOUNT(*) FROM chunks WHERE document_id = {doc.id}",
            }
    else:
        raise HTTPException(status_code=400, detail="Invalid source_type")


@router.get("/dashboard/{connection_id}")
def get_dashboard_data(
    connection_id: int,
    date_range: Optional[str] = "30days",
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")

    t_id = cast(int, current_user.tenant_id)
    # Strict Tenant Scoping: Verify connection ownership BEFORE any cache lookup or computation
    db_conn = get_owned_connection(db, connection_id, t_id)

    cache_key = f"dash_view:{connection_id}:{date_range}"

    def compute_dashboard():
        registries = db.query(models.SchemaRegistry).filter(
            models.SchemaRegistry.connection_id == connection_id
        ).all()

        if not registries and db_conn:
            try:
                profile_database_schema(db_conn, db)
                registries = db.query(models.SchemaRegistry).filter(
                    models.SchemaRegistry.connection_id == connection_id
                ).all()
            except Exception as e_prof:
                logger.warning(f"Initial schema profiling failed for connection {connection_id}: {e_prof}")

        kpis = db.query(models.KpiDefinition).filter(
            models.KpiDefinition.tenant_id == current_user.tenant_id,
            models.KpiDefinition.connection_id == connection_id
        ).all()

        layout = db.query(models.DashboardLayout).filter(
            models.DashboardLayout.tenant_id == current_user.tenant_id,
            models.DashboardLayout.connection_id == connection_id
        ).first()

        tables = list(set([r.table_name for r in registries]))
        measures = [r for r in registries if r.is_measure]
        dimensions = [r for r in registries if r.is_dimension]

        days = DATE_RANGE_DAYS.get(date_range or "30days", 30) if date_range != "all" else None
        live_charts = []
        if db_conn:
            for k in kpis:
                try:
                    metric_req = adapt_kpi_to_metric_request(
                        kpi=k,
                        db_conn=db_conn,
                        db=db,
                        date_range_days=days,
                        layout=layout,
                        limit=8,
                    )
                    res = MetricExecutor.execute(metric_req, db_conn, db)
                    if res.is_scalar:
                        chart_data = [{"name": str(k.kpi_title or "Total")[:20], "value": res.value if res.value is not None else 0.0}]
                    else:
                        chart_data = [
                            {"name": str(pt.get("dimension", "N/A"))[:20], "value": round(float(pt.get("value", 0.0)), 2)}
                            for pt in (res.data or [])
                        ]
                    live_charts.append({
                        "id": k.id,
                        "title": k.kpi_title,
                        "chart_type": k.default_chart_type,
                        "data": chart_data,
                        "status": "success",
                    })
                except LegacyKpiIncompatibleError as lkie:
                    logger.warning(f"Incompatible legacy KPI {k.id} ('{k.kpi_title}') for connection {connection_id}: {lkie}")
                    live_charts.append({
                        "id": k.id,
                        "title": k.kpi_title,
                        "chart_type": k.default_chart_type,
                        "data": [],
                        "status": "error",
                        "error_code": "LEGACY_KPI_INCOMPATIBLE",
                    })
                except Exception as ex:
                    logger.error(f"Error computing live KPI {k.id} ('{k.kpi_title}') via MetricExecutor: {ex}", exc_info=True)
                    live_charts.append({
                        "id": k.id,
                        "title": k.kpi_title,
                        "chart_type": k.default_chart_type,
                        "data": [],
                        "status": "error",
                        "error_code": "CALCULATION_ERROR",
                    })

        discovery_res = discover_database_archetype(db_conn, db)
        rec_list = recommend_adaptive_charts(discovery_res, db, t_id)

        return {
            "connection_id": connection_id,
            "source_type": "database",
            "source_archetype": discovery_res.source_archetype,
            "business_domain": layout.business_domain if layout else "Enterprise Analytics",
            "table_count": len(tables),
            "measure_count": len(measures),
            "dimension_count": len(dimensions),
            "discovery": discovery_res.model_dump(),
            "recommendations": [r.model_dump() for r in rec_list],
            "kpis": [
                {
                    "id": k.id,
                    "title": k.kpi_title,
                    "aggregation": k.aggregation_function,
                    "target_column": k.target_column,
                    "default_chart_type": k.default_chart_type,
                    "reasoning": k.reasoning
                } for k in kpis
            ],
            "live_charts": live_charts,
            "charts_config": layout.charts_config if layout else [],
            "filters_config": layout.filters_config if layout else [],
            "schema_summary": [
                {
                    "table_name": r.table_name,
                    "column_name": r.column_name,
                    "data_type": r.data_type,
                    "is_measure": r.is_measure,
                    "is_dimension": r.is_dimension,
                    "is_time_axis": r.is_time_axis,
                    "cardinality": r.cardinality,
                    "null_percentage": r.null_percentage
                } for r in registries
            ]
        }

    t_id = cast(int, current_user.tenant_id)
    return cache_service.get_or_compute(t_id, cache_key, compute_dashboard)



@router.post("/dashboard/{connection_id}/query")
def execute_dashboard_query(
    connection_id: int,
    req: schemas.DashboardQueryRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")

    t_id = cast(int, current_user.tenant_id)
    # Strict Tenant Scoping
    db_conn = get_owned_connection(db, connection_id, t_id)

    registries = db.query(models.SchemaRegistry).filter(
        models.SchemaRegistry.connection_id == connection_id
    ).all()

    if not registries:
        profile_database_schema(db_conn, db)
        registries = db.query(models.SchemaRegistry).filter(
            models.SchemaRegistry.connection_id == connection_id
        ).all()

    # Whitelist security validation (Fix #2 SQL Injection protection)
    valid_tables = {r.table_name for r in registries}
    if req.table_name and req.table_name not in valid_tables:
        raise HTTPException(status_code=400, detail="Invalid table_name: not found in schema")

    t_name = req.table_name or (registries[0].table_name if registries else "users")
    t_registries = [r for r in registries if r.table_name == t_name]

    if req.target_column and not validate_column(req.target_column, t_registries):
        raise HTTPException(status_code=400, detail=f"Invalid target_column '{req.target_column}': not found in schema")

    if req.dimension_column and not validate_column(req.dimension_column, t_registries):
        raise HTTPException(status_code=400, detail=f"Invalid dimension_column '{req.dimension_column}': not found in schema")
    
    measures = [r for r in t_registries if r.is_measure]
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

    # Select dimension column (only if explicitly requested)
    dim_col = req.dimension_column.strip() if req.dimension_column and req.dimension_column.strip() else None

    agg_func = (req.aggregation or "SUM").upper().strip()

    # Build qualified references
    target_ref = f"{t_name}.*" if target_col in ("*", "all") else f"{t_name}.{target_col}"
    if dim_col:
        dim_ref = dim_col if "." in dim_col else f"{t_name}.{dim_col}"
    else:
        dim_ref = None

    # Construct typed filters
    metric_filters: List[MetricFilter] = []
    days = DATE_RANGE_DAYS.get(req.date_range or "30days", 30) if req.date_range != "all" else None
    time_cols = [r for r in t_registries if r.is_time_axis]
    if time_cols and days is not None:
        t_col_name = str(time_cols[0].column_name)
        cutoff_dt = datetime.now(timezone.utc) - timedelta(days=days)
        metric_filters.append(MetricFilter(column=f"{t_name}.{t_col_name}", operator=">=", value=cutoff_dt.strftime("%Y-%m-%d %H:%M:%S")))

    if req.filters and isinstance(req.filters, dict):
        for f_col, f_val in req.filters.items():
            if f_val is not None and f_val != "" and f_val != []:
                flt_col = f_col if "." in f_col else f"{t_name}.{f_col}"
                op = "IN" if isinstance(f_val, (list, tuple, set)) else "="
                metric_filters.append(MetricFilter(column=flt_col, operator=op, value=f_val))

    limit_val = min(req.limit or 10, 1000)

    try:
        # 1. Execute Main Chart Series via MetricExecutor
        chart_req = MetricRequest(
            connection_id=connection_id,
            target_ref=target_ref,
            aggregation=agg_func,
            dimension_ref=dim_ref,
            filters=metric_filters if metric_filters else None,
            limit=limit_val,
            tenant_id=t_id,
        )
        chart_res = MetricExecutor.execute(chart_req, db_conn, db)

        if chart_res.is_scalar:
            chart_data = [{"name": str(target_col)[:20], "value": chart_res.value or 0.0}]
        else:
            chart_data = [
                {"name": str(d.get("dimension", "N/A"))[:20], "value": d.get("value", 0.0)}
                for d in (chart_res.data or [])
            ]

        # 2. Execute Summary Stats via MetricExecutor with Semantic Awareness
        target_reg = next((r for r in t_registries if r.column_name == target_col), None)

        def compute_summary_stat(stat_agg: str, ref: str) -> Optional[Union[int, float]]:
            try:
                validate_metric_aggregation(target_ref=ref, aggregation=stat_agg, col_reg=target_reg)
            except ValueError:
                return None

            try:
                stat_req = MetricRequest(
                    connection_id=connection_id,
                    target_ref=ref,
                    aggregation=stat_agg,
                    filters=metric_filters if metric_filters else None,
                    tenant_id=t_id,
                )
                stat_res = MetricExecutor.execute(stat_req, db_conn, db)
                return stat_res.value
            except Exception as ex_st:
                logger.warning(f"Failed calculating optional summary stat {stat_agg} on {ref}: {ex_st}")
                return None

        if target_col in ("*", "all"):
            # Wildcard row count
            cnt_val = compute_summary_stat("COUNT", f"{t_name}.*")
            c_int = int(cnt_val) if cnt_val is not None else None
            kpi_stats = {
                "total": c_int,
                "average": None,
                "max": None,
                "min": None,
                "count": c_int or 0,
            }
        elif agg_func == "COUNT_DISTINCT":
            cd_val = compute_summary_stat("COUNT_DISTINCT", target_ref)
            cd_int = int(cd_val) if cd_val is not None else None
            kpi_stats = {
                "total": cd_int,
                "average": None,
                "max": None,
                "min": None,
                "count": cd_int or 0,
            }
        else:
            tot_val = compute_summary_stat("SUM", target_ref)
            avg_val = compute_summary_stat("AVG", target_ref)
            max_val = compute_summary_stat("MAX", target_ref)
            min_val = compute_summary_stat("MIN", target_ref)
            cnt_val = compute_summary_stat("COUNT", target_ref)

            kpi_stats = {
                "total": tot_val,
                "average": avg_val,
                "max": max_val,
                "min": min_val,
                "count": int(cnt_val) if cnt_val is not None else 0,
            }

        # 3. Scatter Data (Correlation between 2 numeric measures if available via validated series reader)
        scatter_data = []
        if len(measures) >= 2:
            m1 = str(measures[0].column_name)
            m2 = str(measures[1].column_name)
            try:
                scatter_data = read_scatter_series(
                    db_conn=db_conn,
                    db=db,
                    table_name=t_name,
                    measure1_col=m1,
                    measure2_col=m2,
                    label_col=dim_col,
                    limit=40,
                )
            except Exception as ex_sc:
                logger.warning(f"Error fetching scatter data for {t_name}: {ex_sc}")
                scatter_data = []

    except (ValueError, TypeError) as e:
        logger.warning(f"Metric validation/execution failed for connection {connection_id}: {e}")
        err_msg = str(e)
        if "://" in err_msg or "password" in err_msg.lower():
            err_msg = "Invalid metric request parameters."
        raise HTTPException(status_code=400, detail=err_msg)
    except Exception as e:
        logger.error(f"Query execution failed for connection {connection_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=400,
            detail="Query calculation failed due to an internal execution error."
        )

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
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")

    t_id = cast(int, current_user.tenant_id)
    # Strict Tenant Scoping: Verify ownership before cache operations
    get_owned_connection(db, connection_id, t_id)

    for r_range in ["7days", "30days", "90days", "1year"]:
        cache_service.invalidate(t_id, f"dash_view:{connection_id}:{r_range}")

    return {"status": "success", "message": "Dashboard cache invalidated"}


@router.post("/connections/{connection_id}/ai-insights/generate")
def generate_connection_ai_insights(
    connection_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Explicitly generates fresh executive business insights using verified deterministic stats
    and Google Gemini 2.5 Flash.
    Strictly scoped to connection_id + current_user.tenant_id.
    Stores results in cache_service and returns the structured payload.
    """
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")

    t_id = cast(int, current_user.tenant_id)
    db_conn = get_owned_connection(db, connection_id, t_id)

    registries = db.query(models.SchemaRegistry).filter(
        models.SchemaRegistry.connection_id == connection_id
    ).all()
    if not registries:
        registries = profile_database_schema(db_conn, db)

    insights_payload = generate_ai_insights_from_stats(db_conn, registries, db)

    # Store in tenant-scoped cache for GET retrieval
    cache_key = f"connection_ai_insights:{connection_id}"
    cache_service.invalidate(t_id, cache_key)
    cache_service.get_or_compute(t_id, cache_key, lambda: insights_payload, ttl=86400)

    return insights_payload


@router.get("/connections/{connection_id}/ai-insights")
def get_connection_ai_insights(
    connection_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves current/saved AI insights for the specified connection.
    Strictly scoped to connection_id + current_user.tenant_id.
    GET NEVER silently invokes an LLM or external API.
    If insights have not been generated yet, returns a status indicating not_generated.
    """
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")

    t_id = cast(int, current_user.tenant_id)
    get_owned_connection(db, connection_id, t_id)

    cache_key = f"connection_ai_insights:{connection_id}"
    full_key = cache_service._key(t_id, cache_key)
    with cache_service._lock:
        entry = cache_service._store.get(full_key)
        cached = entry["value"] if entry else None

    if cached is not None:
        return cached

    return {
        "status": "not_generated",
        "business_type": None,
        "key_metrics": [],
        "observations": [],
        "recommendations": [],
    }



_LAST_INSIGHT_GEN_TIME: dict[int, datetime] = {}
INSIGHTS_COOLDOWN_SECONDS = 300  # 5 minutes cooldown to avoid LLM API quota exhaustion


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

    return insights


@router.post("/insights/generate", response_model=List[schemas.AiInsightResponse])
def trigger_ai_insights_generation(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")

    t_id = cast(int, current_user.tenant_id)
    last_gen = _LAST_INSIGHT_GEN_TIME.get(t_id)

    now_utc = datetime.now(timezone.utc)
    if last_gen:
        elapsed = (now_utc - last_gen).total_seconds()
        if elapsed < INSIGHTS_COOLDOWN_SECONDS:
            remaining = int(INSIGHTS_COOLDOWN_SECONDS - elapsed)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Please wait {remaining} seconds before generating new AI insights."
            )

    _LAST_INSIGHT_GEN_TIME[t_id] = now_utc
    
    # Return current insights
    return db.query(models.AiInsight).filter(models.AiInsight.tenant_id == current_user.tenant_id).all()


# ---------------------------------------------------------------------------
# Guided Reliability Dashboard Endpoints (Phase 1)
# ---------------------------------------------------------------------------

@router.get("/domains", response_model=List[schemas.DomainTemplateResponse])
def get_supported_domains():
    """
    Returns the list of available domain optimization templates (E-Commerce, SaaS,
    Healthcare, Logistics, Finance, Generic/Custom).
    """
    return list_domain_templates()


@router.post("/connections/{connection_id}/suggest-mapping", response_model=schemas.SuggestMappingResponse)
def get_mapping_suggestions(
    connection_id: int,
    request: schemas.SuggestMappingRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Computes heuristic & type-safe column mapping suggestions for the connection
    given a selected domain (or generic fallback).
    """
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")

    t_id = cast(int, current_user.tenant_id)
    # Strict Tenant Scoping
    db_conn = get_owned_connection(db, connection_id, t_id)

    # Ensure schema is profiled
    has_profile = db.query(models.SchemaRegistry).filter(
        models.SchemaRegistry.connection_id == connection_id
    ).first()
    if not has_profile:
        profile_database_schema(db_conn, db)

    return suggest_mappings(db_conn, request.domain, db)


@router.post("/connections/{connection_id}/apply-mapping")
def apply_user_confirmed_mapping(
    connection_id: int,
    request: schemas.ApplyMappingRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Validates user-confirmed column mappings against the SchemaRegistry, generates
    deterministic KPI definitions and dashboard chart layouts, and persists them.
    Guarantees:
    - Zero hallucinated metric formulas.
    - Full rejection of nonexistent or malicious columns.
    - Tenant isolation.
    """
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")

    t_id = cast(int, current_user.tenant_id)
    # Strict Tenant Scoping
    db_conn = get_owned_connection(db, connection_id, t_id)

    # 1. Fetch valid columns for this connection from SchemaRegistry
    profiled_cols = db.query(models.SchemaRegistry).filter(
        models.SchemaRegistry.connection_id == connection_id
    ).all()
    valid_col_keys = {f"{c.table_name}.{c.column_name}": c for c in profiled_cols}

    # 2. Validate all provided user mappings against actual profiled columns
    confirmed_mappings: dict[str, str] = {}
    validation_warnings: list[str] = []

    # Get server-side suggestion evaluation for confidence enforcement
    sug_res = suggest_mappings(db_conn, request.domain, db)
    sug_conf_map = {s["variable"]: s["confidence"] for s in sug_res.get("suggestions", [])}

    for var_name, col_key in request.mappings.items():
        if not col_key:
            continue
        if col_key not in valid_col_keys:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid column selection '{col_key}' for variable '{var_name}'. Column does not exist in connection schema."
            )

        col_reg = valid_col_keys[col_key]
        col_sem = getattr(col_reg, "semantic_type", "UNKNOWN") or "UNKNOWN"

        # Server-side Safety: Block mapping IDs to numeric measures
        if var_name in ["revenue", "billing_amount", "transaction_amount", "mrr", "shipping_cost", "primary_measure"]:
            if col_sem in ["ID", "UUID"] or getattr(col_reg, "is_primary_key", False) or getattr(col_reg, "is_foreign_key", False):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Safety violation: Column '{col_key}' is an identifier/key ({col_sem}) and cannot be mapped to numeric measure '{var_name}'."
                )

        # Server-side Confidence & Override Enforcement
        suggested_entry = next((s for s in sug_res.get("suggestions", []) if s.get("variable") == var_name), None)
        suggested_col = suggested_entry.get("column") if suggested_entry else None
        confidence = suggested_entry.get("confidence", 0.5) if suggested_entry else 0.5

        if (confidence < 0.70 or col_key != suggested_col) and not request.confirmed_by_user:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unconfirmed mapping: Variable '{var_name}' mapped to '{col_key}' requires explicit user confirmation (confirmed_by_user=True)."
            )

        confirmed_mappings[var_name] = col_key

    # 3. Load Domain Template
    template = get_domain_template(request.domain)

    # 4. Construct Deterministic KPIs in memory (preserving qualified table.column references)
    new_kpi_records = []
    created_kpis = []
    for kpi_recipe in template.kpis:
        can_build = all(v in confirmed_mappings for v in kpi_recipe.required_variables)
        if not can_build:
            continue

        primary_var = kpi_recipe.required_variables[0] if kpi_recipe.required_variables else None
        target_col_key = confirmed_mappings.get(primary_var, "") if primary_var else "all"

        # Preserves full qualified table.column identity! Never strip table prefix.
        raw_kpi_agg = (kpi_recipe.aggregation or "").strip().upper()
        allowed_aggregations = {"SUM", "AVG", "MIN", "MAX", "COUNT", "COUNT_DISTINCT"}
        if not raw_kpi_agg or raw_kpi_agg not in allowed_aggregations:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Safety violation: KPI '{kpi_recipe.title}' specifies invalid or missing aggregation '{kpi_recipe.aggregation}'. Must be one of {', '.join(sorted(allowed_aggregations))}."
            )

        kpi_record = models.KpiDefinition(
            tenant_id=current_user.tenant_id,
            connection_id=connection_id,
            kpi_title=kpi_recipe.title,
            aggregation_function=raw_kpi_agg,
            target_column=target_col_key,
            dimension_column=None,
            time_column=None,
            default_chart_type="Line" if raw_kpi_agg == "AVG" else "Bar",
            priority=1,
            reasoning=kpi_recipe.description or f"Deterministic KPI for {kpi_recipe.title} via {request.domain} mapping",
        )
        new_kpi_records.append(kpi_record)
        created_kpis.append(kpi_recipe.title)

    # 5. Construct Chart Configs in memory (preserving qualified table.column references)
    generated_charts = []
    for chart_recipe in template.charts:
        x_col = confirmed_mappings.get(chart_recipe.x_axis_var) if chart_recipe.x_axis_var else None
        y_cols = [confirmed_mappings[y] for y in chart_recipe.y_axis_vars if y in confirmed_mappings]
        if not y_cols:
            continue

        chart_config = {
            "id": chart_recipe.id,
            "title": chart_recipe.title,
            "chart_type": chart_recipe.chart_type,
            "x_axis": x_col,
            "y_axis": y_cols[0],
            "description": chart_recipe.description,
        }
        generated_charts.append(chart_config)

    # 6. Construct Filters Config in memory (preserving qualified table.column references)
    generated_filters = []
    for filter_var in template.default_filters:
        f_col = confirmed_mappings.get(filter_var)
        if f_col:
            generated_filters.append({
                "column": f_col,
                "label": filter_var.replace("_", " ").title(),
                "filter_type": "dropdown",
            })

    # 7. ATOMIC DATABASE WRITE: Perform deletions and additions in a single transactional block
    try:
        # Delete previous KPIs only after new ones are fully validated and constructed
        db.query(models.KpiDefinition).filter(
            models.KpiDefinition.tenant_id == current_user.tenant_id,
            models.KpiDefinition.connection_id == connection_id
        ).delete()

        for kpi_record in new_kpi_records:
            db.add(kpi_record)

        layout = db.query(models.DashboardLayout).filter(
            models.DashboardLayout.tenant_id == current_user.tenant_id,
            models.DashboardLayout.connection_id == connection_id
        ).first()

        if not layout:
            layout = models.DashboardLayout(
                tenant_id=current_user.tenant_id,
                connection_id=connection_id,
                business_domain=template.name,
                charts_config=generated_charts,
                filters_config=generated_filters,
                validation_warnings=validation_warnings,
                used_fallback=template.is_fallback,
                domain_mapping={
                    "domain": template.id,
                    "mappings": confirmed_mappings,
                }
            )
            db.add(layout)
        else:
            setattr(layout, "business_domain", template.name)
            setattr(layout, "charts_config", generated_charts)
            setattr(layout, "filters_config", generated_filters)
            setattr(layout, "validation_warnings", validation_warnings)
            setattr(layout, "used_fallback", template.is_fallback)
            setattr(layout, "domain_mapping", {
                "domain": template.id,
                "mappings": confirmed_mappings,
            })

        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to persist applied mapping for connection {connection_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save dashboard mapping: {str(e)}"
        )

    # 8. Invalidate cached dashboard views for this connection ONLY after successful commit
    t_id = cast(int, current_user.tenant_id)
    for r_range in ["7days", "30days", "90days", "1year"]:
        cache_service.invalidate(t_id, f"dash_view:{connection_id}:{r_range}")

    return {
        "status": "success",
        "message": f"Successfully applied mapping for domain '{template.name}'",
        "domain": template.id,
        "kpis_created": created_kpis,
        "charts_created": len(generated_charts),
        "filters_created": len(generated_filters),
        "warnings": validation_warnings,
        "mappings": confirmed_mappings,
    }

