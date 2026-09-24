import os
import pickle
import math
from typing import List, Dict, Any, Optional

try:

    from rank_bm25 import BM25Okapi  # type: ignore
except ImportError:
    class BM25Okapi:
        """Pure-Python standard BM25Okapi implementation fallback"""
        def __init__(self, corpus, k1=1.5, b=0.75, epsilon=0.25):
            self.k1 = k1
            self.b = b
            self.epsilon = epsilon
            self.corpus_size = len(corpus)
            self.avgdl = sum(len(x) for x in corpus) / self.corpus_size if self.corpus_size > 0 else 0
            self.doc_freqs = []
            self.idf = {}
            self.doc_len = []
            self.nd = {}
            self._initialize(corpus)

        def _initialize(self, corpus):
            for document in corpus:
                self.doc_len.append(len(document))
                frequencies = {}
                for word in document:
                    frequencies[word] = frequencies.get(word, 0) + 1
                self.doc_freqs.append(frequencies)

                for word in frequencies.keys():
                    self.nd[word] = self.nd.get(word, 0) + 1

            for word, freq in self.nd.items():
                idf = math.log((self.corpus_size - freq + 0.5) / (freq + 0.5) + 1)
                self.idf[word] = idf

        def get_scores(self, query):
            score = [0.0] * self.corpus_size
            doc_len = self.doc_len
            for q in query:
                q_freq = [doc.get(q, 0) for doc in self.doc_freqs]
                q_idf = self.idf.get(q, 0.0)
                for i in range(self.corpus_size):
                    if q_freq[i] == 0:
                        continue
                    score[i] += (q_idf * q_freq[i] * (self.k1 + 1)) / (
                        q_freq[i] + self.k1 * (1 - self.b + self.b * doc_len[i] / (self.avgdl or 1))
                    )
            return score


class BM25IndexManager:
    def __init__(self, tenant_id: int):
        self.tenant_id = tenant_id
        self.index_dir = f"vector_store/tenant_{tenant_id}"
        self.index_file = os.path.join(self.index_dir, "bm25.pkl")
        os.makedirs(self.index_dir, exist_ok=True)
        
        self.bm25: Optional[BM25Okapi] = None
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
