"""
Ingestion Package for DataSpeakAI Multimodal Ingestion Pipeline.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

@dataclass
class NarrativeBlock:
    text: str
    page_number: Optional[int] = None
    section_heading: Optional[str] = None

@dataclass
class TableBlock:
    html_content: str
    reference_id: str
    page_number: Optional[int] = None
    table_index: int = 0
    raw_markdown: Optional[str] = None

@dataclass
class VisualBlock:
    description: str
    reference_id: str
    page_number: Optional[int] = None
    visual_type: str = "chart" # chart, diagram, scanned_page

@dataclass
class DocumentStats:
    total_pages: int = 0
    pages_processed: int = 0
    visual_pages: int = 0
    table_count: int = 0
    image_count: int = 0
    line_count: int = 0
    paragraph_count: int = 0

@dataclass
class ExtractedContent:
    narrative_chunks: List[NarrativeBlock] = field(default_factory=list)
    table_chunks: List[TableBlock] = field(default_factory=list)
    visual_chunks: List[VisualBlock] = field(default_factory=list)
    placeholders: Dict[str, str] = field(default_factory=dict)
    stats: DocumentStats = field(default_factory=DocumentStats)
