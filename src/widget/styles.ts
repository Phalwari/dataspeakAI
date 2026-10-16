export function getWidgetStyles(
  theme: string = '#3b82f6',
  position: string = 'bottom-right'
): string {
  const isLeft = position === 'bottom-left';
  const side = isLeft ? 'left: 20px;' : 'right: 20px;';

  return `
:host {
  all: initial;
  position: fixed;
  visibility: visible !important;
  z-index: 2147483647;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  font-size: 14px;
  line-height: 1.5;
  color-scheme: light dark;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;

  --ds-theme: ${theme};
  --ds-bg: #ffffff;
  --ds-bg-soft: #f6f7fb;
  --ds-text: #111827;
  --ds-text-soft: #6b7280;
  --ds-border: #e5e7eb;
  --ds-bubble-bot: #ffffff;
  --ds-bubble-bot-text: #1f2937;
  --ds-shadow: 0 20px 50px rgba(15, 23, 42, 0.18), 0 4px 12px rgba(15, 23, 42, 0.08);
}

@media (prefers-color-scheme: dark) {
  :host {
    --ds-bg: #111827;
    --ds-bg-soft: #0b1220;
    --ds-text: #f3f4f6;
    --ds-text-soft: #9ca3af;
    --ds-border: #1f2937;
    --ds-bubble-bot: #1f2937;
    --ds-bubble-bot-text: #f3f4f6;
    --ds-shadow: 0 20px 50px rgba(0, 0, 0, 0.6), 0 4px 12px rgba(0, 0, 0, 0.4);
  }
}

.dataspeak-container { visibility: visible !important; }

*, *::before, *::after {
  box-sizing: border-box !important;
  margin: 0;
  padding: 0;
  font-family: inherit;
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}

/* ---------- Launcher ---------- */
.dataspeak-launcher {
  position: fixed;
  bottom: 20px;
  ${side}
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--ds-theme), color-mix(in srgb, var(--ds-theme) 70%, #000));
  color: #fff;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 24px color-mix(in srgb, var(--ds-theme) 45%, transparent), 0 2px 6px rgba(0,0,0,.15);
  transition: transform .25s cubic-bezier(.34,1.56,.64,1), box-shadow .25s ease;
  z-index: 2147483647;
  outline: none;
}
.dataspeak-launcher::after {
  content: "";
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 2px solid var(--ds-theme);
  opacity: 0;
  animation: ds-pulse 2.6s ease-out infinite;
  pointer-events: none;
}
.dataspeak-launcher.is-open::after { animation: none; }
.dataspeak-launcher:hover { transform: scale(1.08) rotate(-4deg); }
.dataspeak-launcher:active { transform: scale(.96); }
.dataspeak-launcher:focus-visible { outline: 3px solid #93c5fd; outline-offset: 3px; }
.dataspeak-launcher svg { width: 26px; height: 26px; }

@keyframes ds-pulse {
  0%   { transform: scale(1);   opacity: .55; }
  70%  { transform: scale(1.45); opacity: 0; }
  100% { transform: scale(1.45); opacity: 0; }
}

/* ---------- Panel ---------- */
.dataspeak-panel {
  position: fixed;
  bottom: 92px;
  ${side}
  width: 384px;
  max-width: calc(100vw - 32px);
  height: 600px;
  max-height: calc(100dvh - 116px);
  background: var(--ds-bg);
  color: var(--ds-text);
  border-radius: 20px;
  box-shadow: var(--ds-shadow);
  border: 1px solid var(--ds-border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  z-index: 2147483647;
  opacity: 0;
  visibility: hidden;
  transform: translateY(20px) scale(.96);
  transform-origin: ${isLeft ? 'bottom left' : 'bottom right'};
  pointer-events: none;
  transition: opacity .25s ease, transform .3s cubic-bezier(.16,1,.3,1), visibility .25s;
}
.dataspeak-panel.open {
  opacity: 1;
  visibility: visible;
  transform: translateY(0) scale(1);
  pointer-events: auto;
}

@media (max-width: 480px) {
  .dataspeak-panel {
    inset: 0 !important;
    width: 100% !important;
    height: 100dvh !important;
    max-width: 100% !important;
    max-height: 100dvh !important;
    border-radius: 0 !important;
    border: none !important;
  }
}

/* ---------- Header ---------- */
.dataspeak-header {
  padding: 16px 16px 16px 18px;
  background: linear-gradient(135deg, var(--ds-theme), color-mix(in srgb, var(--ds-theme) 65%, #000));
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  position: relative;
}
.dataspeak-header::after {
  content: "";
  position: absolute;
  inset: auto 0 0 0;
  height: 1px;
  background: rgba(255,255,255,.18);
}
.dataspeak-header-left { display: flex; align-items: center; gap: 12px; }
.dataspeak-avatar {
  width: 38px; height: 38px;
  border-radius: 12px;
  background: rgba(255,255,255,.2);
  backdrop-filter: blur(6px);
  border: 1px solid rgba(255,255,255,.28);
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 13px; letter-spacing: .5px;
}
.dataspeak-header-title { font-weight: 650; font-size: 15.5px; line-height: 1.2; }
.dataspeak-header-status {
  font-size: 11.5px; opacity: .92;
  display: flex; align-items: center; gap: 5px; margin-top: 2px;
}
.dataspeak-status-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: #34d399;
  box-shadow: 0 0 0 0 rgba(52,211,153,.7);
  animation: ds-online 2s infinite;
}
@keyframes ds-online {
  0% { box-shadow: 0 0 0 0 rgba(52,211,153,.6); }
  70% { box-shadow: 0 0 0 6px rgba(52,211,153,0); }
  100% { box-shadow: 0 0 0 0 rgba(52,211,153,0); }
}
.dataspeak-header-actions { display: flex; gap: 2px; }
.dataspeak-icon-btn {
  background: transparent; border: none; color: #fff; cursor: pointer;
  padding: 8px; border-radius: 10px; display: flex;
  align-items: center; justify-content: center;
  opacity: .85; transition: opacity .15s, background-color .15s, transform .15s;
}
.dataspeak-icon-btn:hover { opacity: 1; background: rgba(255,255,255,.18); }
.dataspeak-icon-btn:active { transform: scale(.92); }
.dataspeak-icon-btn:focus-visible { outline: 2px solid #fff; outline-offset: 1px; }

/* ---------- Messages ---------- */
.dataspeak-messages {
  flex: 1;
  overflow-y: auto;
  padding: 18px 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  background: var(--ds-bg-soft);
  scroll-behavior: smooth;
}
.dataspeak-messages::-webkit-scrollbar { width: 6px; }
.dataspeak-messages::-webkit-scrollbar-thumb { background: var(--ds-border); border-radius: 3px; }
.dataspeak-messages::-webkit-scrollbar-thumb:hover { background: var(--ds-text-soft); }

.dataspeak-msg-row {
  display: flex; flex-direction: column; max-width: 86%;
  animation: ds-in .28s cubic-bezier(.16,1,.3,1) both;
}
@keyframes ds-in {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
.dataspeak-msg-row.user { align-self: flex-end; align-items: flex-end; }
.dataspeak-msg-row.assistant { align-self: flex-start; align-items: flex-start; }

.dataspeak-bubble {
  padding: 11px 15px;
  font-size: 13.8px;
  line-height: 1.5;
  word-break: break-word;
  overflow-wrap: anywhere;
}
.dataspeak-msg-row.user .dataspeak-bubble {
  background: linear-gradient(135deg, var(--ds-theme), color-mix(in srgb, var(--ds-theme) 78%, #000));
  color: #fff;
  border-radius: 18px 18px 4px 18px;
  box-shadow: 0 3px 10px color-mix(in srgb, var(--ds-theme) 30%, transparent);
}
.dataspeak-msg-row.assistant .dataspeak-bubble {
  background: var(--ds-bubble-bot);
  color: var(--ds-bubble-bot-text);
  border: 1px solid var(--ds-border);
  border-radius: 18px 18px 18px 4px;
  box-shadow: 0 1px 3px rgba(0,0,0,.05);
}

.dataspeak-time {
  font-size: 10.5px; color: var(--ds-text-soft);
  margin-top: 4px; padding: 0 4px;
}

/* ---------- Sources ---------- */
.dataspeak-sources { margin-top: 7px; display: flex; flex-wrap: wrap; gap: 5px; }
.dataspeak-source-badge {
  font-size: 11px; font-weight: 500;
  background: color-mix(in srgb, var(--ds-theme) 12%, transparent);
  color: var(--ds-theme);
  padding: 3px 8px; border-radius: 999px;
  display: inline-flex; align-items: center; gap: 3px;
  border: 1px solid color-mix(in srgb, var(--ds-theme) 25%, transparent);
}

/* ---------- Quick replies ---------- */
.dataspeak-chips { display: flex; flex-wrap: wrap; gap: 7px; margin-top: 4px; }
.dataspeak-chip {
  background: var(--ds-bg);
  color: var(--ds-theme);
  border: 1px solid color-mix(in srgb, var(--ds-theme) 40%, transparent);
  padding: 7px 13px; border-radius: 999px;
  font-size: 12.5px; font-weight: 500; cursor: pointer;
  transition: all .18s ease;
}
.dataspeak-chip:hover {
  background: var(--ds-theme); color: #fff;
  transform: translateY(-1px);
  box-shadow: 0 4px 10px color-mix(in srgb, var(--ds-theme) 35%, transparent);
}

/* ---------- Typing ---------- */
.dataspeak-typing {
  display: flex; align-items: center; gap: 5px;
  padding: 12px 15px; background: var(--ds-bubble-bot);
  border: 1px solid var(--ds-border);
  border-radius: 18px 18px 18px 4px; width: fit-content;
}
.dataspeak-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--ds-text-soft);
  animation: ds-bounce 1.3s infinite ease-in-out both;
}
.dataspeak-dot:nth-child(1) { animation-delay: -.3s; }
.dataspeak-dot:nth-child(2) { animation-delay: -.15s; }
@keyframes ds-bounce {
  0%, 80%, 100% { transform: translateY(0); opacity: .4; }
  40% { transform: translateY(-5px); opacity: 1; }
}

/* ---------- Error ---------- */
.dataspeak-error-banner {
  padding: 9px 14px;
  background: #fef2f2; color: #b91c1c;
  border-top: 1px solid #fecaca;
  font-size: 12px;
  display: flex; align-items: center; justify-content: space-between;
  animation: ds-in .2s ease both;
}
.dataspeak-countdown { font-weight: 700; }

/* ---------- Footer ---------- */
.dataspeak-footer {
  padding: 12px 14px 10px;
  background: var(--ds-bg);
  border-top: 1px solid var(--ds-border);
  flex-shrink: 0;
}
.dataspeak-input-row { display: flex; align-items: flex-end; gap: 8px; }
.dataspeak-input {
  flex: 1;
  border: 1.5px solid var(--ds-border);
  border-radius: 22px;
  padding: 9px 16px;
  font-size: 13.8px; line-height: 1.4;
  outline: none; resize: none;
  max-height: 110px; min-height: 40px;
  color: var(--ds-text);
  background: var(--ds-bg-soft);
  transition: border-color .15s, box-shadow .15s, background .15s;
}
.dataspeak-input::placeholder { color: var(--ds-text-soft); }
.dataspeak-input:focus {
  border-color: var(--ds-theme);
  background: var(--ds-bg);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--ds-theme) 18%, transparent);
}
.dataspeak-input:disabled { opacity: .6; cursor: not-allowed; }

.dataspeak-send-btn, .dataspeak-stop-btn {
  width: 40px; height: 40px; border-radius: 50%;
  color: #fff; border: none; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  transition: transform .15s, opacity .15s, box-shadow .15s;
}
.dataspeak-send-btn {
  background: linear-gradient(135deg, var(--ds-theme), color-mix(in srgb, var(--ds-theme) 70%, #000));
  box-shadow: 0 4px 12px color-mix(in srgb, var(--ds-theme) 35%, transparent);
}
.dataspeak-send-btn:disabled { opacity: .4; cursor: not-allowed; box-shadow: none; }
.dataspeak-send-btn:not(:disabled):hover { transform: scale(1.08); }
.dataspeak-send-btn:not(:disabled):active { transform: scale(.94); }
.dataspeak-stop-btn { background: #ef4444; box-shadow: 0 4px 12px rgba(239,68,68,.35); }
.dataspeak-stop-btn:hover { background: #dc2626; transform: scale(1.08); }

.dataspeak-branding {
  text-align: center; font-size: 10.5px;
  color: var(--ds-text-soft); margin-top: 8px;
}
.dataspeak-branding a { color: var(--ds-text-soft); text-decoration: none; font-weight: 600; }
.dataspeak-branding a:hover { color: var(--ds-theme); }

/* ---------- Markdown ---------- */
.dataspeak-bubble p { margin-bottom: 8px; }
.dataspeak-bubble p:last-child { margin-bottom: 0; }
.dataspeak-bubble strong { font-weight: 650; }
.dataspeak-bubble em { font-style: italic; }
.dataspeak-bubble h1, .dataspeak-bubble h2, .dataspeak-bubble h3 {
  font-size: 14.5px; font-weight: 650; margin: 8px 0 4px;
}
.dataspeak-bubble code {
  background: color-mix(in srgb, var(--ds-text) 8%, transparent);
  padding: 2px 5px; border-radius: 4px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px;
}
.dataspeak-bubble pre {
  background: #0f172a; color: #e2e8f0;
  padding: 10px 12px; border-radius: 10px;
  overflow-x: auto; margin: 6px 0; font-size: 12px;
}
.dataspeak-bubble pre code { background: none; padding: 0; color: inherit; }
.dataspeak-bubble a { color: var(--ds-theme); text-decoration: underline; word-break: break-all; }
.dataspeak-bubble ul, .dataspeak-bubble ol { margin: 4px 0 8px 20px; }
.dataspeak-bubble li { margin-bottom: 3px; }
`;
}
