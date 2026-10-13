import { getWidgetStyles } from './styles';

export interface WidgetHostInstance {
  host: HTMLDivElement;
  shadowRoot: ShadowRoot;
  mountContainer: HTMLDivElement;
  updateStyles: (themeColor: string, position: string) => void;
}

/**
 * Creates and mounts the Shadow DOM host into the document body.
 * Strictly sets inline `display: block !important` so hostile host CSS rules
 * (such as `div:empty { display: none }`) can never suppress the widget.
 */
export function createWidgetHost(themeColor: string = '#3b82f6', position: string = 'bottom-right'): WidgetHostInstance {
  const host = document.createElement('div');
  host.id = 'dataspeak-chatbot-widget-root';
  // Critical inline styles to bypass host CSS resets and div:empty rules
  host.setAttribute('style', 'display: block !important; visibility: visible !important; position: fixed !important; z-index: 2147483647 !important; border: none !important; margin: 0 !important; padding: 0 !important; width: 0 !important; height: 0 !important; overflow: visible !important;');

  const shadowRoot = host.attachShadow({ mode: 'open' });

  const styleEl = document.createElement('style');
  styleEl.textContent = getWidgetStyles(themeColor, position);
  shadowRoot.appendChild(styleEl);

  const mountContainer = document.createElement('div');
  mountContainer.id = 'dataspeak-widget-app';
  shadowRoot.appendChild(mountContainer);

  document.body.appendChild(host);

  const updateStyles = (newTheme: string, newPos: string) => {
    styleEl.textContent = getWidgetStyles(newTheme, newPos);
  };

  return {
    host,
    shadowRoot,
    mountContainer,
    updateStyles,
  };
}
