"""
tests/test_adaptive_chart_recommender.py
-----------------------------------------
Unit tests for Adaptive Chart Recommendation Engine.
Verifies tailored visualizations for each source archetype.
"""

import sys
import os
backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import pytest
from unittest.mock import MagicMock
from services.source_profiler import SourceDiscoveryResult
from services.adaptive_chart_recommender import recommend_adaptive_charts


def test_recommendations_for_relational_timeseries():
    discovery = SourceDiscoveryResult(
        source_id="db_1",
        source_type="database",
        source_name="Postgres DB",
        source_archetype="relational_timeseries",
        archetype_display_name="POSTGRESQL Transactional Time-Series",
        archetype_description="Transactional database.",
        detected_entities=["orders"],
        detected_measures=["orders.total_amount"],
        detected_dimensions=["orders.status"],
        detected_time_axes=["orders.created_at"],
        stats={"table_count": 1},
        recommended_chart_families=["Line", "Area", "Bar", "KPI"],
    )
    mock_db = MagicMock()
    recs = recommend_adaptive_charts(discovery, mock_db, tenant_id=1)

    chart_types = [r.chart_type for r in recs]
    assert "Line" in chart_types
    assert "Area" in chart_types
    assert "Bar" in chart_types
    assert "KPI" in chart_types

    line_rec = next(r for r in recs if r.chart_type == "Line")
    assert line_rec.time_axis == "orders.created_at"
    assert "Velocity Trend" in line_rec.title


def test_recommendations_for_relational_categorical_with_scatter():
    discovery = SourceDiscoveryResult(
        source_id="db_2",
        source_type="database",
        source_name="MySQL DB",
        source_archetype="relational_categorical",
        archetype_display_name="MYSQL Categorical Catalog",
        archetype_description="Catalog database.",
        detected_entities=["products"],
        detected_measures=["products.price", "products.cost"],
        detected_dimensions=["products.category"],
        detected_time_axes=[],
        stats={"table_count": 1},
        recommended_chart_families=["Bar", "Donut", "Scatter", "KPI"],
    )
    mock_db = MagicMock()
    recs = recommend_adaptive_charts(discovery, mock_db, tenant_id=1)

    chart_types = [r.chart_type for r in recs]
    assert "Donut" in chart_types
    assert "Bar" in chart_types
    assert "Scatter" in chart_types  # Since 2 continuous measures exist!
    assert "KPI" in chart_types


def test_recommendations_for_tabular_spreadsheet():
    discovery = SourceDiscoveryResult(
        source_id="doc_5",
        source_type="document",
        source_name="Report.xlsx",
        source_archetype="tabular_spreadsheet",
        archetype_display_name="Tabular Spreadsheet",
        archetype_description="Spreadsheet data.",
        detected_entities=["Sheet1"],
        detected_measures=["Sales"],
        detected_dimensions=["Region"],
        detected_time_axes=[],
        stats={"table_count": 1},
        recommended_chart_families=["Bar", "Donut", "Line", "KPI"],
    )
    mock_db = MagicMock()
    recs = recommend_adaptive_charts(discovery, mock_db, tenant_id=1)

    chart_types = [r.chart_type for r in recs]
    assert "Bar" in chart_types
    assert "Donut" in chart_types
    assert "KPI" in chart_types


def test_recommendations_for_document_knowledge():
    discovery = SourceDiscoveryResult(
        source_id="doc_8",
        source_type="document",
        source_name="Manual.pdf",
        source_archetype="document_knowledge",
        archetype_display_name="Document Knowledge Base",
        archetype_description="PDF document.",
        detected_entities=["Page_1", "Page_2"],
        detected_measures=["chunk_density"],
        detected_dimensions=["content_type"],
        detected_time_axes=["created_at"],
        stats={"chunks_count": 15},
        recommended_chart_families=["Donut", "Area", "Bar", "KPI"],
    )
    mock_db = MagicMock()
    recs = recommend_adaptive_charts(discovery, mock_db, tenant_id=1)

    chart_types = [r.chart_type for r in recs]
    assert "Donut" in chart_types
    assert "Area" in chart_types
    assert "Bar" in chart_types
    assert "KPI" in chart_types

    donut_rec = next(r for r in recs if r.chart_type == "Donut")
    assert "Modality" in donut_rec.title
    assert len(donut_rec.sample_data) > 0
