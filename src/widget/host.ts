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

  // CSSOM setProperty bypasses host CSS resets without style-attribute parsing (strict CSP compliant)
  host.style.setProperty('display', 'block', 'important');
  host.style.setProperty('visibility', 'visible', 'important');
  host.style.setProperty('position', 'fixed', 'important');
  host.style.setProperty('z-index', '2147483647', 'important');
  host.style.setProperty('border', 'none', 'important');
  host.style.setProperty('margin', '0', 'important');
  host.style.setProperty('padding', '0', 'important');
  host.style.setProperty('width', '0', 'important');
  host.style.setProperty('height', '0', 'important');
  host.style.setProperty('overflow', 'visible', 'important');

  const shadowRoot = host.attachShadow({ mode: 'open' });

  let updateStyles: (newTheme: string, newPos: string) => void;

  // Use adoptedStyleSheets with CSSStyleSheet.replaceSync (valid under CSP without style-src 'unsafe-inline')
  if (
    'adoptedStyleSheets' in shadowRoot &&
    typeof CSSStyleSheet !== 'undefined' &&
    'replaceSync' in CSSStyleSheet.prototype
  ) {
    const sheet = new CSSStyleSheet();
    sheet.replaceSync(getWidgetStyles(themeColor, position));
    shadowRoot.adoptedStyleSheets = [sheet];
    updateStyles = (newTheme: string, newPos: string) => {
      sheet.replaceSync(getWidgetStyles(newTheme, newPos));
    };
  } else {
    // Fallback only if adoptedStyleSheets is unsupported in legacy environments
    const styleEl = document.createElement('style');
    styleEl.textContent = getWidgetStyles(themeColor, position);
    shadowRoot.appendChild(styleEl);
    updateStyles = (newTheme: string, newPos: string) => {
      styleEl.textContent = getWidgetStyles(newTheme, newPos);
    };
  }

  const mountContainer = document.createElement('div');
  mountContainer.id = 'dataspeak-widget-app';
  shadowRoot.appendChild(mountContainer);

  document.body.appendChild(host);

  return {
    host,
    shadowRoot,
    mountContainer,
    updateStyles,
  };
}
