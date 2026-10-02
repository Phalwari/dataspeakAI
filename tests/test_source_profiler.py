"""
tests/test_source_profiler.py
------------------------------
Unit tests for Source Profiler and Archetype Classification Service.
Verifies discovery of:
- relational_timeseries
- relational_categorical
- tabular_spreadsheet
- document_knowledge
- Markdown table extraction & parsing
"""

import sys
import os
backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import pytest
from unittest.mock import MagicMock
from services.source_profiler import (
    discover_database_archetype,
    discover_document_archetype,
    _parse_markdown_table,
    _is_time_column,
)
import models


def test_is_time_column_detection():
    assert _is_time_column("created_at") is True
    assert _is_time_column("order_date") is True
    assert _is_time_column("timestamp", "TIMESTAMP") is True
    assert _is_time_column("event_time") is True
    assert _is_time_column("user_id") is False
    assert _is_time_column("customer_name") is False


def test_parse_markdown_table():
    md = """
    | Product | Category | Sales | Units |
    | --- | --- | --- | --- |
    | Laptop | Electronics | 1200.50 | 10 |
    | Headphones | Audio | $150.00 | 25 |
    | Mouse | Accessories | 45.20 | 80 |
    """
    res = _parse_markdown_table(md)
    assert res["headers"] == ["Product", "Category", "Sales", "Units"]
    assert len(res["rows"]) == 3
    assert res["rows"][0]["Product"] == "Laptop"
    assert res["rows"][0]["Sales"] == 1200.50
    assert res["rows"][0]["Units"] == 10.0
    assert res["rows"][1]["Sales"] == 150.00


def test_parse_html_table():
    html = """
    <table border='1' class='extracted-table'>
      <thead>
        <tr>
          <th>channel_sales</th>
          <th>cons_12m</th>
          <th>net_margin</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>foosdf</td>
          <td>10387</td>
          <td>678.99</td>
        </tr>
        <tr>
          <td>usilxu</td>
          <td>5200</td>
          <td>340.50</td>
        </tr>
      </tbody>
    </table>
    """
    res = _parse_markdown_table(html)
    assert res["headers"] == ["channel_sales", "cons_12m", "net_margin"]
    assert len(res["rows"]) == 2
    assert res["rows"][0]["channel_sales"] == "foosdf"
    assert res["rows"][0]["cons_12m"] == 10387.0
    assert res["rows"][0]["net_margin"] == 678.99


def test_discover_relational_timeseries():
    mock_conn = MagicMock(spec=models.DatabaseConnection)
    mock_conn.id = 1
    mock_conn.name = "Prod Postgres"
    mock_conn.db_type = "postgresql"
    mock_conn.status = "connected"

    # Schema with time column and measures
    reg1 = MagicMock(spec=models.SchemaRegistry)
    reg1.table_name = "orders"
    reg1.column_name = "created_at"
    reg1.is_time_axis = True
    reg1.is_measure = False
    reg1.is_dimension = False
    reg1.data_type = "DATETIME"

    reg2 = MagicMock(spec=models.SchemaRegistry)
    reg2.table_name = "orders"
    reg2.column_name = "total_amount"
    reg2.is_time_axis = False
    reg2.is_measure = True
    reg2.is_dimension = False
    reg2.data_type = "FLOAT"

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = [reg1, reg2]

    res = discover_database_archetype(mock_conn, mock_db)

    assert res.source_archetype == "relational_timeseries"
    assert "Line" in res.recommended_chart_families
    assert "Area" in res.recommended_chart_families
    assert len(res.detected_time_axes) == 1
    assert len(res.detected_measures) == 1


def test_discover_relational_categorical():
    mock_conn = MagicMock(spec=models.DatabaseConnection)
    mock_conn.id = 2
    mock_conn.name = "Inventory DB"
    mock_conn.db_type = "mysql"
    mock_conn.status = "connected"

    reg1 = MagicMock(spec=models.SchemaRegistry)
    reg1.table_name = "products"
    reg1.column_name = "category"
    reg1.is_time_axis = False
    reg1.is_measure = False
    reg1.is_dimension = True
    reg1.data_type = "VARCHAR"

    reg2 = MagicMock(spec=models.SchemaRegistry)
    reg2.table_name = "products"
    reg2.column_name = "stock_quantity"
    reg2.is_time_axis = False
    reg2.is_measure = True
    reg2.is_dimension = False
    reg2.data_type = "INTEGER"

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = [reg1, reg2]

    res = discover_database_archetype(mock_conn, mock_db)

    assert res.source_archetype == "relational_categorical"
    assert "Bar" in res.recommended_chart_families
    assert "Donut" in res.recommended_chart_families
    assert len(res.detected_time_axes) == 0
    assert len(res.detected_dimensions) == 1


def test_discover_tabular_spreadsheet_document():
    mock_doc = MagicMock(spec=models.Document)
    mock_doc.id = 5
    mock_doc.name = "Q3_Sales.xlsx"
    mock_doc.file_type = ".xlsx"
    mock_doc.table_count = 1
    mock_doc.total_pages = 1
    mock_doc.status = "Completed"

    mock_chunk = MagicMock(spec=models.DocumentChunk)
    mock_chunk.content_type = "table"
    mock_chunk.content = "| Region | Revenue |\n| --- | --- |\n| North | 50000 |\n| South | 42000 |"

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_chunk]

    res = discover_document_archetype(mock_doc, mock_db)

    assert res.source_archetype == "tabular_spreadsheet"
    assert "Bar" in res.recommended_chart_families
    assert "Donut" in res.recommended_chart_families
    assert "Revenue" in res.detected_measures
    assert "Region" in res.detected_dimensions


def test_discover_knowledge_base_document():
    mock_doc = MagicMock(spec=models.Document)
    mock_doc.id = 9
    mock_doc.name = "Company_Policy.pdf"
    mock_doc.file_type = ".pdf"
    mock_doc.table_count = 0
    mock_doc.total_pages = 8
    mock_doc.visual_pages = 2
    mock_doc.status = "Completed"

    mock_db = MagicMock()
    # No table chunks
    mock_db.query.return_value.filter.return_value.all.return_value = []
    mock_db.query.return_value.filter.return_value.count.return_value = 24

    res = discover_document_archetype(mock_doc, mock_db)

    assert res.source_archetype == "document_knowledge"
    assert "Donut" in res.recommended_chart_families
    assert "Area" in res.recommended_chart_families
    assert res.stats["chunks_count"] == 24
    assert res.stats["total_pages"] == 8
