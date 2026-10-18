import os
import json
import time
import uuid
import shutil
import threading
from typing import List, Dict, Any, Tuple, Optional
from search.bm25_index import BM25IndexManager

# Lock registry to serialize index builds per (tenant_id, model_slug)
_generation_locks: Dict[Tuple[int, str], threading.Lock] = {}
_registry_lock = threading.Lock()

def get_tenant_generation_lock(tenant_id: int, model_slug: str) -> threading.Lock:
    key = (tenant_id, model_slug)
    with _registry_lock:
        if key not in _generation_locks:
            _generation_locks[key] = threading.Lock()
        return _generation_locks[key]

class IndexGenerationManager:
    """
    Manages immutable index generations for FAISS and BM25 per tenant and embedding model.
    Enforces atomic publication, integrity verification, and zero-downtime pointer swaps (NR-2.2-B-T07).
    """
    def __init__(self, tenant_id: int, model_name: str = "all-MiniLM-L6-v2", base_dir: str = "vector_store"):
        self.tenant_id = tenant_id
        self.model_name = model_name or "all-MiniLM-L6-v2"
        clean_model = "".join(c if (c.isalnum() or c in "_-.") else "_" for c in self.model_name).strip("._")
        self.model_slug = clean_model or "all-MiniLM-L6-v2"
        self.base_dir = base_dir
        self.tenant_dir = os.path.join(self.base_dir, f"tenant_{tenant_id}_{self.model_slug}")
        self.legacy_dir = os.path.join(self.base_dir, f"tenant_{tenant_id}")
        self.pointer_file = os.path.join(self.tenant_dir, "active_generation.json")

    def get_active_generation_path(self) -> Tuple[str, bool]:
        """
        Returns (path, exists).
        If active_generation.json exists, returns the directory of the active generation.
        Falls back to tenant_dir if index.faiss exists there, then legacy_dir.
        """
        if os.path.exists(self.pointer_file):
            try:
                with open(self.pointer_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    gen_name = data.get("active_generation")
                    if gen_name:
                        gen_path = os.path.join(self.tenant_dir, gen_name)
                        if os.path.exists(gen_path) and os.path.exists(os.path.join(gen_path, "index.faiss")):
                            return gen_path, True
            except Exception as e:
                print(f"[IndexGenerationManager] Failed reading active generation pointer: {e}")

        if os.path.exists(os.path.join(self.tenant_dir, "index.faiss")):
            return self.tenant_dir, True
        if os.path.exists(os.path.join(self.legacy_dir, "index.faiss")):
            return self.legacy_dir, True
        return self.tenant_dir, False

    def build_and_publish_generation(
        self,
        embeddings_model: Any,
        new_chunks: List[str],
        new_metadatas: List[Dict[str, Any]],
        all_bm25_chunks: List[Dict[str, Any]],
        full_rebuild: bool = False
    ) -> str:
        """
        Builds a new immutable index generation in a staging area, runs integrity validation,
        and atomically swaps the active pointer upon success.
        """
        from langchain_community.vectorstores import FAISS

        lock = get_tenant_generation_lock(self.tenant_id, self.model_slug)
        with lock:
            os.makedirs(self.tenant_dir, exist_ok=True)
            staging_root = os.path.join(self.tenant_dir, ".staging")
            os.makedirs(staging_root, exist_ok=True)

            gen_id = f"gen_{int(time.time())}_{uuid.uuid4().hex[:8]}"
            staging_gen_dir = os.path.join(staging_root, gen_id)
            os.makedirs(staging_gen_dir, exist_ok=True)

            target_gen_dir = os.path.join(self.tenant_dir, gen_id)

            try:
                # 1. FAISS Build
                active_path, active_exists = self.get_active_generation_path()
                if active_exists and not full_rebuild:
                    vectorstore = FAISS.load_local(active_path, embeddings_model, allow_dangerous_deserialization=True)
                    # Dimension validation (T06)
                    if hasattr(vectorstore, "index") and hasattr(vectorstore.index, "d"):
                        test_vec = embeddings_model.embed_query("dimension_check")
                        if len(test_vec) != vectorstore.index.d:
                            raise ValueError(
                                f"Vector dimension mismatch: query embedding has dimension {len(test_vec)} "
                                f"but index expects {vectorstore.index.d}. Please re-index documents with the matching model."
                            )
                    if new_chunks:
                        vectorstore.add_texts(texts=new_chunks, metadatas=new_metadatas)
                else:
                    if not new_chunks:
                        test_vec = embeddings_model.embed_query("init")
                        new_chunks = ["init_placeholder"]
                        new_metadatas = [{"document_id": -1, "source": "init", "is_placeholder": True}]
                    vectorstore = FAISS.from_texts(texts=new_chunks, embedding=embeddings_model, metadatas=new_metadatas)

                vectorstore.save_local(staging_gen_dir)

                # 2. BM25 Build
                bm25_path = os.path.join(staging_gen_dir, "bm25.pkl")
                bm25_manager = BM25IndexManager(tenant_id=self.tenant_id)
                bm25_manager.index_file = bm25_path
                bm25_manager.build_index(all_bm25_chunks)

                # Also maintain backwards compatible legacy bm25.pkl
                legacy_bm25_manager = BM25IndexManager(tenant_id=self.tenant_id)
                legacy_bm25_manager.build_index(all_bm25_chunks)

                # 3. Integrity Probe
                probe_store = FAISS.load_local(staging_gen_dir, embeddings_model, allow_dangerous_deserialization=True)
                probe_results = probe_store.similarity_search("healthcheck", k=1)
                if not os.path.exists(os.path.join(staging_gen_dir, "index.faiss")):
                    raise RuntimeError("Integrity probe failed: index.faiss not created in staging")
                if not os.path.exists(bm25_path):
                    raise RuntimeError("Integrity probe failed: bm25.pkl not created in staging")

                # 4. Atomic Publication
                shutil.move(staging_gen_dir, target_gen_dir)

                pointer_data = {
                    "active_generation": gen_id,
                    "model_name": self.model_name,
                    "model_slug": self.model_slug,
                    "published_at": time.time(),
                    "chunk_count": len(new_chunks)
                }
                temp_pointer = os.path.join(self.tenant_dir, f"active_generation_{gen_id}.tmp")
                with open(temp_pointer, "w", encoding="utf-8") as f:
                    json.dump(pointer_data, f, indent=2)
                os.replace(temp_pointer, self.pointer_file)

                # Sync index files into tenant_dir directly for backwards compatibility
                for fname in ["index.faiss", "index.pkl"]:
                    src_f = os.path.join(target_gen_dir, fname)
                    dst_f = os.path.join(self.tenant_dir, fname)
                    if os.path.exists(src_f):
                        shutil.copy2(src_f, dst_f)

                # 5. Clean up old generations (keep newest 3)
                self._prune_old_generations(keep=3, active_gen=gen_id)

                return gen_id

            except Exception as e:
                if os.path.exists(staging_gen_dir):
                    shutil.rmtree(staging_gen_dir, ignore_errors=True)
                raise e

    def _prune_old_generations(self, keep: int = 3, active_gen: Optional[str] = None):
        try:
            entries = [
                d for d in os.listdir(self.tenant_dir)
                if d.startswith("gen_") and os.path.isdir(os.path.join(self.tenant_dir, d))
            ]
            entries.sort(reverse=True)
            to_delete = entries[keep:]
            for old_gen in to_delete:
                if old_gen != active_gen:
                    shutil.rmtree(os.path.join(self.tenant_dir, old_gen), ignore_errors=True)
        except Exception as e:
            print(f"[IndexGenerationManager] Generation prune note: {e}")
