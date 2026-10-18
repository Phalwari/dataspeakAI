import { h, ComponentChild } from 'preact';
import { useState, useEffect, useRef } from 'preact/hooks';
import {
  WidgetConfig,
  SessionData,
  SourceCitation,
  getStoredSession,
  createWidgetSession,
  ensureActiveWidgetSession,
  isSessionNearingExpiry,
  clearStoredSession,
  streamWidgetChat,
} from '../api';
import { SafeMarkdown } from '../markdown';

export interface MessageItem {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  sources?: SourceCitation[];
  isStreaming?: boolean;
}

interface WidgetAppProps {
  initialConfig: WidgetConfig;
  onConfigUpdated?: (theme: string, position: string) => void;
}

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
  const abortControllerRef = useRef<AbortController | null>(null);

  // Cleanup active stream on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  // Initialize session & greeting
  useEffect(() => {
    let stored = getStoredSession(config.publicKey);
    if (stored) {
      setSession(stored);
    }

    // Add greeting message
    const greetingText = config.greetingMessage || 'Hello! How can I help you today?';
    setMessages([
      {
        id: 'msg-greeting',
        role: 'assistant',
        text: greetingText,
      },
    ]);
  }, [config.publicKey]);

  // Proactively renew session every 5 minutes if nearing 60-min expiry (at 50 min mark)
  useEffect(() => {
    const checkRenewal = async () => {
      if (session && isSessionNearingExpiry(session)) {
        try {
          const renewed = await ensureActiveWidgetSession(
            config.apiBase,
            config.publicKey,
            session
          );
          setSession(renewed);
        } catch {
          // Gracefully try again on next check
        }
      }
    };
    const interval = setInterval(checkRenewal, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [config.apiBase, config.publicKey, session]);

  // Auto-scroll when messages change or stream updates
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isStreaming]);

  // Focus input when opened; return focus to launcher when closed
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 150);
    } else {
      launcherRef.current?.focus();
    }
  }, [isOpen]);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        setIsOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  // Retry countdown timer
  useEffect(() => {
    if (retryCountdown === null || retryCountdown <= 0) return;
    const timer = setTimeout(() => {
      setRetryCountdown((prev) => (prev && prev > 1 ? prev - 1 : null));
    }, 1000);
    return () => clearTimeout(timer);
  }, [retryCountdown]);

  const handleToggle = () => {
    setIsOpen(!isOpen);
    setErrorMessage(null);
  };

  const handleStopStreaming = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
    setMessages((prev) =>
      prev.map((m, idx) =>
        idx === prev.length - 1 && m.role === 'assistant'
          ? {
              ...m,
              isStreaming: false,
              text: m.text ? m.text + '\n\n*(Generation stopped)*' : '*(Generation cancelled)*',
            }
          : m
      )
    );
  };

  const handleNewChat = async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
    clearStoredSession(config.publicKey);
    setSession(null);
    setMessages([
      {
        id: `msg-greeting-${Date.now()}`,
        role: 'assistant',
        text: config.greetingMessage || 'Hello! How can I help you today?',
      },
    ]);
    setErrorMessage(null);
  };

  const handleSendMessage = async () => {
    const query = inputValue.trim();
    if (!query || isStreaming || retryCountdown !== null) return;

    setInputValue('');
    setErrorMessage(null);

    // 1. Add user message
    const userMsgId = `user-${Date.now()}`;
    const assistantMsgId = `asst-${Date.now()}`;

    setMessages((prev) => [
      ...prev,
      { id: userMsgId, role: 'user', text: query },
      { id: assistantMsgId, role: 'assistant', text: '', isStreaming: true },
    ]);
    setIsStreaming(true);

    const abortCtrl = new AbortController();
    abortControllerRef.current = abortCtrl;

    try {
      // 2. Ensure valid session token (proactively renews at 50 min mark before 60 min expiry)
      const currentSession = await ensureActiveWidgetSession(
        config.apiBase,
        config.publicKey,
        session
      );
      setSession(currentSession);

      // 3. Stream assistant response
      await streamWidgetChat(
        config.apiBase,
        currentSession.sessionToken,
        query,
        currentSession.conversationId,
        (chunk) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsgId ? { ...m, text: m.text + chunk } : m
            )
          );
        },
        (meta) => {
          abortControllerRef.current = null;
          setIsStreaming(false);
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsgId
                ? { ...m, isStreaming: false, sources: meta.sources }
                : m
            )
          );
        },
        (errMsg, retrySec) => {
          abortControllerRef.current = null;
          setIsStreaming(false);
          setErrorMessage(errMsg);
          if (retrySec) {
            setRetryCountdown(retrySec);
          }
          // Remove empty assistant placeholder if failed before stream started
          setMessages((prev) =>
            prev.filter((m) => !(m.id === assistantMsgId && !m.text))
          );
        },
        abortCtrl.signal
      );
    } catch (err: any) {
      abortControllerRef.current = null;
      setIsStreaming(false);
      if (err.name !== 'AbortError' && !abortCtrl.signal.aborted) {
        setErrorMessage(err.message || 'Unable to establish secure connection');
      }
      setMessages((prev) =>
        prev.filter((m) => !(m.id === assistantMsgId && !m.text))
      );
    }
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    h('div', { class: 'dataspeak-container' }, [
      // Launcher Button
      h(
        'button',
        {
          ref: launcherRef,
          class: 'dataspeak-launcher',
          onClick: handleToggle,
          'aria-label': isOpen ? 'Close chat assistant' : 'Open chat assistant',
          'aria-expanded': isOpen,
        },
        isOpen
          ? // Close (X) Icon
            h(
              'svg',
              { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' },
              h('path', { d: 'M18 6L6 18M6 6l12 12' })
            )
          : // Chat Bubble Icon
            h(
              'svg',
              { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' },
              [
                h('path', {
                  d: 'M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z',
                }),
              ]
            )
      ),

      // Chat Window Panel
      h(
        'div',
        {
          class: `dataspeak-panel ${isOpen ? 'open' : ''}`,
          role: 'dialog',
          'aria-modal': 'true',
          'aria-label': config.widgetTitle || 'AI Assistant',
          'aria-hidden': !isOpen ? 'true' : 'false',
        },
        [
          // Header
          h('div', { class: 'dataspeak-header' }, [
            h('div', { class: 'dataspeak-header-left' }, [
              h('div', { class: 'dataspeak-avatar' }, 'AI'),
              h('div', null, [
                h('div', { class: 'dataspeak-header-title' }, config.widgetTitle || 'AI Assistant'),
                h('div', { class: 'dataspeak-header-status' }, [
                  h('span', { class: 'dataspeak-status-dot' }),
                  'Online',
                ]),
              ]),
            ]),
            h('div', { class: 'dataspeak-header-actions' }, [
              // New Chat Button
              h(
                'button',
                {
                  class: 'dataspeak-icon-btn',
                  onClick: handleNewChat,
                  title: 'Start new chat',
                  'aria-label': 'Start new chat',
                },
                h(
                  'svg',
                  { width: '18', height: '18', viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' },
                  h('path', { d: 'M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8M21 3v5h-5M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16M3 21v-5h5' })
                )
              ),
              // Close Panel Button
              h(
                'button',
                {
                  class: 'dataspeak-icon-btn',
                  onClick: () => setIsOpen(false),
                  title: 'Close chat',
                  'aria-label': 'Close chat',
                },
                h(
                  'svg',
                  { width: '18', height: '18', viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' },
                  h('path', { d: 'M18 6L6 18M6 6l12 12' })
                )
              ),
            ]),
          ]),

          // Messages View Area
          h(
            'div',
            { class: 'dataspeak-messages', 'aria-live': 'polite' },
            [
              ...messages.map((m) =>
                h(
                  'div',
                  { key: m.id, class: `dataspeak-msg-row ${m.role}` },
                  [
                    h(
                      'div',
                      { class: 'dataspeak-bubble' },
                      m.role === 'assistant'
                        ? h(SafeMarkdown, { content: m.text })
                        : m.text
                    ),
                    // Source citation badges
                    m.sources && m.sources.length > 0
                      ? h(
                          'div',
                          { class: 'dataspeak-sources' },
                          m.sources.map((src, i) =>
                            h(
                              'span',
                              {
                                key: `src-${i}`,
                                class: `dataspeak-source-badge ${src.grounding_status === 'unverified' ? 'unverified' : ''}`,
                                title: src.grounding_status === 'unverified' ? 'Evidence unverified' : undefined,
                              },
                              `${src.grounding_status === 'unverified' ? '⚠️' : '📄'} ${src.document_name}${src.page_number ? ` (p. ${src.page_number})` : ''}`
                            )
                          )
                        )
                      : null,
                  ]
                )
              ),

              // Typing indicator
              isStreaming && messages[messages.length - 1]?.text === ''
                ? h(
                    'div',
                    { class: 'dataspeak-typing', 'aria-label': 'Assistant is thinking' },
                    [
                      h('span', { class: 'dataspeak-dot' }),
                      h('span', { class: 'dataspeak-dot' }),
                      h('span', { class: 'dataspeak-dot' }),
                    ]
                  )
                : null,

              h('div', { ref: messagesEndRef }),
            ]
          ),

          // Error / Rate Limit Banner
          errorMessage
            ? h('div', { class: 'dataspeak-error-banner' }, [
                h('span', null, errorMessage),
                retryCountdown !== null
                  ? h('span', { class: 'dataspeak-countdown' }, ` (${retryCountdown}s)`)
                  : null,
              ])
            : null,

          // Input Footer
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
                onKeyDown: handleKeyDown,
              }),
              isStreaming
                ? h(
                    'button',
                    {
                      class: 'dataspeak-stop-btn',
                      onClick: handleStopStreaming,
                      'aria-label': 'Stop generation',
                      title: 'Stop generation',
                    },
                    h(
                      'svg',
                      { width: '14', height: '14', viewBox: '0 0 24 24', fill: 'currentColor' },
                      h('rect', { x: '4', y: '4', width: '16', height: '16', rx: '2' })
                    )
                  )
                : h(
                    'button',
                    {
                      class: 'dataspeak-send-btn',
                      onClick: handleSendMessage,
                      disabled: !inputValue.trim() || retryCountdown !== null,
                      'aria-label': 'Send message',
                    },
                    h(
                      'svg',
                      { width: '16', height: '16', viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2.5' },
                      h('path', { d: 'M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z' })
                    )
                  ),
            ]),
            h('div', { class: 'dataspeak-branding' }, [
              'Powered by ',
              h('a', { href: 'https://dataspeak.ai', target: '_blank', rel: 'noopener noreferrer' }, 'DataSpeakAI'),
            ]),
          ]),
        ]
      ),
    ])
  );
}
