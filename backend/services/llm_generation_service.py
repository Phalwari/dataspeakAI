"""
Universal LLM direct generation service supporting text-only and multimodal (vision) generation.
Features:
- Multi-key harvesting: GEMINI_API_KEY_1..9, GOOGLE_API_KEY_1..9, GROQ_API_KEY_1..9
- Thread-safe Round-Robin key rotation across requests to distribute quota
- Robust fallback order on 429/503/500:
  Gemini (all keys + models) → Groq (all keys + models) → DeepSeek → Ollama → graceful text
- Direct REST endpoints via HTTPX (bypassing heavy SDK cold starts when needed)
"""
import os
import httpx
import time
import random
import threading
import logging
from typing import List, Optional, Any

logger = logging.getLogger("dataspeak.llm_generation")

# ── Key Helpers & Harvesting ──────────────────────────────────────────────────

def _get_all_gemini_keys() -> List[str]:
    keys = []
    for i in range(1, 10):
        k = os.getenv(f"GEMINI_API_KEY_{i}") or os.getenv(f"GOOGLE_API_KEY_{i}")
        if k and k.strip() and k.strip() not in keys:
            keys.append(k.strip())
    k = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if k and k.strip() and k.strip() not in keys:
        keys.append(k.strip())
    return keys


def _get_all_groq_keys() -> List[str]:
    keys = []
    for i in range(1, 10):
        k = os.getenv(f"GROQ_API_KEY_{i}")
        if k and k.strip() and k.strip() not in keys:
            keys.append(k.strip())
    k = os.getenv("GROQ_API_KEY")
    if k and k.strip() and k.strip() not in keys:
        keys.append(k.strip())
    return keys


def _get_all_deepseek_keys() -> List[str]:
    keys = []
    for i in range(1, 10):
        k = os.getenv(f"DEEPSEEK_API_KEY_{i}")
        if k and k.strip() and k.strip() not in keys:
            keys.append(k.strip())
    k = os.getenv("DEEPSEEK_API_KEY")
    if k and k.strip() and k.strip() not in keys:
        keys.append(k.strip())
    return keys


# ── Round-Robin Key Balancing ─────────────────────────────────────────────────

_gemini_counter = 0
_groq_counter = 0
_counter_lock = threading.Lock()

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


GEMINI_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.8-pro",
]

GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
    "qwen/qwen3.8-27b",
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
    """Try all Gemini keys (round-robin) × all Gemini models until one succeeds."""
    keys = []
    if api_key:
        keys.append(api_key)
    if user and getattr(user, "gemini_api_key", None):
        keys.append(user.gemini_api_key)
    keys.extend(_get_all_gemini_keys())
    keys = list(dict.fromkeys(k for k in keys if k))

    if not keys:
        raise RuntimeError("No Gemini API keys available")

    # Rotate starting key for even quota distribution
    keys = _rotate_keys(keys, "gemini")
    models_to_try = [model] + GEMINI_MODELS if model else GEMINI_MODELS

    last_err = None
    for key in keys:
        masked_key = f"...{key[-4:]}" if len(key) >= 4 else "key"
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
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts:
                            return parts[0].get("text", "")
                    return ""
                elif resp.status_code in RETRYABLE_STATUS_CODES:
                    logger.warning(f"[Gemini] {m} (key {masked_key}) returned status {resp.status_code}, trying next model/key...")
                    last_err = RuntimeError(f"Gemini {m} returned {resp.status_code}")
                    if resp.status_code == 429:
                        time.sleep(random.uniform(0.3, 0.8))
                    continue
                else:
                    logger.warning(f"[Gemini] {m} (key {masked_key}) non-retryable error {resp.status_code}")
                    last_err = RuntimeError(f"Gemini {m} returned {resp.status_code}")
                    break
            except Exception as e:
                last_err = e
                logger.warning(f"[Gemini Exception] {m} with key {masked_key}: {e}")
                continue

    raise last_err or RuntimeError("All Gemini keys/models exhausted")


