import { h, render } from 'preact';
import { WidgetConfig, fetchWidgetConfig } from './api';
import { createWidgetHost } from './host';
import { WidgetApp } from './ui/WidgetApp';

/**
 * Synchronously capture script element and data attributes at module evaluation time.
 * document.currentScript is null if deferred or accessed later!
 */
const currentScript = (document.currentScript as HTMLScriptElement) || null;

function parseScriptConfig(): WidgetConfig {
  let publicKey = '';
  let apiBase = window.location.origin;
  let themeColor = '#3b82f6';
  let widgetTitle = 'AI Assistant';
  let greetingMessage = 'Hello! How can I help you today?';
  let position = 'bottom-right';
  let welcomeDelay = 1;
  let soundEnabled = false;

  if (currentScript) {
    publicKey = currentScript.getAttribute('data-key') || '';
    const scriptSrc = currentScript.src;
    if (scriptSrc) {
      try {
        apiBase = new URL(scriptSrc).origin;
      } catch {
        // Fallback to location origin
      }
    }
    const apiAttr = currentScript.getAttribute('data-api');
    if (apiAttr) {
      apiBase = apiAttr;
    }

    if (currentScript.getAttribute('data-theme')) {
      themeColor = currentScript.getAttribute('data-theme')!;
    }
    if (currentScript.getAttribute('data-title')) {
      widgetTitle = currentScript.getAttribute('data-title')!;
    }
    if (currentScript.getAttribute('data-position')) {
      position = currentScript.getAttribute('data-position')!;
    }
    if (currentScript.getAttribute('data-welcome')) {
      greetingMessage = currentScript.getAttribute('data-welcome')!;
    }
  }

  return {
    publicKey,
    apiBase,
    themeColor,
    widgetTitle,
    greetingMessage,
    position,
    welcomeDelay,
    soundEnabled,
  };
}

// Top-level bootstrap
export function initWidget(overrideConfig?: Partial<WidgetConfig>) {
  const baseConfig = parseScriptConfig();
  const config: WidgetConfig = {
    ...baseConfig,
    ...overrideConfig,
  };

  if (!config.publicKey) {
    console.warn('[DataSpeakAI] Missing data-key on widget script. Widget initialization aborted.');
    return;
  }

  // Prevent multiple mountings
  if (document.getElementById('dataspeak-chatbot-widget-root')) {
    return;
  }

  const hostInstance = createWidgetHost(config.themeColor, config.position);

  // Mount UI immediately
  render(h(WidgetApp, { initialConfig: config }), hostInstance.mountContainer);

  // Asynchronously enrich with server branding config
  fetchWidgetConfig(config.apiBase, config.publicKey)
    .then((serverCfg) => {
      if (serverCfg.themeColor || serverCfg.position) {
        const updatedTheme = config.themeColor || serverCfg.themeColor || '#3b82f6';
        const updatedPos = config.position || serverCfg.position || 'bottom-right';
        hostInstance.updateStyles(updatedTheme, updatedPos);
      }
    })
    .catch(() => {
      // Offline / network failure graceful fallback
    });

  return hostInstance;
}

// Auto-initialize when loaded via <script> tag
if (typeof window !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => initWidget());
  } else {
    initWidget();
  }

  // Expose global API
  (window as any).DataSpeakAI = {
    init: initWidget,
    version: '1.0.0',
  };
}
