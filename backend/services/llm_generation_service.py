"""
Universal LLM direct generation service supporting text-only and multimodal (vision) generation,
unified under the non-blocking async LLMGateway.

Features:
- Multi-key harvesting: comma-separated GEMINI_API_KEY(s), GEMINI_API_KEY_1..15, GROQ_API_KEY(s)
- Automatic rate-limit (429/403) token exhaustion detection & instant failover to next key
- Proactive key cooldown tracker to bypass exhausted keys on subsequent calls
- Non-blocking async generate() and native SSE generate_stream() via httpx.AsyncClient
- Observability datastore integration via LLMMetrics
- Direct Google Gemini REST API -> Groq API failover chain
- Thread-safe Round-Robin key rotation across requests to distribute quota
"""
import os
import json
import httpx
import time
import random
import asyncio
import threading
import logging
from typing import List, Optional, Any, Dict, AsyncGenerator
from dotenv import load_dotenv

from services.llm_metrics import llm_metrics

# Ensure .env is always loaded from backend or root directory
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_env_backend = os.path.join(_backend_dir, ".env")
_env_root = os.path.join(os.path.dirname(_backend_dir), ".env")
if os.path.exists(_env_backend):
    load_dotenv(_env_backend)
if os.path.exists(_env_root):
    load_dotenv(_env_root)
load_dotenv()

logger = logging.getLogger("dataspeak.llm_generation")


class LLMFailure(RuntimeError):
    """A safe, categorized LLM failure; provider details stay internal."""

    def __init__(self, category: str, *, retryable: bool = False):
        if category not in {"Timeout", "Quota", "ProviderError", "InvalidResponse"}:
            raise ValueError("Unsupported LLM failure category")
        self.category = category
        self.retryable = retryable
        super().__init__(category)


def _configured_seconds(name: str, default: float, *, allow_zero: bool = False) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = float(raw)
        if not (value >= 0 if allow_zero else value > 0) or not value < float("inf"):
            raise ValueError
        return value
    except ValueError:
        logger.warning("Invalid LLM setting %s; using default", name)
        return default


def _classify_failure(error: Exception) -> LLMFailure:
    if isinstance(error, LLMFailure):
        return error
    if isinstance(error, json.JSONDecodeError):
        return LLMFailure("InvalidResponse")
    if isinstance(error, (httpx.TimeoutException, TimeoutError, asyncio.TimeoutError)):
        return LLMFailure("Timeout", retryable=True)
    if isinstance(error, httpx.TransportError):
        return LLMFailure("ProviderError", retryable=True)
    return LLMFailure("ProviderError")


def _remaining(deadline: Optional[float], default: float) -> float:
    if deadline is None:
        return default
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise LLMFailure("Timeout", retryable=True)
    return min(default, remaining)


def _provider_text(response: httpx.Response, provider: str) -> str:
    try:
        data = response.json()
        if provider == "gemini":
            value = data["candidates"][0]["content"]["parts"][0]["text"]
        else:
            value = data["choices"][0]["message"]["content"]
        if not isinstance(value, str) or not value.strip():
            raise ValueError
        return value
    except (ValueError, TypeError, KeyError, IndexError):
        raise LLMFailure("InvalidResponse") from None

# ── Key Harvesting & Extraction ───────────────────────────────────────────────

def _extract_keys(val: Optional[str]) -> List[str]:
    """Split comma, semicolon, or newline-separated API keys."""
    if not val:
        return []
    res = []
    cleaned = val.replace(";", ",").replace("\n", ",")
    for part in cleaned.split(","):
        p = part.strip()
        if p and p not in res:
            res.append(p)
    return res


def _get_all_gemini_keys() -> List[str]:
    keys = []
    # Check plural and singular environment variables
    for var in ["GEMINI_API_KEYS", "GOOGLE_API_KEYS", "GEMINI_API_KEY", "GOOGLE_API_KEY"]:
        for k in _extract_keys(os.getenv(var)):
            if k not in keys:
                keys.append(k)
    # Check indexed variables (GEMINI_API_KEY_1..15)
    for i in range(1, 16):
        for var in [f"GEMINI_API_KEY_{i}", f"GOOGLE_API_KEY_{i}"]:
            for k in _extract_keys(os.getenv(var)):
                if k not in keys:
                    keys.append(k)
    return keys


