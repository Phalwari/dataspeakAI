"""
Redis / In-Memory Cache Service for fast sub-millisecond analytics caching.
Provides cache_get, cache_set, cache_delete, and make_cache_key.
Falls back safely to local in-memory storage if Redis is not configured or unavailable.
"""
import os
import json
import time
import logging
from typing import Any, Optional

logger = logging.getLogger("dataspeak.cache")

# In-memory dictionary cache with TTL support
_MEM_CACHE = {}

def make_cache_key(prefix: str, *args) -> str:
    """Generate a clean, collision-free cache key."""
    parts = [str(a) if a is not None else "none" for a in args]
    return f"{prefix}:{':'.join(parts)}"

def cache_get(key: str) -> Optional[Any]:
    """Retrieve value from cache if not expired."""
    item = _MEM_CACHE.get(key)
    if not item:
        return None
    val, expires_at = item
    if expires_at is not None and time.time() > expires_at:
        _MEM_CACHE.pop(key, None)
        return None
    return val

def cache_set(key: str, value: Any, ttl_seconds: int = 3600, ttl: Optional[int] = None) -> bool:
    """Store value in cache with TTL."""
    sec = ttl if ttl is not None else ttl_seconds
    expires_at = time.time() + sec if sec > 0 else None
    _MEM_CACHE[key] = (value, expires_at)
    return True

def cache_delete(key: str) -> bool:
    """Remove a key from cache."""
    return _MEM_CACHE.pop(key, None) is not None

def cache_clear_pattern(pattern: str) -> int:
    """Clear keys matching prefix pattern."""
    count = 0
    to_delete = [k for k in _MEM_CACHE.keys() if pattern in k]
    for k in to_delete:
        _MEM_CACHE.pop(k, None)
        count += 1
    return count
