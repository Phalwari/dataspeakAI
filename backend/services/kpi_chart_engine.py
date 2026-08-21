import logging
from sqlalchemy.orm import Session
import models

logger = logging.getLogger(__name__)

def select_chart_type(
    has_time: bool, 
    has_dimension: bool, 
    measure_count: int, 
    dimension_cardinality: int = 5
) -> str:
    """
    Applies rule-based decision tree to select optimal visualization chart type.
    """
    if has_time and measure_count == 1 and not has_dimension:
        return "Line"
    if has_time and has_dimension:
        return "Area"
    if has_dimension and not has_time:
        if dimension_cardinality <= 8:
            return "Donut"
        return "Bar"
    if measure_count >= 2:
        return "Scatter"
    return "Bar"

def generate_kpis_and_chart_specs(tenant_id: int, connection_id: int, db: Session) -> list[models.KpiDefinition]:
    """
    Analyzes SchemaRegistry for the connection, generates KPI specifications,
    maps appropriate default chart types, and saves to kpi_definitions.
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
    db.commit()

    measures = [s for s in schema_entries if s.is_measure]
    dimensions = [s for s in schema_entries if s.is_dimension]
    time_axes = [s for s in schema_entries if s.is_time_axis]

    # Filter out pure ID columns from primary measures list if non-ID measures exist
    non_id_measures = [m for m in measures if not m.column_name.lower().endswith("id") and m.column_name.lower() != "id"]
    target_measures = non_id_measures if non_id_measures else measures

    kpi_list = []
    chart_types = ["Bar", "Donut", "Line", "Area"]

    # 1. Group measures by table and prioritize tables with text dimensions/time axes
    tables_with_measures = list(set([m.table_name for m in target_measures]))
    tables_with_dims = [t for t in tables_with_measures if any(d.table_name == t for d in dimensions) or any(tx.table_name == t for tx in time_axes)]
    target_tables = tables_with_dims if tables_with_dims else tables_with_measures

    for t_name in target_tables:
        t_measures = [m for m in target_measures if m.table_name == t_name]
        t_dims = [d for d in dimensions if d.table_name == t_name]
        t_times = [t for t in time_axes if t.table_name == t_name]

        for m in t_measures:
            if len(kpi_list) >= 4:
                break
                
            # Pick a dimension from the SAME table
            dim_entry = t_dims[len(kpi_list) % len(t_dims)] if t_dims else None
            time_entry = t_times[0] if t_times else None

            if not dim_entry and not time_entry:
                continue

            dim_col = f"{t_name}.{dim_entry.column_name}" if dim_entry else None
            time_col = f"{t_name}.{time_entry.column_name}" if time_entry else None


            chart_type = chart_types[len(kpi_list) % len(chart_types)]
            if time_entry and len(kpi_list) == 2:
                chart_type = "Line"

            clean_m_name = m.column_name.replace("_", " ").title()
            clean_d_name = dim_entry.column_name.replace("_", " ").title() if dim_entry else ""
            
            if dim_entry:
                kpi_title = f"{t_name} {clean_m_name} by {clean_d_name}"
            else:
                kpi_title = f"Total {t_name} {clean_m_name}"

            target_col = f"{t_name}.{m.column_name}"

            kpi = models.KpiDefinition(
                tenant_id=tenant_id,
                connection_id=connection_id,
                kpi_title=kpi_title,
                aggregation_function="SUM",
                target_column=target_col,
                dimension_column=dim_col,
                time_column=time_col,
                default_chart_type=chart_type
            )
            db.add(kpi)
            kpi_list.append(kpi)

        if len(kpi_list) >= 4:
            break


    # 2. If no measures exist, create table record count KPIs
    if not kpi_list and schema_entries:
        tables = list(set([s.table_name for s in schema_entries]))
        for idx, t_name in enumerate(tables[:4]):
            t_dims = [s for s in schema_entries if s.table_name == t_name and s.is_dimension]
            dim_col = f"{t_name}.{t_dims[0].column_name}" if t_dims else None
            kpi = models.KpiDefinition(
                tenant_id=tenant_id,
                connection_id=connection_id,
                kpi_title=f"Total Records in {t_name}",
                aggregation_function="COUNT",
                target_column=f"{t_name}.*",
                dimension_column=dim_col,
                default_chart_type=chart_types[idx % len(chart_types)]
            )
            db.add(kpi)
            kpi_list.append(kpi)

    db.commit()
    return kpi_list

