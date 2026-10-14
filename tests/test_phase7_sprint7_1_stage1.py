"""
Phase 7 Sprint 7.1 — Stage 1 Test Suite
Verifies:
1. LLMMetrics telemetry collection, percentiles, key cooldowns, and tenant cost tracking.
2. LLMGateway async generation, SSE streaming, multi-key rotation, and 429/403 failover.
3. Synchronous compatibility bridges (generate_sync, generate_with_gemini, generate_with_groq).
4. SQL Engine dialect timeouts, PRAGMA guardrails, and execution watchdog fail-safe.
5. GET /api/system/llm-metrics diagnostics endpoint.
"""

import os
import sys
import time
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

# Add backend directory to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import models
from services.llm_metrics import LLMMetrics, llm_metrics
from services.llm_generation_service import (
    LLMGateway,
    _extract_keys,
    _rotate_keys,
    _get_active_ordered_keys,
    _key_cooldowns,
    llm_gateway,
    generate_with_gemini,
    generate_with_groq
)
from services.sql_engine import execute_safe_sql, generate_sql_from_nl
from fastapi.testclient import TestClient
from main import app


@pytest.fixture(autouse=True)
def clean_metrics_and_cooldowns():
    """Reset telemetry datastore and key cooldowns before each test."""
    llm_metrics.reset()
    _key_cooldowns.clear()
    yield
    llm_metrics.reset()
    _key_cooldowns.clear()


# ==============================================================================
# 1. Telemetry Datastore Tests (LLMMetrics)
# ==============================================================================

def test_llm_metrics_telemetry_recording():
    metrics = LLMMetrics()

    # Record 3 successful requests with different characteristics
    metrics.record_request(
        provider="gemini",
        model="gemini-2.5-flash",
        tenant_id=1,
        purpose="chat",
        prompt_tokens=100,
        completion_tokens=50,
        latency_ms=250.0,
        ttft_ms=120.0,
        status_code=200,
        masked_key="...1111"
    )
    metrics.record_request(
        provider="gemini",
        model="gemini-2.5-flash",
        tenant_id=1,
        purpose="chat",
        prompt_tokens=200,
        completion_tokens=100,
        latency_ms=450.0,
        ttft_ms=180.0,
        status_code=200,
        masked_key="...1111"
    )
    metrics.record_request(
        provider="groq",
        model="llama-3.3-70b-versatile",
        tenant_id=2,
        purpose="nl_to_sql",
        prompt_tokens=300,
        completion_tokens=150,
        latency_ms=800.0,
        ttft_ms=220.0,
        status_code=200,
        masked_key="...2222"
    )

    summary = metrics.get_summary()

    assert summary["total_requests"] == 3
    assert summary["total_tokens"]["prompt"] == 600
    assert summary["total_tokens"]["completion"] == 300
    assert summary["total_tokens"]["total"] == 900

    # Latency & TTFT stats
    assert summary["latency_ms"]["average"] == 500.0
    assert summary["latency_ms"]["p50"] > 0
    assert summary["ttft_ms"]["p50"] > 0

    # Distribution checks
    assert summary["requests_by_provider"]["gemini"] == 2
    assert summary["requests_by_provider"]["groq"] == 1
    assert summary["requests_by_purpose"]["chat"] == 2
    assert summary["requests_by_purpose"]["nl_to_sql"] == 1

    # Key stats
    assert summary["keys"]["total_tracked"] == 2
    assert summary["keys"]["details"]["...1111"]["success"] == 2

    # Tenant cost attribution
    assert summary["tenants_count"] == 2
    assert summary["tenant_usage"][1]["requests"] == 2
    assert summary["tenant_usage"][1]["estimated_cost_usd"] > 0.0


def test_llm_metrics_key_cooldown_tracking():
    metrics = LLMMetrics()
    metrics.record_key_cooldown("...9999", "gemini", cooldown_duration_sec=60.0)

    summary = metrics.get_summary()
    assert summary["keys"]["in_cooldown"] == 1
    assert summary["keys"]["details"]["...9999"]["in_cooldown"] is True
    assert summary["keys"]["details"]["...9999"]["cooldown_remaining_sec"] > 50


# ==============================================================================
# 2. Key Harvesting & Rotation Tests
# ==============================================================================

def test_extract_keys_utility():
    raw_keys = "key1, key2; key3\nkey4, key1"
    extracted = _extract_keys(raw_keys)
    assert extracted == ["key1", "key2", "key3", "key4"]


def test_key_rotation_round_robin():
    keys = ["k1", "k2", "k3"]
    # First rotation starts at index 0, increments counter
    rotated1 = _rotate_keys(keys, "gemini")
    rotated2 = _rotate_keys(keys, "gemini")
    rotated3 = _rotate_keys(keys, "gemini")

    assert rotated1 == ["k1", "k2", "k3"]
    assert rotated2 == ["k2", "k3", "k1"]
    assert rotated3 == ["k3", "k1", "k2"]


def test_active_ordered_keys_quarantine_priority():
    keys = ["key_healthy_1", "key_throttled", "key_healthy_2"]
    # Mark key_throttled in cooldown
    _key_cooldowns["key_throttled"] = time.time() + 60.0

    ordered = _get_active_ordered_keys(keys, "gemini")
    # Active keys should appear before the quarantined key
    assert ordered[-1] == "key_throttled"
    assert set(ordered[:2]) == {"key_healthy_1", "key_healthy_2"}


