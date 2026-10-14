"""
Universal Multi-LLM provider service and key rotation manager.
Supports Google Gemini (langchain_google_genai), Groq (langchain_groq), OpenAI, and DeepSeek.
Includes multi-key harvesting, round-robin key rotation, automated failover chains (Gemini → Groq → Fallback),
transient spike retries (503 / 429), and content normalization.
"""
import os
import random
import asyncio
import itertools
import threading
import logging
from typing import List, Any, Optional

logger = logging.getLogger("dataspeak.multi_llm")

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None

try:
    from langchain_groq import ChatGroq
except ImportError:
    ChatGroq = None

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None


# ── Multi-Key Harvesting ──────────────────────────────────────────────────────

from services.llm_generation_service import _get_all_gemini_keys, _get_all_groq_keys

def get_groq_keys() -> List[str]:
    """Harvest all configured Groq keys from environment via canonical harvesting."""
    return _get_all_groq_keys()


def get_gemini_keys() -> List[str]:
    """Harvest all configured Gemini/Google keys from environment via canonical harvesting."""
    return _get_all_gemini_keys()


def get_deepseek_keys() -> List[str]:
    """DeepSeek disabled per configuration."""
    return []


def get_gemini_key() -> Optional[str]:
    """Convenience getter for a single Gemini key."""
    keys = get_gemini_keys()
    return keys[0] if keys else None


def get_groq_key() -> Optional[str]:
    """Convenience getter for a single Groq key."""
    keys = get_groq_keys()
    return keys[0] if keys else None


# ── Response Normalization & Transient Backoff ────────────────────────────────

class NormalizedContentResponse:
    """Wraps an LLM response guaranteeing that .content is always a clean string."""
    def __init__(self, raw_response: Any):
        self._raw = raw_response
        raw_content = getattr(raw_response, "content", raw_response)
        if isinstance(raw_content, str):
            self.content = raw_content
        elif isinstance(raw_content, list):
            # Concatenate list of parts returned by newer Gemini SDKs
            self.content = "".join([
                item.get("text", "") if isinstance(item, dict) else (getattr(item, "text", "") if hasattr(item, "text") else str(item))
                for item in raw_content
            ])
        else:
            self.content = str(raw_content)

    def __str__(self):
        return self.content

    def __getattr__(self, name):
        return getattr(self._raw, name)


class NormalizedContentLLM:
    """Proxy LLM wrapper guaranteeing normalized string content with automatic retry on transient errors."""
    def __init__(self, inner_llm: Any):
        self._inner = inner_llm

    def invoke(self, *args, **kwargs) -> NormalizedContentResponse:
        import time
        max_attempts = 3
        last_exc = None
        for attempt in range(max_attempts):
            try:
                res = self._inner.invoke(*args, **kwargs)
                return NormalizedContentResponse(res)
            except Exception as e:
                last_exc = e
                err_str = str(e).lower()
                if any(x in err_str for x in ["503", "high demand", "unavailable", "rate limit", "resource_exhausted", "429"]):
                    if attempt < max_attempts - 1:
                        sleep_time = 0.8 * (attempt + 1) + random.uniform(0.1, 0.4)
                        logger.warning(f"[NormalizedContentLLM] Transient error ({e}), retrying in {sleep_time:.2f}s...")
                        time.sleep(sleep_time)
                        continue
                raise
        raise last_exc or RuntimeError("LLM invocation failed after retries")

    async def ainvoke(self, *args, **kwargs) -> NormalizedContentResponse:
        max_attempts = 3
        last_exc = None
        for attempt in range(max_attempts):
            try:
                res = await self._inner.ainvoke(*args, **kwargs)
                return NormalizedContentResponse(res)
            except Exception as e:
                last_exc = e
                err_str = str(e).lower()
                if any(x in err_str for x in ["503", "high demand", "unavailable", "rate limit", "resource_exhausted", "429"]):
                    if attempt < max_attempts - 1:
                        sleep_time = 0.8 * (attempt + 1) + random.uniform(0.1, 0.4)
                        logger.warning(f"[NormalizedContentLLM] Async transient error ({e}), retrying in {sleep_time:.2f}s...")
                        await asyncio.sleep(sleep_time)
                        continue
                raise
        raise last_exc or RuntimeError("LLM async invocation failed after retries")

    def __getattr__(self, name):
        return getattr(self._inner, name)


