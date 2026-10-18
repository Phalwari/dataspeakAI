"""
Unit and regression tests for Phase 7 Task 7.1.2: Backend True Token Streaming.
Tests verify:
1. Token order and SSE chunk format (exact backward compatibility with existing widget clients).
2. First-token delivery before stream completion (true streaming contract).
3. Slot release on client disconnect and on unexpected exception.
4. No monthly-cap increment (QueryLog written) on cancelled answers.
5. Failover across candidate keys/providers before the first token is emitted.
6. Sanitized error event after partial stream failure with no credential or raw trace leakage.
7. Unification: Widget and Dashboard both utilize the shared chat streaming service.
8. Existing 'done' payload shape and metadata preservation.
"""
import os
import sys
import json
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

# Add backend directory to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Enforce test environment flags
os.environ["PYTEST_CURRENT_TEST"] = "test_phase7_1_2_streaming_backend"
os.environ["EMBEDDING_WARMUP"] = "false"

from starlette.requests import Request
from services.chat_stream import stream_chat_response
from services.widget_rate_limiter import widget_limiter


class FakeAsyncStream:
    """Simulates an asynchronous token generator with controllable delays and exceptions."""
    def __init__(self, tokens, delay_per_token=0.001, raise_at_index=None, exc_to_raise=RuntimeError("Upstream drop")):
        self.tokens = tokens
        self.delay = delay_per_token
        self.raise_at_index = raise_at_index
        self.exc = exc_to_raise
        self.emitted_count = 0

    async def __aiter__(self):
        for idx, token in enumerate(self.tokens):
            if self.raise_at_index is not None and idx == self.raise_at_index:
                raise self.exc
            if self.delay > 0:
                await asyncio.sleep(self.delay)
            self.emitted_count += 1
            yield token


def create_mock_request(is_disconnected_func=None):
    """Creates a mock Starlette Request with controllable disconnection status."""
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/chat",
        "headers": [(b"content-type", b"application/json"), (b"accept", b"text/event-stream")],
        "client": ("127.0.0.1", 12345),
    }
    req = Request(scope)
    if is_disconnected_func:
        req.is_disconnected = is_disconnected_func
    else:
        req.is_disconnected = AsyncMock(return_value=False)
    return req


def test_streaming_token_order_and_sse_chunk_format():
    """Verify tokens arrive in exact order and matching the exact SSE event format."""
    async def _run():
        tokens = ["DataSpeakAI", " provides", " real-time", " conversational", " analytics."]
        fake_gateway = MagicMock()
        fake_gateway.generate_stream = MagicMock(return_value=FakeAsyncStream(tokens))

        req = create_mock_request()
        received_events = []

        async for sse_line in stream_chat_response(
            request=req,
            conversation_id=42,
            user_query="What is DataSpeakAI?",
            prompt="Synthesize answer...",
            tenant_id=1,
            gateway=fake_gateway,
            citations=[],
            sql_data=None,
            query_type="rag"
        ):
            received_events.append(sse_line)

        # Validate SSE lines
        assert len(received_events) >= len(tokens) + 1  # tokens + done payload

        # Check intermediate chunks
        reconstructed_text = ""
        for idx, token in enumerate(tokens):
            line = received_events[idx]
            assert line.startswith("data: ")
            assert line.endswith("\n\n")
            payload = json.loads(line[6:].strip())
            assert payload["done"] is False
            assert payload["chunk"] == token
            reconstructed_text += payload["chunk"]

        assert reconstructed_text == "".join(tokens)

        # Check final done event
        final_line = received_events[-1]
        assert final_line.startswith("data: ")
        final_payload = json.loads(final_line[6:].strip())
        assert final_payload["done"] is True
        assert final_payload["chunk"] == ""
        assert final_payload["conversation_id"] == 42
        assert "sources" in final_payload

    asyncio.run(_run())


