"""
LLM Metrics & Telemetry Datastore (Thread-Safe In-Memory Observability).
Tracks token counts, TTFT, latency percentiles, error rates (429/403/5xx),
provider distribution, and tenant cost attribution for Phase 7.1.
"""

import time
import threading
from typing import Dict, List, Optional, Any


class LLMMetrics:
    def __init__(self, max_samples: int = 1000):
        self._lock = threading.Lock()
        self._max_samples = max_samples
        self._total_requests = 0
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0
        self._total_latency_ms = 0.0

        self._requests_by_provider: Dict[str, int] = {}
        self._requests_by_model: Dict[str, int] = {}
        self._requests_by_purpose: Dict[str, int] = {}
        self._errors_by_status: Dict[int, int] = {}
        self._key_stats: Dict[str, Dict[str, Any]] = {}
        self._tenant_usage: Dict[int, Dict[str, Any]] = {}

        self._recent_latency_samples: List[float] = []
        self._recent_ttft_samples: List[float] = []

    def record_request(
        self,
        provider: str,
        model: str,
        tenant_id: Optional[int] = None,
        purpose: str = "general",
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        latency_ms: float = 0.0,
        ttft_ms: Optional[float] = None,
        status_code: int = 200,
        error: Optional[str] = None,
        masked_key: Optional[str] = None
    ) -> None:
        """Records telemetry for an LLM generation or streaming call."""
        with self._lock:
            self._total_requests += 1
            self._total_prompt_tokens += max(0, prompt_tokens)
            self._total_completion_tokens += max(0, completion_tokens)
            self._total_latency_ms += max(0.0, latency_ms)

            # Provider & Model distribution
            prov = provider.lower() if provider else "unknown"
            self._requests_by_provider[prov] = self._requests_by_provider.get(prov, 0) + 1
            mod = model.lower() if model else "unknown"
            self._requests_by_model[mod] = self._requests_by_model.get(mod, 0) + 1

            # Purpose
            purp = purpose.lower() if purpose else "general"
            self._requests_by_purpose[purp] = self._requests_by_purpose.get(purp, 0) + 1

            # Status codes
            if status_code != 200:
                self._errors_by_status[status_code] = self._errors_by_status.get(status_code, 0) + 1

            # Latency samples (keep bounded)
            if latency_ms > 0:
                self._recent_latency_samples.append(latency_ms)
                if len(self._recent_latency_samples) > self._max_samples:
                    self._recent_latency_samples.pop(0)

            # TTFT samples
            if ttft_ms is not None and ttft_ms > 0:
                self._recent_ttft_samples.append(ttft_ms)
                if len(self._recent_ttft_samples) > self._max_samples:
                    self._recent_ttft_samples.pop(0)

            # Key stats
            if masked_key:
                if masked_key not in self._key_stats:
                    self._key_stats[masked_key] = {
                        "provider": prov,
                        "success": 0,
                        "rate_limited": 0,
                        "failures": 0,
                        "last_used": time.time()
                    }
                k_stat = self._key_stats[masked_key]
                k_stat["last_used"] = time.time()
                if status_code == 200:
                    k_stat["success"] += 1
                elif status_code in (429, 403):
                    k_stat["rate_limited"] += 1
                else:
                    k_stat["failures"] += 1

            # Tenant cost & usage attribution
            if tenant_id is not None:
                if tenant_id not in self._tenant_usage:
                    self._tenant_usage[tenant_id] = {
                        "requests": 0,
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "estimated_cost_usd": 0.0
                    }
                t_stat = self._tenant_usage[tenant_id]
                t_stat["requests"] += 1
                t_stat["prompt_tokens"] += max(0, prompt_tokens)
                t_stat["completion_tokens"] += max(0, completion_tokens)
                # Approximate blended rate: $0.10/M input, $0.40/M output
                cost = (prompt_tokens * 0.0000001) + (completion_tokens * 0.0000004)
                t_stat["estimated_cost_usd"] = round(t_stat["estimated_cost_usd"] + cost, 6)

    def record_key_cooldown(self, masked_key: str, provider: str, cooldown_duration_sec: float = 60.0) -> None:
        """Records that a key has entered quarantine due to 429/403 exhaustion."""
        with self._lock:
            if masked_key not in self._key_stats:
                self._key_stats[masked_key] = {
                    "provider": provider.lower(),
                    "success": 0,
                    "rate_limited": 0,
                    "failures": 0,
                    "last_used": time.time()
                }
            self._key_stats[masked_key]["rate_limited"] += 1
            self._key_stats[masked_key]["cooldown_until"] = time.time() + cooldown_duration_sec

    def _calculate_percentile(self, samples: List[float], percentile: float) -> float:
        if not samples:
            return 0.0
        sorted_samples = sorted(samples)
        k = (len(sorted_samples) - 1) * (percentile / 100.0)
        f = int(k)
        c = f + 1
        if c < len(sorted_samples):
            d0 = sorted_samples[f] * (c - k)
            d1 = sorted_samples[c] * (k - f)
            return round(d0 + d1, 2)
        return round(sorted_samples[f], 2)

    def get_summary(self) -> Dict[str, Any]:
        """Returns structured observability summary."""
        with self._lock:
            avg_latency = (
                round(self._total_latency_ms / self._total_requests, 2)
                if self._total_requests > 0
                else 0.0
            )

            p50_latency = self._calculate_percentile(self._recent_latency_samples, 50)
            p95_latency = self._calculate_percentile(self._recent_latency_samples, 95)
            p99_latency = self._calculate_percentile(self._recent_latency_samples, 99)

            p50_ttft = self._calculate_percentile(self._recent_ttft_samples, 50)
            p95_ttft = self._calculate_percentile(self._recent_ttft_samples, 95)

            now = time.time()
            active_keys = 0
            cooldown_keys = 0
            key_health_summary = {}

            for k, stat in self._key_stats.items():
                in_cool = stat.get("cooldown_until", 0) > now
                if in_cool:
                    cooldown_keys += 1
                else:
                    active_keys += 1
                key_health_summary[k] = {
                    "provider": stat["provider"],
                    "success": stat["success"],
                    "rate_limited": stat["rate_limited"],
                    "failures": stat["failures"],
                    "in_cooldown": in_cool,
                    "cooldown_remaining_sec": max(0, int(stat.get("cooldown_until", 0) - now)) if in_cool else 0
                }

            return {
                "total_requests": self._total_requests,
                "total_tokens": {
                    "prompt": self._total_prompt_tokens,
                    "completion": self._total_completion_tokens,
                    "total": self._total_prompt_tokens + self._total_completion_tokens
                },
                "latency_ms": {
                    "average": avg_latency,
                    "p50": p50_latency,
                    "p95": p95_latency,
                    "p99": p99_latency
                },
                "ttft_ms": {
                    "p50": p50_ttft,
                    "p95": p95_ttft
                },
                "requests_by_provider": dict(self._requests_by_provider),
                "requests_by_model": dict(self._requests_by_model),
                "requests_by_purpose": dict(self._requests_by_purpose),
                "errors_by_status": dict(self._errors_by_status),
                "keys": {
                    "total_tracked": len(self._key_stats),
                    "active": active_keys,
                    "in_cooldown": cooldown_keys,
                    "details": key_health_summary
                },
                "tenants_count": len(self._tenant_usage),
                "tenant_usage": dict(self._tenant_usage)
            }

    def reset(self) -> None:
        """Reset all metrics (primarily for test suite isolation)."""
        with self._lock:
            self._total_requests = 0
            self._total_prompt_tokens = 0
            self._total_completion_tokens = 0
            self._total_latency_ms = 0.0
            self._requests_by_provider.clear()
            self._requests_by_model.clear()
            self._requests_by_purpose.clear()
            self._errors_by_status.clear()
            self._key_stats.clear()
            self._tenant_usage.clear()
            self._recent_latency_samples.clear()
            self._recent_ttft_samples.clear()


# Global singleton instance
llm_metrics = LLMMetrics()
