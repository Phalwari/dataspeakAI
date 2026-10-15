"""
DataSpeakAI — Semantic & Hierarchical Document Chunker (Phase 7: Task 7.2.2)

Splits document text into a two-level hierarchical representation:
- Level 0 (Parent Chunks): Cohesive logical sections, subsections, and complete tables preserving broad context.
- Level 1 (Child Chunks): Granular chunks (~300-500 tokens) with high semantic precision for vector retrieval.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from langchain_text_splitters import RecursiveCharacterTextSplitter


@dataclass
class SemanticChunkSpec:
    content: str
    hierarchy_level: int  # 0 = parent (section/table), 1 = child (granular leaf)
    content_type: str     # "text" | "table" | "image"
    section_heading: Optional[str] = None
    page_number: Optional[int] = None
    reference_id: Optional[str] = None
    parent_local_index: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SemanticHierarchicalChunker:
    """
    Boundary-aware hierarchical document chunker preserving markdown sections,
    tables, and narrative flows intact.
    """

    def __init__(self, target_chunk_size: int = 512, chunk_overlap: int = 50):
        self.chunk_size = target_chunk_size
        self.chunk_overlap = chunk_overlap
        self.child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=target_chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", "; ", " ", ""]
        )

    def _split_into_sections(self, text: str) -> List[Tuple[Optional[str], str]]:
        """
        Splits text by markdown section headings (#, ##, ###, ====, ----).
        Returns list of (section_heading, section_body).
        """
        lines = text.splitlines()
        sections: List[Tuple[Optional[str], List[str]]] = []
        current_heading: Optional[str] = None
        current_lines: List[str] = []

        header_regex = re.compile(r'^(#{1,4}\s+.+|[A-Z0-9\s]{4,}:|Section\s+\d+:?.*)$', re.IGNORECASE)

        for line in lines:
            stripped = line.strip()
            if header_regex.match(stripped) and len(stripped) < 120:
                if current_lines:
                    sections.append((current_heading, current_lines))
                    current_lines = []
                current_heading = stripped.lstrip("#").strip()
            else:
                current_lines.append(line)

        if current_lines:
            sections.append((current_heading, current_lines))

        result: List[Tuple[Optional[str], str]] = []
        for heading, s_lines in sections:
            body = "\n".join(s_lines).strip()
            if body:
                result.append((heading, body))

        if not result and text.strip():
            result.append((None, text.strip()))

        return result

    def chunk_extracted_content(
        self,
        extracted_content: Any,
        document_id: int,
        document_name: str
    ) -> Tuple[List[SemanticChunkSpec], List[SemanticChunkSpec]]:
        """
        Processes ExtractedContent into (parent_chunks, child_chunks).
        Parent chunks carry hierarchy_level = 0.
        Child chunks carry hierarchy_level = 1 and parent_local_index referencing parent list.
        """
        parents: List[SemanticChunkSpec] = []
        children: List[SemanticChunkSpec] = []

        # 1. Process Narrative Blocks
        narrative_blocks = getattr(extracted_content, "narrative_chunks", [])
        for block in narrative_blocks:
            block_text = getattr(block, "text", "")
            page_num = getattr(block, "page_number", None)
            base_heading = getattr(block, "section_heading", None)

            sections = self._split_into_sections(block_text)
            for heading, sec_body in sections:
                effective_heading = heading or base_heading or "Overview"
                p_idx = len(parents)

                # Parent chunk: Full section
                parent_chunk = SemanticChunkSpec(
                    content=sec_body,
                    hierarchy_level=0,
                    content_type="text",
                    section_heading=effective_heading,
                    page_number=page_num,
                    metadata={
                        "document_id": document_id,
                        "source": document_name,
                        "page_number": page_num,
                        "content_type": "text",
                        "section_heading": effective_heading,
                        "hierarchy_level": 0
                    }
                )
                parents.append(parent_chunk)

                # Child chunks: Sub-divided for vector precision
                sub_texts = self.child_splitter.split_text(sec_body)
                if not sub_texts:
                    sub_texts = [sec_body]

                for sub in sub_texts:
                    child_chunk = SemanticChunkSpec(
                        content=sub,
                        hierarchy_level=1,
                        content_type="text",
                        section_heading=effective_heading,
                        page_number=page_num,
                        parent_local_index=p_idx,
                        metadata={
                            "document_id": document_id,
                            "source": document_name,
                            "page_number": page_num,
                            "content_type": "text",
                            "section_heading": effective_heading,
                            "hierarchy_level": 1
                        }
                    )
                    children.append(child_chunk)

        # 2. Process Tables (Preserve table structure as Level 0 parent)
        table_blocks = getattr(extracted_content, "table_chunks", [])
        for tbl in table_blocks:
            tbl_html = getattr(tbl, "html_content", "") or getattr(tbl, "markdown", "") or ""
            p_num = getattr(tbl, "page_number", None)
            ref_id = getattr(tbl, "reference_id", None)
            tbl_heading = f"Table {ref_id}" if ref_id else "Extracted Table"

            p_idx = len(parents)
            parent_table = SemanticChunkSpec(
                content=tbl_html,
                hierarchy_level=0,
                content_type="table",
                section_heading=tbl_heading,
                page_number=p_num,
                reference_id=ref_id,
                metadata={
                    "document_id": document_id,
                    "source": document_name,
                    "page_number": p_num,
                    "content_type": "table",
                    "reference_id": ref_id,
                    "hierarchy_level": 0
                }
            )
            parents.append(parent_table)

            # Tables can also be indexed as child chunks
            child_table = SemanticChunkSpec(
                content=tbl_html,
                hierarchy_level=1,
                content_type="table",
                section_heading=tbl_heading,
                page_number=p_num,
                reference_id=ref_id,
                parent_local_index=p_idx,
                metadata={
                    "document_id": document_id,
                    "source": document_name,
                    "page_number": p_num,
                    "content_type": "table",
                    "reference_id": ref_id,
                    "hierarchy_level": 1
                }
            )
            children.append(child_table)

        # 3. Process Visual Blocks (OCR & diagrams)
        visual_blocks = getattr(extracted_content, "visual_chunks", [])
        for vis in visual_blocks:
            desc = getattr(vis, "description", "")
            p_num = getattr(vis, "page_number", None)
            ref_id = getattr(vis, "reference_id", None)

            p_idx = len(parents)
            parent_vis = SemanticChunkSpec(
                content=desc,
                hierarchy_level=0,
                content_type="image",
                page_number=p_num,
                reference_id=ref_id,
                metadata={
                    "document_id": document_id,
                    "source": document_name,
                    "page_number": p_num,
                    "content_type": "image",
                    "reference_id": ref_id,
                    "hierarchy_level": 0
                }
            )
            parents.append(parent_vis)

            child_vis = SemanticChunkSpec(
                content=desc,
                hierarchy_level=1,
                content_type="image",
                page_number=p_num,
                reference_id=ref_id,
                parent_local_index=p_idx,
                metadata={
                    "document_id": document_id,
                    "source": document_name,
                    "page_number": p_num,
                    "content_type": "image",
                    "reference_id": ref_id,
                    "hierarchy_level": 1
                }
            )
            children.append(child_vis)

        return parents, children

    def chunk_raw_text(
        self,
        raw_text: str,
        document_id: int = 1,
        document_name: str = "document.txt",
        source_name: Optional[str] = None,
        page_number: Optional[int] = 1,
        **kwargs
    ) -> Tuple[List[SemanticChunkSpec], List[SemanticChunkSpec]]:
        """
        Convenience method to chunk raw text or markdown strings into parent and child chunks.
        Recognizes markdown sections (#, ##) and markdown tables.
        """
        doc_name = source_name or document_name
        parents: List[SemanticChunkSpec] = []
        children: List[SemanticChunkSpec] = []

        sections = self._split_into_sections(raw_text)
        for heading, sec_body in sections:
            effective_heading = heading or "Overview"
            
            # Check if sec_body contains markdown table
            lines = sec_body.splitlines()
            table_lines = [l for l in lines if l.strip().startswith("|")]
            non_table_lines = [l for l in lines if not l.strip().startswith("|")]

            if table_lines and len(table_lines) >= 2:
                # Add table parent & child
                table_content = "\n".join(table_lines)
                p_idx = len(parents)
                parent_tbl = SemanticChunkSpec(
                    content=table_content,
                    hierarchy_level=0,
                    content_type="table",
                    section_heading=f"{effective_heading} Table",
                    page_number=page_number,
                    metadata={
                        "document_id": document_id,
                        "source": doc_name,
                        "page_number": page_number,
                        "content_type": "table",
                        "section_heading": f"{effective_heading} Table",
                        "hierarchy_level": 0
                    }
                )
                parents.append(parent_tbl)
                child_tbl = SemanticChunkSpec(
                    content=table_content,
                    hierarchy_level=1,
                    content_type="table",
                    section_heading=f"{effective_heading} Table",
                    page_number=page_number,
                    parent_local_index=p_idx,
                    metadata={
                        "document_id": document_id,
                        "source": doc_name,
                        "page_number": page_number,
                        "content_type": "table",
                        "section_heading": f"{effective_heading} Table",
                        "hierarchy_level": 1
                    }
                )
                children.append(child_tbl)

            narrative_body = "\n".join(non_table_lines).strip()
            if narrative_body:
                p_idx = len(parents)
                parent_chunk = SemanticChunkSpec(
                    content=narrative_body,
                    hierarchy_level=0,
                    content_type="text",
                    section_heading=effective_heading,
                    page_number=page_number,
                    metadata={
                        "document_id": document_id,
                        "source": doc_name,
                        "page_number": page_number,
                        "content_type": "text",
                        "section_heading": effective_heading,
                        "hierarchy_level": 0
                    }
                )
                parents.append(parent_chunk)

                sub_texts = self.child_splitter.split_text(narrative_body)
                if not sub_texts:
                    sub_texts = [narrative_body]

                for sub in sub_texts:
                    child_chunk = SemanticChunkSpec(
                        content=sub,
                        hierarchy_level=1,
                        content_type="text",
                        section_heading=effective_heading,
                        page_number=page_number,
                        parent_local_index=p_idx,
                        metadata={
                            "document_id": document_id,
                            "source": doc_name,
                            "page_number": page_number,
                            "content_type": "text",
                            "section_heading": effective_heading,
                            "hierarchy_level": 1
                        }
                    )
                    children.append(child_chunk)

        return parents, children

    # Alias for flexibility
    chunk_document = chunk_raw_text

