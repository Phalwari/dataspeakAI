export interface WidgetConfig {
  publicKey: string;
  apiBase: string;
  themeColor: string;
  widgetTitle: string;
  greetingMessage: string;
  position: string;
  welcomeDelay: number;
  soundEnabled: boolean;
}

export interface SessionData {
  sessionToken: string;
  expiresAt: number;
  tenantId: number;
  conversationId: number;
  continuityToken?: string;
}

export interface SourceCitation {
  document_name: string;
  page_number?: number;
  content_type?: string;
  reference_id?: string;
  snippet?: string;
  score?: number;
}

const STORAGE_KEY_PREFIX = 'dataspeak_widget_';

/**
 * Safe local storage reader that gracefully degrades if cookies/storage are blocked.
 */
export function getStoredSession(publicKey: string): SessionData | null {
  try {
    const raw = localStorage.getItem(`${STORAGE_KEY_PREFIX}${publicKey}`);
    if (!raw) return null;
    const data = JSON.parse(raw) as SessionData;
    // Check expiration (give 60-second buffer)
    if (Date.now() > data.expiresAt - 60000) {
      localStorage.removeItem(`${STORAGE_KEY_PREFIX}${publicKey}`);
      return null;
    }
    return data;
  } catch {
    return null;
  }
}

export function saveStoredSession(publicKey: string, data: SessionData): void {
  try {
    localStorage.setItem(`${STORAGE_KEY_PREFIX}${publicKey}`, JSON.stringify(data));
  } catch {
    // Storage blocked in third-party context; in-memory fallback will be used
  }
}

export function clearStoredSession(publicKey: string): void {
  try {
    localStorage.removeItem(`${STORAGE_KEY_PREFIX}${publicKey}`);
  } catch {
    // Graceful no-op
  }
}

/**
 * Returns true if the session is nearing its expiration.
 * Default threshold is 10 minutes (600,000 ms), representing the 50-minute mark of a 60-minute token.
 */
export function isSessionNearingExpiry(
  session: SessionData,
  thresholdMs: number = 10 * 60 * 1000
): boolean {
  return Date.now() > session.expiresAt - thresholdMs;
}

/**
 * Performs public handshake to obtain a short-lived HMAC session token.
 * If resuming, passes conversation_id and continuity_token to prove visitor ownership.
 */
export async function createWidgetSession(
  apiBase: string,
  publicKey: string,
  conversationId?: number,
  continuityToken?: string
): Promise<SessionData> {
  const url = `${apiBase.replace(/\/+$/, '')}/api/widget/session`;
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      public_key: publicKey,
      conversation_id: conversationId,
      continuity_token: continuityToken,
    }),
  });

  if (!res.ok) {
    let errorDetail = 'Failed to initialize session';
    try {
      const errJson = await res.json();
      errorDetail = errJson.detail || errorDetail;
    } catch {
      // Non-json error
    }
    throw new Error(errorDetail);
  }

  const data = await res.json();
  const sessionData: SessionData = {
    sessionToken: data.session_token,
    expiresAt: Date.now() + data.expires_in * 1000,
    tenantId: data.tenant_id,
    conversationId: data.conversation_id,
    continuityToken: data.continuity_token,
  };

  saveStoredSession(publicKey, sessionData);
  return sessionData;
}

/**
 * Ensures an active session, proactively renewing at the 50-minute mark before 60-minute HMAC expiration.
 */
export async function ensureActiveWidgetSession(
  apiBase: string,
  publicKey: string,
  existingSession?: SessionData | null
): Promise<SessionData> {
  const current = existingSession || getStoredSession(publicKey);
  if (!current) {
    return await createWidgetSession(apiBase, publicKey);
  }

  if (isSessionNearingExpiry(current)) {
    try {
      return await createWidgetSession(
        apiBase,
        publicKey,
        current.conversationId,
        current.continuityToken
      );
    } catch (err) {
      console.warn('[Widget] Proactive session renewal failed, attempting existing session:', err);
      if (Date.now() < current.expiresAt - 30000) {
        return current;
      }
      return await createWidgetSession(apiBase, publicKey);
    }
  }

  return current;
}

/**
 * Fetches public-safe branding configuration from /api/widget/config.
 */
