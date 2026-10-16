import { h, ComponentChild } from 'preact';

function isSafeUrl(url: string): boolean {
  try {
    const u = new URL(url, 'https://dummy-base-domain.internal');
    return u.protocol === 'http:' || u.protocol === 'https:';
  } catch {
    return false;
  }
}

function parseInline(text: string): ComponentChild[] {
  const out: ComponentChild[] = [];
  let rest = text;
  let k = 0;

  while (rest.length > 0) {
    const link = rest.match(/^\[([^\]]+)\]\(([^)]+)\)/);
    if (link) {
      const url = link[2].trim();
      out.push(
        isSafeUrl(url)
          ? h('a', { key: `l${k++}`, href: url, target: '_blank', rel: 'noopener noreferrer' }, link[1])
          : link[1]
      );
      rest = rest.slice(link[0].length);
      continue;
    }

    const cite = rest.match(/^\[Source:\s*([^\]]+)\]/);
    if (cite) {
      out.push(h('span', { key: `c${k++}`, class: 'dataspeak-source-badge' }, `📄 ${cite[1]}`));
      rest = rest.slice(cite[0].length);
      continue;
    }

    const bold = rest.match(/^(\*\*|__)(.+?)\1/);
    if (bold) {
      out.push(h('strong', { key: `b${k++}` }, parseInline(bold[2])));
      rest = rest.slice(bold[0].length);
      continue;
    }

    const code = rest.match(/^`([^`]+)`/);
    if (code) {
      out.push(h('code', { key: `k${k++}` }, code[1]));
      rest = rest.slice(code[0].length);
      continue;
    }

    const em = rest.match(/^(\*|_)(.+?)\1/);
    if (em) {
      out.push(h('em', { key: `e${k++}` }, parseInline(em[2])));
      rest = rest.slice(em[0].length);
      continue;
    }

    const next = rest.slice(1).search(/(\[|\*\*|__|`|\*|_)/);
    if (next === -1) {
      out.push(rest);
      break;
    }
    out.push(rest.slice(0, next + 1));
    rest = rest.slice(next + 1);
  }
  return out;
}

export function SafeMarkdown({ content }: { content: string }): ComponentChild {
  if (!content) return h('span', null, '');

  const lines = content.split('\n');
  const blocks: ComponentChild[] = [];
  let ul: ComponentChild[] = [];
  let ol: ComponentChild[] = [];
  let codeBuf: string[] | null = null;
  let k = 0;

  const flushLists = () => {
    if (ul.length) { blocks.push(h('ul', { key: `ul${k++}` }, ul)); ul = []; }
    if (ol.length) { blocks.push(h('ol', { key: `ol${k++}` }, ol)); ol = []; }
  };

  for (const raw of lines) {
    const line = raw.trim();

    // fenced code block
    if (line.startsWith('```')) {
      if (codeBuf === null) {
        flushLists();
        codeBuf = [];
      } else {
        blocks.push(h('pre', { key: `pre${k++}` }, h('code', null, codeBuf.join('\n'))));
        codeBuf = null;
      }
      continue;
    }
    if (codeBuf !== null) { codeBuf.push(raw); continue; }

    const bullet = line.match(/^[-*]\s+(.*)$/);
    if (bullet) {
      if (ol.length) flushLists();
      ul.push(h('li', { key: `li${k++}` }, parseInline(bullet[1])));
      continue;
    }

    const numbered = line.match(/^\d+[.)]\s+(.*)$/);
    if (numbered) {
      if (ul.length) flushLists();
      ol.push(h('li', { key: `li${k++}` }, parseInline(numbered[1])));
      continue;
    }

    flushLists();
    if (!line) continue;

    const heading = line.match(/^(#{1,3})\s+(.*)$/);
    if (heading) {
      blocks.push(h(`h${heading[1].length}`, { key: `h${k++}` }, parseInline(heading[2])));
      continue;
    }

    blocks.push(h('p', { key: `p${k++}` }, parseInline(raw)));
  }

  if (codeBuf !== null) {
    blocks.push(h('pre', { key: `pre${k++}` }, h('code', null, codeBuf.join('\n'))));
  }
  flushLists();

  return h('div', { class: 'dataspeak-markdown-body' }, blocks);
}
