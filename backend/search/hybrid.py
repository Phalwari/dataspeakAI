from typing import List, Dict, Any, Optional

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
        content = doc.get("content", "")
        doc_key = f"{doc.get('metadata', {}).get('document_id')}_{doc.get('metadata', {}).get('chunk_index')}"
        if not doc_key or doc_key == "None_None":
            doc_key = str(hash(content))
            
        doc_map[doc_key] = doc
        rrf_scores[doc_key] = rrf_scores.get(doc_key, 0.0) + (1.0 / (k + rank))

    # Process Sparse BM25 Results
    for rank, doc in enumerate(sparse_results, 1):
        content = doc.get("content", "")
        doc_key = f"{doc.get('metadata', {}).get('document_id')}_{doc.get('metadata', {}).get('chunk_index')}"
        if not doc_key or doc_key == "None_None":
            doc_key = str(hash(content))
            
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

def cross_encoder_rerank(query: str, candidates: list, top_k: int = 5) -> list:
    if not candidates:
        return []
    from sentence_transformers import CrossEncoder
    model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    pairs = [(query, c["content"]) for c in candidates]
    scores = model.predict(pairs)
    for i, c in enumerate(candidates):
        c["rerank_score"] = float(scores[i])
    return sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)[:top_k]

