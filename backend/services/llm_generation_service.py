"""
Universal LLM direct generation service supporting text-only and multimodal (vision) generation.
Features:
- Multi-key harvesting: comma-separated GEMINI_API_KEY(s), GEMINI_API_KEY_1..9, GROQ_API_KEY(s)
- Automatic rate-limit (429/403) token exhaustion detection & instant failover to next key
- Proactive key cooldown tracker to bypass exhausted keys on subsequent calls
- Direct Google Gemini REST API -> Groq API failover chain (DeepSeek removed per user preference)
- Thread-safe Round-Robin key rotation across requests to distribute quota
"""
import os
import httpx
import time
import random
import threading
import logging
from typing import List, Optional, Any, Dict
from dotenv import load_dotenv

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
    for i in range(1, 15):
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
    for i in range(1, 15):
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
    if len(keys) <= 1:
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


# ── Active Model Configurations ──────────────────────────────────────────────

GEMINI_MODELS = [
    "gemini-flash-lite-latest",
    "gemma-4-26b-a4b-it",
    "gemini-3.8-flash",
    "gemini-flash-latest",
]

GROQ_MODELS = [
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
]

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


# ── Provider Implementations ──────────────────────────────────────────────────

def generate_with_gemini(
    prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.2,
    api_key: Optional[str] = None,
    user: Optional[Any] = None,
) -> str:
    """
    Generate using Google Gemini API.
    If a key hits token limit or quota (429/403), instantly shifts to the next key.
    """
    keys = []
    if api_key:
        keys.extend(_extract_keys(api_key))
    if user and getattr(user, "gemini_api_key", None):
        keys.extend(_extract_keys(user.gemini_api_key))
    keys.extend(_get_all_gemini_keys())
    keys = list(dict.fromkeys(k for k in keys if k))

    if not keys:
        raise RuntimeError("No Gemini API keys available")

    # Order keys so fresh keys are tried first, then rotated
    ordered_keys = _get_active_ordered_keys(keys, "gemini")
    models_to_try = [model] + GEMINI_MODELS if model else GEMINI_MODELS

    last_err = None
    for key in ordered_keys:
        masked_key = f"...{key[-4:]}" if len(key) >= 4 else "key"
        
        # Check if key was previously exhausted and we still have healthy keys left
        now = time.time()
        if _key_cooldowns.get(key, 0) > now and len(ordered_keys) > 1:
            continue

        for m in models_to_try:
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{m}:generateContent?key={key}"
            )
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": temperature},
            }
            try:
                resp = httpx.post(url, json=payload, timeout=60.0)
                if resp.status_code == 200:
                    # Clear cooldown on successful response
                    _key_cooldowns.pop(key, None)
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts:
                            return parts[0].get("text", "")
                    return ""
                
                # Quota or Token Exhaustion (429 / 403) -> IMMEDIATELY SHIFT TO NEXT KEY
                elif resp.status_code in {429, 403}:
                    _key_cooldowns[key] = time.time() + 60.0  # Cooldown this key for 60s
                    logger.warning(
                        f"[Gemini Quota] Key {masked_key} quota/tokens exhausted (status {resp.status_code}). "
                        f"Instantly shifting to next available key..."
                    )
                    last_err = RuntimeError(f"Gemini key {masked_key} rate-limited/depleted ({resp.status_code})")
                    break  # Break out of models loop to immediately switch to the next key!

                # Temporary Server Issues (503 / 500 / 502) -> Try next model or next key
                elif resp.status_code in RETRYABLE_STATUS_CODES:
                    logger.warning(f"[Gemini] {m} (key {masked_key}) status {resp.status_code}, trying next model...")
                    last_err = RuntimeError(f"Gemini {m} returned {resp.status_code}")
                    continue

                # Model Not Found (404) -> Try next model
                elif resp.status_code == 404:
                    logger.warning(f"[Gemini] {m} (key {masked_key}) returned 404, trying next model...")
                    last_err = RuntimeError(f"Gemini {m} returned 404")
                    continue

                else:
                    logger.warning(f"[Gemini] {m} (key {masked_key}) non-retryable error {resp.status_code}")
                    last_err = RuntimeError(f"Gemini {m} returned {resp.status_code}")
                    break

            except Exception as e:
                last_err = e
                logger.warning(f"[Gemini Exception] {m} with key {masked_key}: {e}")
                continue

    raise last_err or RuntimeError("All Gemini keys and models exhausted")