def generate_with_groq(
    prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.2,
    api_key: Optional[str] = None,
    user: Optional[Any] = None,
) -> str:
    """Try all Groq keys (round-robin) × all Groq models until one succeeds."""
    keys = []
    if api_key:
        keys.append(api_key)
    if user and getattr(user, "groq_api_key", None):
        keys.append(user.groq_api_key)
    keys.extend(_get_all_groq_keys())
    keys = list(dict.fromkeys(k for k in keys if k))

    if not keys:
        raise RuntimeError("No Groq API keys available")

    # Rotate starting key for even quota distribution
    keys = _rotate_keys(keys, "groq")
    models_to_try = [model] + GROQ_MODELS if model else GROQ_MODELS
    url = "https://api.groq.com/openai/v1/chat/completions"

    last_err = None
    for key in keys:
        masked_key = f"...{key[-4:]}" if len(key) >= 4 else "key"
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
                    return resp.json()["choices"][0]["message"]["content"]
                elif resp.status_code in RETRYABLE_STATUS_CODES:
                    logger.warning(f"[Groq] {m} (key {masked_key}) returned {resp.status_code}, trying next model/key...")
                    last_err = RuntimeError(f"Groq {m} returned {resp.status_code}")
                    continue
                else:
                    logger.warning(f"[Groq] {m} (key {masked_key}) non-retryable error {resp.status_code}")
                    last_err = RuntimeError(f"Groq {m} returned {resp.status_code}")
                    break
            except Exception as e:
                last_err = e
                logger.warning(f"[Groq Exception] {m} with key {masked_key}: {e}")
                continue

    raise last_err or RuntimeError("All Groq keys/models exhausted")


def generate_with_deepseek(
    prompt: str,
    model: Optional[str] = "deepseek-chat",
    temperature: float = 0.2,
    api_key: Optional[str] = None,
    user: Optional[Any] = None,
) -> str:
    key = api_key or (getattr(user, "deepseek_api_key", None) if user else None) or os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("No DeepSeek API key available")
    url = "https://api.deepseek.com/chat/completions"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {
        "model": model or "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
    }
    response = httpx.post(url, headers=headers, json=payload, timeout=120.0)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def generate_with_ollama(prompt: str, model: str, temperature: float = 0.2) -> str:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    url = f"{base_url}/api/generate"
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
    model: str = "gemini-3.8-flash",
    temperature: float = 0.2,
    api_key: Optional[str] = None,
    user: Optional[Any] = None,
) -> str:
    """Send text + Base64 PNG images to Gemini with multi-key failover."""
    keys = []
    if api_key:
        keys.append(api_key)
    if user and getattr(user, "gemini_api_key", None):
        keys.append(user.gemini_api_key)
    keys.extend(_get_all_gemini_keys())
    keys = list(dict.fromkeys(k for k in keys if k))

    if not keys:
        raise RuntimeError("GEMINI_API_KEY not set")

    keys = _rotate_keys(keys, "gemini")

    parts: list[dict[str, Any]] = []
    for b64 in (image_b64_list or []):
        parts.append({"inline_data": {"mime_type": "image/png", "data": b64}})
    parts.append({"text": prompt})

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {"temperature": temperature},
    }

    last_err = None
    for key in keys:
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
      Gemini (all keys + models) → Groq (all keys + models) → DeepSeek → Ollama
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
                model=model or "gemini-3.8-flash",
                temperature=temperature,
                api_key=api_key,
                user=user,
            )
        except Exception as e:
            logger.warning(f"[Multimodal Gemini failed] Falling back to text-only: {e}")

    # Build ordered provider chain
    provider_order = _build_provider_order(provider)

    last_err = None
    for p in provider_order:
        try:
            if p == "gemini":
                return generate_with_gemini(prompt, model, temperature, api_key=api_key, user=user)
            elif p == "groq":
                return generate_with_groq(prompt, model, temperature, api_key=api_key, user=user)
            elif p == "deepseek":
                return generate_with_deepseek(prompt, model, temperature, api_key=api_key, user=user)
            elif p == "ollama":
                return generate_with_ollama(prompt, model or os.getenv("OLLAMA_MODEL", "llama3"), temperature)
        except Exception as e:
            last_err = e
            logger.warning(f"[LLM Fallback] Provider '{p}' unavailable ({e}) — failing over to next provider...")
            continue

    logger.error(f"[LLM] All providers failed. Last error: {last_err}")
    return "Sorry, all AI providers are currently unavailable. Please try again in a moment."


def _build_provider_order(requested: str) -> list:
    """Return provider list with requested provider first, followed by safe fallbacks."""
    all_providers = ["gemini", "groq", "deepseek", "ollama"]
    if requested in all_providers:
        return [requested] + [p for p in all_providers if p != requested]
    return all_providers