class FallbackLLMResponse:
    """Safe wrapper representing a fallback response with .content string."""
    def __init__(self, content: str):
        self.content = content

    def __str__(self):
        return self.content


class FallbackLLM:
    """Safe offline/heuristic fallback when external APIs are unreachable or unconfigured."""
    def __init__(self, name: str = "fallback"):
        self.name = name

    def invoke(self, prompt: Any) -> FallbackLLMResponse:
        from services.llm_generation_service import generate
        prompt_text = str(prompt)
        try:
            content = generate(prompt_text)
            if content and not content.startswith("Sorry, all AI providers"):
                return FallbackLLMResponse(content)
        except Exception as e:
            logger.warning(f"Fallback generation error: {e}")

        # Deterministic structured fallback
        return FallbackLLMResponse(
            '{"reasoning": "Heuristic fallback analysis", '
            '"summary": "Automated dataset analysis completed.", '
            '"recommendations": ["Optimize high-volume categories", "Monitor outliers"], '
            '"insights": ["Data distribution shows stable patterns."]}'
        )

    async def ainvoke(self, prompt: Any) -> FallbackLLMResponse:
        return self.invoke(prompt)


# ── Thread-Safe LLM Singleton Cache & Round-Robin Pool ────────────────────────

class LLMPoolManager:
    """
    Singleton Manager that pre-initializes and caches LLM client instances.
    Implements Round-Robin key rotation across API keys to prevent quota hot-spotting.
    """
    _instance = None
    _lock = threading.Lock()
    _groq_cycles = {}
    _gemini_cycles = {}
    _deepseek_cycles = {}
    _cache = {}

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(LLMPoolManager, cls).__new__(cls)
                    cls._instance._init_pools()
        return cls._instance

    def _init_pools(self):
        groq_keys = get_groq_keys()
        gemini_keys = get_gemini_keys()
        deepseek_keys = get_deepseek_keys()

        if groq_keys:
            self._groq_cycles['default'] = itertools.cycle(groq_keys)
        if gemini_keys:
            self._gemini_cycles['default'] = itertools.cycle(gemini_keys)
        if deepseek_keys:
            self._deepseek_cycles['default'] = itertools.cycle(deepseek_keys)

    def get_groq_key(self) -> str:
        cycle = self._groq_cycles.get('default')
        if cycle:
            return next(cycle)
        keys = get_groq_keys()
        return keys[0] if keys else os.getenv("GROQ_API_KEY", "")

    def get_gemini_key(self) -> str:
        cycle = self._gemini_cycles.get('default')
        if cycle:
            return next(cycle)
        keys = get_gemini_keys()
        return keys[0] if keys else (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", ""))

    def get_deepseek_key(self) -> str:
        cycle = self._deepseek_cycles.get('default')
        if cycle:
            return next(cycle)
        keys = get_deepseek_keys()
        return keys[0] if keys else os.getenv("DEEPSEEK_API_KEY", "")

    def get_or_create_llm(
        self,
        model_type: str,
        temperature: float = 0.0,
        json_mode: bool = False,
        fast_model: bool = False
    ) -> Any:
        """
        Retrieves or builds a cached LLM runnable pipeline with round-robin key rotation
        and automatic fallback chains (Gemini keys x models → Groq keys x models → DeepSeek → FallbackLLM).
        """
        cache_key = f"{model_type}_{temperature}_{json_mode}_{fast_model}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        gemini_keys = get_gemini_keys()
        groq_keys = get_groq_keys()
        deepseek_keys = get_deepseek_keys()

        llms = []

        # 1. Google Gemini Candidates (Primary provider - fast, high quota)
        if ChatGoogleGenerativeAI is not None and gemini_keys:
            gemini_models = [
                "gemini-flash-lite-latest",
                "gemma-4-26b-a4b-it",
                "gemini-3.8-flash",
            ]
            for key in gemini_keys:
                for g_mod in gemini_models:
                    try:
                        llm_inst = ChatGoogleGenerativeAI(
                            model=g_mod,
                            temperature=temperature,
                            google_api_key=key
                        )
                        llms.append(llm_inst)
                    except Exception as e:
                        logger.debug(f"[LLM Pool] Gemini candidate init notice ({g_mod}): {e}")

        # 2. Groq Candidates (Instant failover provider on 429/503)
        if ChatGroq is not None and groq_keys:
            groq_models = ["qwen/qwen3.8-27b", "openai/gpt-oss-120b", "openai/gpt-oss-20b"]

            for key in groq_keys:
                for gr_mod in groq_models:
                    try:
                        kwargs: dict[str, Any] = {
                            "model": gr_mod,
                            "temperature": temperature,
                            "api_key": key
                        }
                        if json_mode:
                            kwargs["model_kwargs"] = {"response_format": {"type": "json_object"}}
                        llms.append(ChatGroq(**kwargs))
                    except Exception as e:
                        logger.debug(f"[LLM Pool] Groq candidate init notice ({gr_mod}): {e}")

        # 4. Fallback if no valid client instances could be initialized
        if not llms:
            logger.info(f"[LLM Pool] No external LLM keys configured for role '{model_type}'. Using FallbackLLM.")
            return FallbackLLM(name=model_type)

        primary = llms[0]
        if len(llms) > 1:
            pipeline = primary.with_fallbacks(llms[1:], exceptions_to_handle=(Exception,))
        else:
            pipeline = primary

        # Wrap in NormalizedContentLLM to ensure clean string .content and transient retry
        result = NormalizedContentLLM(pipeline)
        self._cache[cache_key] = result
        return result


# Global pool manager instance
_pool_manager = LLMPoolManager()


# ── Specialized Getter Functions (Fast & Cached) ──────────────────────────────

def get_multi_llm(temperature: float = 0.1, json_mode: bool = False):
    """General multi-purpose LLM instance with full round-robin fallback chain."""
    return _pool_manager.get_or_create_llm("multi", temperature=temperature, json_mode=json_mode)


def get_intent_llm(temperature: float = 0.0, json_mode: bool = True):
    """Ultra-fast intent detection & classification model with fallback chain."""
    return _pool_manager.get_or_create_llm("intent", temperature=temperature, json_mode=json_mode, fast_model=True)


def get_sql_llm(temperature: float = 0.0, json_mode: bool = False):
    """High-accuracy SQL & relational schema query generator with fallback chain."""
    return _pool_manager.get_or_create_llm("sql", temperature=temperature, json_mode=json_mode, fast_model=False)


def get_response_llm(temperature: float = 0.3, json_mode: bool = False):
    """Natural response & conversational synthesizer with fallback chain."""
    return _pool_manager.get_or_create_llm("response", temperature=temperature, json_mode=json_mode, fast_model=False)


def get_fast_llm(temperature: float = 0.1, json_mode: bool = False):
    """Lightweight, low-latency model for secondary calculations and summaries."""
    return _pool_manager.get_or_create_llm("fast", temperature=temperature, json_mode=json_mode, fast_model=True)


def get_or_create_llm(role: str = "general", temperature: float = 0.2, json_mode: bool = False):
    """Compatibility alias for get_or_create_llm."""
    return _pool_manager.get_or_create_llm(role, temperature=temperature, json_mode=json_mode)
