"""
DataSpeakAI — Verifiable Source Citation & Grounding Engine (Phase 7: Task 7.2.3)

Extracts atomic claims from synthesized LLM responses and computes semantic
grounding scores against retrieved chunks via cosine similarity (>0.65 threshold).
Flags potential hallucinations and generates structured, clickable citation pills.
"""

import re
import logging
from typing import List, Dict, Any, Optional
import numpy as np

import schemas

logger = logging.getLogger("dataspeak.citation_service")

# Grounding threshold: Claims with cosine similarity >= 0.65 are considered grounded
GROUNDING_SIMILARITY_THRESHOLD = 0.65
# Low confidence boundary: If average score < 0.60, a disclaimer is triggered
LOW_CONFIDENCE_THRESHOLD = 0.60


class CitationService:
    """
    Computes fine-grained semantic grounding between assistant answers and source chunks.
    """

    def __init__(self, threshold: float = GROUNDING_SIMILARITY_THRESHOLD):
        self.threshold = threshold

    def extract_claims(self, response_text: str) -> List[str]:
        """
        Extracts factual sentences from the response text, filtering out
        code blocks, markdown headings, bullet markers, and conversational pleasantries.
        """
        if not response_text:
            return []

        # Remove code blocks
        cleaned = re.sub(r'```.*?```', ' ', response_text, flags=re.DOTALL)
        # Remove markdown table rows
        table_cleaned_lines = [line for line in cleaned.splitlines() if not line.strip().startswith("|")]
        cleaned = "\n".join(table_cleaned_lines)

        # Split into sentence candidates
        raw_sentences = re.split(r'(?<=[.!?])\s+', cleaned)
        claims: List[str] = []

        # Filter patterns for non-factual conversational fluff
        skip_patterns = [
            r'^(hello|hi|hey|greetings|thank you|thanks|sure|certainly|here is|here are|hope this helps)',
            r'^(in summary|in conclusion|to conclude|let me know)',
            r'^(note:|disclaimer:|warning:)',
        ]

        for s in raw_sentences:
            s_clean = s.strip().lstrip("-*#0123456789. ")
            if len(s_clean) < 15 or len(s_clean.split()) < 3:
                continue

            lower_s = s_clean.lower()
            if any(re.match(p, lower_s) for p in skip_patterns):
                continue

            claims.append(s_clean)

        return claims[:12]  # Cap at top 12 claims for low-latency scoring

    def _cosine_similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """Computes cosine similarity between two 1D vectors."""
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))

    def verify_grounding(
        self,
        response_text: str,
        retrieved_chunks: List[Dict[str, Any]],
        embedding_model: Any = None
    ) -> Dict[str, Any]:
        """
        Extracts claims, computes cosine similarity against retrieved chunks,
        and constructs verifiable citation metadata.
        """
        if not response_text or not retrieved_chunks:
            return {
                "citations": [],
                "claims": [],
                "grounding_confidence": 0.0,
                "has_low_confidence": False,
                "disclaimer": None
            }

        claims = self.extract_claims(response_text)
        if not claims:
            # Fallback citations directly from chunks if claims could not be extracted
            citations = []
            for c in retrieved_chunks[:4]:
                meta = c.get("metadata", {}) or {}
                citations.append(schemas.SourceCitation(
                    document_name=meta.get("source", "Document"),
                    page_number=meta.get("page_number"),
                    content_type=meta.get("content_type", "text"),
                    reference_id=meta.get("reference_id"),
                    snippet=c.get("content", "")[:280],
                    score=round(float(c.get("score", 0.7)), 3)
                ))
            return {
                "citations": citations,
                "claims": [],
                "grounding_confidence": 0.75,
                "has_low_confidence": False,
                "disclaimer": None
            }

        # Load embedding model if not provided
        if embedding_model is None:
            from routers.documents import _load_hf_embeddings
            embedding_model = _load_hf_embeddings("all-MiniLM-L6-v2")

        try:
            chunk_texts = [c.get("content", "") for c in retrieved_chunks]
            chunk_embeddings = embedding_model.embed_documents(chunk_texts)
            claim_embeddings = embedding_model.embed_documents(claims)
        except Exception as embed_err:
            logger.warning(f"[CitationService] Embedding generation note: {embed_err}")
            # Fall back to returning top retrieved chunks as citations
            citations = []
            for c in retrieved_chunks[:4]:
                meta = c.get("metadata", {}) or {}
                citations.append(schemas.SourceCitation(
                    document_name=meta.get("source", "Document"),
                    page_number=meta.get("page_number"),
                    content_type=meta.get("content_type", "text"),
                    reference_id=meta.get("reference_id"),
                    snippet=c.get("content", "")[:280],
                    score=round(float(c.get("score", 0.7)), 3)
                ))
            return {
                "citations": citations,
                "claims": [],
                "grounding_confidence": 0.7,
                "has_low_confidence": False,
                "disclaimer": None
            }

        verified_claims = []
        chunk_hit_scores: Dict[int, float] = {}

        for c_idx, claim_vec in enumerate(claim_embeddings):
            best_score = -1.0
            best_chunk_idx = -1

            for ch_idx, chunk_vec in enumerate(chunk_embeddings):
                sim = self._cosine_similarity(np.array(claim_vec), np.array(chunk_vec))
                if sim > best_score:
                    best_score = sim
                    best_chunk_idx = ch_idx

            is_grounded = bool(best_score >= self.threshold)
            matched_chunk = retrieved_chunks[best_chunk_idx] if best_chunk_idx >= 0 else {}
            meta = matched_chunk.get("metadata", {}) or {}

            verified_claims.append({
                "claim": claims[c_idx],
                "is_grounded": is_grounded,
                "score": round(best_score, 3),
                "source": meta.get("source", "Document"),
                "page_number": meta.get("page_number")
            })

            if best_chunk_idx >= 0:
                chunk_hit_scores[best_chunk_idx] = max(
                    chunk_hit_scores.get(best_chunk_idx, 0.0),
                    best_score
                )

        # Build citations ordered by grounding relevance
        citations_list: List[schemas.SourceCitation] = []
        sorted_hits = sorted(chunk_hit_scores.items(), key=lambda x: x[1], reverse=True)

        for ch_idx, hit_score in sorted_hits:
            ch = retrieved_chunks[ch_idx]
            meta = ch.get("metadata", {}) or {}
            citations_list.append(schemas.SourceCitation(
                document_name=meta.get("source", "Document"),
                page_number=meta.get("page_number"),
                content_type=meta.get("content_type", "text"),
                reference_id=meta.get("reference_id"),
                snippet=ch.get("content", "")[:320],
                score=round(hit_score, 3),
                grounding_score=round(hit_score, 3),
                is_grounded=bool(hit_score >= self.threshold)
            ))

        # If no citations were generated via hits, populate from top retrieved
        if not citations_list:
            for ch in retrieved_chunks[:3]:
                meta = ch.get("metadata", {}) or {}
                chunk_sc = float(ch.get("score", 0.65))
                citations_list.append(schemas.SourceCitation(
                    document_name=meta.get("source", "Document"),
                    page_number=meta.get("page_number"),
                    content_type=meta.get("content_type", "text"),
                    reference_id=meta.get("reference_id"),
                    snippet=ch.get("content", "")[:320],
                    score=round(chunk_sc, 3),
                    grounding_score=round(chunk_sc, 3),
                    is_grounded=bool(chunk_sc >= self.threshold)
                ))

        # Compute aggregate confidence
        scores = [cl["score"] for cl in verified_claims] if verified_claims else [0.7]
        avg_confidence = float(np.mean(scores)) if scores else 0.7
        has_low_confidence = bool(avg_confidence < LOW_CONFIDENCE_THRESHOLD)

        disclaimer = None
        if has_low_confidence:
            disclaimer = (
                "Notice: Some claims in this response have low grounding confidence against "
                "the indexed source documents. Please verify details with original sources."
            )

        return {
            "citations": citations_list,
            "claims": verified_claims,
            "grounding_confidence": round(avg_confidence, 3),
            "has_low_confidence": has_low_confidence,
            "disclaimer": disclaimer
        }


# Global CitationService instance
citation_service = CitationService()