def generate_with_groq(
    prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.2,
    api_key: Optional[str] = None,
    user: Optional[Any] = None,
) -> str:
    """
    Generate using Groq Cloud API.
    If a key hits token limit or quota (429), instantly shifts to the next key.
    """
    keys = []
    if api_key:
        keys.extend(_extract_keys(api_key))
    if user and getattr(user, "groq_api_key", None):
        keys.extend(_extract_keys(user.groq_api_key))
    keys.extend(_get_all_groq_keys())
    keys = list(dict.fromkeys(k for k in keys if k))

    if not keys:
        raise RuntimeError("No Groq API keys available")

    ordered_keys = _get_active_ordered_keys(keys, "groq")
    models_to_try = [model] + GROQ_MODELS if model else GROQ_MODELS
    url = "https://api.groq.com/openai/v1/chat/completions"

    last_err = None
    for key in ordered_keys:
        masked_key = f"...{key[-4:]}" if len(key) >= 4 else "key"

        now = time.time()
        if _key_cooldowns.get(key, 0) > now and len(ordered_keys) > 1:
            continue

        for m in models_to_try:
            try:
                headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
                payload = {
                    "model": m,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "max_tokens": 4096,
                }
                resp = httpx.post(url, headers=headers, json=payload, timeout=60.0)
                if resp.status_code == 200:
                    _key_cooldowns.pop(key, None)
                    return resp.json()["choices"][0]["message"]["content"]

                # Quota / Token limit reached (429) -> IMMEDIATELY SHIFT TO NEXT KEY
                elif resp.status_code == 429:
                    _key_cooldowns[key] = time.time() + 60.0
                    logger.warning(
                        f"[Groq Quota] Key {masked_key} rate-limited/tokens exhausted (429). "
                        f"Instantly shifting to next available key..."
                    )
                    last_err = RuntimeError(f"Groq key {masked_key} rate-limited (429)")
                    break  # Break out of models loop to immediately try next key!

                elif resp.status_code in RETRYABLE_STATUS_CODES:
                    logger.warning(f"[Groq] {m} (key {masked_key}) status {resp.status_code}, trying next model...")
                    last_err = RuntimeError(f"Groq {m} returned {resp.status_code}")
                    continue

                elif resp.status_code == 404:
                    logger.warning(f"[Groq] {m} (key {masked_key}) model not found (404), trying next model...")
                    last_err = RuntimeError(f"Groq {m} returned 404")
                    continue

                else:
                    logger.warning(f"[Groq] {m} (key {masked_key}) non-retryable error {resp.status_code}")
                    last_err = RuntimeError(f"Groq {m} returned {resp.status_code}")
                    break

            except Exception as e:
                last_err = e
                logger.warning(f"[Groq Exception] {m} with key {masked_key}: {e}")
                continue

    raise last_err or RuntimeError("All Groq keys and models exhausted")


def generate_with_ollama(
    prompt: str,
    model: str = "llama3",
    temperature: float = 0.2,
) -> str:
    """Local Ollama endpoint fallback (active only if local Ollama daemon is running)."""
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    url = f"{ollama_host}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    response = httpx.post(url, json=payload, timeout=120.0)
    response.raise_for_status()
    return response.json().get("response", "")


# ── Multimodal Generation (Text + Vision) ────────────────────────────────────

def generate_multimodal_with_gemini(
    prompt: str,
    image_b64_list: Optional[List[str]] = None,
    model: str = "gemini-flash-lite-latest",
    temperature: float = 0.2,
    api_key: Optional[str] = None,
    user: Optional[Any] = None,
) -> str:
    """Send text + Base64 PNG images to Gemini with multi-key failover."""
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
            f"{model}:generateContent?key={key}"
        )
        try:
            resp = httpx.post(url, json=payload, timeout=120.0)
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
            logger.warning(f"[Gemini Multimodal] key failover: {e}")
            continue

    raise last_err or RuntimeError("All Gemini keys failed for multimodal")


# ── Unified generate() Entry Point ───────────────────────────────────────────

def generate(
    prompt: str,
    provider: str = "gemini",
    model: Optional[str] = None,
    temperature: float = 0.2,
    image_b64_list: Optional[List[str]] = None,
    api_key: Optional[str] = None,
    user: Optional[Any] = None,
) -> str:
    """
    Generate a response with automatic provider failover.
    Default fallback sequence:
      Gemini (all keys + models) → Groq (all keys + models) → graceful text fallback
      (DeepSeek is excluded per user configuration).
    """
    provider = (provider or "gemini").lower()
    if provider == "auto":
        provider = "gemini"

    # Multimodal route
    if image_b64_list:
        try:
            return generate_multimodal_with_gemini(
                prompt,
                image_b64_list=image_b64_list,
                model=model or "gemini-flash-lite-latest",
                temperature=temperature,
                api_key=api_key,
                user=user,
            )
        except Exception as e:
            logger.warning(f"[Multimodal Gemini failed] Falling back to text-only: {e}")

    # Build ordered provider chain (Gemini -> Groq)
    provider_order = _build_provider_order(provider)

    last_err = None
    for p in provider_order:
        try:
            if p == "gemini":
                return generate_with_gemini(prompt, model, temperature, api_key=api_key, user=user)
            elif p == "groq":
                return generate_with_groq(prompt, model, temperature, api_key=api_key, user=user)
            elif p == "ollama":
                return generate_with_ollama(prompt, model or os.getenv("OLLAMA_MODEL", "llama3"), temperature)
        except Exception as e:
            last_err = e
            logger.warning(f"[LLM Failover] Provider '{p}' exhausted ({e}) — shifting to next provider...")
            continue

    logger.error(f"[LLM] All providers failed. Last error: {last_err}")
    return "Sorry, all AI providers are currently unavailable. Please try again in a moment."


def _build_provider_order(requested: str) -> list:
    """Return provider list with requested provider first, followed by safe fallbacks. DeepSeek excluded."""
    all_providers = ["gemini", "groq"]
    if requested in all_providers:
        return [requested] + [p for p in all_providers if p != requested]
    return all_providers
