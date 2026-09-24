"""
schemas.py
----------
Har agent ka output in Pydantic models me STRICT force hota hai
(LangChain's with_structured_output ke zariye). Free-text JSON
parsing kabhi nahi karte — malformed output ka risk khatam ho jata hai.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------
# AGENT 1 — Semantic Understanding
# ---------------------------------------------------------------------

class SemanticColumn(BaseModel):
    table_name: str = Field(description="Table jahan ye column hai")
    column_name: str = Field(description="Column ka exact naam, schema se copy karo, mat banao")
    business_meaning: str = Field(description="Ek chhota phrase — is column ka real business meaning")
    role: Literal["measure", "dimension", "time", "funnel_stage", "identifier", "ignore"] = Field(
        description="funnel_stage sirf tab jab column ek lifecycle/status progression represent kare"
    )
    is_primary_metric: bool = Field(
        default=False, description="True agar ye column business ke liye sabse important measure hai"
    )


class SemanticAnalysis(BaseModel):
    business_domain: str = Field(description="e.g. 'E-commerce Retail', 'Healthcare Clinic', 'SaaS Subscription'")
    domain_confidence: float = Field(ge=0, le=1, description="0-1 confidence score")
    columns: List[SemanticColumn]
    detected_relationships: List[str] = Field(
        default_factory=list,
        description="e.g. 'orders.customer_id links to customers.id' — sirf agar clear ho"
    )


# ---------------------------------------------------------------------
# AGENT 2 — KPI Selection
# ---------------------------------------------------------------------

class KpiSpec(BaseModel):
    kpi_title: str = Field(description="e.g. 'Profit Margin', 'Customer Retention Rate', 'Admission Rate'")
    formula_description: str = Field(description="Plain-language formula, e.g. 'SUM(revenue) - SUM(cost)' or 'status == Active / Total'")
    aggregation_function: Literal["sum", "avg", "count", "count_distinct", "computed", "ratio", "difference"] = "sum"
    primary_column: str = Field(description="table.column format, exact schema se")
    secondary_column: Optional[str] = Field(default=None, description="Second column for arithmetic computation (e.g. cost column or denominator)")
    target_value: Optional[str] = Field(default=None, description="For categorical ratios (e.g. 'Active', 'Admitted', 'Paid', 'Completed')")
    priority: int = Field(ge=1, le=10, description="1 = sabse important, dashboard ke top pe")
    reasoning: str = Field(description="1 line — kyun ye KPI business ke liye meaningful hai")


class KpiAgentOutput(BaseModel):
    kpis: List[KpiSpec] = Field(max_length=6)


# ---------------------------------------------------------------------
# AGENT 3 — Chart & Layout
# ---------------------------------------------------------------------

class ChartSpec(BaseModel):
    chart_type: Literal["line", "bar", "horizontal_bar", "donut", "scatter",
                          "stacked_area", "funnel", "map", "table"]
    title: str
    x_axis_column: Optional[str] = Field(default=None, description="table.column format")
    y_axis_column: Optional[str] = Field(default=None, description="table.column format")
    group_by_column: Optional[str] = Field(default=None, description="table.column format, multi-series ke liye")
    x_axis_label: str = Field(description="Human-readable axis label, column-naam nahi")
    y_axis_label: str
    legend_needed: bool = Field(default=False)
    sort_order: Optional[str] = Field(
        default=None, description="e.g. 'pending>processing>shipped>delivered' funnel ke liye"
    )
    priority: int = Field(ge=1, le=10, description="1 = dashboard ke top pe (hero chart)")


class FilterSpec(BaseModel):
    column: str = Field(description="table.column format")
    filter_type: Literal["multiselect", "date_range", "range_slider"]
    label: str


class ChartLayoutOutput(BaseModel):
    charts: List[ChartSpec] = Field(max_length=8)
    filters: List[FilterSpec] = Field(max_length=8)


# ---------------------------------------------------------------------
# FINAL — Validator ka output (jo query_builder consume karega)
# ---------------------------------------------------------------------

class ValidatedDashboardConfig(BaseModel):
    business_domain: str
    kpis: List[KpiSpec]
    charts: List[ChartSpec]
    filters: List[FilterSpec]
    validation_warnings: List[str] = Field(
        default_factory=list, description="Konsi cheezein drop/correct hui aur kyun"
    )
    used_fallback: bool = Field(default=False, description="True agar LLM pipeline fail hua aur rule-based fallback chala")
