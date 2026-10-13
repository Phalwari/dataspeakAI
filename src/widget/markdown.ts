import { h, VNode } from 'preact';

/**
 * Validates link URL to only allow strict http: or https: schemes.
 * Rejects javascript:, data:, vbscript:, and relative malicious protocols.
 */
function isSafeUrl(url: string): boolean {
  try {
    const parsed = new URL(url, 'https://dummy-base-domain.internal');
    return parsed.protocol === 'http:' || parsed.protocol === 'https:';
  } catch {
    return false;
  }
}

/**
 * Tokenizes and parses inline text into safe Preact VNodes without ever touching innerHTML.
 */
function parseInline(text: string): (string | VNode)[] {
  const elements: (string | VNode)[] = [];
  let remaining = text;
  let keyIndex = 0;

  while (remaining.length > 0) {
    // 1. Markdown Links [text](url)
    const linkMatch = remaining.match(/^\[([^\]]+)\]\(([^)]+)\)/);
    if (linkMatch) {
      const linkText = linkMatch[1];
      const linkHref = linkMatch[2].trim();
      if (isSafeUrl(linkHref)) {
        elements.push(
          h(
            'a',
            {
              key: `lnk-${keyIndex++}`,
              href: linkHref,
              target: '_blank',
              rel: 'noopener noreferrer',
            },
            linkText
          )
        );
      } else {
        elements.push(linkText);
      }
      remaining = remaining.slice(linkMatch[0].length);
      continue;
    }

    // 2. Bold text **text** or __text__
    const boldMatch = remaining.match(/^(\*\*|__)(.*?)\1/);
    if (boldMatch && boldMatch[2]) {
      elements.push(
        h('strong', { key: `b-${keyIndex++}` }, parseInline(boldMatch[2]))
      );
      remaining = remaining.slice(boldMatch[0].length);
      continue;
    }

    // 3. Inline code `text`
    const codeMatch = remaining.match(/^`([^`]+)`/);
    if (codeMatch && codeMatch[1]) {
      elements.push(
        h('code', { key: `code-${keyIndex++}` }, codeMatch[1])
      );
      remaining = remaining.slice(codeMatch[0].length);
      continue;
    }

    // 4. Italic text *text* or _text_
    const italicMatch = remaining.match(/^(\*|_)(.*?)\1/);
    if (italicMatch && italicMatch[2]) {
      elements.push(
        h('em', { key: `em-${keyIndex++}` }, parseInline(italicMatch[2]))
      );
      remaining = remaining.slice(italicMatch[0].length);
      continue;
    }

    // 5. Source Citations [Source: filename]
    const citationMatch = remaining.match(/^\[Source:\s*([^\]]+)\]/);
    if (citationMatch && citationMatch[1]) {
      elements.push(
        h(
          'span',
          { key: `cit-${keyIndex++}`, class: 'dataspeak-source-badge' },
          `📄 ${citationMatch[1]}`
        )
      );
      remaining = remaining.slice(citationMatch[0].length);
      continue;
    }

    // Regular character consumption
    const nextSpecial = remaining.search(/(\[|\*\*|__|`|\*|_)/);
    if (nextSpecial === -1) {
      elements.push(remaining);
      break;
    } else if (nextSpecial === 0) {
      elements.push(remaining[0]);
      remaining = remaining.slice(1);
    } else {
      elements.push(remaining.slice(0, nextSpecial));
      remaining = remaining.slice(nextSpecial);
    }
  }

  return elements;
}

/**
 * Safe, zero-innerHTML markdown renderer component for untrusted LLM assistant messages.
 */
export function SafeMarkdown({ content }: { content: string }): VNode {
  if (!content) {
    return h('span', null, '');
  }

  const lines = content.split('\n');
  const blocks: VNode[] = [];
  let currentListItems: VNode[] = [];
  let blockIndex = 0;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    // List item (- or *)
    const listMatch = trimmed.match(/^[-*]\s+(.*)$/);
    if (listMatch) {
      currentListItems.push(
        h('li', { key: `li-${blockIndex}-${currentListItems.length}` }, parseInline(listMatch[1]))
      );
      continue;
    }

    // If previous lines were a list and current line is not
    if (currentListItems.length > 0) {
      blocks.push(h('ul', { key: `ul-${blockIndex++}` }, currentListItems));
      currentListItems = [];
    }

    if (trimmed.length === 0) {
      continue;
    }

    // Standard paragraph
    blocks.push(h('p', { key: `p-${blockIndex++}` }, parseInline(line)));
  }

  if (currentListItems.length > 0) {
    blocks.push(h('ul', { key: `ul-${blockIndex++}` }, currentListItems));
  }

  return h('div', { class: 'dataspeak-markdown-body' }, blocks);
}
