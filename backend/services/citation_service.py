"""
DataSpeakAI — Verifiable Source Citation & Grounding Engine (NR-2.2 / Tasks NR-2.2-A-T01 to T05)

Extracts atomic claims from synthesized LLM responses and computes semantic
grounding scores against retrieved chunks via cosine similarity (>0.65 threshold).
Enforces deterministic numerical/date checks, negation polarity verification,
and honest unverified states (no positive fallback confidence on embedding errors).
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
import numpy as np

import schemas

logger = logging.getLogger("dataspeak.citation_service")

# Grounding threshold: Claims with cosine similarity >= 0.65 are considered grounded
GROUNDING_SIMILARITY_THRESHOLD = 0.65
# Low confidence boundary: If coverage ratio < 0.80 or confidence < 0.60, a disclaimer is triggered
LOW_CONFIDENCE_THRESHOLD = 0.60

# Negation words indicating opposite polarity
NEGATION_TOKENS = {
    "not", "never", "no", "none", "neither", "nor", "without",
    "hardly", "scarcely", "barely", "failed", "fails", "cannot", "can't",
    "won't", "didn't", "doesn't", "isn't", "aren't", "wasn't", "weren't"
}


def extract_numbers_and_dates(text: str) -> Set[str]:
    """
    Extracts numerical amounts, currency, percentages, years, and dates.
    Normalizes them for substring or token comparison.
    """
    if not text:
        return set()
    
    tokens = set()
    # Currency with amounts: $10M, $12.4 million, €50, etc.
    currency_matches = re.findall(r'[\$€£]\s*\d+(?:,\d{3})*(?:\.\d+)?(?:\s*(?:million|billion|thousand|[kKmMbBtT]))?', text)
    for m in currency_matches:
        tokens.add(re.sub(r'\s+', '', m.lower()))
    
    # Percentages: 40%, 12.5%
    pct_matches = re.findall(r'\b\d+(?:\.\d+)?%', text)
    for m in pct_matches:
        tokens.add(m.lower())
    
    # Years: 1990-2099
    year_matches = re.findall(r'\b(?:19|20)\d{2}\b', text)
    for m in year_matches:
        tokens.add(m)
        
    # Standard numbers with decimals or commas (e.g. 10000, 12.4, 250)
    raw_nums = re.findall(r'\b\d+(?:,\d{3})*(?:\.\d+)?\b', text)
    for m in raw_nums:
        clean_num = m.replace(',', '')
        # Only add if not part of small indexing or single digit if possible, but keep specific numbers
        if len(clean_num) > 1 or clean_num in {"0", "1"}:
            tokens.add(clean_num)
            
    # Written month dates: "September 2021", "Jan 15, 2024"
    date_matches = re.findall(r'\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember))\s+\d{1,4}\b', text, flags=re.IGNORECASE)
    for m in date_matches:
        tokens.add(m.lower().strip())
        
    return tokens


def has_negation(text: str) -> bool:
    """Checks whether the text contains explicit negation tokens."""
    words = set(re.findall(r'\b\w+\b', text.lower()))
    return bool(words & NEGATION_TOKENS)


def verify_numerical_and_negation(claim: str, chunk_content: str) -> Tuple[bool, Optional[str]]:
    """
    Deterministically verifies that numbers/dates and negation polarity in a claim
    are supported by the source chunk content.
    Returns (is_valid, failure_reason).
    """
    claim_nums = extract_numbers_and_dates(claim)
    chunk_nums = extract_numbers_and_dates(chunk_content)
    
    # If the claim asserts specific numbers/dates that don't appear in the chunk
    missing_nums = []
    chunk_lower = chunk_content.lower()
    for num in claim_nums:
        # Check either in chunk_nums set or as a substring
        if num not in chunk_nums and num not in chunk_lower and num.replace('$', '') not in chunk_lower:
            missing_nums.append(num)
            
    if missing_nums:
        return False, f"Numerical/date token mismatch: {missing_nums} not found in source evidence"
    
    # Check negation polarity mismatch
    claim_neg = has_negation(claim)
    chunk_neg = has_negation(chunk_content)
    if claim_neg != chunk_neg:
        return False, f"Negation polarity mismatch (claim negation={claim_neg}, source negation={chunk_neg})"
        
    return True, None


class CitationService:
    """
    Computes fine-grained semantic grounding between assistant answers and source chunks.
    Maintains distinct retrieval similarity vs claim support scores, and honest unverified states.
    """

    def __init__(self, threshold: float = GROUNDING_SIMILARITY_THRESHOLD):
        self.threshold = threshold

    def extract_claims_with_stats(
        self,
        response_text: str,
        parse_tables: bool = False
    ) -> Tuple[List[str], int]:
        """
        Extracts factual sentences and statements from response text,
        filtering out conversational pleasantries, markdown headings, and code.
        Returns (claims_list, skipped_claims_count).
        """
        if not response_text:
            return [], 0

        # Remove code blocks
        cleaned = re.sub(r'```.*?```', ' ', response_text, flags=re.DOTALL)
        
        table_claims: List[str] = []
        skipped_count = 0
        
        # Handle markdown tables if requested
        if parse_tables:
            lines = cleaned.splitlines()
            table_rows = []
            non_table_lines = []
            headers = []
            
            for line in lines:
                sline = line.strip()
                if sline.startswith("|") and sline.endswith("|"):
                    cells = [c.strip() for c in sline.strip("|").split("|")]
                    if all(re.match(r'^:?-+:?$', c) for c in cells):
                        continue  # Separator row
                    if not headers:
                        headers = cells
                    else:
                        table_rows.append(cells)
                else:
                    non_table_lines.append(line)
                    
            for row in table_rows:
                # Pair headers with row cells if lengths match
                if headers and len(row) == len(headers):
                    row_facts = [f"{headers[i]} is {row[i]}" for i in range(len(row)) if row[i] and headers[i]]
                    if row_facts:
                        table_claims.append(", ".join(row_facts) + ".")
                else:
                    valid_cells = [c for c in row if c and len(c) > 2]
                    if valid_cells:
                        table_claims.append(": ".join(valid_cells) + ".")
                        
            cleaned = "\n".join(non_table_lines)
        else:
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
                skipped_count += 1
                continue

            lower_s = s_clean.lower()
            if any(re.match(p, lower_s) for p in skip_patterns):
                skipped_count += 1
                continue

            claims.append(s_clean)

        if parse_tables and table_claims:
            claims.extend(table_claims)

        return claims[:12], skipped_count

    def extract_claims(self, response_text: str, parse_tables: bool = False) -> List[str]:
        """
        Extracts factual sentences from the response text.
        Maintains backward compatibility with earlier callers and tests.
        """
        claims, _ = self.extract_claims_with_stats(response_text, parse_tables=parse_tables)
        return claims

    def _cosine_similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """Computes cosine similarity between two 1D vectors."""
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))

    def verify_grounding(
        self,
        response_text: str = "",
        retrieved_chunks: List[Dict[str, Any]] = None,
        embedding_model: Any = None,
        answer: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Extracts claims, computes cosine similarity against retrieved chunks,
        verifies numerical and negation constraints, and constructs verifiable citation metadata.
        Honors unverified states and never produces positive confidence on embedding failures.
        """
        actual_text = answer or response_text or ""
        chunks = retrieved_chunks or []

        if not actual_text or not chunks:
            return {
                "citations": [],
                "claims": [],
                "grounding_status": schemas.GroundingStatus.NO_CLAIMS.value if not actual_text else schemas.GroundingStatus.UNVERIFIED.value,
                "grounding_confidence": 0.0,
                "claim_coverage_ratio": 0.0,
                "total_claims_count": 0,
                "verified_claims_count": 0,
                "skipped_claims_count": 0,
                "unverified_reason": "No response text or no retrieved chunks provided" if not chunks else None,
                "has_low_confidence": False,
                "disclaimer": None
            }

        claims, skipped_count = self.extract_claims_with_stats(actual_text, parse_tables=False)
        if not claims:
            # Fallback citations directly from chunks if claims could not be extracted
            citations = []
            for c in chunks[:4]:
                meta = c.get("metadata", {}) or {}
                ret_sim = round(float(c.get("score", 0.0)), 3)
                citations.append(schemas.SourceCitation(
                    document_name=meta.get("source", "Document"),
                    page_number=meta.get("page_number"),
                    content_type=meta.get("content_type", "text"),
                    reference_id=meta.get("reference_id"),
                    snippet=c.get("content", "")[:280],
                    score=ret_sim,
                    retrieval_similarity=ret_sim,
                    claim_support_score=0.0,
                    document_id=meta.get("document_id"),
                    chunk_id=meta.get("chunk_id") or c.get("id"),
                    document_version=meta.get("version", 1),
                    grounding_status=schemas.GroundingStatus.NO_CLAIMS.value,
                    is_grounded=False
                ))
            return {
                "citations": citations,
                "claims": [],
                "grounding_status": schemas.GroundingStatus.NO_CLAIMS.value,
                "grounding_confidence": 0.0,
                "claim_coverage_ratio": 0.0,
                "total_claims_count": 0,
                "verified_claims_count": 0,
                "skipped_claims_count": skipped_count,
                "unverified_reason": "No factual claims identified in answer",
                "has_low_confidence": False,
                "disclaimer": None
            }

        # Load embedding model if not provided
        if embedding_model is None:
            from routers.documents import _load_hf_embeddings
            embedding_model = _load_hf_embeddings("all-MiniLM-L6-v2")

        try:
            chunk_texts = [c.get("content", "") for c in chunks]
            chunk_embeddings = embedding_model.embed_documents(chunk_texts)
            claim_embeddings = embedding_model.embed_documents(claims)
        except Exception as embed_err:
            logger.warning(f"[CitationService] Embedding generation failure: {embed_err}")
            unverified_msg = f"Grounding verification unavailable: {str(embed_err)}"
            citations = []
            for c in chunks[:4]:
                meta = c.get("metadata", {}) or {}
                ret_sim = round(float(c.get("score", 0.0)), 3)
                citations.append(schemas.SourceCitation(
                    document_name=meta.get("source", "Document"),
                    page_number=meta.get("page_number"),
                    content_type=meta.get("content_type", "text"),
                    reference_id=meta.get("reference_id"),
                    snippet=c.get("content", "")[:280],
                    score=ret_sim,
                    retrieval_similarity=ret_sim,
                    claim_support_score=0.0,
                    document_id=meta.get("document_id"),
                    chunk_id=meta.get("chunk_id") or c.get("id"),
                    document_version=meta.get("version", 1),
                    grounding_status=schemas.GroundingStatus.UNVERIFIED.value,
                    grounding_score=0.0,
                    is_grounded=False
                ))
            return {
                "citations": citations,
                "claims": [{"claim": cl, "is_grounded": False, "score": 0.0, "reason": unverified_msg} for cl in claims],
                "grounding_status": schemas.GroundingStatus.UNVERIFIED.value,
                "grounding_confidence": 0.0,
                "claim_coverage_ratio": 0.0,
                "total_claims_count": len(claims),
                "verified_claims_count": 0,
                "skipped_claims_count": skipped_count,
                "unverified_reason": unverified_msg,
                "has_low_confidence": True,
                "disclaimer": "Grounding verification is currently unverified due to embedding service unavailability. Please review original sources."
            }

        verified_claims = []
        chunk_claim_scores: Dict[int, float] = {}

        for c_idx, claim_vec in enumerate(claim_embeddings):
            claim_text = claims[c_idx]
            best_score = -1.0
            best_chunk_idx = -1

            for ch_idx, chunk_vec in enumerate(chunk_embeddings):
                sim = self._cosine_similarity(np.array(claim_vec), np.array(chunk_vec))
                if sim > best_score:
                    best_score = sim
                    best_chunk_idx = ch_idx

            matched_chunk = chunks[best_chunk_idx] if best_chunk_idx >= 0 else {}
            chunk_content = matched_chunk.get("content", "")
            meta = matched_chunk.get("metadata", {}) or {}

            # Perform deterministic numerical and negation checks
            num_ok, num_err = verify_numerical_and_negation(claim_text, chunk_content)
            
            if not num_ok:
                # Contradiction or hallucination detected
                is_grounded = False
                effective_score = 0.0
                claim_reason = num_err
            else:
                is_grounded = bool(best_score >= self.threshold)
                effective_score = round(best_score, 3)
                claim_reason = None

            verified_claims.append({
                "claim": claim_text,
                "is_grounded": is_grounded,
                "score": effective_score,
                "raw_similarity": round(best_score, 3),
                "source": meta.get("source", "Document"),
                "page_number": meta.get("page_number"),
                "reason": claim_reason
            })

            if best_chunk_idx >= 0 and is_grounded:
                chunk_claim_scores[best_chunk_idx] = max(
                    chunk_claim_scores.get(best_chunk_idx, 0.0),
                    effective_score
                )

        total_claims_count = len(claims)
        verified_claims_count = sum(1 for cl in verified_claims if cl["is_grounded"])
        coverage_ratio = float(verified_claims_count / total_claims_count) if total_claims_count > 0 else 0.0

        # Determine overall grounding status
        if coverage_ratio >= 0.8:
            grounding_status = schemas.GroundingStatus.SUPPORTED.value
        elif coverage_ratio > 0.0:
            grounding_status = schemas.GroundingStatus.PARTIALLY_SUPPORTED.value
        else:
            grounding_status = schemas.GroundingStatus.UNSUPPORTED.value

        # Build citations ordered by claim support score
        citations_list: List[schemas.SourceCitation] = []
        sorted_hits = sorted(chunk_claim_scores.items(), key=lambda x: x[1], reverse=True)

        for ch_idx, hit_score in sorted_hits:
            ch = chunks[ch_idx]
            meta = ch.get("metadata", {}) or {}
            ret_sim = round(float(ch.get("score", hit_score)), 3)
            citations_list.append(schemas.SourceCitation(
                document_name=meta.get("source", "Document"),
                page_number=meta.get("page_number"),
                content_type=meta.get("content_type", "text"),
                reference_id=meta.get("reference_id"),
                snippet=ch.get("content", "")[:320],
                score=round(hit_score, 3),
                retrieval_similarity=ret_sim,
                claim_support_score=round(hit_score, 3),
                grounding_score=round(hit_score, 3),
                document_id=meta.get("document_id"),
                chunk_id=meta.get("chunk_id") or ch.get("id"),
                document_version=meta.get("version", 1),
                grounding_status=schemas.GroundingStatus.SUPPORTED.value if hit_score >= self.threshold else schemas.GroundingStatus.PARTIALLY_SUPPORTED.value,
                is_grounded=True
            ))

        # If no chunk met full threshold, populate from top retrieved chunks
        if not citations_list:
            for ch in chunks[:3]:
                meta = ch.get("metadata", {}) or {}
                chunk_sc = float(ch.get("score", 0.0))
                citations_list.append(schemas.SourceCitation(
                    document_name=meta.get("source", "Document"),
                    page_number=meta.get("page_number"),
                    content_type=meta.get("content_type", "text"),
                    reference_id=meta.get("reference_id"),
                    snippet=ch.get("content", "")[:320],
                    score=round(chunk_sc, 3),
                    retrieval_similarity=round(chunk_sc, 3),
                    claim_support_score=0.0,
                    grounding_score=0.0,
                    document_id=meta.get("document_id"),
                    chunk_id=meta.get("chunk_id") or ch.get("id"),
                    document_version=meta.get("version", 1),
                    grounding_status=schemas.GroundingStatus.UNSUPPORTED.value,
                    is_grounded=False
                ))

        # Compute aggregate confidence
        scores = [cl["score"] for cl in verified_claims] if verified_claims else [0.0]
        avg_confidence = float(np.mean(scores)) if scores else 0.0
        has_low_confidence = bool(avg_confidence < LOW_CONFIDENCE_THRESHOLD or coverage_ratio < 0.8)

        disclaimer = None
        if has_low_confidence:
            disclaimer = (
                "Notice: Some claims in this response have low grounding confidence against "
                "the indexed source documents. Please verify details with original sources."
            )

        return {
            "citations": citations_list,
            "claims": verified_claims,
            "grounding_status": grounding_status,
            "grounding_confidence": round(avg_confidence, 3),
            "claim_coverage_ratio": round(coverage_ratio, 3),
            "total_claims_count": total_claims_count,
            "verified_claims_count": verified_claims_count,
            "skipped_claims_count": skipped_count,
            "unverified_reason": None,
            "has_low_confidence": has_low_confidence,
            "disclaimer": disclaimer
        }


# Global CitationService instance
citation_service = CitationService()

