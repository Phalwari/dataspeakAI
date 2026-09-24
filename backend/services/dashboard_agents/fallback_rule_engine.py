"""
fallback_rule_engine.py
------------------------
Agar 4-agent LLM pipeline kisi bhi wajah se fail ho (timeout, API down,
malformed output jo validator bhi na bacha sake), ye deterministic
rule-based engine turant chalta hai. Simple hai (keyword + cardinality
based) lekin GUARANTEED kaam karta hai — dashboard kabhi khaali screen
nahi dikhata.
"""

from .schemas import ValidatedDashboardConfig, KpiSpec, ChartSpec, FilterSpec

MEASURE_KEYWORDS = {"amount", "revenue", "sales", "price", "total", "qty", "cost", "profit", "value"}
CARDINALITY_DIMENSION_THRESHOLD = 8


def _get_role(column) -> str:
    role = getattr(column, "role", "ignore")
    return role.value if hasattr(role, "value") else str(role)


def generate_fallback_config(table_profiles: list) -> ValidatedDashboardConfig:
    kpis, charts, filters = [], [], []

    for tp in table_profiles:
        measures = [c for c in tp.columns if _get_role(c) == "measure"]
        dimensions = [c for c in tp.columns if _get_role(c) == "dimension"]
        time_cols = [c for c in tp.columns if _get_role(c) == "time"]

        measures.sort(key=lambda c: any(k in c.name.lower() for k in MEASURE_KEYWORDS), reverse=True)

        for m in measures[:4]:
            if len(kpis) >= 6:
                break
            col_ref = f"{tp.table_name}.{m.name}"
            p_val = min(len(kpis) + 1, 10)
            clean_name = m.name.replace('_', ' ').title()
            kpi_title = clean_name if clean_name.lower().startswith("total") else f"Total {clean_name}"
            kpis.append(KpiSpec(
                kpi_title=kpi_title,
                formula_description=f"SUM({m.name})",
                aggregation_function="sum",
                primary_column=col_ref,
                priority=p_val,
                reasoning="Fallback: numeric column with keyword match",
            ))

        primary_measure_ref = f"{tp.table_name}.{measures[0].name}" if measures else None

        if time_cols and primary_measure_ref:
            charts.append(ChartSpec(
                chart_type="line", title=f"{tp.table_name} Trend Over Time",
                x_axis_column=f"{tp.table_name}.{time_cols[0].name}",
                y_axis_column=primary_measure_ref,
                x_axis_label="Date", y_axis_label="Value", priority=10,
            ))

        for dim in dimensions[:3]:
            if not primary_measure_ref:
                break
            chart_type = "donut" if (dim.cardinality or 0) <= CARDINALITY_DIMENSION_THRESHOLD else "horizontal_bar"
            charts.append(ChartSpec(
                chart_type=chart_type, title=f"By {dim.name.replace('_', ' ').title()}",
                x_axis_column=f"{tp.table_name}.{dim.name}", y_axis_column=primary_measure_ref,
                x_axis_label=dim.name.replace("_", " ").title(), y_axis_label="Value", priority=6,
            ))
            filters.append(FilterSpec(
                column=f"{tp.table_name}.{dim.name}", filter_type="multiselect",
                label=dim.name.replace("_", " ").title(),
            ))

        for t in time_cols:
            filters.append(FilterSpec(
                column=f"{tp.table_name}.{t.name}", filter_type="date_range",
                label=t.name.replace("_", " ").title(),
            ))

    return ValidatedDashboardConfig(
        business_domain="Unknown (fallback mode — LLM analysis unavailable)",
        kpis=kpis[:6], charts=charts[:6], filters=filters,
        validation_warnings=["Used deterministic rule-based fallback — LLM pipeline unavailable"],
        used_fallback=True,
    )