def _get_all_groq_keys() -> List[str]:
    keys = []
    for var in ["GROQ_API_KEYS", "GROQ_API_KEY"]:
        for k in _extract_keys(os.getenv(var)):
            if k not in keys:
                keys.append(k)
    for i in range(1, 16):
        for k in _extract_keys(os.getenv(f"GROQ_API_KEY_{i}")):
            if k not in keys:
                keys.append(k)
    return keys


# ── Token Depletion & Quota Cooldown Tracker ─────────────────────────────────

_gemini_counter = 0
_groq_counter = 0
_counter_lock = threading.Lock()
# Maps key -> timestamp until which it is throttled / exhausted
_key_cooldowns: Dict[str, float] = {}


def _rotate_keys(keys: List[str], provider_type: str) -> List[str]:
    """Rotate keys list so that subsequent requests start from the next key (Round-Robin)."""
    global _gemini_counter, _groq_counter
    if len(keys) <= 1 or provider_type == "explicit":
        return keys
    with _counter_lock:
        if provider_type == "gemini":
            start_idx = _gemini_counter % len(keys)
            _gemini_counter += 1
        else:
            start_idx = _groq_counter % len(keys)
            _groq_counter += 1
    return keys[start_idx:] + keys[:start_idx]


def _get_active_ordered_keys(keys: List[str], provider_type: str) -> List[str]:
    """
    Returns keys prioritized by health status:
    1. Active keys (not on cooldown), rotated round-robin.
    2. Depleted/cooldown keys placed at the very end as an emergency last resort.
    """
    now = time.time()
    active = [k for k in keys if _key_cooldowns.get(k, 0) < now]
    cooling = [k for k in keys if _key_cooldowns.get(k, 0) >= now]

    rotated_active = _rotate_keys(active, provider_type) if active else []
    return rotated_active + cooling


def _mask_key(key: str) -> str:
    return f"...{key[-4:]}" if len(key) >= 4 else "key"


# ── Active Model Configurations ──────────────────────────────────────────────

GEMINI_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
]

GROQ_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
]

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


# ── Unified Non-Blocking Async LLMGateway ────────────────────────────────────