export async function fetchWidgetConfig(
  apiBase: string,
  publicKey: string
): Promise<Partial<WidgetConfig>> {
  try {
    const url = `${apiBase.replace(/\/+$/, '')}/api/widget/config?key=${encodeURIComponent(publicKey)}`;
    const res = await fetch(url);
    if (!res.ok) return {};
    const data = await res.json();
    return {
      themeColor: data.theme_color,
      widgetTitle: data.widget_title,
      greetingMessage: data.greeting_message,
      position: data.position,
      welcomeDelay: data.welcome_delay,
      soundEnabled: data.sound_enabled,
    };
  } catch {
    return {};
  }
}

export interface SseEventPayload {
  chunk?: string;
  done?: boolean;
  error?: string;
  conversation_id?: number;
  message_id?: number;
  sources?: SourceCitation[];
  sql_data?: any;
}

export function parseSseBlock(block: string): SseEventPayload | null {
  const trimmed = block.trim();
  if (!trimmed.startsWith('data:')) return null;
  const jsonStr = trimmed.slice(5).trim();
  if (!jsonStr || jsonStr === '[DONE]') return null;
  try {
    return JSON.parse(jsonStr) as SseEventPayload;
  } catch {
    return null;
  }
}

export class SseStreamParser {
  private buffer: string = '';

  public feed(chunkText: string): SseEventPayload[] {
    this.buffer += chunkText;
    const parts = this.buffer.split('\n\n');
    this.buffer = parts.pop() || '';
    const events: SseEventPayload[] = [];
    for (const part of parts) {
      const parsed = parseSseBlock(part);
      if (parsed) {
        events.push(parsed);
      }
    }
    return events;
  }

  public flush(): SseEventPayload[] {
    if (!this.buffer.trim()) return [];
    const parsed = parseSseBlock(this.buffer);
    this.buffer = '';
    return parsed ? [parsed] : [];
  }
}

/**
 * Streams chat response over POST using fetch + ReadableStream (SSE format).
 */
export async function streamWidgetChat(
  apiBase: string,
  sessionToken: string,
  query: string,
  conversationId: number,
  onChunk: (chunk: string) => void,
  onDone: (meta: { conversationId: number; messageId?: number; sources?: SourceCitation[] }) => void,
  onError: (errorMsg: string, retryAfter?: number) => void,
  signal?: AbortSignal
): Promise<void> {
  const url = `${apiBase.replace(/\/+$/, '')}/api/chat/widget`;

  try {
    const res = await fetch(url, {
      method: 'POST',
      signal,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${sessionToken}`,
        Accept: 'text/event-stream',
      },
      body: JSON.stringify({
        query,
        session_token: sessionToken,
        conversation_id: conversationId,
        stream: true,
      }),
    });

    if (res.status === 429) {
      const retryHeader = res.headers.get('Retry-After');
      const retrySec = retryHeader ? parseInt(retryHeader, 10) : 5;
      let errDetail = 'Too many requests. Please wait before asking again.';
      try {
        const j = await res.json();
        if (j.detail) errDetail = j.detail;
      } catch {
        // Ignored
      }
      onError(errDetail, retrySec);
      return;
    }

    if (!res.ok) {
      let errDetail = 'Failed to send message';
      try {
        const j = await res.json();
        if (j.detail) errDetail = j.detail;
      } catch {
        // Ignored
      }
      onError(errDetail);
      return;
    }

    if (!res.body) {
      onError('No response received from assistant');
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder('utf-8');
    const parser = new SseStreamParser();

    while (true) {
      if (signal?.aborted) {
        try {
          await reader.cancel();
        } catch {
          // ignore cancel error
        }
        return;
      }

      const { done, value } = await reader.read();
      if (done) break;

      const chunkText = decoder.decode(value, { stream: true });
      const events = parser.feed(chunkText);

      for (const ev of events) {
        if (ev.error) {
          onError(ev.error);
        }
        if (ev.chunk) {
          onChunk(ev.chunk);
        }
        if (ev.done) {
          onDone({
            conversationId: ev.conversation_id || conversationId,
            messageId: ev.message_id,
            sources: ev.sources || [],
          });
        }
      }
    }

    // Flush any remaining buffered event
    const remaining = parser.flush();
    for (const ev of remaining) {
      if (ev.error) {
        onError(ev.error);
      }
      if (ev.chunk) {
        onChunk(ev.chunk);
      }
      if (ev.done) {
        onDone({
          conversationId: ev.conversation_id || conversationId,
          messageId: ev.message_id,
          sources: ev.sources || [],
        });
      }
    }
  } catch (err: any) {
    if (err.name === 'AbortError' || signal?.aborted) {
      return;
    }
    onError(err.message || 'Network connection error');
  }
}
