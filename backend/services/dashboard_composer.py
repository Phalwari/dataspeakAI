"""
Dashboard Layout & Composition Engine (Phase 2F / 2F.1 Architecture)
Assembles Metric Recipes, Recommended Charts, and Interactive Filters into a
deterministic layout plan ready for front-end rendering and typed persistence.
"""

from __future__ import annotations
from typing import Any, Sequence, Optional
from pydantic import BaseModel, ConfigDict
from services.metric_recipes import MetricRecipe
from services.chart_recommender import ChartRecommendation
from services.filter_recommender import FilterRecommendation, FilterRecommendationResult


class DashboardLayoutPlan(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)
    table_name: str
    kpi_cards: list[dict[str, Any]] = []
    charts: list[dict[str, Any]] = []
    filters: list[dict[str, Any]] = []
    strategic_insights: list[dict[str, Any]] = []
    anomalies: list[dict[str, Any]] = []
    executive_summary: dict[str, Any] = {}
    metadata: dict[str, Any] = {}


def compose_dashboard_layout(
    *,
    table_name: str,
    metrics: Sequence[dict[str, Any]],
    charts: Sequence[dict[str, Any]],
    filters: Sequence[dict[str, Any]],
    executive_summary: Optional[dict[str, Any]] = None,
    anomalies: Sequence[dict[str, Any]] = [],
) -> DashboardLayoutPlan:
    """
    Composes the multi-layer results into a unified dashboard structure.
    """
    return DashboardLayoutPlan(
        table_name=table_name,
        kpi_cards=list(metrics),
        charts=list(charts),
        filters=list(filters),
        strategic_insights=executive_summary.get("insights", []) if executive_summary else [],
        anomalies=list(anomalies),
        executive_summary=executive_summary or {},
        metadata={"composed": True, "engine_version": "2.0-deterministic"}
    )