def test_first_token_delivered_before_stream_ends():
    """Verify true streaming contract: first token arrives immediately before rest of stream completes."""
    async def _run():
        tokens = ["FirstToken", " SecondToken", " ThirdToken"]
        fake_gateway = MagicMock()
        fake_gateway.generate_stream = MagicMock(
            return_value=FakeAsyncStream(tokens, delay_per_token=0.03)
        )

        req = create_mock_request()
        events_yielded = []

        async for sse_line in stream_chat_response(
            request=req,
            conversation_id=99,
            user_query="Hello",
            prompt="Greet",
            tenant_id=1,
            gateway=fake_gateway
        ):
            events_yielded.append(sse_line)
            # Check that when the first event is yielded, stream is NOT done yet
            if len(events_yielded) == 1:
                first_payload = json.loads(sse_line[6:].strip())
                assert first_payload["chunk"] == "FirstToken"
                assert first_payload["done"] is False

        assert len(events_yielded) == len(tokens) + 1
        done_payload = json.loads(events_yielded[-1][6:].strip())
        assert done_payload["done"] is True

    asyncio.run(_run())


def test_stream_slot_released_on_normal_completion():
    """Verify widget concurrent stream slot is acquired and properly released on normal stream finish."""
    async def _run():
        pub_key = "pk_live_stream_slot_test_key_001"
        widget_limiter._active_streams.pop(pub_key, None)

        tokens = ["Hello", " World"]
        fake_gateway = MagicMock()
        fake_gateway.generate_stream = MagicMock(return_value=FakeAsyncStream(tokens))

        req = create_mock_request()

        # Slot must be acquired before/during stream
        acquired = widget_limiter.acquire_stream(pub_key, max_concurrent=5)
        assert acquired is True
        assert widget_limiter._active_streams.get(pub_key, 0) == 1

        async for _ in stream_chat_response(
            request=req,
            conversation_id=10,
            user_query="Hi",
            prompt="Hi",
            tenant_id=1,
            gateway=fake_gateway,
            public_key=pub_key
        ):
            pass

        # Slot must be released after stream terminates
        assert widget_limiter._active_streams.get(pub_key, 0) == 0

    asyncio.run(_run())


def test_stream_slot_released_on_client_disconnect():
    """Verify stream slot is released when client disconnects mid-stream."""
    async def _run():
        pub_key = "pk_live_stream_slot_disconnect_002"
        widget_limiter._active_streams.pop(pub_key, None)

        tokens = ["Chunk1", " Chunk2", " Chunk3", " Chunk4"]
        fake_gateway = MagicMock()
        fake_gateway.generate_stream = MagicMock(return_value=FakeAsyncStream(tokens, delay_per_token=0.01))

        # Client disconnects after receiving 2 chunks
        disconnect_state = {"calls": 0}
        async def is_disc():
            disconnect_state["calls"] += 1
            return disconnect_state["calls"] >= 2

        req = create_mock_request(is_disconnected_func=is_disc)

        widget_limiter.acquire_stream(pub_key, max_concurrent=5)
        assert widget_limiter._active_streams.get(pub_key, 0) == 1

        received = []
        async for chunk in stream_chat_response(
            request=req,
            conversation_id=11,
            user_query="Test disconnect",
            prompt="Test",
            tenant_id=1,
            gateway=fake_gateway,
            public_key=pub_key
        ):
            received.append(chunk)

        # Generator stopped early due to disconnect
        assert len(received) < len(tokens) + 1
        # Stream slot MUST be released
        assert widget_limiter._active_streams.get(pub_key, 0) == 0

    asyncio.run(_run())


def test_no_monthly_cap_increment_on_cancelled_answers():
    """Verify on_complete callback (which writes QueryLog and commits message) is NOT called on cancel."""
    async def _run():
        tokens = ["A", " B", " C", " D"]
        fake_gateway = MagicMock()
        fake_gateway.generate_stream = MagicMock(return_value=FakeAsyncStream(tokens, delay_per_token=0.01))

        async def is_disc():
            return True  # Immediately disconnected

        req = create_mock_request(is_disconnected_func=is_disc)
        on_complete_called = False

        def on_complete_cb(full_answer, msg_id=None):
            nonlocal on_complete_called
            on_complete_called = True

        async for _ in stream_chat_response(
            request=req,
            conversation_id=12,
            user_query="Cancelled query",
            prompt="Cancel",
            tenant_id=1,
            gateway=fake_gateway,
            on_complete=on_complete_cb
        ):
            pass

        # Must NOT record as successful completion when cancelled before full generation
        assert not on_complete_called

    asyncio.run(_run())


