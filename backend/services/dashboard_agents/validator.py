"""
validator.py
------------
Agent 4: Ye agent LLM NAHI hai — pure deterministic Python logic.
Kaam: Agent 2 (KPI) aur Agent 3 (Chart/Layout) ke output me jitne bhi
"table.column" references hain, unhe schema_registry (actual profiled
schema) ke against verify karo. Agar LLM ne column-naam thoda sa
galat likha (e.g. "revenue_total" jabke actual column "total_revenue"
hai), fuzzy-match se correct karo. Agar match hi nahi mila, entry
DROP karo aur warning record karo — LLM ka hallucination kabhi
query-execution tak nahi pahunchna chahiye.
"""

import logging
import difflib
from typing import Optional, Set, Dict

from .schemas import KpiAgentOutput, ChartLayoutOutput, SemanticAnalysis, ValidatedDashboardConfig

logger = logging.getLogger("nexabi.agents.validator")

FUZZY_MATCH_THRESHOLD = 0.8   # 0-1, kitna similar naam ho to auto-correct karo


def _build_valid_column_set(table_profiles: list) -> Set[str]:
    """Saari actual 'table.column' combinations ka whitelist banao."""
    valid = set()
    for tp in table_profiles:
        for c in tp.columns:
            valid.add(f"{tp.table_name}.{c.name}")
    return valid


def _resolve_column(ref: Optional[str], valid_columns: Set[str], warnings: list) -> Optional[str]:
    """
    Ek column-reference ko whitelist ke against resolve karo.
    Exact match → use karo. Fuzzy match (>threshold) → auto-correct + warn.
    No match → None return karo (caller isay drop karega) + warn.
    """
    if not ref:
        return None
    if ref in valid_columns:
        return ref

    close = difflib.get_close_matches(ref, valid_columns, n=1, cutoff=FUZZY_MATCH_THRESHOLD)
    if close:
        corrected = close[0]
        warnings.append(f"Auto-corrected '{ref}' → '{corrected}' (fuzzy match)")
        return corrected

    warnings.append(f"DROPPED: '{ref}' not found in schema — likely LLM hallucination")
    return None


def validate_dashboard_config(
    semantic: SemanticAnalysis,
    kpi_output: KpiAgentOutput,
    chart_output: ChartLayoutOutput,
    table_profiles: list,
) -> ValidatedDashboardConfig:
    valid_columns = _build_valid_column_set(table_profiles)
    warnings: list = []

    col_roles = {}
    col_cardinalities = {}
    col_sample_values = {}
    for tp in table_profiles:
        for c in tp.columns:
            ref = f"{tp.table_name}.{c.name}"
            col_roles[ref] = getattr(c, "role", "ignore")
            col_cardinalities[ref] = getattr(c, "cardinality", None)
            col_sample_values[ref] = [str(v) for v in getattr(c, "top_values", []) if v is not None]

    # --- KPIs validate karo ---
    safe_kpis = []
    for kpi in kpi_output.kpis:
        primary = _resolve_column(kpi.primary_column, valid_columns, warnings)
        if primary is None:
            continue  # invalid primary column wali KPI poori drop karo
        kpi.primary_column = primary

        if kpi.aggregation_function in ("difference", "ratio", "subtract") and kpi.secondary_column:
            secondary = _resolve_column(kpi.secondary_column, valid_columns, warnings)
            if secondary is None:
                warnings.append(f"DROPPED arithmetic KPI '{kpi.kpi_title}': secondary_column '{kpi.secondary_column}' invalid")
                continue
            kpi.secondary_column = secondary
        elif kpi.secondary_column:
            kpi.secondary_column = _resolve_column(kpi.secondary_column, valid_columns, warnings)

        # Validate target_value against actual sample distinct values of primary column
        if kpi.target_value and primary in col_sample_values:
            samples = col_sample_values[primary]
            if samples:
                if kpi.target_value in samples:
                    pass
                else:
                    case_match = next((s for s in samples if s.strip().lower() == kpi.target_value.strip().lower()), None)
                    if case_match:
                        kpi.target_value = case_match
                    else:
                        close_vals = difflib.get_close_matches(kpi.target_value, samples, n=1, cutoff=FUZZY_MATCH_THRESHOLD)
                        if close_vals:
                            warnings.append(f"Auto-corrected target_value '{kpi.target_value}' → '{close_vals[0]}' in '{kpi.kpi_title}'")
                            kpi.target_value = close_vals[0]
                        else:
                            warnings.append(f"DROPPED KPI '{kpi.kpi_title}': target_value '{kpi.target_value}' not in samples {samples}")
                            continue

        safe_kpis.append(kpi)

    # --- Charts validate karo ---
    safe_charts = []
    for chart in chart_output.charts:
        chart.x_axis_column = _resolve_column(chart.x_axis_column, valid_columns, warnings)
        chart.y_axis_column = _resolve_column(chart.y_axis_column, valid_columns, warnings)
        chart.group_by_column = _resolve_column(chart.group_by_column, valid_columns, warnings)

        # Agar chart ke essential axes hi resolve nahi hue (dono None), poora chart drop karo
        if chart.chart_type != "table" and not chart.x_axis_column and not chart.y_axis_column:
            warnings.append(f"DROPPED chart '{chart.title}' — no valid axis columns")
            continue

        # Data-shape guardrails
        if chart.chart_type == "scatter":
            is_x_meas = col_roles.get(chart.x_axis_column) == "measure"
            is_y_meas = col_roles.get(chart.y_axis_column) == "measure"
            if not (is_x_meas and is_y_meas and chart.x_axis_column != chart.y_axis_column):
                warnings.append(f"DROPPED chart '{chart.title}': scatter chart requires 2 distinct numeric measures")
                continue

        if chart.chart_type in ("donut", "pie"):
            dim_col = chart.x_axis_column or chart.group_by_column
            card = col_cardinalities.get(dim_col)
            if card and card > 8:
                chart.chart_type = "horizontal_bar"
                warnings.append(f"Converted '{chart.title}' from donut to horizontal_bar (cardinality {card} > 8)")

        safe_charts.append(chart)

    # --- Filters validate karo ---
    safe_filters = []
    for f in chart_output.filters:
        resolved = _resolve_column(f.column, valid_columns, warnings)
        if resolved is None:
            continue
        f.column = resolved
        safe_filters.append(f)

    # Safety net: agar sab KPIs drop ho gayi (worst case), empty list return karo —
    # orchestrator isay dekh kar rule-based fallback trigger karega
    if not safe_kpis:
        warnings.append("CRITICAL: All KPIs failed validation — fallback required")

    logger.info("Validator: %d/%d KPIs, %d/%d charts, %d/%d filters passed",
                len(safe_kpis), len(kpi_output.kpis),
                len(safe_charts), len(chart_output.charts),
                len(safe_filters), len(chart_output.filters))

    return ValidatedDashboardConfig(
        business_domain=semantic.business_domain,
        kpis=safe_kpis,
        charts=safe_charts,
        filters=safe_filters,
        validation_warnings=warnings,
        used_fallback=False,
    )
