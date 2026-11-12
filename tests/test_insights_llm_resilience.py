"""Offline LLM resilience checks with temporary SQLite and mocked provider HTTP."""

import json
import logging
import sqlite3
import time

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

import models
from services import db_pipeline_service as pipeline
from services import db_pool, db_utils, llm_generation_service as llm


@pytest.fixture
def orders_case(isolated_db, tmp_path, monkeypatch):
    db_path = tmp_path / "transactions.sqlite"
    with sqlite3.connect(db_path) as source:
        source.execute(
            "CREATE TABLE transactions (id INTEGER, amount REAL, created_on TEXT)"
        )
        source.executemany(
            "INSERT INTO transactions VALUES (?, ?, ?)",
            [(1, 12.5, "2026-01-01"), (2, 7.5, "2026-01-02")],
        )
    tenant = models.Tenant(name="Synthetic tenant")
    isolated_db.add(tenant)
    isolated_db.flush()
    connection = models.DatabaseConnection(
        tenant_id=tenant.id,
        name="Synthetic transactions",
        db_type="sqlite",
        database=str(db_path),
        tables_metadata={
            "transactions": {
                "columns": {
                    "id": "INTEGER", "amount": "REAL", "created_on": "TEXT",
                },
                "row_count": 2,
            }
        },
    )
    isolated_db.add(connection)
    isolated_db.flush()
    engine = create_engine(URL.create("sqlite", database=str(db_path)))
    monkeypatch.setattr(db_utils, "get_connection_url", lambda _connection: engine.url)
    monkeypatch.setattr(db_pool, "get_engine", lambda _url: engine)
    monkeypatch.setattr(pipeline, "cache_get", lambda _key: None)
    monkeypatch.setattr(pipeline, "cache_set", lambda *_args, **_kwargs: True)
    monkeypatch.setenv("LLM_PIPELINE_BUDGET_SECONDS", "1")
    monkeypatch.setenv("LLM_RETRY_BACKOFF_SECONDS", "0")
    yield isolated_db, tenant.id, connection.id
    engine.dispose()


def _run(case):
    db, tenant_id, connection_id = case
    return pipeline.DatabasePipelineService().run_db_pipeline(
        db=db, tenant_id=tenant_id, connection_id=connection_id,
        selected_table="transactions",
    )


def _success_response():
    return json.dumps({
        "business_domain": "Unknown",
        "executive_summary": "Computed from supplied values.",
        "strategic_insights": [],
        "tactical_recommendations": [],
    })


def test_format_repair_is_bounded_and_does_not_forward_invalid_response(orders_case, monkeypatch):
    prompts = []
    deadlines = []
    def generate(prompt, **kwargs):
        prompts.append(prompt)
        deadlines.append(kwargs['deadline'])
        return 'PRIVATE_INVALID_OUTPUT' if len(prompts) == 1 else '```JSON\n' + _success_response() + '\n```'
    monkeypatch.setattr(llm, 'generate', generate)
    result = _run(orders_case)
    assert result['executive_summary']['source'] == 'llm'
    assert len(prompts) == 2
    assert deadlines[0] == deadlines[1]
    assert 'PRIVATE_INVALID_OUTPUT' not in prompts[1]


def test_T1_hanging_generate_returns_fallback_within_budget(orders_case, monkeypatch):
    def slow_generate(*_args, **_kwargs):
        time.sleep(5)
        return _success_response()

    monkeypatch.setattr(llm, "generate", slow_generate)
    started = time.monotonic()
    result = _run(orders_case)
    elapsed = time.monotonic() - started
    assert elapsed < 3.0
    assert result["executive_summary"]["source"] == "deterministic_fallback"
    assert result["executive_summary"]["llm_error"] == "Timeout"


def test_T2_one_timeout_then_success_retries_once(orders_case, monkeypatch):
    calls = []
    deadlines = []

    def fake_gateway(*_args, **_kwargs):
        calls.append(1)
        deadlines.append(_kwargs.get("deadline"))
        if len(calls) == 1:
            raise httpx.TimeoutException("synthetic timeout")
        return _success_response()

    monkeypatch.setattr(llm.llm_gateway, "generate_sync", fake_gateway)
    monkeypatch.setenv("LLM_RETRY_BACKOFF_SECONDS", "0")
    result = _run(orders_case)
    assert result["executive_summary"]["source"] == "llm"
    assert len(calls) == 2
    assert all(deadline is not None for deadline in deadlines)


