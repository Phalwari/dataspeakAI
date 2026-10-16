import { h, ComponentChild } from 'preact';
import { useState, useEffect, useRef } from 'preact/hooks';
import {
  WidgetConfig,
  SessionData,
  SourceCitation,
  getStoredSession,
  createWidgetSession,
  clearStoredSession,
  streamWidgetChat,
} from '../api';
import { SafeMarkdown } from '../markdown';

export interface MessageItem {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  time?: number;
  sources?: SourceCitation[];
  isStreaming?: boolean;
}

interface WidgetAppProps {
  initialConfig: WidgetConfig;
}

const QUICK_REPLIES = ['What can you help with?', 'Pricing', 'Talk to support'];

const fmtTime = (t?: number) =>
  t ? new Date(t).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';

export function WidgetApp({ initialConfig }: WidgetAppProps): ComponentChild {
  const [isOpen, setIsOpen] = useState(false);
  const [config, setConfig] = useState<WidgetConfig>(initialConfig);
  const [session, setSession] = useState<SessionData | null>(null);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [retryCountdown, setRetryCountdown] = useState<number | null>(null);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const launcherRef = useRef<HTMLButtonElement | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const didMount = useRef(false);

  const greeting = () => config.greetingMessage || 'Hello! How can I help you today?';

  // React to initialConfig updates (e.g. after server config fetch)
  useEffect(() => {
    setConfig(initialConfig);
  }, [initialConfig]);

  // cleanup on unmount
  useEffect(() => () => abortRef.current?.abort(), []);

  // init session + greeting
  useEffect(() => {
    const stored = getStoredSession(config.publicKey);
    if (stored) setSession(stored);
    setMessages((prev) => {
      // If user hasn't sent any messages yet, update the initial greeting
      if (prev.length <= 1 && (prev.length === 0 || prev[0].id === 'msg-greeting')) {
        return [{ id: 'msg-greeting', role: 'assistant', text: greeting(), time: Date.now() }];
      }
      return prev;
    });
  }, [config.publicKey, config.greetingMessage]);

  // autoscroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, isStreaming]);

  // focus mgmt (FIX: don't steal host page focus on first render)
  useEffect(() => {
    if (!didMount.current) {
      didMount.current = true;
      return;
    }
    if (isOpen) setTimeout(() => inputRef.current?.focus(), 200);
    else launcherRef.current?.focus();
  }, [isOpen]);

  // escape key
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) setIsOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [isOpen]);

  // retry countdown
  useEffect(() => {
    if (retryCountdown === null || retryCountdown <= 0) return;
    const t = setTimeout(() => setRetryCountdown((p) => (p && p > 1 ? p - 1 : null)), 1000);
    return () => clearTimeout(t);
  }, [retryCountdown]);

  // textarea auto-resize
  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 110) + 'px';
  }, [inputValue]);

  const stopStreaming = () => {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsStreaming(false);
    setMessages((prev) =>
      prev.map((m, i) =>
        i === prev.length - 1 && m.role === 'assistant'
          ? { ...m, isStreaming: false, text: m.text ? m.text + '\n\n*(Generation stopped)*' : '*(Generation cancelled)*' }
          : m
      )
    );
  };

  const newChat = () => {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsStreaming(false);
    clearStoredSession(config.publicKey);
    setSession(null);
    setMessages([{ id: `msg-greeting-${Date.now()}`, role: 'assistant', text: greeting(), time: Date.now() }]);
    setErrorMessage(null);
  };

  const send = async (override?: string) => {
    const query = (override ?? inputValue).trim();
    if (!query || isStreaming || retryCountdown !== null) return;

    setInputValue('');
    setErrorMessage(null);

    const userId = `user-${Date.now()}`;
    const asstId = `asst-${Date.now()}`;
    const now = Date.now();

    setMessages((prev) => [
      ...prev,
      { id: userId, role: 'user', text: query, time: now },
      { id: asstId, role: 'assistant', text: '', time: now, isStreaming: true },
    ]);
    setIsStreaming(true);

    const ctrl = new AbortController();
    abortRef.current = ctrl;

    try {
      let cur = session;
      if (!cur || Date.now() > cur.expiresAt - 60000) {
        cur = await createWidgetSession(config.apiBase, config.publicKey, cur?.conversationId);
        setSession(cur);
      }

      await streamWidgetChat(
        config.apiBase,
        cur.sessionToken,
        query,
        cur.conversationId,
        (chunk) =>
          setMessages((prev) => prev.map((m) => (m.id === asstId ? { ...m, text: m.text + chunk } : m))),
        (meta) => {
          abortRef.current = null;
          setIsStreaming(false);
          setMessages((prev) =>
            prev.map((m) => (m.id === asstId ? { ...m, isStreaming: false, sources: meta.sources } : m))
          );
        },
        (errMsg, retrySec) => {
          abortRef.current = null;
          setIsStreaming(false);
          setErrorMessage(errMsg);
          if (retrySec) setRetryCountdown(retrySec);
          setMessages((prev) => prev.filter((m) => !(m.id === asstId && !m.text)));
        },
        ctrl.signal
      );
    } catch (err: any) {
      abortRef.current = null;
      setIsStreaming(false);
      if (err.name !== 'AbortError' && !ctrl.signal.aborted) {
        setErrorMessage(err.message || 'Unable to establish secure connection');
      }
      setMessages((prev) => prev.filter((m) => !(m.id === asstId && !m.text)));
    }
  };

  const onKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const showChips = messages.length === 1 && !isStreaming;
  const lastIsEmpty = messages[messages.length - 1]?.text === '';

  const icon = (d: string, size = '18', sw = '2') =>
    h('svg', { width: size, height: size, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': sw, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, h('path', { d }));

  return h('div', { class: 'dataspeak-container' }, [
    // Launcher
    h(
      'button',
      {
        ref: launcherRef,
        class: `dataspeak-launcher ${isOpen ? 'is-open' : ''}`,
        onClick: () => { setIsOpen(!isOpen); setErrorMessage(null); },
        'aria-label': isOpen ? 'Close chat assistant' : 'Open chat assistant',
        'aria-expanded': isOpen,
      },
      isOpen
        ? icon('M18 6L6 18M6 6l12 12', '26')
        : icon('M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z', '26')
    ),

    // Panel (FIX: aria-modal only when open)
    h(
      'div',
      {
        class: `dataspeak-panel ${isOpen ? 'open' : ''}`,
        role: 'dialog',
        'aria-modal': isOpen ? 'true' : 'false',
        'aria-label': config.widgetTitle || 'AI Assistant',
        'aria-hidden': isOpen ? 'false' : 'true',
      },
      [
        // Header
        h('div', { class: 'dataspeak-header' }, [
          h('div', { class: 'dataspeak-header-left' }, [
            h('div', { class: 'dataspeak-avatar' }, 'AI'),
            h('div', null, [
              h('div', { class: 'dataspeak-header-title' }, config.widgetTitle || 'AI Assistant'),
              h('div', { class: 'dataspeak-header-status' }, [h('span', { class: 'dataspeak-status-dot' }), 'Online']),
            ]),
          ]),
          h('div', { class: 'dataspeak-header-actions' }, [
            h('button', { class: 'dataspeak-icon-btn', onClick: newChat, title: 'Start new chat', 'aria-label': 'Start new chat' },
              icon('M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8M21 3v5h-5M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16M3 21v-5h5')),
            h('button', { class: 'dataspeak-icon-btn', onClick: () => setIsOpen(false), title: 'Close chat', 'aria-label': 'Close chat' },
              icon('M18 6L6 18M6 6l12 12')),
          ]),
        ]),

        // Messages
        h('div', { class: 'dataspeak-messages', 'aria-live': 'polite' }, [
          ...messages.map((m) =>
            // don't render the empty streaming placeholder (typing dots handle it)
            m.role === 'assistant' && m.text === '' && m.isStreaming
              ? null
              : h('div', { key: m.id, class: `dataspeak-msg-row ${m.role}` }, [
                  h('div', { class: 'dataspeak-bubble' }, m.role === 'assistant' ? h(SafeMarkdown, { content: m.text }) : m.text),
                  m.sources && m.sources.length > 0
                    ? h('div', { class: 'dataspeak-sources' },
                        m.sources.map((s, i) =>
                          h('span', { key: `s${i}`, class: 'dataspeak-source-badge' },
                            `📄 ${s.document_name}${s.page_number ? ` (p. ${s.page_number})` : ''}`)))
                    : null,
                  !m.isStreaming && m.time ? h('div', { class: 'dataspeak-time' }, fmtTime(m.time)) : null,
                ])
          ),

          isStreaming && lastIsEmpty
            ? h('div', { class: 'dataspeak-typing', 'aria-label': 'Assistant is thinking' }, [
                h('span', { class: 'dataspeak-dot' }),
                h('span', { class: 'dataspeak-dot' }),
                h('span', { class: 'dataspeak-dot' }),
              ])
            : null,

          showChips
            ? h('div', { class: 'dataspeak-chips' },
                QUICK_REPLIES.map((q) => h('button', { key: q, class: 'dataspeak-chip', onClick: () => send(q) }, q)))
            : null,

          h('div', { ref: messagesEndRef }),
        ]),

        // Error
        errorMessage
          ? h('div', { class: 'dataspeak-error-banner', role: 'alert' }, [
              h('span', null, errorMessage),
              retryCountdown !== null ? h('span', { class: 'dataspeak-countdown' }, ` (${retryCountdown}s)`) : null,
            ])
          : null,

        // Footer
        h('div', { class: 'dataspeak-footer' }, [
          h('div', { class: 'dataspeak-input-row' }, [
            h('textarea', {
              ref: inputRef,
              class: 'dataspeak-input',
              placeholder: retryCountdown !== null ? `Rate limit active... wait ${retryCountdown}s` : 'Type a message...',
              value: inputValue,
              disabled: retryCountdown !== null,
              rows: 1,
              onInput: (e: any) => setInputValue(e.target.value),
              onKeyDown,
            }),
            isStreaming
              ? h('button', { class: 'dataspeak-stop-btn', onClick: stopStreaming, 'aria-label': 'Stop generation', title: 'Stop generation' },
                  h('svg', { width: '14', height: '14', viewBox: '0 0 24 24', fill: 'currentColor' }, h('rect', { x: '4', y: '4', width: '16', height: '16', rx: '2' })))
              : h('button', { class: 'dataspeak-send-btn', onClick: () => send(), disabled: !inputValue.trim() || retryCountdown !== null, 'aria-label': 'Send message' },
                  icon('M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z', '16', '2.5')),
          ]),
          h('div', { class: 'dataspeak-branding' }, [
            'Powered by ',
            h('a', { href: 'https://dataspeak.ai', target: '_blank', rel: 'noopener noreferrer' }, 'DataSpeakAI'),
          ]),
        ]),
      ]
    ),
  ]);
}
