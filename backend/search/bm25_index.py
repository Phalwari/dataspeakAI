import os
import pickle
from typing import List, Dict, Any
from rank_bm25 import BM25Okapi

class BM25IndexManager:
    def __init__(self, tenant_id: int):
        self.tenant_id = tenant_id
        self.index_dir = f"vector_store/tenant_{tenant_id}"
        self.index_file = os.path.join(self.index_dir, "bm25.pkl")
        os.makedirs(self.index_dir, exist_ok=True)
        
        self.bm25: BM25Okapi = None
        self.doc_ids: List[int] = []
        self.chunk_metadatas: List[Dict[str, Any]] = []
        self.corpus: List[List[str]] = []
        
        self.load_index()

    def tokenize(self, text: str) -> List[str]:
        return text.lower().split()

    def build_index(self, chunks: List[Dict[str, Any]]):
        """
        chunks: List of dicts with keys: 'id' (db chunk id), 'content', 'metadata'
        """
        self.doc_ids = []
        self.chunk_metadatas = []
        self.corpus = []
        
        for c in chunks:
            tokens = self.tokenize(c["content"])
            self.corpus.append(tokens)
            self.doc_ids.append(c["id"])
            self.chunk_metadatas.append(c.get("metadata", {}))
            
        if self.corpus:
            self.bm25 = BM25Okapi(self.corpus)
            self.save_index()

    def search(self, query: str, top_k: int = 50) -> List[Dict[str, Any]]:
        if not self.bm25 or not self.doc_ids:
            return []
            
        query_tokens = self.tokenize(query)
        scores = self.bm25.get_scores(query_tokens)
        
        indexed_scores = list(enumerate(scores))
        indexed_scores.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for idx, score in indexed_scores[:top_k]:
            if score <= 0:
                continue
            results.append({
                "chunk_id": self.doc_ids[idx],
                "score": float(score),
                "metadata": self.chunk_metadatas[idx]
            })
            
        return results

    def save_index(self):
        with open(self.index_file, "wb") as f:
            pickle.dump({
                "doc_ids": self.doc_ids,
                "chunk_metadatas": self.chunk_metadatas,
                "corpus": self.corpus
            }, f)

    def load_index(self):
        if os.path.exists(self.index_file):
            try:
                with open(self.index_file, "rb") as f:
                    data = pickle.load(f)
                    self.doc_ids = data.get("doc_ids", [])
                    self.chunk_metadatas = data.get("chunk_metadatas", [])
                    self.corpus = data.get("corpus", [])
                    if self.corpus:
                        self.bm25 = BM25Okapi(self.corpus)
            except Exception as e:
                print(f"Failed to load BM25 index for tenant {self.tenant_id}: {e}")
