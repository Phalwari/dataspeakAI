export function getWidgetStyles(themeColor: string = "#3b82f6", position: string = "bottom-right"): string {
  const isLeft = position === "bottom-left";
  const posCss = isLeft
    ? "bottom: 20px; left: 20px;"
    : "bottom: 20px; right: 20px;";

  const panelPosCss = isLeft
    ? "bottom: 84px; left: 20px;"
    : "bottom: 84px; right: 20px;";

  return `
:host {
  all: initial;
  position: fixed;
  visibility: visible !important;
  z-index: 2147483647;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  font-size: 14px;
  line-height: 1.5;
  letter-spacing: normal;
  text-align: left;
  color: #111827;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.dataspeak-container {
  visibility: visible !important;
}

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

.dataspeak-launcher {
  position: fixed;
  ${posCss}
  width: 56px;
  height: 56px;
  border-radius: 28px;
  background-color: ${themeColor};
  color: #ffffff;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.2), 0 2px 4px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.2s ease;
  z-index: 2147483647;
  outline: none;
}

.dataspeak-launcher:hover {
  transform: scale(1.06);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.25);
}

.dataspeak-launcher:focus-visible {
  outline: 3px solid #93c5fd;
  outline-offset: 2px;
}

.dataspeak-launcher svg {
  width: 26px;
  height: 26px;
  fill: currentColor;
  transition: transform 0.2s ease;
}

.dataspeak-panel {
  position: fixed;
  ${panelPosCss}
  width: 380px;
  max-width: calc(100vw - 32px);
  height: 580px;
  max-height: calc(100dvh - 100px);
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 12px 36px rgba(0, 0, 0, 0.16), 0 2px 8px rgba(0, 0, 0, 0.06);
  border: 1px solid rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  z-index: 2147483647;
  opacity: 0;
  visibility: hidden;
  transform: translateY(16px) scale(0.97);
  pointer-events: none;
  transition: opacity 0.22s ease, transform 0.22s cubic-bezier(0.16, 1, 0.3, 1), visibility 0.22s;
}

.dataspeak-panel.open {
  opacity: 1;
  visibility: visible;
  transform: translateY(0) scale(1);
  pointer-events: auto;
}

@media (max-width: 480px) {
  .dataspeak-panel {
    top: 0 !important;
    bottom: 0 !important;
    left: 0 !important;
    right: 0 !important;
    width: 100vw !important;
    height: 100dvh !important;
    max-width: 100vw !important;
    max-height: 100dvh !important;
    border-radius: 0 !important;
    border: none !important;
  }
  .dataspeak-launcher {
    ${posCss}
  }
}

.dataspeak-header {
  padding: 14px 16px;
  background-color: ${themeColor};
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.dataspeak-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.dataspeak-avatar {
  width: 32px;
  height: 32px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.22);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 14px;
}

.dataspeak-header-title {
  font-weight: 600;
  font-size: 15px;
  line-height: 1.2;
}

.dataspeak-header-status {
  font-size: 11px;
  opacity: 0.88;
  display: flex;
  align-items: center;
  gap: 4px;
}

.dataspeak-status-dot {
  width: 6px;
  height: 6px;
  border-radius: 3px;
  background-color: #34d399;
}

.dataspeak-header-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.dataspeak-icon-btn {
  background: transparent;
  border: none;
  color: #ffffff;
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0.88;
  transition: opacity 0.15s, background-color 0.15s;
}

.dataspeak-icon-btn:hover {
  opacity: 1;
  background-color: rgba(255, 255, 255, 0.18);
}

.dataspeak-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: #f9fafb;
}

.dataspeak-msg-row {
  display: flex;
  flex-direction: column;
  max-width: 85%;
}

.dataspeak-msg-row.user {
  align-self: flex-end;
  align-items: flex-end;
}

.dataspeak-msg-row.assistant {
  align-self: flex-start;
  align-items: flex-start;
}

.dataspeak-bubble {
  padding: 10px 14px;
  font-size: 13.5px;
  line-height: 1.45;
  word-break: break-word;
}

.dataspeak-msg-row.user .dataspeak-bubble {
  background-color: ${themeColor};
  color: #ffffff;
  border-radius: 14px 14px 2px 14px;
}

.dataspeak-msg-row.assistant .dataspeak-bubble {
  background-color: #ffffff;
  color: #1f2937;
  border: 1px solid #e5e7eb;
  border-radius: 14px 14px 14px 2px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

.dataspeak-sources {
  margin-top: 6px;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.dataspeak-source-badge {
  font-size: 11px;
  background: #eef2ff;
  color: #4338ca;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 3px;
}

.dataspeak-typing {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 10px 14px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 14px 14px 14px 2px;
  width: fit-content;
}

.dataspeak-dot {
  width: 6px;
  height: 6px;
  border-radius: 3px;
  background-color: #9ca3af;
  animation: dataspeak-bounce 1.4s infinite ease-in-out both;
}

.dataspeak-dot:nth-child(1) { animation-delay: -0.32s; }
.dataspeak-dot:nth-child(2) { animation-delay: -0.16s; }

@keyframes dataspeak-bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

.dataspeak-error-banner {
  margin: 8px 16px;
  padding: 8px 12px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
  border-radius: 8px;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.dataspeak-footer {
  padding: 12px 14px;
  background: #ffffff;
  border-top: 1px solid #e5e7eb;
  flex-shrink: 0;
}

.dataspeak-input-row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}

.dataspeak-input {
  flex: 1;
  border: 1px solid #d1d5db;
  border-radius: 20px;
  padding: 8px 14px;
  font-size: 13.5px;
  line-height: 1.4;
  outline: none;
  resize: none;
  max-height: 96px;
  min-height: 38px;
  color: #111827;
  background: #ffffff;
  font-family: inherit;
  transition: border-color 0.15s;
}

.dataspeak-input:focus {
  border-color: ${themeColor};
}

.dataspeak-send-btn {
  width: 36px;
  height: 36px;
  border-radius: 18px;
  background-color: ${themeColor};
  color: #ffffff;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: opacity 0.15s, transform 0.15s;
}

.dataspeak-send-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  transform: none;
}

.dataspeak-send-btn:not(:disabled):hover {
  transform: scale(1.05);
}

.dataspeak-branding {
  text-align: center;
  font-size: 11px;
  color: #9ca3af;
  margin-top: 6px;
}

.dataspeak-branding a {
  color: #6b7280;
  text-decoration: none;
  font-weight: 500;
}

/* Markdown styling inside assistant bubble */
.dataspeak-bubble p {
  margin-bottom: 6px;
}
.dataspeak-bubble p:last-child {
  margin-bottom: 0;
}
.dataspeak-bubble strong {
  font-weight: 600;
}
.dataspeak-bubble em {
  font-style: italic;
}
.dataspeak-bubble code {
  background: #f3f4f6;
  padding: 2px 4px;
  border-radius: 3px;
  font-family: monospace;
  font-size: 12px;
}
.dataspeak-bubble a {
  color: ${themeColor};
  text-decoration: underline;
  word-break: break-all;
}
.dataspeak-bubble ul, .dataspeak-bubble ol {
  margin-left: 18px;
  margin-bottom: 6px;
}

.dataspeak-error-banner {
  background-color: #fee2e2;
  color: #991b1b;
  font-size: 12px;
  padding: 6px 12px;
  border-top: 1px solid #fecaca;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.dataspeak-countdown {
  font-weight: 600;
}
`;
}
