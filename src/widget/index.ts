import { h, render } from 'preact';
import { WidgetConfig, fetchWidgetConfig } from './api';
import { createWidgetHost } from './host';
import { WidgetApp } from './ui/WidgetApp';

/**
 * Synchronously capture script element and data attributes at module evaluation time.
 * document.currentScript is null if deferred or accessed later!
 */
const currentScript = (document.currentScript as HTMLScriptElement) || null;

interface ParsedScriptResult {
  config: WidgetConfig;
  hasExplicitTheme: boolean;
  hasExplicitTitle: boolean;
  hasExplicitGreeting: boolean;
  hasExplicitPosition: boolean;
}

function parseScriptConfig(): ParsedScriptResult {
  let publicKey = '';
  let apiBase = window.location.origin;
  let themeColor = '#3b82f6';
  let widgetTitle = 'AI Assistant';
  let greetingMessage = 'Hello! How can I help you today?';
  let position = 'bottom-right';
  let welcomeDelay = 1;
  let soundEnabled = false;

  let hasExplicitTheme = false;
  let hasExplicitTitle = false;
  let hasExplicitGreeting = false;
  let hasExplicitPosition = false;

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
      hasExplicitTheme = true;
    }
    if (currentScript.getAttribute('data-title')) {
      widgetTitle = currentScript.getAttribute('data-title')!;
      hasExplicitTitle = true;
    }
    if (currentScript.getAttribute('data-position')) {
      position = currentScript.getAttribute('data-position')!;
      hasExplicitPosition = true;
    }
    if (currentScript.getAttribute('data-welcome')) {
      greetingMessage = currentScript.getAttribute('data-welcome')!;
      hasExplicitGreeting = true;
    }
  }

  return {
    config: {
      publicKey,
      apiBase,
      themeColor,
      widgetTitle,
      greetingMessage,
      position,
      welcomeDelay,
      soundEnabled,
    },
    hasExplicitTheme,
    hasExplicitTitle,
    hasExplicitGreeting,
    hasExplicitPosition,
  };
}

// Top-level bootstrap
export function initWidget(overrideConfig?: Partial<WidgetConfig>) {
  const {
    config: baseConfig,
    hasExplicitTheme,
    hasExplicitTitle,
    hasExplicitGreeting,
    hasExplicitPosition,
  } = parseScriptConfig();

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
      // Script attribute or explicit JS override takes precedence over server database config;
      // otherwise server database config takes precedence over hardcoded fallback defaults.
      const resolvedTheme = overrideConfig?.themeColor || (hasExplicitTheme ? config.themeColor : (serverCfg.themeColor || config.themeColor || '#3b82f6'));
      const resolvedPos = overrideConfig?.position || (hasExplicitPosition ? config.position : (serverCfg.position || config.position || 'bottom-right'));
      const resolvedTitle = overrideConfig?.widgetTitle || (hasExplicitTitle ? config.widgetTitle : (serverCfg.widgetTitle || config.widgetTitle || 'AI Assistant'));
      const resolvedGreeting = overrideConfig?.greetingMessage || (hasExplicitGreeting ? config.greetingMessage : (serverCfg.greetingMessage || config.greetingMessage || 'Hello! How can I help you today?'));
      const resolvedSound = overrideConfig?.soundEnabled ?? (serverCfg.soundEnabled ?? config.soundEnabled);
      const resolvedDelay = overrideConfig?.welcomeDelay ?? (serverCfg.welcomeDelay ?? config.welcomeDelay);

      // Re-apply styles with resolved theme and position
      hostInstance.updateStyles(resolvedTheme, resolvedPos);

      // Re-render Preact app with updated server branding
      const updatedConfig: WidgetConfig = {
        ...config,
        themeColor: resolvedTheme,
        position: resolvedPos,
        widgetTitle: resolvedTitle,
        greetingMessage: resolvedGreeting,
        soundEnabled: resolvedSound,
        welcomeDelay: resolvedDelay,
      };
      render(h(WidgetApp, { initialConfig: updatedConfig }), hostInstance.mountContainer);
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
