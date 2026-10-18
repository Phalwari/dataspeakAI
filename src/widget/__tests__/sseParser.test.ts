import { describe, it, expect, vi } from 'vitest';
import {
  parseSseBlock,
  SseStreamParser,
  streamWidgetChat,
  isSessionNearingExpiry,
  ensureActiveWidgetSession,
  SessionData,
} from '../api';

describe('SSE Parser and Streaming Contract (Task 7.1.2)', () => {
  describe('parseSseBlock', () => {
    it('parses a valid token chunk event', () => {
      const block = 'data: {"chunk": "Hello", "done": false}';
      const parsed = parseSseBlock(block);
      expect(parsed).toEqual({ chunk: 'Hello', done: false });
    });

    it('parses a valid done event with metadata', () => {
      const block = 'data: {"chunk": "", "done": true, "conversation_id": 42, "message_id": 100, "sources": [{"document_name": "policy.pdf"}]}';
      const parsed = parseSseBlock(block);
      expect(parsed).toEqual({
        chunk: '',
        done: true,
        conversation_id: 42,
        message_id: 100,
        sources: [{ document_name: 'policy.pdf' }],
      });
    });

    it('returns null for [DONE] sentinel and empty blocks', () => {
      expect(parseSseBlock('data: [DONE]')).toBeNull();
      expect(parseSseBlock('')).toBeNull();
      expect(parseSseBlock('   ')).toBeNull();
    });

    it('gracefully returns null for malformed JSON without crashing', () => {
      expect(parseSseBlock('data: {invalid-json')).toBeNull();
      expect(parseSseBlock('event: message')).toBeNull();
    });
  });

  describe('SseStreamParser buffering & splitting', () => {
    it('handles partial chunks split across feed() calls', () => {
      const parser = new SseStreamParser();

      // Part 1: incomplete JSON line
      const events1 = parser.feed('data: {"chunk": "DataSp');
      expect(events1).toEqual([]);

      // Part 2: completes the first event and starts a second
      const events2 = parser.feed('eakAI", "done": false}\n\ndata: {"chunk": " provides"');
      expect(events2).toEqual([{ chunk: 'DataSpeakAI', done: false }]);

      // Part 3: completes the second event
      const events3 = parser.feed(', "done": false}\n\n');
      expect(events3).toEqual([{ chunk: ' provides', done: false }]);
    });

    it('handles multiple split events in a single feed() chunk', () => {
      const parser = new SseStreamParser();
      const rawChunk =
        'data: {"chunk": "A", "done": false}\n\n' +
        'data: {"chunk": "B", "done": false}\n\n' +
        'data: {"chunk": "C", "done": false}\n\n';

      const events = parser.feed(rawChunk);
      expect(events).toEqual([
        { chunk: 'A', done: false },
        { chunk: 'B', done: false },
        { chunk: 'C', done: false },
      ]);
    });

    it('safely skips malformed events amidst valid events', () => {
      const parser = new SseStreamParser();
      const mixedChunk =
        'data: {"chunk": "Valid 1", "done": false}\n\n' +
        'data: {corrupt:json\n\n' +
        'data: {"chunk": "Valid 2", "done": false}\n\n';

      const events = parser.feed(mixedChunk);
      expect(events).toEqual([
        { chunk: 'Valid 1', done: false },
        { chunk: 'Valid 2', done: false },
      ]);
    });

    it('flush() delivers a trailing event without closing newlines', () => {
      const parser = new SseStreamParser();
      parser.feed('data: {"chunk": "Final", "done": true}');
      const flushed = parser.flush();
      expect(flushed).toEqual([{ chunk: 'Final', done: true }]);
    });
  });

  describe('streamWidgetChat execution & abort handling', () => {
    it('streams chunks and invokes onDone callback', async () => {
      const ssePayload =
        'data: {"chunk": "Hello", "done": false}\n\n' +
        'data: {"chunk": " world", "done": false}\n\n' +
        'data: {"chunk": "", "done": true, "conversation_id": 99, "message_id": 500, "sources": []}\n\n';

      const mockResponse = new Response(
        new ReadableStream({
          start(controller) {
            controller.enqueue(new TextEncoder().encode(ssePayload));
            controller.close();
          },
        }),
        { status: 200, headers: { 'Content-Type': 'text/event-stream' } }
      );

      globalThis.fetch = vi.fn().mockResolvedValue(mockResponse);

      const chunks: string[] = [];
      let doneResult: any = null;

      await streamWidgetChat(
        'http://localhost:8000',
        'session_token_123',
        'Hello',
        99,
        (c) => chunks.push(c),
        (meta) => {
          doneResult = meta;
        },
        () => {}
      );

      expect(chunks).toEqual(['Hello', ' world']);
      expect(doneResult).toEqual({
        conversationId: 99,
        messageId: 500,
        sources: [],
      });
    });

    it('handles stream abort cleanly when AbortController.abort() is called', async () => {
      const abortCtrl = new AbortController();

      const mockResponse = new Response(
        new ReadableStream({
          start(controller) {
            controller.enqueue(new TextEncoder().encode('data: {"chunk": "First", "done": false}\n\n'));
            controller.enqueue(new TextEncoder().encode('data: {"chunk": "Second", "done": false}\n\n'));
            controller.close();
          },
        }),
        { status: 200, headers: { 'Content-Type': 'text/event-stream' } }
      );

      globalThis.fetch = vi.fn().mockResolvedValue(mockResponse);

      const chunks: string[] = [];
      let errorMessage: string | null = null;

      await streamWidgetChat(
        'http://localhost:8000',
        'session_token_123',
        'Query',
        1,
        (c) => {
          chunks.push(c);
          // Abort mid-stream on first token
          abortCtrl.abort();
        },
        () => {},
        (err) => {
          errorMessage = err;
        },
        abortCtrl.signal
      );

      // Successfully received first chunk; did not treat user abort as a crash error
      expect(chunks).toContain('First');
      expect(chunks).not.toContain('Second');
      expect(errorMessage).toBeNull();
    });

    it('calls onError callback when error event is received from server and does not trigger onDone', async () => {
      const ssePayload =
        'data: {"chunk": "Start", "done": false}\n\n' +
        'data: {"chunk": "", "done": true, "error": "AI service quota exhausted", "conversation_id": 10}\n\n';

      const mockResponse = new Response(
        new ReadableStream({
          start(controller) {
            controller.enqueue(new TextEncoder().encode(ssePayload));
            controller.close();
          },
        }),
        { status: 200, headers: { 'Content-Type': 'text/event-stream' } }
      );

      globalThis.fetch = vi.fn().mockResolvedValue(mockResponse);

      let reportedError = '';
      let doneCalled = false;
      await streamWidgetChat(
        'http://localhost:8000',
        'token',
        'Query',
        10,
        () => {},
        () => {
          doneCalled = true;
        },
        (err) => {
          reportedError = err;
        }
      );

      expect(reportedError).toBe('AI service quota exhausted');
      expect(doneCalled).toBe(false);
    });
  });

  describe('Widget Session Renewal & Expiry Contract (NR-1.1-B-T08)', () => {
    it('detects session nearing expiry at the 50-minute mark (within 10 min)', () => {
      const now = Date.now();
      // Fresh token: 60 minutes remaining -> not nearing expiry
      const freshSession: SessionData = {
        sessionToken: 'fresh-token',
        expiresAt: now + 60 * 60 * 1000,
        tenantId: 1,
        conversationId: 10,
        continuityToken: 'continuity-1',
      };
      expect(isSessionNearingExpiry(freshSession)).toBe(false);

      // 51 minutes old: 9 minutes remaining -> nearing expiry
      const expiringSession: SessionData = {
        sessionToken: 'expiring-token',
        expiresAt: now + 9 * 60 * 1000,
        tenantId: 1,
        conversationId: 10,
        continuityToken: 'continuity-1',
      };
      expect(isSessionNearingExpiry(expiringSession)).toBe(true);

      // Already expired token -> nearing expiry
      const expiredSession: SessionData = {
        sessionToken: 'expired-token',
        expiresAt: now - 1000,
        tenantId: 1,
        conversationId: 10,
        continuityToken: 'continuity-1',
      };
      expect(isSessionNearingExpiry(expiredSession)).toBe(true);
    });

    it('proactively renews session via continuityToken when nearing expiry', async () => {
      const now = Date.now();
      const expiringSession: SessionData = {
        sessionToken: 'old-session-token',
        expiresAt: now + 5 * 60 * 1000, // 5 min remaining
        tenantId: 1,
        conversationId: 42,
        continuityToken: 'continuity-proof-abc',
      };

      const mockResponse = new Response(
        JSON.stringify({
          session_token: 'new-renewed-token',
          expires_in: 3600,
          tenant_id: 1,
          conversation_id: 42,
          continuity_token: 'continuity-proof-abc',
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      );

      const mockFetch = vi.fn().mockResolvedValue(mockResponse);
      globalThis.fetch = mockFetch;

      const renewed = await ensureActiveWidgetSession(
        'http://localhost:8000',
        'pk_live_test_key',
        expiringSession
      );

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const requestBody = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(requestBody.public_key).toBe('pk_live_test_key');
      expect(requestBody.conversation_id).toBe(42);
      expect(requestBody.continuity_token).toBe('continuity-proof-abc');

      expect(renewed.sessionToken).toBe('new-renewed-token');
      expect(renewed.conversationId).toBe(42);
      expect(renewed.continuityToken).toBe('continuity-proof-abc');
      expect(renewed.expiresAt).toBeGreaterThan(now + 3500 * 1000);
    });

    it('returns existing session without renewal if fresh and far from expiry', async () => {
      const now = Date.now();
      const freshSession: SessionData = {
        sessionToken: 'fresh-active-token',
        expiresAt: now + 55 * 60 * 1000, // 55 min remaining
        tenantId: 1,
        conversationId: 42,
        continuityToken: 'continuity-proof-abc',
      };

      const mockFetch = vi.fn();
      globalThis.fetch = mockFetch;

      const result = await ensureActiveWidgetSession(
        'http://localhost:8000',
        'pk_live_test_key',
        freshSession
      );

      expect(mockFetch).not.toHaveBeenCalled();
      expect(result.sessionToken).toBe('fresh-active-token');
    });
  });
});
