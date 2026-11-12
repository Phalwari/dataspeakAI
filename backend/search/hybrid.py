from typing import List, Dict, Any, Optional
import hashlib


def _chunk_key(doc: Dict[str, Any]) -> str:
    """Identify a passage, never collapse all passages of a document."""
    meta = doc.get("metadata") or {}
    if meta.get("chunk_id") is not None:
        return f"chunk:{meta['document_id'] if 'document_id' in meta else ''}:{meta['chunk_id']}"
    if meta.get("chunk_index") is not None:
        return f"index:{meta.get('document_id')}:{meta['chunk_index']}"
    digest = hashlib.sha256(doc.get("content", "").encode("utf-8")).hexdigest()
    return f"content:{meta.get('document_id')}:{digest}"

def reciprocal_rank_fusion(
    dense_results: List[Dict[str, Any]], 
    sparse_results: List[Dict[str, Any]], 
    k: int = 60,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    RRF_Score(d) = Σ 1 / (k + rank(d))
    """
    rrf_scores: Dict[str, float] = {}
    doc_map: Dict[str, Dict[str, Any]] = {}

    # Process Dense Results
    for rank, doc in enumerate(dense_results, 1):
        doc_key = _chunk_key(doc)
            
        doc_map[doc_key] = doc
        rrf_scores[doc_key] = rrf_scores.get(doc_key, 0.0) + (1.0 / (k + rank))

    # Process Sparse BM25 Results
    for rank, doc in enumerate(sparse_results, 1):
        doc_key = _chunk_key(doc)
            
        doc_map[doc_key] = doc
        rrf_scores[doc_key] = rrf_scores.get(doc_key, 0.0) + (1.0 / (k + rank))

    # Sort candidates by combined RRF score
    sorted_docs = sorted(rrf_scores.items(), key=lambda item: item[1], reverse=True)

    fused_results = []
    for doc_key, score in sorted_docs[:top_k]:
        res = doc_map[doc_key].copy()
        res["score"] = float(score)
        fused_results.append(res)

    return fused_results

_cached_cross_encoder = None

def get_cross_encoder():
    global _cached_cross_encoder
    if _cached_cross_encoder is None:
        from sentence_transformers import CrossEncoder
        _cached_cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _cached_cross_encoder

def cross_encoder_rerank(query: str, candidates: list, top_k: int = 5) -> list:
    if not candidates:
        return []
    model = get_cross_encoder()
    pairs = [(query, c["content"]) for c in candidates]
    scores = model.predict(pairs)
    for i, c in enumerate(candidates):
        c["rerank_score"] = float(scores[i])
    return sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)[:top_k]