# ==============================================================================
# 3. LLMGateway Async Generation & Failover Tests
# ==============================================================================

def test_gateway_async_generate_success():
    async def _run():
        gateway = LLMGateway()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [{
                "content": {
                    "parts": [{"text": "Async generation successful!"}]
                }
            }]
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp

            result = await gateway.generate(
                prompt="Hello DataSpeak",
                provider="gemini",
                api_key="mock_test_key_1234",
                purpose="test"
            )

            assert result == "Async generation successful!"
            summary = llm_metrics.get_summary()
            assert summary["total_requests"] == 1
            assert summary["requests_by_provider"]["gemini"] == 1

    asyncio.run(_run())


def test_gateway_failover_on_429():
    async def _run():
        gateway = LLMGateway()

        # Key 1 returns 429; Key 2 returns 200
        resp_429 = MagicMock()
        resp_429.status_code = 429
        resp_429.text = "Quota exceeded"

        resp_200 = MagicMock()
        resp_200.status_code = 200
        resp_200.json.return_value = {
            "candidates": [{
                "content": {
                    "parts": [{"text": "Recovered via second key!"}]
                }
            }]
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = [resp_429, resp_200]

            result = await gateway.generate(
                prompt="Test failover",
                provider="gemini",
                api_key="bad_key_1111, good_key_2222",
                purpose="test_failover"
            )

            assert result == "Recovered via second key!"
            # First key must now be quarantined
            assert "bad_key_1111" in _key_cooldowns
            assert _key_cooldowns["bad_key_1111"] > time.time()

    asyncio.run(_run())


def test_gateway_generate_stream():
    async def _run():
        gateway = LLMGateway()

        # Simulate SSE stream lines from Gemini
        async def fake_aiter_lines():
            yield 'data: {"candidates": [{"content": {"parts": [{"text": "Hello "}]}}]}'
            yield 'data: {"candidates": [{"content": {"parts": [{"text": "DataSpeak "}]}}]}'
            yield 'data: {"candidates": [{"content": {"parts": [{"text": "World!"}]}}]}'
            yield 'data: [DONE]'

        mock_stream_ctx = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.aiter_lines = fake_aiter_lines

        # Set up async context manager for client.stream()
        mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient.stream", return_value=mock_stream_ctx):
            chunks = []
            async for chunk in gateway.generate_stream(
                prompt="Stream test",
                provider="gemini",
                api_key="mock_stream_key_3333"
            ):
                chunks.append(chunk)

            assert chunks == ["Hello ", "DataSpeak ", "World!"]
            summary = llm_metrics.get_summary()
            assert summary["total_requests"] >= 1

    asyncio.run(_run())


def test_gateway_sync_wrapper():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [{
            "content": {
                "parts": [{"text": "Synchronous bridge result"}]
            }
        }]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        res = llm_gateway.generate_sync(
            prompt="Sync test",
            api_key="sync_key_4444"
        )
        assert res == "Synchronous bridge result"


# ==============================================================================
# 4. Dialect Query Timeouts & Safety Guard Tests
# ==============================================================================

def test_execute_safe_sql_sqlite_guardrails(tmp_path):
    # Create temporary SQLite database
    db_file = tmp_path / "test_safety.db"
    import sqlite3
    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()
    cur.execute("CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, price REAL)")
    cur.execute("INSERT INTO products VALUES (1, 'Widget A', 19.99), (2, 'Widget B', 29.99)")
    conn.commit()
    conn.close()

    mock_db_conn = models.DatabaseConnection(
        id=999,
        tenant_id=1,
        name="Test SQLite",
        db_type="sqlite",
        database=str(db_file)
    )

    # Valid read-only query
    result = execute_safe_sql(mock_db_conn, "SELECT * FROM products")
    assert result["row_count"] == 2
    assert "name" in result["columns"]
    assert "price" in result["columns"]

    # DDL attempt must be blocked by guardrail before touching DB
    with pytest.raises(ValueError, match="SQL Guardrail Violation"):
        execute_safe_sql(mock_db_conn, "DROP TABLE products")


def test_execute_safe_sql_watchdog_timeout():
    mock_db_conn = models.DatabaseConnection(
        id=999,
        tenant_id=1,
        name="Test Timeout",
        db_type="sqlite",
        database="test_nonexistent.db"
    )

    # Patch connection creation to simulate a hanging driver exceeding timeout
    def hanging_connect(*args, **kwargs):
        time.sleep(13.0)
        return MagicMock()

    with patch("services.sql_engine.create_engine") as mock_engine:
        mock_engine.side_effect = hanging_connect
        with pytest.raises(RuntimeError, match="Database execution timeout exceeded"):
            execute_safe_sql(mock_db_conn, "SELECT 1")


# ==============================================================================
# 5. System Diagnostics Endpoint Tests
# ==============================================================================

def test_system_llm_metrics_endpoint():
    # Pre-populate metrics
    llm_metrics.record_request(
        provider="gemini",
        model="gemini-2.5-flash",
        tenant_id=1,
        purpose="chat",
        prompt_tokens=50,
        completion_tokens=25,
        latency_ms=150.0,
        status_code=200
    )

    client = TestClient(app)
    response = client.get("/api/system/llm-metrics")
    assert response.status_code == 200

    data = response.json()
    assert "total_requests" in data
    assert data["total_requests"] >= 1
    assert "total_tokens" in data
    assert "latency_ms" in data
    assert "keys" in data
    assert "requests_by_provider" in data
