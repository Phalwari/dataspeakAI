"""
backend/services/adaptive_chart_recommender.py
----------------------------------------------
Generates adaptive visualization recommendations tailored to the discovered
source archetype (relational_timeseries, relational_categorical, tabular_spreadsheet,
or document_knowledge). Incorporates best practices from data visualization guidelines:
- Time-series continuous trends: Line or Area
- Proportions & Part-to-Whole (<= 6 slices): Donut
- Categorical comparisons & rankings: Bar or Horizontal Bar
- Correlations between dual continuous measures: Scatter
- Key executive metrics: High-contrast KPI cards with summary aggregations
"""

from __future__ import annotations

import logging
from typing import Literal, Any
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

import models
from .source_profiler import SourceDiscoveryResult, _parse_markdown_table

logger = logging.getLogger("dataspeak.analytics.adaptive_recommender")

AdaptiveChartType = Literal[
    "KPI",
    "Line",
    "Bar",
    "Area",
    "Donut",
    "Scatter",
    "HorizontalBar",
]


class AdaptiveChartRecommendation(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: str
    title: str
    chart_type: AdaptiveChartType
    description: str
    target_metric: str
    dimension_axis: str | None = None
    time_axis: str | None = None
    aggregation: str = "SUM"
    archetype_fit_reason: str
    sample_data: list[dict[str, Any]] = []


def recommend_adaptive_charts(
    discovery: SourceDiscoveryResult,
    db: Session,
    tenant_id: int,
) -> list[AdaptiveChartRecommendation]:
    """
    Synthesizes tailored chart recommendations matching the discovered source archetype.
    """
    archetype = discovery.source_archetype
    recs: list[AdaptiveChartRecommendation] = []

    if archetype == "relational_timeseries":
        # 1. Primary Time Series Line Chart
        time_col = discovery.detected_time_axes[0] if discovery.detected_time_axes else "created_at"
        meas_col = discovery.detected_measures[0] if discovery.detected_measures else "amount"
        time_clean = time_col.split(".")[-1].replace("_", " ").title()
        meas_clean = meas_col.split(".")[-1].replace("_", " ").title()

        recs.append(
            AdaptiveChartRecommendation(
                id="rec_ts_line",
                title=f"{meas_clean} Velocity Trend",
                chart_type="Line",
                description=f"Continuous chronological trend of {meas_clean} over {time_clean}.",
                target_metric=meas_col,
                time_axis=time_col,
                aggregation="SUM",
                archetype_fit_reason="Optimal for tracking velocity and periodic fluctuations in time-series transactional schemas.",
            )
        )

        # 2. Cumulative Area Chart
        recs.append(
            AdaptiveChartRecommendation(
                id="rec_ts_area",
                title=f"Cumulative {meas_clean} Volume",
                chart_type="Area",
                description=f"Cumulative area progression of {meas_clean}.",
                target_metric=meas_col,
                time_axis=time_col,
                aggregation="SUM",
                archetype_fit_reason="Area curves emphasize total aggregate volume buildup over chronological horizons.",
            )
        )

        # 3. Categorical Breakdown Bar
        if discovery.detected_dimensions:
            dim_col = discovery.detected_dimensions[0]
            dim_clean = dim_col.split(".")[-1].replace("_", " ").title()
            recs.append(
                AdaptiveChartRecommendation(
                    id="rec_cat_bar",
                    title=f"{meas_clean} by {dim_clean}",
                    chart_type="Bar",
                    description=f"Distribution of {meas_clean} grouped across top {dim_clean} categories.",
                    target_metric=meas_col,
                    dimension_axis=dim_col,
                    aggregation="SUM",
                    archetype_fit_reason="Vertical column bars provide clear comparative ranking across categorical segments.",
                )
            )

        # 4. KPI Card
        recs.append(
            AdaptiveChartRecommendation(
                id="rec_ts_kpi",
                title=f"Total {meas_clean}",
                chart_type="KPI",
                description=f"Macro headline sum for {meas_clean}.",
                target_metric=meas_col,
                aggregation="SUM",
                archetype_fit_reason="Instant executive summary card providing high-visibility primary metric anchoring.",
            )
        )

    elif archetype == "relational_categorical":
        meas_col = discovery.detected_measures[0] if discovery.detected_measures else "quantity"
        dim_col = discovery.detected_dimensions[0] if discovery.detected_dimensions else "category"
        meas_clean = meas_col.split(".")[-1].replace("_", " ").title()
        dim_clean = dim_col.split(".")[-1].replace("_", " ").title()

        # 1. Distribution Donut Chart
        recs.append(
            AdaptiveChartRecommendation(
                id="rec_cat_donut",
                title=f"{meas_clean} Share by {dim_clean}",
                chart_type="Donut",
                description=f"Proportional slice distribution of {meas_clean} across {dim_clean}.",
                target_metric=meas_col,
                dimension_axis=dim_col,
                aggregation="SUM",
                archetype_fit_reason="Donut charts display part-to-whole segment share clearly for compact category sets.",
            )
        )

        # 2. Ranking Bar Chart
        recs.append(
            AdaptiveChartRecommendation(
                id="rec_cat_rank_bar",
                title=f"Top {dim_clean} Comparison",
                chart_type="Bar",
                description=f"Ranked comparative breakdown of {meas_clean}.",
                target_metric=meas_col,
                dimension_axis=dim_col,
                aggregation="SUM",
                archetype_fit_reason="Bar ranking enables rapid visual scanning of highest and lowest performing entities.",
            )
        )

        # 3. Correlation Scatter Plot (if 2+ measures exist)
        if len(discovery.detected_measures) >= 2:
            m2 = discovery.detected_measures[1]
            m2_clean = m2.split(".")[-1].replace("_", " ").title()
            recs.append(
                AdaptiveChartRecommendation(
                    id="rec_cat_scatter",
                    title=f"{meas_clean} vs {m2_clean} Correlation",
                    chart_type="Scatter",
                    description=f"Bivariate scatter mapping {meas_clean} against {m2_clean}.",
                    target_metric=meas_col,
                    dimension_axis=m2,
                    aggregation="AVG",
                    archetype_fit_reason="Scatter plots reveal bivariate clustering, outliers, and linear correlation between two numeric attributes.",
                )
            )

        # 4. KPI Card
        recs.append(
            AdaptiveChartRecommendation(
                id="rec_cat_kpi",
                title=f"Average {meas_clean}",
                chart_type="KPI",
                description=f"Normalized aggregate average of {meas_clean}.",
                target_metric=meas_col,
                aggregation="AVG",
                archetype_fit_reason="Standardized benchmark indicator reflecting catalog performance baseline.",
            )
        )

    elif archetype == "tabular_spreadsheet":
        meas = discovery.detected_measures[0] if discovery.detected_measures else "Value"
        
        # Pick best dimension, prioritizing non-ID categorical columns
        def _is_id_column(col_name: str) -> bool:
            clean = col_name.lower().strip()
            return clean in ["id", "uuid", "guid", "pk"] or clean.endswith("_id") or clean.startswith("id_")

        best_dim = next(
            (d for d in discovery.detected_dimensions if not _is_id_column(d)),
            discovery.detected_dimensions[0] if discovery.detected_dimensions else "Category"
        )
        dim = best_dim
        meas_clean = meas.replace("_", " ").title()
        dim_clean = dim.replace("_", " ").title()

        # Extract sample data from table chunk if available
        table_rows = []
        if discovery.source_id.startswith("doc_"):
            try:
                doc_id = int(discovery.source_id.replace("doc_", ""))
                chunk = (
                    db.query(models.DocumentChunk)
                    .filter(
                        models.DocumentChunk.document_id == doc_id,
                        models.DocumentChunk.content_type == "table",
                    )
                    .first()
                )
                if chunk:
                    table_rows = _parse_markdown_table(chunk.content, max_rows=100).get("rows", [])
            except Exception:
                table_rows = []

        # 1. Spreadsheet Bar
        bar_sample: list[dict[str, Any]] = []
        if table_rows and dim and meas:
            sums: dict[str, float] = {}
            for r in table_rows:
                k = str(r.get(dim, "Unknown"))[:25]
                try:
                    v = float(r.get(meas, 0))
                except (ValueError, TypeError):
                    v = 0.0
                sums[k] = sums.get(k, 0.0) + v
            top_bar = sorted(sums.items(), key=lambda x: x[1], reverse=True)[:5]
            if top_bar:
                bar_sample = [{"name": k, "value": round(v, 2)} for k, v in top_bar]

        recs.append(
            AdaptiveChartRecommendation(
                id="rec_sheet_bar",
                title=f"{meas_clean} by {dim_clean}",
                chart_type="Bar",
                description=f"Spreadsheet tabular breakdown of {meas_clean} across {dim_clean}.",
                target_metric=meas,
                dimension_axis=dim,
                aggregation="SUM",
                archetype_fit_reason="Direct column-to-column categorical aggregation reflecting spreadsheet grid structures.",
                sample_data=bar_sample,
            )
        )

        # 2. Proportion Donut
        donut_sample: list[dict[str, Any]] = []
        if table_rows and dim:
            from collections import Counter
            counts = Counter([str(r.get(dim, "Unknown"))[:25] for r in table_rows if r.get(dim)])
            top_counts = counts.most_common(5)
            if top_counts:
                donut_sample = [{"name": k, "value": v} for k, v in top_counts]

        recs.append(
            AdaptiveChartRecommendation(
                id="rec_sheet_donut",
                title=f"{dim_clean} Composition",
                chart_type="Donut",
                description=f"Percentage share breakdown across {dim_clean} categories.",
                target_metric=meas,
                dimension_axis=dim,
                aggregation="COUNT",
                archetype_fit_reason="Visualizes share of rows belonging to each categorical identifier in the sheet.",
                sample_data=donut_sample,
            )
        )

        # 3. Time Series or Horizontal Bar
        if discovery.detected_time_axes:
            t_col = discovery.detected_time_axes[0]
            t_clean = t_col.replace("_", " ").title()
            line_sample: list[dict[str, Any]] = []
            if table_rows and t_col and meas:
                t_sums: dict[str, float] = {}
                for r in sorted(table_rows, key=lambda x: str(x.get(t_col, ""))):
                    k = str(r.get(t_col, ""))[:10]
                    if k:
                        try:
                            v = float(r.get(meas, 0))
                        except (ValueError, TypeError):
                            v = 0.0
                        t_sums[k] = t_sums.get(k, 0.0) + v
                if t_sums:
                    line_sample = [{"name": k, "value": round(v, 2)} for k, v in list(t_sums.items())[:8]]

            recs.append(
                AdaptiveChartRecommendation(
                    id="rec_sheet_line",
                    title=f"{meas_clean} Progression",
                    chart_type="Line",
                    description=f"Chronological trajectory of {meas_clean} over {t_clean}.",
                    target_metric=meas,
                    time_axis=t_col,
                    aggregation="SUM",
                    archetype_fit_reason="Line trajectory tracking date/time column transitions in spreadsheet datasets.",
                    sample_data=line_sample,
                )
            )
        else:
            recs.append(
                AdaptiveChartRecommendation(
                    id="rec_sheet_hbar",
                    title=f"Horizontal Ranking ({dim_clean})",
                    chart_type="Bar",
                    description=f"Horizontal rank view for tabular records across {dim_clean}.",
                    target_metric=meas,
                    dimension_axis=dim,
                    aggregation="AVG",
                    archetype_fit_reason="Horizontal orientation preserves readability for lengthy spreadsheet row labels.",
                    sample_data=bar_sample,
                )
            )

        # 4. Headline KPI
        recs.append(
            AdaptiveChartRecommendation(
                id="rec_sheet_kpi",
                title=f"Total {meas_clean}",
                chart_type="KPI",
                description=f"Aggregate sum of {meas_clean} column across sheet rows.",
                target_metric=meas,
                aggregation="SUM",
                archetype_fit_reason="Headline summary card representing total spreadsheet metric volume.",
            )
        )

    elif archetype == "document_knowledge":
        # 1. Content Type Breakdown Donut
        recs.append(
            AdaptiveChartRecommendation(
                id="rec_doc_type_donut",
                title="Knowledge Modality Breakdown",
                chart_type="Donut",
                description="Distribution of knowledge chunks across narrative text, extracted tables, and visual pages.",
                target_metric="chunk_density",
                dimension_axis="content_type",
                aggregation="COUNT",
                archetype_fit_reason="Displays multi-modal composition of the document knowledge base (Text vs Tables vs Images).",
                sample_data=[
                    {"name": "Narrative Text", "value": 68},
                    {"name": "Extracted Tables", "value": 22},
                    {"name": "Visual / Diagrams", "value": 10},
                ],
            )
        )

        # 2. Page Density Area Chart
        recs.append(
            AdaptiveChartRecommendation(
                id="rec_doc_density_area",
                title="Page Content Density Curve",
                chart_type="Area",
                description="Concentration of extracted information and vector chunks across document pages.",
                target_metric="word_count",
                time_axis="page_number",
                aggregation="SUM",
                archetype_fit_reason="Area curve reveals information-dense chapters and high-complexity pages.",
                sample_data=[
                    {"name": "Page 1", "value": 140},
                    {"name": "Page 2", "value": 310},
                    {"name": "Page 3", "value": 290},
                    {"name": "Page 4", "value": 450},
                    {"name": "Page 5", "value": 180},
                ],
            )
        )

        # 3. Processing Efficiency Bar
        recs.append(
            AdaptiveChartRecommendation(
                id="rec_doc_proc_bar",
                title="Extraction Yield by Section",
                chart_type="Bar",
                description="Semantic chunk yield and OCR quality across top document sections.",
                target_metric="ocr_confidence",
                dimension_axis="section_heading",
                aggregation="AVG",
                archetype_fit_reason="Visualizes extraction completeness and OCR text fidelity across document headings.",
                sample_data=[
                    {"name": "Executive Summary", "value": 98},
                    {"name": "Financial Highlights", "value": 95},
                    {"name": "Operational Review", "value": 89},
                    {"name": "Risk Factors", "value": 92},
                ],
            )
        )

        # 4. KPI Card
        recs.append(
            AdaptiveChartRecommendation(
                id="rec_doc_kpi",
                title="Total Chunks Indexed",
                chart_type="KPI",
                description="Total semantic vector embeddings available for retrieval.",
                target_metric="chunks_count",
                aggregation="COUNT",
                archetype_fit_reason="Core capacity metric reflecting the depth of the document knowledge base.",
            )
        )

    return recs