class LLMGateway:
    """
    Unified Non-Blocking Async LLM Gateway with Multi-Key Harvesting,
    Round-Robin Quota Rotation, Instant 429/403 Failover, and Native SSE Streaming.
    """

    def __init__(self, request_timeout: float = 45.0):
        self.request_timeout = request_timeout

    def _get_gemini_candidates(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        user: Optional[Any] = None
    ) -> tuple[List[str], List[str]]:
        explicit_keys = []
        if api_key:
            explicit_keys.extend(_extract_keys(api_key))
        if user and getattr(user, "gemini_api_key", None):
            explicit_keys.extend(_extract_keys(user.gemini_api_key))

        if explicit_keys:
            ordered_keys = _get_active_ordered_keys(list(dict.fromkeys(explicit_keys)), "explicit")
        else:
            harvested = list(dict.fromkeys(_get_all_gemini_keys()))
            ordered_keys = _get_active_ordered_keys(harvested, "gemini")

        env_model = os.getenv("GEMINI_MODEL")
        base_models = list(GEMINI_MODELS)
        if env_model and env_model not in base_models:
            base_models = [env_model] + base_models
        elif env_model:
            base_models = [env_model] + [m for m in base_models if m != env_model]

        models_to_try = [model] + [m for m in base_models if m != model] if model else base_models
        return ordered_keys, models_to_try

    def _get_groq_candidates(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        user: Optional[Any] = None
    ) -> tuple[List[str], List[str]]:
        explicit_keys = []
        if api_key:
            explicit_keys.extend(_extract_keys(api_key))
        if user and getattr(user, "groq_api_key", None):
            explicit_keys.extend(_extract_keys(user.groq_api_key))

        if explicit_keys:
            ordered_keys = _get_active_ordered_keys(list(dict.fromkeys(explicit_keys)), "explicit")
        else:
            harvested = list(dict.fromkeys(_get_all_groq_keys()))
            ordered_keys = _get_active_ordered_keys(harvested, "groq")

        env_model = os.getenv("GROQ_MODEL")
        base_models = list(GROQ_MODELS)
        if env_model and env_model not in base_models:
            base_models = [env_model] + base_models
        elif env_model:
            base_models = [env_model] + [m for m in base_models if m != env_model]

        models_to_try = [model] + [m for m in base_models if m != model] if model else base_models
        return ordered_keys, models_to_try

    async def generate(
        self,
        prompt: str,
        provider: str = "auto",
        model: Optional[str] = None,
        temperature: float = 0.2,
        api_key: Optional[str] = None,
        user: Optional[Any] = None,
        tenant_id: Optional[int] = None,
        purpose: str = "general",
        deadline: Optional[float] = None,
    ) -> str:
        """
        Non-blocking async text generation with multi-key rotation and Groq failover.
        """
        start_time = time.time()
        prompt_tokens_est = max(1, len(prompt) // 4)
        last_err: Optional[LLMFailure] = None

        prov = (provider or "auto").lower()
        try_gemini_first = prov in ("gemini", "auto")

        # ── Step 1: Attempt Gemini Candidates ─────────────────────────────────
        if try_gemini_first:
            gemini_keys, gemini_models = self._get_gemini_candidates(model, api_key, user)
            has_active_gemini = any(_key_cooldowns.get(k, 0) <= time.time() for k in gemini_keys)
            async with httpx.AsyncClient(timeout=self.request_timeout) as client:
                for key in gemini_keys:
                    masked = _mask_key(key)
                    now = time.time()
                    if has_active_gemini and _key_cooldowns.get(key, 0) > now:
                        continue

                    for m in gemini_models:
                        request_timeout = _remaining(deadline, self.request_timeout)
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={key}"
                        payload = {
                            "contents": [{"parts": [{"text": prompt}]}],
                            "generationConfig": {"temperature": temperature},
                        }
                        try:
                            resp = await client.post(url, json=payload, timeout=request_timeout)
                            latency_ms = (time.time() - start_time) * 1000

                            if resp.status_code == 200:
                                _key_cooldowns.pop(key, None)
                                text_out = _provider_text(resp, "gemini")

                                comp_tokens_est = max(1, len(text_out) // 4)
                                llm_metrics.record_request(
                                    provider="gemini",
                                    model=m,
                                    tenant_id=tenant_id,
                                    purpose=purpose,
                                    prompt_tokens=prompt_tokens_est,
                                    completion_tokens=comp_tokens_est,
                                    latency_ms=latency_ms,
                                    status_code=200,
                                    masked_key=masked
                                )
                                return text_out

                            elif resp.status_code in {429, 403}:
                                _key_cooldowns[key] = time.time() + 60.0
                                llm_metrics.record_key_cooldown(masked, "gemini", 60.0)
                                llm_metrics.record_request(
                                    provider="gemini",
                                    model=m,
                                    tenant_id=tenant_id,
                                    purpose=purpose,
                                    status_code=resp.status_code,
                                    error="Quota / Rate limit exhausted",
                                    masked_key=masked
                                )
                                logger.warning("provider=gemini category=Quota duration_ms=%d", int(latency_ms))
                                last_err = LLMFailure("Quota")
                                break  # Break model loop to switch key immediately

                            elif resp.status_code in RETRYABLE_STATUS_CODES or resp.status_code == 404:
                                llm_metrics.record_request(
                                    provider="gemini",
                                    model=m,
                                    tenant_id=tenant_id,
                                    purpose=purpose,
                                    status_code=resp.status_code,
                                    error=f"Server status {resp.status_code}",
                                    masked_key=masked
                                )
                                last_err = LLMFailure("ProviderError", retryable=resp.status_code >= 500)
                                logger.warning("provider=gemini category=%s duration_ms=%d", last_err.category, int(latency_ms))
                                continue

                            else:
                                last_err = LLMFailure("ProviderError")
                                break

                        except Exception as ex:
                            last_err = _classify_failure(ex)
                            logger.warning("provider=gemini category=%s duration_ms=%d", last_err.category, int((time.time() - start_time) * 1000))
                            if last_err.category == "InvalidResponse":
                                break
                            continue

        # ── Step 2: Attempt Groq Candidates (Failover) ────────────────────────
        groq_keys, groq_models = self._get_groq_candidates(model, api_key, user)
        if groq_keys:
            has_active_groq = any(_key_cooldowns.get(k, 0) <= time.time() for k in groq_keys)
            async with httpx.AsyncClient(timeout=self.request_timeout) as client:
                for key in groq_keys:
                    masked = _mask_key(key)
                    now = time.time()
                    if has_active_groq and _key_cooldowns.get(key, 0) > now:
                        continue

                    for m in groq_models:
                        request_timeout = _remaining(deadline, self.request_timeout)
                        url = "https://api.groq.com/openai/v1/chat/completions"
                        payload = {
                            "model": m,
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": temperature,
                        }
                        headers = {
                            "Authorization": f"Bearer {key}",
                            "Content-Type": "application/json",
                        }
                        try:
                            resp = await client.post(url, json=payload, headers=headers, timeout=request_timeout)
                            latency_ms = (time.time() - start_time) * 1000

                            if resp.status_code == 200:
                                _key_cooldowns.pop(key, None)
                                text_out = _provider_text(resp, "groq")

                                comp_tokens_est = max(1, len(text_out) // 4)
                                llm_metrics.record_request(
                                    provider="groq",
                                    model=m,
                                    tenant_id=tenant_id,
                                    purpose=purpose,
                                    prompt_tokens=prompt_tokens_est,
                                    completion_tokens=comp_tokens_est,
                                    latency_ms=latency_ms,
                                    status_code=200,
                                    masked_key=masked
                                )
                                return text_out

                            elif resp.status_code in {429, 403}:
                                _key_cooldowns[key] = time.time() + 60.0
                                llm_metrics.record_key_cooldown(masked, "groq", 60.0)
                                llm_metrics.record_request(
                                    provider="groq",
                                    model=m,
                                    tenant_id=tenant_id,
                                    purpose=purpose,
                                    status_code=resp.status_code,
                                    error="Groq Rate limit exhausted",
                                    masked_key=masked
                                )
                                logger.warning("provider=groq category=Quota duration_ms=%d", int(latency_ms))
                                last_err = LLMFailure("Quota")
                                break

                            elif resp.status_code in RETRYABLE_STATUS_CODES or resp.status_code == 404:
                                last_err = LLMFailure("ProviderError", retryable=True)
                                continue

                            else:
                                last_err = LLMFailure("ProviderError")
                                break

                        except Exception as ex:
                            last_err = _classify_failure(ex)
                            logger.warning("provider=groq category=%s duration_ms=%d", last_err.category, int((time.time() - start_time) * 1000))
                            if last_err.category == "InvalidResponse":
                                break
                            continue

        # ── Step 3: Ollama Local Fallback (if running) ─────────────────────────
        try:
            return generate_with_ollama(
                prompt, model or os.getenv("OLLAMA_MODEL", "llama3"), temperature,
                timeout=_remaining(deadline, self.request_timeout),
            )
        except Exception as ex:
            if last_err is None:
                last_err = _classify_failure(ex)

        logger.warning("provider=auto category=%s duration_ms=%d", (last_err or LLMFailure("ProviderError")).category, int((time.time() - start_time) * 1000))
        raise last_err or LLMFailure("ProviderError")

    async def generate_stream(
        self,
        prompt: str,
        provider: str = "auto",
        model: Optional[str] = None,
        temperature: float = 0.2,
        api_key: Optional[str] = None,
        user: Optional[Any] = None,
        tenant_id: Optional[int] = None,
        purpose: str = "chat"
    ) -> AsyncGenerator[str, None]:
        """
        True token-level Server-Sent Events (SSE) streaming generator.
        Consumes provider HTTP streaming lines and yields text token chunks in real-time.
        """
        start_time = time.time()
        ttft_recorded = False
        prompt_tokens_est = max(1, len(prompt) // 4)
        total_text_yielded = []
        last_err: Optional[Exception] = None

        prov = (provider or "auto").lower()
        try_gemini_first = prov in ("gemini", "auto")

        # ── Step 1: Gemini SSE Streaming ──────────────────────────────────────
        if try_gemini_first:
            gemini_keys, gemini_models = self._get_gemini_candidates(model, api_key, user)
            has_active_gemini = any(_key_cooldowns.get(k, 0) <= time.time() for k in gemini_keys)
            async with httpx.AsyncClient(timeout=self.request_timeout) as client:
                for key in gemini_keys:
                    masked = _mask_key(key)
                    now = time.time()
                    if has_active_gemini and _key_cooldowns.get(key, 0) > now:
                        continue

                    for m in gemini_models:
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:streamGenerateContent?alt=sse&key={key}"
                        payload = {
                            "contents": [{"parts": [{"text": prompt}]}],
                            "generationConfig": {"temperature": temperature},
                        }
                        try:
                            async with client.stream("POST", url, json=payload) as resp:
                                if resp.status_code == 200:
                                    _key_cooldowns.pop(key, None)
                                    async for line in resp.aiter_lines():
                                        if not line or not line.startswith("data:"):
                                            continue
                                        raw_json = line[len("data:"):].strip()
                                        if not raw_json or raw_json == "[DONE]":
                                            continue

                                        try:
                                            chunk_data = json.loads(raw_json)
                                            cands = chunk_data.get("candidates", [])
                                            if cands and "content" in cands[0]:
                                                parts = cands[0]["content"].get("parts", [])
                                                if parts and "text" in parts[0]:
                                                    token = parts[0]["text"]
                                                    if token:
                                                        if not ttft_recorded:
                                                            ttft_ms = (time.time() - start_time) * 1000
                                                            llm_metrics.record_request(
                                                                provider="gemini",
                                                                model=m,
                                                                tenant_id=tenant_id,
                                                                purpose=purpose,
                                                                prompt_tokens=prompt_tokens_est,
                                                                latency_ms=ttft_ms,
                                                                ttft_ms=ttft_ms,
                                                                masked_key=masked
                                                            )
                                                            ttft_recorded = True
                                                        total_text_yielded.append(token)
                                                        yield token
                                        except json.JSONDecodeError:
                                            continue

                                    # Stream completed successfully
                                    total_latency = (time.time() - start_time) * 1000
                                    full_text = "".join(total_text_yielded)
                                    llm_metrics.record_request(
                                        provider="gemini",
                                        model=m,
                                        tenant_id=tenant_id,
                                        purpose=purpose,
                                        prompt_tokens=prompt_tokens_est,
                                        completion_tokens=max(1, len(full_text) // 4),
                                        latency_ms=total_latency,
                                        status_code=200,
                                        masked_key=masked
                                    )
                                    return

                                elif resp.status_code in {429, 403}:
                                    _key_cooldowns[key] = time.time() + 60.0
                                    llm_metrics.record_key_cooldown(masked, "gemini", 60.0)
                                    logger.warning("provider=gemini category=Quota duration_ms=%d", int((time.time() - start_time) * 1000))
                                    last_err = RuntimeError(f"Gemini key {masked} throttled ({resp.status_code})")
                                    break

                                else:
                                    last_err = RuntimeError(f"Gemini stream returned {resp.status_code}")
                                    continue

                        except Exception as ex:
                            last_err = ex
                            logger.warning("provider=gemini category=%s duration_ms=%d", _classify_failure(ex).category, int((time.time() - start_time) * 1000))
                            continue

        # ── Step 2: Groq SSE Streaming (Failover) ──────────────────────────────
        groq_keys, groq_models = self._get_groq_candidates(model, api_key, user)
        if groq_keys:
            has_active_groq = any(_key_cooldowns.get(k, 0) <= time.time() for k in groq_keys)
            async with httpx.AsyncClient(timeout=self.request_timeout) as client:
                for key in groq_keys:
                    masked = _mask_key(key)
                    now = time.time()
                    if has_active_groq and _key_cooldowns.get(key, 0) > now:
                        continue

                    for m in groq_models:
                        url = "https://api.groq.com/openai/v1/chat/completions"
                        payload = {
                            "model": m,
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": temperature,
                            "stream": True,
                        }
                        headers = {
                            "Authorization": f"Bearer {key}",
                            "Content-Type": "application/json",
                        }
                        try:
                            async with client.stream("POST", url, json=payload, headers=headers) as resp:
                                if resp.status_code == 200:
                                    _key_cooldowns.pop(key, None)
                                    async for line in resp.aiter_lines():
                                        if not line or not line.startswith("data:"):
                                            continue
                                        raw_json = line[len("data:"):].strip()
                                        if not raw_json or raw_json == "[DONE]":
                                            continue

                                        try:
                                            chunk_data = json.loads(raw_json)
                                            choices = chunk_data.get("choices", [])
                                            if choices and "delta" in choices[0]:
                                                token = choices[0]["delta"].get("content", "")
                                                if token:
                                                    if not ttft_recorded:
                                                        ttft_ms = (time.time() - start_time) * 1000
                                                        llm_metrics.record_request(
                                                            provider="groq",
                                                            model=m,
                                                            tenant_id=tenant_id,
                                                            purpose=purpose,
                                                            prompt_tokens=prompt_tokens_est,
                                                            latency_ms=ttft_ms,
                                                            ttft_ms=ttft_ms,
                                                            masked_key=masked
                                                        )
                                                        ttft_recorded = True
                                                    total_text_yielded.append(token)
                                                    yield token
                                        except json.JSONDecodeError:
                                            continue

                                    # Stream completed successfully
                                    total_latency = (time.time() - start_time) * 1000
                                    full_text = "".join(total_text_yielded)
                                    llm_metrics.record_request(
                                        provider="groq",
                                        model=m,
                                        tenant_id=tenant_id,
                                        purpose=purpose,
                                        prompt_tokens=prompt_tokens_est,
                                        completion_tokens=max(1, len(full_text) // 4),
                                        latency_ms=total_latency,
                                        status_code=200,
                                        masked_key=masked
                                    )
                                    return

                                elif resp.status_code in {429, 403}:
                                    _key_cooldowns[key] = time.time() + 60.0
                                    llm_metrics.record_key_cooldown(masked, "groq", 60.0)
                                    logger.warning("provider=groq category=Quota duration_ms=%d", int((time.time() - start_time) * 1000))
                                    last_err = RuntimeError(f"Groq key {masked} throttled ({resp.status_code})")
                                    break

                                else:
                                    last_err = RuntimeError(f"Groq stream returned {resp.status_code}")
                                    continue

                        except Exception as ex:
                            last_err = ex
                            logger.warning("provider=groq category=%s duration_ms=%d", _classify_failure(ex).category, int((time.time() - start_time) * 1000))
                            continue

        failure = _classify_failure(last_err) if last_err else LLMFailure("ProviderError")
        logger.error("provider=auto category=%s duration_ms=%d", failure.category, int((time.time() - start_time) * 1000))
        raise failure

    def generate_sync(
        self,
        prompt: str,
        provider: str = "auto",
        model: Optional[str] = None,
        temperature: float = 0.2,
        api_key: Optional[str] = None,
        user: Optional[Any] = None,
        tenant_id: Optional[int] = None,
        purpose: str = "general",
        deadline: Optional[float] = None,
    ) -> str:
        """
        Synchronous bridge for existing synchronous services.
        Uses a separate background thread event loop if a loop is already running.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            try:
                future = pool.submit(
                    asyncio.run,
                    self.generate(
                        prompt=prompt,
                        provider=provider,
                        model=model,
                        temperature=temperature,
                        api_key=api_key,
                        user=user,
                        tenant_id=tenant_id,
                        purpose=purpose,
                        deadline=deadline,
                    )
                )
                return future.result(timeout=_remaining(deadline, self.request_timeout))
            finally:
                pool.shutdown(wait=False, cancel_futures=True)
        else:
            return asyncio.run(
                self.generate(
                    prompt=prompt,
                    provider=provider,
                    model=model,
                    temperature=temperature,
                    api_key=api_key,
                    user=user,
                    tenant_id=tenant_id,
                    purpose=purpose,
                    deadline=deadline,
                )
            )


# Singleton LLMGateway instance
llm_gateway = LLMGateway()


# ── Backward Compatibility Bridge Exports ────────────────────────────────────

def generate_with_gemini(
    prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.2,
    api_key: Optional[str] = None,
    user: Optional[Any] = None,
) -> str:
    """Synchronous Gemini generation bridge through LLMGateway."""
    return llm_gateway.generate_sync(
        prompt=prompt,
        provider="gemini",
        model=model,
        temperature=temperature,
        api_key=api_key,
        user=user
    )


def generate_with_groq(
    prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.2,
    api_key: Optional[str] = None,
    user: Optional[Any] = None,
) -> str:
    """Synchronous Groq generation bridge through LLMGateway."""
    return llm_gateway.generate_sync(
        prompt=prompt,
        provider="groq",
        model=model,
        temperature=temperature,
        api_key=api_key,
        user=user
    )


def generate_with_ollama(
    prompt: str,
    model: str = "llama3",
    temperature: float = 0.2,
    timeout: float = 60.0,
) -> str:
    """Local Ollama endpoint fallback."""
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    url = f"{ollama_host}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    response = httpx.post(url, json=payload, timeout=timeout)
    response.raise_for_status()
    return response.json().get("response", "")


def generate_multimodal_with_gemini(
    prompt: str,
    image_b64_list: Optional[List[str]] = None,
    model: Optional[str] = None,
    temperature: float = 0.2,
    api_key: Optional[str] = None,
    user: Optional[Any] = None,
    deadline: Optional[float] = None,
) -> str:
    """Send text + Base64 PNG images to Gemini with multi-key failover."""
    active_model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    keys = []
    if api_key:
        keys.extend(_extract_keys(api_key))
    if user and getattr(user, "gemini_api_key", None):
        keys.extend(_extract_keys(user.gemini_api_key))
    keys.extend(_get_all_gemini_keys())
    keys = list(dict.fromkeys(k for k in keys if k))

    if not keys:
        raise RuntimeError("No Gemini API keys available for multimodal generation")

    ordered_keys = _get_active_ordered_keys(keys, "gemini")

    parts = [{"text": prompt}]
    for b64 in (image_b64_list or []):
        parts.append({
            "inline_data": {
                "mime_type": "image/png",
                "data": b64,
            }
        })

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {"temperature": temperature},
    }

    last_err = None
    for key in ordered_keys:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{active_model}:generateContent?key={key}"
        )
        try:
            resp = httpx.post(url, json=payload, timeout=_remaining(deadline, 120.0))
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates and "content" in candidates[0]:
                    p = candidates[0]["content"].get("parts", [])
                    if p:
                        return p[0].get("text", "")
                return ""
            elif resp.status_code in {429, 403}:
                _key_cooldowns[key] = time.time() + 60.0
                last_err = RuntimeError(f"Gemini multimodal rate-limited ({resp.status_code})")
                continue
            elif resp.status_code in RETRYABLE_STATUS_CODES:
                last_err = RuntimeError(f"Gemini multimodal {resp.status_code}")
                continue
            else:
                resp.raise_for_status()
        except Exception as e:
            last_err = e
            logger.warning("provider=gemini category=%s duration_ms=0", _classify_failure(e).category)
            continue

    raise last_err or RuntimeError("All Gemini keys failed for multimodal")


def generate(
    prompt: str,
    provider: str = "auto",
    model: Optional[str] = None,
    temperature: float = 0.2,
    image_b64_list: Optional[List[str]] = None,
    api_key: Optional[str] = None,
    user: Optional[Any] = None,
    raise_on_failure: bool = False,
    deadline: Optional[float] = None,
) -> str:
    """
    Main synchronous generation facade.
    Dispatches multimodal requests or text requests through LLMGateway.
    """
    if deadline is None:
        deadline = time.monotonic() + _configured_seconds("LLM_HTTP_TIMEOUT_SECONDS", 20.0)
    backoff = _configured_seconds("LLM_RETRY_BACKOFF_SECONDS", 1.0, allow_zero=True)
    if image_b64_list:
        try:
            return generate_multimodal_with_gemini(
                prompt,
                image_b64_list=image_b64_list,
                model=model,
                temperature=temperature,
                api_key=api_key,
                user=user,
                deadline=deadline,
            )
        except Exception as error:
            logger.warning("provider=gemini category=%s duration_ms=0", _classify_failure(error).category)

    for attempt in range(2):
        started = time.monotonic()
        try:
            _remaining(deadline, 20.0)
            return llm_gateway.generate_sync(
                prompt=prompt, provider=provider, model=model,
                temperature=temperature, api_key=api_key, user=user,
                deadline=deadline,
            )
        except Exception as error:
            failure = _classify_failure(error)
            safe_provider = provider if provider in {"auto", "gemini", "groq", "ollama"} else "unknown"
            logger.warning(
                "provider=%s category=%s duration_ms=%d",
                safe_provider, failure.category, int((time.monotonic() - started) * 1000),
            )
            if attempt == 0 and failure.retryable:
                remaining = deadline - time.monotonic()
                if remaining > backoff:
                    time.sleep(backoff)
                    continue
            if raise_on_failure:
                raise failure from None
            return "Sorry, all AI providers are currently unavailable. Please try again in a moment."
