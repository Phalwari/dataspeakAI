import json
import hashlib
import threading
import time
from typing import Callable, Any

class InMemoryCacheService:
    """Redis na ho to bhi kaam kare — simple in-memory TTL cache."""
    def __init__(self, default_ttl=600):
        self._store = {}
        self._lock = threading.Lock()
        self.default_ttl = default_ttl

    def _key(self, tenant_id, cache_key):
        return f"{tenant_id}:{cache_key}"

    def get_or_compute(self, tenant_id: int, cache_key: str, compute_fn: Callable[[], Any], ttl: int = None):
        full_key = self._key(tenant_id, cache_key)
        ttl = ttl or self.default_ttl
        with self._lock:
            entry = self._store.get(full_key)
            if entry and (time.time() - entry["ts"]) < ttl:
                return entry["value"]
        value = compute_fn()
        with self._lock:
            self._store[full_key] = {"value": value, "ts": time.time()}
        return value

    def invalidate(self, tenant_id: int, cache_key: str):
        full_key = self._key(tenant_id, cache_key)
        with self._lock:
            self._store.pop(full_key, None)

cache_service = InMemoryCacheService()
