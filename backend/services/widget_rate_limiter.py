import os
import time
import threading
from typing import Dict, Tuple, Optional
from datetime import datetime, timezone

class InMemoryTokenBucket:
    def __init__(self, capacity: int, fill_rate_per_sec: float):
        self.capacity = capacity
        self.tokens = float(capacity)
        self.fill_rate = fill_rate_per_sec
        self.last_updated = time.time()
        self.lock = threading.Lock()

    def consume(self, tokens: int = 1) -> Tuple[bool, int]:
        with self.lock:
            now = time.time()
            elapsed = now - self.last_updated
            self.last_updated = now
            self.tokens = min(float(self.capacity), self.tokens + elapsed * self.fill_rate)

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True, 0
            else:
                needed = tokens - self.tokens
                retry_after = int(needed / self.fill_rate) + 1
                return False, max(1, retry_after)


class WidgetRateLimiter:
    """
    Tiered Rate Limiter & Concurrent Stream Tracker for Widget Endpoints.
    Enforces:
    1. Key-level rate limit (default 60 req/min)
    2. IP-level rate limit (default 30 req/min)
    3. Session-level rate limit (default 20 req/min)
    4. Max concurrent streaming connections per widget key (default 5)

    Supports optional Redis backend (via REDIS_URL) for distributed multi-worker
    deployments, with automatic graceful fallback to in-memory token buckets.
    """

    def __init__(self):
        self._lock = threading.Lock()
        # Storage for in-memory token buckets
        self._key_buckets: Dict[str, InMemoryTokenBucket] = {}
        self._ip_buckets: Dict[str, InMemoryTokenBucket] = {}
        self._session_buckets: Dict[str, InMemoryTokenBucket] = {}

        # Concurrent active streams per widget key
        self._active_streams: Dict[str, int] = {}

        # Redis backend (optional)
        self.redis_client = None
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                import redis
                client = redis.from_url(redis_url, decode_responses=True)
                client.ping()
                self.redis_client = client
                print("[WIDGET_RATE_LIMITER] Connected to distributed Redis backend.")
            except Exception as e:
                self.redis_client = None
                print(f"[WARNING] [WIDGET_RATE_LIMITER] REDIS_URL is configured but Redis is unreachable ({e}). Falling back to in-memory rate limiting. Multi-worker deployments will enforce rate limits per worker.")
        else:
            print("[WARNING] [WIDGET_RATE_LIMITER] REDIS_URL is unset. Falling back to in-memory rate limiting. In multi-worker deployments (e.g., Docker, Gunicorn, Uvicorn with multiple workers), limits will be enforced per worker process rather than globally.")

    def _get_or_create_bucket(
        self,
        registry: Dict[str, InMemoryTokenBucket],
        identifier: str,
        capacity: int,
        fill_rate: float
    ) -> InMemoryTokenBucket:
        with self._lock:
            if identifier not in registry:
                registry[identifier] = InMemoryTokenBucket(capacity, fill_rate)
            return registry[identifier]

    def _check_redis_limit(self, bucket_key: str, limit: int, window_sec: int = 60) -> Tuple[bool, int]:
        try:
            now = time.time()
            pipe = self.redis_client.pipeline()
            pipe.zremrangebyscore(bucket_key, 0, now - window_sec)
            pipe.zcard(bucket_key)
            pipe.zadd(bucket_key, {f"{now}:{time.time_ns()}": now})
            pipe.expire(bucket_key, window_sec + 2)
            results = pipe.execute()
            count = results[1]
            if count >= limit:
                return False, max(1, int(window_sec - (now % window_sec)))
            return True, 0
        except Exception:
            return True, 0

    def check_rate_limits(
        self,
        public_key: str,
        client_ip: str,
        session_id: str,
        key_limit: int = 60,
        ip_limit: int = 30,
        session_limit: int = 20
    ) -> Tuple[bool, int]:
        """
        Evaluates token buckets for key, ip, and session.
        Uses Redis if configured, otherwise in-memory token buckets.
        Returns (is_allowed, retry_after_seconds).
        """
        if self.redis_client:
            # 1. Key limit
            ok, retry = self._check_redis_limit(f"widget_rl:key:{public_key}", key_limit, 60)
            if not ok:
                return False, retry
            # 2. IP limit
            ok, retry = self._check_redis_limit(f"widget_rl:ip:{client_ip}", ip_limit, 60)
            if not ok:
                return False, retry
            # 3. Session limit
            ok, retry = self._check_redis_limit(f"widget_rl:sess:{session_id}", session_limit, 60)
            if not ok:
                return False, retry
            return True, 0

        # In-memory fallback
        # 1. Key limit
        key_bucket = self._get_or_create_bucket(
            self._key_buckets, public_key, capacity=key_limit, fill_rate=key_limit / 60.0
        )
        ok, retry = key_bucket.consume(1)
        if not ok:
            return False, retry

        # 2. IP limit
        ip_bucket = self._get_or_create_bucket(
            self._ip_buckets, client_ip, capacity=ip_limit, fill_rate=ip_limit / 60.0
        )
        ok, retry = ip_bucket.consume(1)
        if not ok:
            return False, retry

        # 3. Session limit
        session_bucket = self._get_or_create_bucket(
            self._session_buckets, session_id, capacity=session_limit, fill_rate=session_limit / 60.0
        )
        ok, retry = session_bucket.consume(1)
        if not ok:
            return False, retry

        return True, 0

    def acquire_stream(self, public_key: str, max_concurrent: int = 5) -> bool:
        """
        Attempts to acquire a concurrent streaming slot for the widget key.
        Returns True if acquired, False if limit exceeded.
        """
        if self.redis_client:
            try:
                cur = self.redis_client.incr(f"widget_streams:{public_key}")
                if cur > max_concurrent:
                    self.redis_client.decr(f"widget_streams:{public_key}")
                    return False
                return True
            except Exception:
                pass

        with self._lock:
            current = self._active_streams.get(public_key, 0)
            if current >= max_concurrent:
                return False
            self._active_streams[public_key] = current + 1
            return True

    def release_stream(self, public_key: str) -> None:
        """
        Releases an active streaming slot for the widget key.
        """
        if self.redis_client:
            try:
                cur = self.redis_client.decr(f"widget_streams:{public_key}")
                if cur < 0:
                    self.redis_client.set(f"widget_streams:{public_key}", 0)
                return
            except Exception:
                pass

        with self._lock:
            current = self._active_streams.get(public_key, 0)
            if current > 0:
                self._active_streams[public_key] = current - 1


# Global singleton instance
widget_limiter = WidgetRateLimiter()

