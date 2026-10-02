"""
backend/services/source_profiler.py
------------------------------------
Discovers and classifies connected data sources (Relational SQL databases and
Uploaded Documents / Spreadsheets) into high-fidelity source archetypes:
1. relational_timeseries: Relational OLTP with clear time series and transactional measures.
2. relational_categorical: Relational catalogs, dimension lookup tables, or master data.
3. tabular_spreadsheet: CSV, Excel spreadsheets, or documents with structured extracted tables.
4. document_knowledge: Unstructured PDF, Word, or text corpora indexed for semantic RAG.
"""

from __future__ import annotations

import re
import logging
from typing import Literal, Any
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from sqlalchemy import text

import models

logger = logging.getLogger("dataspeak.analytics.source_profiler")

SourceArchetype = Literal[
    "relational_timeseries",
    "relational_categorical",
    "tabular_spreadsheet",
    "document_knowledge",
]


class SourceDiscoveryResult(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    source_id: str
    source_type: Literal["database", "document"]
    source_name: str
    source_archetype: SourceArchetype
    archetype_display_name: str
    archetype_description: str
    detected_entities: list[str]
    detected_measures: list[str]
    detected_dimensions: list[str]
    detected_time_axes: list[str]
    stats: dict[str, Any]
    recommended_chart_families: list[str]


TIME_COLUMN_HINTS = {
    "date", "time", "created_at", "updated_at", "timestamp", "datetime",
    "order_date", "trans_date", "transaction_date", "invoice_date",
    "shipped_date", "paid_at", "month", "year", "day"
}


def _is_time_column(col_name: str, data_type: str = "") -> bool:
    c_lower = col_name.lower()
    t_lower = data_type.lower()
    if any(h in c_lower for h in TIME_COLUMN_HINTS):
        return True
    if any(dt in t_lower for dt in ["date", "time", "timestamp", "year", "month"]):
        return True
    return False


def discover_database_archetype(
    db_conn: models.DatabaseConnection,
    db: Session,
) -> SourceDiscoveryResult:
    """
    Introspects SchemaRegistry entries and profiling metadata for a connected database.
    Distinguishes time-series/transactional databases from categorical/lookup databases.
    """
    schema_entries = (
        db.query(models.SchemaRegistry)
        .filter(models.SchemaRegistry.connection_id == db_conn.id)
        .all()
    )

    entities = sorted(list(set(e.table_name for e in schema_entries))) if schema_entries else []
    measures = sorted(list(set(f"{e.table_name}.{e.column_name}" for e in schema_entries if e.is_measure)))
    dimensions = sorted(list(set(f"{e.table_name}.{e.column_name}" for e in schema_entries if e.is_dimension)))
    time_axes = sorted(list(set(
        f"{e.table_name}.{e.column_name}"
        for e in schema_entries
        if e.is_time_axis or _is_time_column(e.column_name, e.data_type)
    )))

    has_time = len(time_axes) > 0
    has_measures = len(measures) > 0

    if has_time and has_measures:
        archetype: SourceArchetype = "relational_timeseries"
        display_name = f"{db_conn.db_type.upper()} Transactional Time-Series"
        description = (
            "Transactional relational database with active temporal axes and numerical performance measures. "
            "Ideal for chronological velocity, cumulative trends, and multi-period comparisons."
        )
        recommended_charts = ["Line", "Area", "Bar", "KPI"]
    elif has_measures and len(dimensions) > 0:
        archetype = "relational_categorical"
        display_name = f"{db_conn.db_type.upper()} Categorical Catalog"
        description = (
            "Structured relational database organized primarily around categorical entities, segments, and metrics. "
            "Best suited for ranking breakdowns, distribution donuts, and correlation scatters."
        )
        recommended_charts = ["Bar", "Donut", "Scatter", "KPI"]
    else:
        archetype = "relational_timeseries" if has_time else "relational_categorical"
        display_name = f"{db_conn.db_type.upper()} Relational Database"
        description = "Relational database connection ready for exploratory visual queries and schema inspection."
        recommended_charts = ["Bar", "Line", "KPI"]

    total_cols = len(schema_entries)

    return SourceDiscoveryResult(
        source_id=f"db_{db_conn.id}",
        source_type="database",
        source_name=db_conn.name,
        source_archetype=archetype,
        archetype_display_name=display_name,
        archetype_description=description,
        detected_entities=entities,
        detected_measures=measures,
        detected_dimensions=dimensions,
        detected_time_axes=time_axes,
        stats={
            "db_type": db_conn.db_type,
            "table_count": len(entities),
            "column_count": total_cols,
            "measure_count": len(measures),
            "dimension_count": len(dimensions),
            "time_axis_count": len(time_axes),
            "status": db_conn.status,
        },
        recommended_chart_families=recommended_charts,
    )


def _parse_html_table(html_content: str, max_rows: int = 100) -> dict[str, Any]:
    """
    Parses an HTML table chunk (generated by extractors.py) into structured headers and rows.
    Uses BeautifulSoup with a sample window for instant sub-millisecond execution.
    """
    try:
        from bs4 import BeautifulSoup
        sample = html_content[:250000] if len(html_content) > 250000 else html_content
        soup = BeautifulSoup(sample, "html.parser")

        # 1. Extract headers from <th> or first <tr>
        headers = [th.get_text(strip=True) for th in soup.find_all("th")]
        if not headers:
            first_tr = soup.find("tr")
            if first_tr:
                headers = [c.get_text(strip=True) for c in first_tr.find_all(["th", "td"])]

        clean_headers = [h if h else f"col_{i+1}" for i, h in enumerate(headers)]
        if not clean_headers:
            return {"headers": [], "rows": []}

        # 2. Extract rows from <tr>
        rows = []
        trs = soup.find_all("tr")
        data_trs = trs[1:] if soup.find("th") else trs

        for tr in data_trs[:max_rows]:
            tds = tr.find_all("td")
            if not tds:
                continue
            cells = [td.get_text(strip=True) for td in tds]
            if len(cells) < len(clean_headers):
                cells += [""] * (len(clean_headers) - len(cells))
            row_dict = {}
            for h, c in zip(clean_headers, cells[:len(clean_headers)]):
                try:
                    num_c = float(c.replace(",", "").replace("$", ""))
                    row_dict[h] = num_c
                except (ValueError, TypeError):
                    row_dict[h] = c
            rows.append(row_dict)

        return {"headers": clean_headers, "rows": rows}
    except Exception as e:
        logger.warning(f"Failed to parse HTML table chunk: {e}")
        return {"headers": [], "rows": []}


def _parse_markdown_table(md_content: str, max_rows: int = 100) -> dict[str, Any]:
    """
    Parses a markdown, pipe-delimited, or HTML table chunk into structured headers and rows.
    """
    if not md_content:
        return {"headers": [], "rows": []}

    trimmed = md_content.strip()
    if "<table" in trimmed.lower() or (trimmed.startswith("<") and ">" in trimmed):
        return _parse_html_table(md_content, max_rows=max_rows)

    lines = [l.strip() for l in trimmed.splitlines() if l.strip()]
    table_lines = [l for l in lines if l.startswith("|") and l.endswith("|")]
    if len(table_lines) < 2:
        return {"headers": [], "rows": []}

    raw_headers = [c.strip() for c in table_lines[0].strip("|").split("|")]
    clean_headers = [h if h else f"col_{i+1}" for i, h in enumerate(raw_headers)]

    rows = []
    # Skip separator line (usually index 1, containing '---')
    for row_line in table_lines[1:max_rows + 2]:
        if "---" in row_line:
            continue
        cells = [c.strip() for c in row_line.strip("|").split("|")]
        # Pad or trim to match header length
        if len(cells) < len(clean_headers):
            cells += [""] * (len(clean_headers) - len(cells))
        row_dict = {}
        for h, c in zip(clean_headers, cells[:len(clean_headers)]):
            # Try float/int parsing
            try:
                num_c = float(c.replace(",", "").replace("$", ""))
                row_dict[h] = num_c
            except (ValueError, TypeError):
                row_dict[h] = c
        rows.append(row_dict)

    return {"headers": clean_headers, "rows": rows}


def discover_document_archetype(
    doc: models.Document,
    db: Session,
) -> SourceDiscoveryResult:
    """
    Analyzes an uploaded Document record and its DocumentChunk records.
    Distinguishes tabular/spreadsheet documents from text/knowledge-base documents.
    """
    file_ext = (doc.file_type or "").lower().strip()
    is_spreadsheet_file = file_ext in [".csv", ".xlsx", ".xls", "csv", "xlsx", "xls", "application/vnd.ms-excel"]

    # Check for extracted table chunks
    table_chunks = (
        db.query(models.DocumentChunk)
        .filter(
            models.DocumentChunk.document_id == doc.id,
            models.DocumentChunk.content_type == "table",
        )
        .all()
    )

    has_tables = len(table_chunks) > 0 or (doc.table_count and doc.table_count > 0) or is_spreadsheet_file

    if has_tables:
        archetype: SourceArchetype = "tabular_spreadsheet"
        display_name = f"Tabular Document ({file_ext.upper().lstrip('.')} Sheet)"
        description = (
            "Structured document with extracted tables, columns, and numeric records. "
            "Supports spreadsheet-style aggregations, categorical distributions, and multi-metric scatter."
        )
        recommended_charts = ["Bar", "Donut", "Line", "KPI"]

        # Extract sample structure from first table chunk if available
        headers = []
        rows = []
        if table_chunks:
            parsed = _parse_markdown_table(table_chunks[0].content)
            headers = parsed["headers"]
            rows = parsed["rows"]

        detected_measures = []
        detected_dimensions = []
        detected_time = []

        for h in headers:
            # Check column types across parsed sample rows
            is_num = False
            for r in rows:
                if isinstance(r.get(h), (int, float)):
                    is_num = True
                    break
            if is_num:
                detected_measures.append(h)
            elif _is_time_column(h):
                detected_time.append(h)
            else:
                detected_dimensions.append(h)

        entities = [doc.name]

        return SourceDiscoveryResult(
            source_id=f"doc_{doc.id}",
            source_type="document",
            source_name=doc.name,
            source_archetype=archetype,
            archetype_display_name=display_name,
            archetype_description=description,
            detected_entities=entities,
            detected_measures=detected_measures,
            detected_dimensions=detected_dimensions,
            detected_time_axes=detected_time,
            stats={
                "file_type": doc.file_type,
                "table_count": len(table_chunks) or (doc.table_count or 1),
                "total_rows": len(rows),
                "column_count": len(headers),
                "measure_count": len(detected_measures),
                "dimension_count": len(detected_dimensions),
                "time_axis_count": len(detected_time),
                "total_pages": doc.total_pages or 1,
                "status": doc.status,
            },
            recommended_chart_families=recommended_charts,
        )
    else:
        archetype = "document_knowledge"
        display_name = f"Document Knowledge Base ({file_ext.upper().lstrip('.')})"
        description = (
            "Unstructured or narrative document knowledge corpus with semantic vector embeddings. "
            "Suited for document density analysis, chunk distribution, and knowledge retrieval metrics."
        )
        recommended_charts = ["Donut", "Area", "Bar", "KPI"]

        chunks_count = (
            db.query(models.DocumentChunk)
            .filter(models.DocumentChunk.document_id == doc.id)
            .count()
        )

        return SourceDiscoveryResult(
            source_id=f"doc_{doc.id}",
            source_type="document",
            source_name=doc.name,
            source_archetype=archetype,
            archetype_display_name=display_name,
            archetype_description=description,
            detected_entities=[f"Page_{p}" for p in range(1, (doc.total_pages or 1) + 1)][:10],
            detected_measures=["chunk_density", "word_count", "ocr_confidence"],
            detected_dimensions=["section_heading", "content_type", "page_number"],
            detected_time_axes=["created_at"],
            stats={
                "file_type": doc.file_type,
                "chunks_count": chunks_count,
                "total_pages": doc.total_pages,
                "visual_pages": doc.visual_pages,
                "status": doc.status,
            },
            recommended_chart_families=recommended_charts,
        )


def discover_source(
    source_type: str,
    source_id: int,
    tenant_id: int,
    db: Session,
) -> SourceDiscoveryResult:
    """
    Unified entry point to discover and profile any connected database or uploaded document.
    """
    if source_type == "database":
        db_conn = (
            db.query(models.DatabaseConnection)
            .filter(
                models.DatabaseConnection.id == source_id,
                models.DatabaseConnection.tenant_id == tenant_id,
            )
            .first()
        )
        if not db_conn:
            raise ValueError(f"Database connection {source_id} not found for tenant {tenant_id}")
        return discover_database_archetype(db_conn, db)
    elif source_type == "document":
        doc = (
            db.query(models.Document)
            .filter(
                models.Document.id == source_id,
                models.Document.tenant_id == tenant_id,
            )
            .first()
        )
        if not doc:
            raise ValueError(f"Document {source_id} not found for tenant {tenant_id}")
        return discover_document_archetype(doc, db)
    else:
        raise ValueError(f"Unsupported source type '{source_type}'. Expected 'database' or 'document'.")
