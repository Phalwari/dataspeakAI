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
        self.last_accessed = self.last_updated
        self.lock = threading.Lock()

    def consume(self, tokens: int = 1) -> Tuple[bool, int]:
        with self.lock:
            now = time.time()
            self.last_accessed = now
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
        self._last_prune_time = time.time()

        # Concurrent active streams per widget key
        self._active_streams: Dict[str, int] = {}
        self._last_cleanup = time.time()

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

    @property
    def key_limit(self) -> int:
        try:
            return int(os.getenv("WIDGET_RATE_LIMIT_KEY_PER_MIN", "60"))
        except (ValueError, TypeError):
            return 60

    @property
    def ip_limit(self) -> int:
        try:
            return int(os.getenv("WIDGET_RATE_LIMIT_IP_PER_MIN", "30"))
        except (ValueError, TypeError):
            return 30

    @property
    def session_limit(self) -> int:
        try:
            return int(os.getenv("WIDGET_RATE_LIMIT_SESSION_PER_MIN", "20"))
        except (ValueError, TypeError):
            return 20

    @property
    def max_concurrent_streams(self) -> int:
        try:
            return int(os.getenv("WIDGET_MAX_CONCURRENT_STREAMS", "5"))
        except (ValueError, TypeError):
            return 5

    def cleanup_idle_buckets(self, ttl_seconds: int = 600) -> int:
        """
        SEC-05: Evicts idle in-memory token buckets older than ttl_seconds (default 10 min).
        """
        now = time.time()
        evicted = 0
        with self._lock:
            for registry in (self._ip_buckets, self._session_buckets, self._key_buckets):
                to_delete = [
                    k for k, b in list(registry.items())
                    if (now - getattr(b, "last_updated", now)) > ttl_seconds
                ]
                for k in to_delete:
                    del registry[k]
                    evicted += 1
            self._last_cleanup = now
        return evicted

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

    def _prune_inactive_buckets(self, max_idle_seconds: int = 600, max_entries: int = 5000) -> None:
        """
        Prunes in-memory rate limit buckets that have been inactive for > max_idle_seconds (SEC-05).
        Caps registry size at max_entries, dropping the oldest if necessary.
        """
        now = time.time()
        with self._lock:
            for registry in (self._ip_buckets, self._session_buckets):
                # 1. Prune by idle time
                expired_keys = [
                    k for k, b in registry.items()
                    if (now - getattr(b, "last_accessed", b.last_updated)) > max_idle_seconds
                ]
                for k in expired_keys:
                    del registry[k]

                # 2. Cap max size if still over limit
                if len(registry) > max_entries:
                    sorted_by_accessed = sorted(
                        registry.items(),
                        key=lambda item: getattr(item[1], "last_accessed", item[1].last_updated)
                    )
                    excess = len(registry) - max_entries
                    for k, _ in sorted_by_accessed[:excess]:
                        del registry[k]

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
        key_limit: Optional[int] = None,
        ip_limit: Optional[int] = None,
        session_limit: Optional[int] = None
    ) -> Tuple[bool, int]:
        """
        Evaluates token buckets for key, ip, and session.
        Uses Redis if configured, otherwise in-memory token buckets.
        Returns (is_allowed, retry_after_seconds).
        """
        k_limit = key_limit if key_limit is not None else self.key_limit
        i_limit = ip_limit if ip_limit is not None else self.ip_limit
        s_limit = session_limit if session_limit is not None else self.session_limit

        # Periodic idle bucket cleanup (once every 60s)
        if time.time() - self._last_cleanup > 60:
            self.cleanup_idle_buckets(ttl_seconds=600)

        if self.redis_client:
            # 1. Key limit
            ok, retry = self._check_redis_limit(f"widget_rl:key:{public_key}", k_limit, 60)
            if not ok:
                return False, retry
            # 2. IP limit
            ok, retry = self._check_redis_limit(f"widget_rl:ip:{client_ip}", i_limit, 60)
            if not ok:
                return False, retry
            # 3. Session limit
            ok, retry = self._check_redis_limit(f"widget_rl:sess:{session_id}", s_limit, 60)
            if not ok:
                return False, retry
            return True, 0

        # In-memory fallback
        # 1. Key limit
        key_bucket = self._get_or_create_bucket(
            self._key_buckets, public_key, capacity=k_limit, fill_rate=k_limit / 60.0
        )
        ok, retry = key_bucket.consume(1)
        if not ok:
            return False, retry

        # 2. IP limit
        ip_bucket = self._get_or_create_bucket(
            self._ip_buckets, client_ip, capacity=i_limit, fill_rate=i_limit / 60.0
        )
        ok, retry = ip_bucket.consume(1)
        if not ok:
            return False, retry

        # 3. Session limit
        session_bucket = self._get_or_create_bucket(
            self._session_buckets, session_id, capacity=s_limit, fill_rate=s_limit / 60.0
        )
        ok, retry = session_bucket.consume(1)
        if not ok:
            return False, retry

        return True, 0

    def check_session_handshake_rate_limits(
        self,
        public_key: str,
        client_ip: str,
        key_limit: Optional[int] = None,
        ip_limit: Optional[int] = None
    ) -> Tuple[bool, int]:
        k_limit = key_limit or self.key_limit
        i_limit = ip_limit or self.ip_limit

        self._prune_inactive_buckets()

        if self.redis_client:
            ok, retry = self._check_redis_limit(f"widget_rl:handshake:key:{public_key}", k_limit, 60)
            if not ok:
                return False, retry
            ok, retry = self._check_redis_limit(f"widget_rl:handshake:ip:{client_ip}", i_limit, 60)
            if not ok:
                return False, retry
            return True, 0

        # In-memory fallback
        key_bucket = self._get_or_create_bucket(
            self._key_buckets, f"hs_key_{public_key}", capacity=k_limit, fill_rate=k_limit / 60.0
        )
        ok, retry = key_bucket.consume(1)
        if not ok:
            return False, retry

        ip_bucket = self._get_or_create_bucket(
            self._ip_buckets, f"hs_ip_{client_ip}", capacity=i_limit, fill_rate=i_limit / 60.0
        )
        ok, retry = ip_bucket.consume(1)
        if not ok:
            return False, retry

        return True, 0

    def acquire_stream(self, public_key: str, max_concurrent: Optional[int] = None) -> bool:
        """
        Attempts to acquire a concurrent streaming slot for the widget key.
        Returns True if acquired, False if limit exceeded.
        """
        max_streams = max_concurrent if max_concurrent is not None else self.max_concurrent_streams

        if self.redis_client:
            try:
                cur = self.redis_client.incr(f"widget_streams:{public_key}")
                # SEC-06: set 120s TTL with refresh so crashed worker cannot leak slots
                self.redis_client.expire(f"widget_streams:{public_key}", 120)
                if cur > max_streams:
                    self.redis_client.decr(f"widget_streams:{public_key}")
                    return False
                return True
            except Exception:
                pass

        with self._lock:
            current = self._active_streams.get(public_key, 0)
            if current >= max_streams:
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
                if cur <= 0:
                    self.redis_client.delete(f"widget_streams:{public_key}")
                else:
                    self.redis_client.expire(f"widget_streams:{public_key}", 120)
                return
            except Exception:
                pass

        with self._lock:
            current = self._active_streams.get(public_key, 0)
            if current > 0:
                self._active_streams[public_key] = current - 1


# Global singleton instance
widget_limiter = WidgetRateLimiter()

