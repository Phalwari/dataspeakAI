import logging
from sqlalchemy.orm import Session
import models

logger = logging.getLogger(__name__)

def select_chart_type(
    is_time_series: bool, 
    has_dimension: bool, 
    measure_count: int, 
    dimension_cardinality: int = 5
) -> str:
    """
    Applies rule-based decision tree to select optimal visualization chart type
    based on the SPECIFIC chart's axes and data shape.
    """
    if is_time_series:
        if has_dimension:
            return "Area"
        return "Line"
    if has_dimension:
        if dimension_cardinality <= 8:
            return "Donut"
        return "Bar"
    if measure_count >= 2:
        return "Scatter"
    return "Bar"

def generate_kpis_and_chart_specs(tenant_id: int, connection_id: int, db: Session) -> list[models.KpiDefinition]:
    """
    Analyzes SchemaRegistry for the connection, generates diverse KPI specifications,
    maps appropriate default chart types using select_chart_type, builds filter specs,
    and saves to kpi_definitions and dashboard_layouts.
    """
    schema_entries = db.query(models.SchemaRegistry).filter(
        models.SchemaRegistry.connection_id == connection_id
    ).all()

    if not schema_entries:
        return []

    # Clear previous KPI definitions for this connection
    db.query(models.KpiDefinition).filter(
        models.KpiDefinition.tenant_id == tenant_id,
        models.KpiDefinition.connection_id == connection_id
    ).delete()

    measures = [s for s in schema_entries if s.is_measure]
    dimensions = [s for s in schema_entries if s.is_dimension]
    time_axes = [s for s in schema_entries if s.is_time_axis]

    kpi_list = []
    charts_config = []
    filters_config = []

    # 1. Generate Filters from dimensions and time axes
    for dim in dimensions:
        filters_config.append({
            "column": f"{dim.table_name}.{dim.column_name}",
            "filter_type": "multiselect",
            "label": dim.column_name.replace("_", " ").title()
        })
    for t_col in time_axes:
        filters_config.append({
            "column": f"{t_col.table_name}.{t_col.column_name}",
            "filter_type": "date_range",
            "label": t_col.column_name.replace("_", " ").title()
        })

    # 2. Build diverse KPIs across tables
    tables = list(set([s.table_name for s in schema_entries]))

    for t_name in tables:
        t_measures = [m for m in measures if m.table_name == t_name]
        t_dims = [d for d in dimensions if d.table_name == t_name]
        t_times = [t for t in time_axes if t.table_name == t_name]

        # A. Primary Measure SUM by Category Dimension
        if t_measures and t_dims:
            m = t_measures[0]
            dim_entry = t_dims[0]
            card = int(dim_entry.cardinality) if dim_entry.cardinality is not None else 5
            chart_type = select_chart_type(is_time_series=False, has_dimension=True, measure_count=len(t_measures), dimension_cardinality=card)
            
            clean_m = m.column_name.replace("_", " ").title()
            clean_d = dim_entry.column_name.replace("_", " ").title()
            kpi = models.KpiDefinition(
                tenant_id=tenant_id,
                connection_id=connection_id,
                kpi_title=f"Total {clean_m} by {clean_d}",
                aggregation_function="SUM",
                target_column=f"{t_name}.{m.column_name}",
                dimension_column=f"{t_name}.{dim_entry.column_name}",
                time_column=None,
                default_chart_type=chart_type,
                priority=1,
                reasoning=f"High-impact business measure {clean_m} grouped by {clean_d}"
            )
            db.add(kpi)
            kpi_list.append(kpi)
            charts_config.append({
                "chart_type": chart_type.lower(),
                "title": f"Total {clean_m} by {clean_d}",
                "x_axis_column": f"{t_name}.{dim_entry.column_name}",
                "y_axis_column": f"{t_name}.{m.column_name}",
                "x_axis_label": clean_d,
                "y_axis_label": clean_m
            })

        # B. Average Measure KPI
        if t_measures:
            m = t_measures[0]
            clean_m = m.column_name.replace("_", " ").title()
            dim_col = f"{t_name}.{t_dims[1].column_name}" if len(t_dims) > 1 else (f"{t_name}.{t_dims[0].column_name}" if t_dims else None)
            dim_card = int(t_dims[1].cardinality) if len(t_dims) > 1 and t_dims[1].cardinality is not None else (int(t_dims[0].cardinality) if t_dims and t_dims[0].cardinality is not None else 5)
            chart_type = select_chart_type(is_time_series=False, has_dimension=bool(dim_col), measure_count=len(t_measures), dimension_cardinality=dim_card)
            
            kpi_avg = models.KpiDefinition(
                tenant_id=tenant_id,
                connection_id=connection_id,
                kpi_title=f"Average {clean_m}",
                aggregation_function="AVG",
                target_column=f"{t_name}.{m.column_name}",
                dimension_column=dim_col,
                time_column=None,
                default_chart_type=chart_type,
                priority=2,
                reasoning=f"Unit economics baseline tracking average {clean_m}"
            )
            db.add(kpi_avg)
            kpi_list.append(kpi_avg)

        # C. Time-series Trend Line KPI if date column exists
        if t_measures and t_times:
            m = t_measures[0]
            t_col = t_times[0]
            clean_m = m.column_name.replace("_", " ").title()
            clean_t = t_col.column_name.replace("_", " ").title()
            
            kpi_trend = models.KpiDefinition(
                tenant_id=tenant_id,
                connection_id=connection_id,
                kpi_title=f"{clean_m} Trend Over Time",
                aggregation_function="SUM",
                target_column=f"{t_name}.{m.column_name}",
                dimension_column=None,
                time_column=f"{t_name}.{t_col.column_name}",
                default_chart_type="Line",
                priority=3,
                reasoning=f"Historical performance tracking across {clean_t}"
            )
            db.add(kpi_trend)
            kpi_list.append(kpi_trend)
            charts_config.append({
                "chart_type": "line",
                "title": f"{clean_m} Trend",
                "x_axis_column": f"{t_name}.{t_col.column_name}",
                "y_axis_column": f"{t_name}.{m.column_name}",
                "x_axis_label": clean_t,
                "y_axis_label": clean_m
            })

        # D. Table Volume / Record Count KPI
        kpi_cnt = models.KpiDefinition(
            tenant_id=tenant_id,
            connection_id=connection_id,
            kpi_title=f"Total {t_name.title()} Volume",
            aggregation_function="COUNT",
            target_column=f"{t_name}.*",
            dimension_column=f"{t_name}.{t_dims[0].column_name}" if t_dims else None,
            time_column=f"{t_name}.{t_times[0].column_name}" if t_times else None,
            default_chart_type="Bar" if t_dims else "Line",
            priority=4,
            reasoning=f"Operational volume tracking total records in {t_name}"
        )
        db.add(kpi_cnt)
        kpi_list.append(kpi_cnt)

    # 3. Update DashboardLayout in DB with charts_config and filters_config
    layout = db.query(models.DashboardLayout).filter(
        models.DashboardLayout.tenant_id == tenant_id,
        models.DashboardLayout.connection_id == connection_id
    ).first()

    if not layout:
        layout = models.DashboardLayout(
            tenant_id=tenant_id,
            connection_id=connection_id,
            layout_name="Auto BI Dashboard",
            business_domain="Business Operations Analytics",
            charts_config=charts_config,
            filters_config=filters_config,
            validation_warnings=[],
            used_fallback=True
        )
        db.add(layout)
    else:
        layout.charts_config = charts_config
        layout.filters_config = filters_config

    db.commit()
    return kpi_list
