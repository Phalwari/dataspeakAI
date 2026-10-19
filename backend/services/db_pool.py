"""Bounded SQLAlchemy engine cache for tenant database connections."""

from collections import OrderedDict
import hashlib
import json
import threading
from typing import Any, Mapping

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

_ENGINE_CACHE_LIMIT = 128
_engine_cache: OrderedDict[str, Engine] = OrderedDict()
_lock = threading.RLock()


def _cache_key(url: str, connect_args: Mapping[str, Any] | None = None) -> str:
    """Hash credentials and options so cache keys never retain connection URLs."""
    material = json.dumps(connect_args or {}, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(f"{url}\0{material}".encode("utf-8")).hexdigest()


def get_engine(url: str, connect_args: Mapping[str, Any] | None = None) -> Engine:
    key = _cache_key(url, connect_args)
    with _lock:
        engine = _engine_cache.get(key)
        if engine is not None:
            _engine_cache.move_to_end(key)
            return engine

        options: dict[str, Any] = {
            "pool_pre_ping": True,
            "pool_recycle": 1800,
            "connect_args": dict(connect_args or {}),
        }
        if url.startswith("sqlite"):
            is_memory = ":memory:" in url or url.rstrip("/") in {
                "sqlite:", "sqlite+pysqlite:"
            }
            if not is_memory:
                options.update({"pool_size": 5, "max_overflow": 5, "pool_timeout": 10})
            options["connect_args"].setdefault("check_same_thread", False)
            options["connect_args"].setdefault("timeout", 10.0)
        else:
            options.update({"pool_size": 5, "max_overflow": 5, "pool_timeout": 10})

        engine = create_engine(url, **options)
        _engine_cache[key] = engine
        if len(_engine_cache) > _ENGINE_CACHE_LIMIT:
            _, evicted = _engine_cache.popitem(last=False)
            evicted.dispose()
        return engine


def invalidate_engine(url: str, connect_args: Mapping[str, Any] | None = None) -> bool:
    """Remove and dispose one cached engine after credentials/connection changes."""
    key = _cache_key(url, connect_args)
    with _lock:
        engine = _engine_cache.pop(key, None)
    if engine is None:
        return False
    engine.dispose()
    return True


def clear_engine_cache() -> None:
    """Dispose all cached engines; intended for controlled shutdown and tests."""
    with _lock:
        engines = list(_engine_cache.values())
        _engine_cache.clear()
    for engine in engines:
        engine.dispose()