def test_T3_quota_rotates_keys_without_outer_retry(monkeypatch):
    calls = []
    real_client = httpx.AsyncClient

    def http_client(*_args, **_kwargs):
        async def handler(request):
            calls.append(request)
            return httpx.Response(429, json={"error": "quota"})

        return real_client(transport=httpx.MockTransport(handler), timeout=0.1)

    monkeypatch.setattr(llm.httpx, "AsyncClient", http_client)
    monkeypatch.setattr(llm.llm_gateway, "_get_gemini_candidates", lambda *_args: (["fixture-a", "fixture-b"], ["fixture-model"]))
    monkeypatch.setattr(llm.llm_gateway, "_get_groq_candidates", lambda *_args: ([], []))
    monkeypatch.setattr(llm, "generate_with_ollama", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("offline")))
    with pytest.raises(llm.LLMFailure) as exc:
        llm.generate("aggregate-only", provider="auto", raise_on_failure=True)
    assert exc.value.category == "Quota"
    assert len(calls) == 2


def test_T4_two_timeouts_exhaust_retry(orders_case, monkeypatch):
    calls = []

    def fake_gateway(*_args, **_kwargs):
        calls.append(1)
        raise httpx.TimeoutException("synthetic timeout")

    monkeypatch.setattr(llm.llm_gateway, "generate_sync", fake_gateway)
    result = _run(orders_case)
    assert len(calls) == 2
    assert result["executive_summary"]["source"] == "deterministic_fallback"
    assert result["executive_summary"]["llm_error"] == "Timeout"


def test_T5_logs_exclude_prompt_response_and_raw_error(monkeypatch, caplog):
    prompt_marker = "PROMPT_MARKER_PRIVATE"
    response_marker = "RESPONSE_MARKER_PRIVATE"

    def fake_gateway(*_args, **_kwargs):
        raise ValueError(response_marker)

    monkeypatch.setattr(llm.llm_gateway, "generate_sync", fake_gateway)
    with caplog.at_level(logging.WARNING):
        with pytest.raises(llm.LLMFailure) as exc:
            llm.generate(prompt_marker, provider="auto", raise_on_failure=True)
    rendered = "\n".join(record.getMessage() for record in caplog.records)
    assert exc.value.category == "ProviderError"
    assert prompt_marker not in rendered
    assert response_marker not in rendered
    assert "auto" in rendered
    assert "ProviderError" in rendered
    assert "duration_ms" in rendered


def test_T6_fallback_uses_computed_numbers_only(orders_case, monkeypatch):
    monkeypatch.setattr(llm, "generate", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("offline")))
    result = _run(orders_case)
    summary = result["executive_summary"]
    assert summary["source"] == "deterministic_fallback"
    assert "20.00" in summary["executive_summary"]
    assert "2 records" in summary["executive_summary"]
    assert all(term not in json.dumps(summary) for term in ("USA", "Canada", "35%"))


def test_T7_invalid_json_returns_categorized_fallback(orders_case, monkeypatch):
    monkeypatch.setattr(llm, "generate", lambda *_args, **_kwargs: "invalid-json")
    result = _run(orders_case)
    assert result["executive_summary"]["source"] == "deterministic_fallback"
    assert result["executive_summary"]["llm_error"] == "InvalidResponse"


def test_T8_default_generate_preserves_apology_string(monkeypatch):
    monkeypatch.setattr(llm.llm_gateway, "generate_sync", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("offline")))
    result = llm.generate("aggregate-only")
    assert isinstance(result, str)
    assert "currently unavailable" in result


def test_malformed_provider_json_is_invalid_response_without_retry(monkeypatch):
    calls = []
    real_client = httpx.AsyncClient

    def http_client(*_args, **_kwargs):
        async def handler(request):
            calls.append(request)
            return httpx.Response(200, text="{not-json")

        return real_client(transport=httpx.MockTransport(handler), timeout=0.1)

    monkeypatch.setattr(llm.httpx, "AsyncClient", http_client)
    monkeypatch.setattr(llm.llm_gateway, "_get_gemini_candidates", lambda *_args: (["fixture-key"], ["fixture-model"]))
    monkeypatch.setattr(llm.llm_gateway, "_get_groq_candidates", lambda *_args: ([], []))
    monkeypatch.setattr(llm, "generate_with_ollama", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("offline")))
    with pytest.raises(llm.LLMFailure) as exc:
        llm.generate("aggregate-only", raise_on_failure=True)
    assert exc.value.category == "InvalidResponse"
    assert len(calls) == 1


def test_malformed_insight_shape_uses_invalid_response_fallback(orders_case, monkeypatch):
    monkeypatch.setattr(llm, "generate", lambda *_args, **_kwargs: json.dumps({
        "business_domain": "Unknown", "executive_summary": "Malformed insight",
        "strategic_insights": ["not an object"], "tactical_recommendations": [],
    }))
    result = _run(orders_case)
    assert result["executive_summary"]["source"] == "deterministic_fallback"
    assert result["executive_summary"]["llm_error"] == "InvalidResponse"
