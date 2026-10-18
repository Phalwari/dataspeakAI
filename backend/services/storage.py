import os
import shutil
import hashlib
from typing import Optional

class LocalStorageAdapter:
    """
    Local filesystem storage adapter conforming to the durable object storage contract (NR-2.2-B-T01 / NR-3.1-A-T03).
    Stores uploaded document originals under content-addressed, tenant-isolated paths:
    storage/documents/{tenant_id}/{doc_id}_{content_sha256}.bin
    """
    def __init__(self, base_dir: str = "storage"):
        self.base_dir = base_dir
        os.makedirs(os.path.join(self.base_dir, "documents"), exist_ok=True)

    def get_storage_path(self, tenant_id: int, doc_id: int, sha256_hash: str, filename: Optional[str] = None) -> str:
        tenant_dir = os.path.join(self.base_dir, "documents", str(tenant_id))
        os.makedirs(tenant_dir, exist_ok=True)
        ext = ""
        if filename:
            ext = os.path.splitext(filename)[1].lower()
        if not ext:
            ext = ".bin"
        return os.path.join(tenant_dir, f"{doc_id}_{sha256_hash}{ext}")

    def store_file(self, tenant_id: int, doc_id: int, source_path: str, sha256_hash: str, filename: Optional[str] = None) -> str:
        target_path = self.get_storage_path(tenant_id, doc_id, sha256_hash, filename)
        if os.path.abspath(source_path) != os.path.abspath(target_path):
            shutil.copy2(source_path, target_path)
        return target_path

    def get_file_path(self, tenant_id: int, doc_id: int, sha256_hash: str, filename: Optional[str] = None) -> Optional[str]:
        target_path = self.get_storage_path(tenant_id, doc_id, sha256_hash, filename)
        if os.path.exists(target_path):
            return target_path
        # Legacy fallback to .bin if filename-specific path doesn't exist
        legacy_path = os.path.join(self.base_dir, "documents", str(tenant_id), f"{doc_id}_{sha256_hash}.bin")
        if os.path.exists(legacy_path):
            return legacy_path
        return None

    def delete_file(self, tenant_id: int, doc_id: int, sha256_hash: str, filename: Optional[str] = None) -> bool:
        target_path = self.get_storage_path(tenant_id, doc_id, sha256_hash, filename)
        deleted = False
        if os.path.exists(target_path):
            try:
                os.remove(target_path)
                deleted = True
            except OSError:
                pass
        # Also clean up legacy .bin path if present
        legacy_path = os.path.join(self.base_dir, "documents", str(tenant_id), f"{doc_id}_{sha256_hash}.bin")
        if os.path.exists(legacy_path) and legacy_path != target_path:
            try:
                os.remove(legacy_path)
                deleted = True
            except OSError:
                pass
        return deleted

storage_service = LocalStorageAdapter()