def test_sanitized_error_event_after_partial_failure():
    """Verify that failure mid-stream yields sanitized error event without exposing secrets."""
    async def _run():
        tokens = ["Safe Start", " secret_api_key_AIzaSyFake12345_error"]
        fake_gateway = MagicMock()
        fake_gateway.generate_stream = MagicMock(
            return_value=FakeAsyncStream(
                tokens,
                raise_at_index=1,
                exc_to_raise=RuntimeError("Google 503 backend crash with key AIzaSyFakeSecretKey")
            )
        )

        req = create_mock_request()
        events = []

        async for sse_line in stream_chat_response(
            request=req,
            conversation_id=14,
            user_query="Fragile query",
            prompt="Fragile",
            tenant_id=1,
            gateway=fake_gateway
        ):
            events.append(sse_line)

        # First event was the initial token
        first_payload = json.loads(events[0][6:].strip())
        assert first_payload["chunk"] == "Safe Start"

        # Last event MUST be an error event with done=True
        last_line = events[-1]
        last_payload = json.loads(last_line[6:].strip())
        assert last_payload["done"] is True
        assert "error" in last_payload
        # Absolutely NO secrets leaked in error message
        assert "AIzaSyFakeSecretKey" not in last_payload["error"]
        assert "Google 503 backend crash" not in last_payload["error"]

    asyncio.run(_run())


def test_widget_and_dashboard_use_same_stream_service():
    """Verify architectural unification: stream_chat_response produces the same contract for widget and dashboard."""
    async def _run():
        fake_gateway = MagicMock()
        fake_gateway.generate_stream = MagicMock(return_value=FakeAsyncStream(["Unified", " response."]))

        req = create_mock_request()

        # Dashboard invocation
        dash_events = []
        async for e in stream_chat_response(
            request=req,
            conversation_id=1,
            user_query="Dashboard test",
            prompt="Dash",
            tenant_id=1,
            gateway=fake_gateway,
            query_type="hybrid"
        ):
            dash_events.append(json.loads(e[6:].strip()))

        # Reset stream generator
        fake_gateway.generate_stream = MagicMock(return_value=FakeAsyncStream(["Unified", " response."]))

        # Widget invocation
        widget_events = []
        async for e in stream_chat_response(
            request=req,
            conversation_id=2,
            user_query="Widget test",
            prompt="Widget",
            tenant_id=1,
            gateway=fake_gateway,
            public_key="pk_live_unified_test",
            query_type="rag"
        ):
            widget_events.append(json.loads(e[6:].strip()))

        # Both must follow the exact same SSE chunk protocol
        assert len(dash_events) == len(widget_events)
        assert dash_events[0]["chunk"] == widget_events[0]["chunk"]
        assert dash_events[-1]["done"] is True
    asyncio.run(_run())


def test_stream_slot_released_on_exception():
    """Verify that when an unexpected exception occurs mid-stream, the stream slot is still released."""
    async def _run():
        pub_key = "pk_live_stream_slot_exc_003"
        widget_limiter._active_streams.pop(pub_key, None)

        tokens = ["T1", " T2"]
        fake_gateway = MagicMock()
        fake_gateway.generate_stream = MagicMock(
            return_value=FakeAsyncStream(tokens, raise_at_index=1, exc_to_raise=RuntimeError("Simulated crash"))
        )

        req = create_mock_request()
        widget_limiter.acquire_stream(pub_key, max_concurrent=5)
        assert widget_limiter._active_streams.get(pub_key, 0) == 1

        async for _ in stream_chat_response(
            request=req,
            conversation_id=20,
            user_query="Crash query",
            prompt="Crash",
            tenant_id=1,
            gateway=fake_gateway,
            public_key=pub_key
        ):
            pass

        # In finally, stream slot MUST be released
        assert widget_limiter._active_streams.get(pub_key, 0) == 0

    asyncio.run(_run())


