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
 * Performs public handshake to obtain a short-lived HMAC session token.
 */
export async function createWidgetSession(
  apiBase: string,
  publicKey: string,
  conversationId?: number
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
  };

  saveStoredSession(publicKey, sessionData);
  return sessionData;
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
  onError: (errorMsg: string, retryAfter?: number) => void
): Promise<void> {
  const url = `${apiBase.replace(/\/+$/, '')}/api/chat/widget`;

  try {
    const res = await fetch(url, {
      method: 'POST',
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
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith('data:')) {
          const jsonStr = trimmed.slice(5).trim();
          try {
            const parsed = JSON.parse(jsonStr);
            if (parsed.chunk) {
              onChunk(parsed.chunk);
            }
            if (parsed.done) {
              onDone({
                conversationId: parsed.conversation_id || conversationId,
                messageId: parsed.message_id,
                sources: parsed.sources || [],
              });
            }
          } catch {
            // Malformed chunk ignored
          }
        }
      }
    }
  } catch (err: any) {
    onError(err.message || 'Network connection error');
  }
}
