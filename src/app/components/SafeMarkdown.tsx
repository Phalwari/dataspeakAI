import React, { useState } from "react";
import { Copy, Check, ExternalLink } from "lucide-react";

interface SafeMarkdownProps {
  content: string;
  className?: string;
  onCitationClick?: (citationText: string) => void;
}

/**
 * Renders inline text formatting (bold, italic, inline code, and source badges).
 */
export function formatInlineText(
  text: string,
  onCitationClick?: (citationText: string) => void
): React.ReactNode[] {
  if (!text) return [];

  // Match tokens: code `...`, bold **...**, italic *...*, citation [Source: ...], safe link [Text](url)
  const tokenRegex = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*|\[(?:source|Source):\s*[^\]]+\]|\[[^\]]+\]\((?:https?:\/\/|\/)[^\s\)]+\))/gi;
  const parts = text.split(tokenRegex);

  return parts.map((part, idx) => {
    if (!part) return null;

    // Inline Code
    if (part.startsWith("`") && part.endsWith("`") && part.length >= 2) {
      return (
        <code
          key={idx}
          className="px-1.5 py-0.5 rounded bg-gray-100 text-indigo-700 font-mono text-[11px] border border-gray-200/80"
        >
          {part.slice(1, -1)}
        </code>
      );
    }

    // Bold
    if (part.startsWith("**") && part.endsWith("**") && part.length >= 4) {
      return (
        <strong key={idx} className="font-semibold text-gray-900">
          {formatInlineText(part.slice(2, -2), onCitationClick)}
        </strong>
      );
    }

    // Italic
    if (part.startsWith("*") && part.endsWith("*") && part.length >= 2) {
      return (
        <em key={idx} className="italic text-gray-800">
          {formatInlineText(part.slice(1, -1), onCitationClick)}
        </em>
      );
    }

    // Source Citation Badge: [Source: filename.pdf, p. 3] or [source: filename.pdf]
    if (/^\[source:\s*[^\]]+\]$/i.test(part)) {
      const citeContent = part.slice(1, -1).trim();
      return (
        <span
          key={idx}
          onClick={() => onCitationClick && onCitationClick(citeContent)}
          className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 mx-0.5 text-[10px] font-medium rounded bg-emerald-50 text-emerald-800 border border-emerald-200/80 ${
            onCitationClick ? "cursor-pointer hover:bg-emerald-100 hover:text-emerald-900" : ""
          }`}
          title="Grounded document reference"
        >
          {citeContent}
        </span>
      );
    }

    // Safe Markdown Link: [Title](url)
    const linkMatch = part.match(/^\[([^\]]+)\]\(((?:https?:\/\/|\/)[^\s\)]+)\)$/);
    if (linkMatch) {
      const linkText = linkMatch[1];
      const linkUrl = linkMatch[2];
      const isExternal = linkUrl.startsWith("http://") || linkUrl.startsWith("https://");
      return (
        <a
          key={idx}
          href={linkUrl}
          target={isExternal ? "_blank" : undefined}
          rel={isExternal ? "noopener noreferrer" : undefined}
          className="text-blue-600 hover:text-blue-800 underline inline-flex items-center gap-0.5"
        >
          {linkText}
          {isExternal && <ExternalLink className="w-2.5 h-2.5 inline-block opacity-70" />}
        </a>
      );
    }

    return <span key={idx}>{part}</span>;
  });
}

function CodeBlock({ code, language }: { code: string; language: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    try {
      if (typeof navigator !== "undefined" && navigator?.clipboard?.writeText) {
        navigator.clipboard.writeText(code).then(
          () => {
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
          },
          () => {
            // Clipboard access denied or failed
          }
        );
      }
    } catch {
      // Ignore copy error in non-secure or restricted environments
    }
  };

  return (
    <div className="my-2.5 rounded-lg border border-gray-800 bg-gray-950 overflow-hidden shadow-xs text-xs">
      <div className="flex items-center justify-between px-3 py-1.5 bg-gray-900/90 border-b border-gray-800 text-[10px] text-gray-400 font-mono">
        <span>{language || "code"}</span>
        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1 text-gray-400 hover:text-white transition-colors cursor-pointer"
          title="Copy code"
        >
          {copied ? (
            <>
              <Check className="w-3 h-3 text-emerald-400" />
              <span className="text-emerald-400">Copied!</span>
            </>
          ) : (
            <>
              <Copy className="w-3 h-3" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>
      <pre className="p-3 text-gray-100 font-mono text-[11px] overflow-x-auto leading-relaxed">
        <code>{code}</code>
      </pre>
    </div>
  );
}

function MarkdownTable({ rows }: { rows: string[] }) {
  if (rows.length < 2) return null;

  const parseCells = (rowStr: string) => {
    const trimmed = rowStr.trim();
    const stripped = trimmed.replace(/^\|/, "").replace(/\|$/, "");
    return stripped.split("|").map((c) => c.trim());
  };

  const headerCells = parseCells(rows[0]);
  // Row 1 is usually the separator |---|---|
  const dataRows = rows.slice(2).filter((r) => r.includes("|"));

  return (
    <div className="my-3 overflow-x-auto border border-gray-200 rounded-lg shadow-xs max-w-full">
      <table className="w-full text-left text-[11px] border-collapse">
        <thead className="bg-gray-100/80 border-b border-gray-200 text-gray-800 font-semibold">
          <tr>
            {headerCells.map((cell, cIdx) => (
              <th key={cIdx} className="p-2 border-r border-gray-200 last:border-r-0 whitespace-nowrap">
                {formatInlineText(cell)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {dataRows.map((row, rIdx) => {
            const cells = parseCells(row);
            while (cells.length < headerCells.length) {
              cells.push("");
            }
            return (
              <tr
                key={rIdx}
                className={rIdx % 2 === 0 ? "bg-white hover:bg-blue-50/30" : "bg-gray-50/60 hover:bg-blue-50/40"}
              >
                {cells.map((cell, cIdx) => (
                  <td key={cIdx} className="p-2 border-r border-gray-100 last:border-r-0 text-gray-700 whitespace-nowrap">
                    {formatInlineText(cell)}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function SafeMarkdown({ content, className = "", onCitationClick }: SafeMarkdownProps) {
  if (!content) return null;

  // Split lines
  const rawLines = content.split(/\r?\n/);
  const elements: React.ReactNode[] = [];

  let i = 0;
  while (i < rawLines.length) {
    const line = rawLines[i];
    const trimmed = line.trim();

    // 1. Fenced Code Block
    if (trimmed.startsWith("```")) {
      const language = trimmed.slice(3).trim();
      const codeLines: string[] = [];
      i++;
      while (i < rawLines.length && !rawLines[i].trim().startsWith("```")) {
        codeLines.push(rawLines[i]);
        i++;
      }
      if (i < rawLines.length) {
        i++; // Skip closing ```
      }
      elements.push(
        <CodeBlock
          key={`code-${elements.length}`}
          code={codeLines.join("\n")}
          language={language}
        />
      );
      continue;
    }

    // 2. Markdown Table
    if (trimmed.startsWith("|") && trimmed.includes("|", 1)) {
      const tableLines: string[] = [];
      let tempIdx = i;
      while (tempIdx < rawLines.length && rawLines[tempIdx].trim().startsWith("|")) {
        tableLines.push(rawLines[tempIdx]);
        tempIdx++;
      }
      if (tableLines.length >= 2 && tableLines[1].includes("-")) {
        i = tempIdx;
        elements.push(
          <MarkdownTable key={`table-${elements.length}`} rows={tableLines} />
        );
        continue;
      }
    }

    // 3. Headings (h1 through h6)
    const headingMatch = trimmed.match(/^(#{1,6})\s+(.*)$/);
    if (headingMatch) {
      const level = headingMatch[1].length;
      const title = headingMatch[2];
      const headingClasses: Record<number, string> = {
        1: "font-extrabold text-gray-900 text-sm mt-4 mb-2",
        2: "font-bold text-gray-900 text-sm mt-3.5 mb-1.5",
        3: "font-bold text-gray-900 text-xs mt-3 mb-1.5 flex items-center gap-1.5",
        4: "font-semibold text-gray-900 text-xs mt-3 mb-1",
        5: "font-semibold text-gray-800 text-[11px] mt-2 mb-1",
        6: "font-medium text-gray-700 text-[11px] mt-2 mb-0.5"
      };
      const Tag = (`h${Math.min(level + 1, 6)}`) as keyof JSX.IntrinsicElements;
      elements.push(
        <Tag key={`h-${i}`} className={headingClasses[level] || headingClasses[4]}>
          {formatInlineText(title, onCitationClick)}
        </Tag>
      );
      i++;
      continue;
    }

    // Horizontal Rule
    if (/^(\-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
      elements.push(<hr key={`hr-${i}`} className="my-3 border-gray-200" />);
      i++;
      continue;
    }

    // 4. Blockquote
    if (trimmed.startsWith("> ")) {
      elements.push(
        <blockquote
          key={`quote-${i}`}
          className="border-l-2 border-blue-500 pl-3 py-1 my-2 text-gray-600 bg-blue-50/30 rounded-r text-[11px] italic"
        >
          {formatInlineText(trimmed.slice(2), onCitationClick)}
        </blockquote>
      );
      i++;
      continue;
    }

    // 5. Unordered List Items
    if (/^[\-\*•]\s+/.test(trimmed)) {
      const listItems: string[] = [];
      while (i < rawLines.length && /^[\-\*•]\s+/.test(rawLines[i].trim())) {
        listItems.push(rawLines[i].trim().replace(/^[\-\*•]\s+/, ""));
        i++;
      }
      elements.push(
        <ul key={`ul-${elements.length}`} className="my-2 space-y-1 pl-4 list-disc text-gray-700">
          {listItems.map((item, idx) => (
            <li key={idx} className="leading-relaxed">
              {formatInlineText(item, onCitationClick)}
            </li>
          ))}
        </ul>
      );
      continue;
    }

    // 6. Ordered List Items
    if (/^\d+[\.\)]\s+/.test(trimmed)) {
      const listItems: string[] = [];
      while (i < rawLines.length && /^\d+[\.\)]\s+/.test(rawLines[i].trim())) {
        listItems.push(rawLines[i].trim().replace(/^\d+[\.\)]\s+/, ""));
        i++;
      }
      elements.push(
        <ol key={`ol-${elements.length}`} className="my-2 space-y-1 pl-4 list-decimal text-gray-700">
          {listItems.map((item, idx) => (
            <li key={idx} className="leading-relaxed">
              {formatInlineText(item, onCitationClick)}
            </li>
          ))}
        </ol>
      );
      continue;
    }

    // 7. Empty line spacer
    if (!trimmed) {
      elements.push(<div key={`space-${i}`} className="h-1.5" />);
      i++;
      continue;
    }

    // 8. Regular Paragraph
    elements.push(
      <p key={`p-${i}`} className="leading-relaxed">
        {formatInlineText(line, onCitationClick)}
      </p>
    );
    i++;
  }

  return <div className={`space-y-1 ${className}`}>{elements}</div>;
}