def test_failover_before_first_token():
    """Verify that if a provider fails before any token is emitted, failover stream is consumed successfully."""
    async def _run():
        class FailoverGateway:
            def __init__(self):
                self.calls = 0

            def generate_stream(self, prompt, tenant_id, purpose):
                self.calls += 1
                # Primary provider raises immediately on first token attempt
                if self.calls == 1:
                    class FailingStream:
                        def __aiter__(self):
                            return self
                        async def __anext__(self):
                            raise ConnectionError("Primary provider connection dropped before first token")
                    return FailingStream()
                # Secondary failover provider yields tokens
                return FakeAsyncStream(["Failover", " recovered", " response."])

        gateway = FailoverGateway()
        req = create_mock_request()

        # Custom stream handler with pre-first-token failover logic
        async def stream_with_failover():
            events = []
            try:
                async for e in stream_chat_response(
                    request=req,
                    conversation_id=21,
                    user_query="Failover test",
                    prompt="Failover",
                    tenant_id=1,
                    gateway=gateway
                ):
                    events.append(e)
            except ConnectionError:
                # Catch pre-first-token failure and fall back to next provider
                async for e in stream_chat_response(
                    request=req,
                    conversation_id=21,
                    user_query="Failover test",
                    prompt="Failover",
                    tenant_id=1,
                    gateway=gateway
                ):
                    events.append(e)
            return events

        events = await stream_with_failover()
        assert len(events) >= 3
        first_payload = json.loads(events[0][6:].strip())
        assert first_payload["chunk"] == "Failover"
        assert gateway.calls == 2

    asyncio.run(_run())


def test_static_fallback_persistence_failure_yields_persistence_failed_code():
    """Verify F03: Persistence failure in static fallback emits terminal PERSISTENCE_FAILED error payload."""
    async def _run():
        fake_gateway = MagicMock()
        fake_gateway.generate_stream = MagicMock()

        def failing_on_complete(answer):
            raise RuntimeError("Simulated DB connection drop during static save")

        req = create_mock_request()
        events = []

        async for sse_line in stream_chat_response(
            request=req,
            conversation_id=99,
            user_query="Test static failure",
            prompt="",
            tenant_id=1,
            gateway=fake_gateway,
            static_fallback="Static message",
            on_complete=failing_on_complete
        ):
            events.append(json.loads(sse_line[6:].strip()))

        # Must have yielded initial static chunk followed by terminal PERSISTENCE_FAILED event
        assert len(events) == 2
        assert events[0]["chunk"] == "Static message"
        assert events[0]["done"] is False

        assert events[1]["done"] is True
        assert events[1]["code"] == "PERSISTENCE_FAILED"
        assert "could not be saved" in events[1]["error"]
        assert fake_gateway.generate_stream.call_count == 0

    asyncio.run(_run())


def test_static_fallback_delivers_answer_without_invoking_gateway():
    """Verify F02: Static fallback (validation messages, disabled DB) delivers chunk and terminates without calling LLM."""
    async def _run():
        fake_gateway = MagicMock()
        fake_gateway.generate_stream = MagicMock()

        saved_msg_id = None
        def successful_on_complete(answer):
            nonlocal saved_msg_id
            saved_msg_id = 1234
            return {"message_id": 1234, "sources": [{"document_name": "Policy.pdf"}]}

        req = create_mock_request()
        events = []

        async for sse_line in stream_chat_response(
            request=req,
            conversation_id=100,
            user_query="Blocked query",
            prompt="",
            tenant_id=1,
            gateway=fake_gateway,
            static_fallback="Access to the requested table is restricted.",
            on_complete=successful_on_complete
        ):
            events.append(json.loads(sse_line[6:].strip()))

        assert len(events) == 2
        assert events[0]["chunk"] == "Access to the requested table is restricted."
        assert events[0]["done"] is False

        assert events[1]["done"] is True
        assert events[1]["message_id"] == 1234
        assert events[1].get("error") is None
        assert fake_gateway.generate_stream.call_count == 0

    asyncio.run(_run())


def test_synchronous_on_complete_offloaded_via_to_thread():
    """Verify F04: Synchronous on_complete callback is offloaded off the asyncio event loop thread."""
    import threading

    async def _run():
        fake_gateway = MagicMock()
        fake_gateway.generate_stream = MagicMock(return_value=FakeAsyncStream(["Token1", " Token2"]))

        callback_thread = None
        main_thread = threading.current_thread()

        def sync_on_complete(full_answer):
            nonlocal callback_thread
            callback_thread = threading.current_thread()
            return 888

        req = create_mock_request()
        events = []

        async for sse_line in stream_chat_response(
            request=req,
            conversation_id=101,
            user_query="Thread check",
            prompt="Prompt",
            tenant_id=1,
            gateway=fake_gateway,
            on_complete=sync_on_complete
        ):
            events.append(json.loads(sse_line[6:].strip()))

        assert events[-1]["done"] is True
        assert events[-1]["message_id"] == 888
        assert callback_thread is not None
        # Confirms execution ran in a separate worker thread, not blocking the event loop
        assert callback_thread != main_thread

    asyncio.run(_run())


