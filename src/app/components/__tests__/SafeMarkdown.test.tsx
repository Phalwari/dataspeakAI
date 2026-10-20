import { describe, it, expect } from "vitest";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { SafeMarkdown, formatInlineText } from "../SafeMarkdown";

describe("SafeMarkdown Component", () => {
  it("renders plain text without crashing", () => {
    const html = renderToStaticMarkup(<SafeMarkdown content="Hello world" />);
    expect(html).toContain("Hello world");
  });

  it("formats inline bold and code tags", () => {
    const html = renderToStaticMarkup(
      <SafeMarkdown content="Here is **bold text** and `inline_code`." />
    );
    expect(html).toContain("<strong");
    expect(html).toContain("bold text");
    expect(html).toContain("<code");
    expect(html).toContain("inline_code");
  });

  it("renders markdown tables with header and alternating rows", () => {
    const tableMarkdown = [
      "| Column A | Column B |",
      "| --- | --- |",
      "| Value 1 | Value 2 |",
      "| Value 3 | Value 4 |",
    ].join("\n");

    const html = renderToStaticMarkup(<SafeMarkdown content={tableMarkdown} />);
    expect(html).toContain("<table");
    expect(html).toContain("<th");
    expect(html).toContain("Column A");
    expect(html).toContain("Column B");
    expect(html).toContain("<td");
    expect(html).toContain("Value 1");
    expect(html).toContain("Value 2");
  });

  it("renders fenced code blocks with copy button", () => {
    const codeBlockMarkdown = "```sql\nSELECT * FROM orders WHERE status = 'active';\n```";
    const html = renderToStaticMarkup(<SafeMarkdown content={codeBlockMarkdown} />);

    expect(html).toContain("<pre");
    expect(html).toContain("SELECT * FROM orders");
    expect(html).toContain("sql");
  });

  it("renders bullet and numbered lists", () => {
    const listMarkdown = "- First point\n- Second point\n1. Numbered item";
    const html = renderToStaticMarkup(<SafeMarkdown content={listMarkdown} />);

    expect(html).toContain("<ul");
    expect(html).toContain("<ol");
    expect(html).toContain("First point");
    expect(html).toContain("Numbered item");
  });

  it("renders source citation pills", () => {
    const citationMarkdown = "According to the annual report [Source: AnnualReport_2024.pdf, p. 12], revenues grew.";
    const html = renderToStaticMarkup(<SafeMarkdown content={citationMarkdown} />);

    expect(html).toContain("Source: AnnualReport_2024.pdf, p. 12");
  });

  it("does not swallow single pipe lines that are not valid tables", () => {
    const content = "| Note: Single line with pipe |";
    const html = renderToStaticMarkup(<SafeMarkdown content={content} />);
    expect(html).toContain("Note: Single line with pipe");
  });

  it("renders safe markdown links for internal and external URLs", () => {
    const content = "Check [Documentation](https://docs.dataspeak.ai) and [Databases](/dashboard/databases).";
    const html = renderToStaticMarkup(<SafeMarkdown content={content} />);
    expect(html).toContain('href="https://docs.dataspeak.ai"');
    expect(html).toContain('target="_blank"');
    expect(html).toContain('rel="noopener noreferrer"');
    expect(html).toContain("Documentation");
    expect(html).toContain('href="/dashboard/databases"');
    expect(html).toContain("Databases");
  });

  it("handles unclosed fenced code blocks gracefully during streaming", () => {
    const unclosed = "```sql\nSELECT * FROM users\nWHERE active = true";
    const html = renderToStaticMarkup(<SafeMarkdown content={unclosed} />);
    expect(html).toContain("<pre");
    expect(html).toContain("SELECT * FROM users");
  });

  it("renders case-insensitive citation badges", () => {
    const content = "Grounding verification [source: compliance_guide.pdf] succeeded.";
    const html = renderToStaticMarkup(<SafeMarkdown content={content} />);
    expect(html).toContain("compliance_guide.pdf");
    expect(html).toContain("bg-emerald-50");
  });

  it("renders horizontal rules and deep headings (h5, h6)", () => {
    const content = "# Main\n---\n#### Sub-section Level 4\n##### Fine Print Level 5";
    const html = renderToStaticMarkup(<SafeMarkdown content={content} />);
    expect(html).toContain("<hr");
    expect(html).toContain("<h5");
    expect(html).toContain("Sub-section Level 4");
    expect(html).toContain("<h6");
    expect(html).toContain("Fine Print Level 5");
  });

  it("pads missing table cells in sparse rows", () => {
    const tableWithSparseRow = [
      "| Col 1 | Col 2 | Col 3 |",
      "| --- | --- | --- |",
      "| Val A | Val B | Val C |",
      "| Val D | |",
    ].join("\n");
    const html = renderToStaticMarkup(<SafeMarkdown content={tableWithSparseRow} />);
    expect(html).toContain("<table");
    expect(html).toContain("Val D");
  });
});
