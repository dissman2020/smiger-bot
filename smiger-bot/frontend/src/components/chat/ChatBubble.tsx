"use client";

import { ReactNode } from "react";
import { ChatMessage } from "@/lib/types";
import clsx from "clsx";

/* ── Inline markdown: **bold**, *italic*, [link](url) ─────────────── */
function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  const regex = /(\*\*(.+?)\*\*|\*(.+?)\*|\[(.+?)\]\((.+?)\))/g;
  let lastIdx = 0;
  let match: RegExpExecArray | null;
  let pi = 0;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIdx) {
      nodes.push(<span key={`${keyPrefix}-t${pi++}`}>{text.slice(lastIdx, match.index)}</span>);
    }
    if (match[2]) {
      nodes.push(<strong key={`${keyPrefix}-b${pi++}`} className="font-semibold">{match[2]}</strong>);
    } else if (match[3]) {
      nodes.push(<em key={`${keyPrefix}-i${pi++}`}>{match[3]}</em>);
    } else if (match[4] && match[5]) {
      nodes.push(
        <a key={`${keyPrefix}-a${pi++}`} href={match[5]} target="_blank" rel="noopener noreferrer"
           className="underline underline-offset-2 text-brand-400 hover:text-brand-300">
          {match[4]}
        </a>
      );
    }
    lastIdx = match.index + match[0].length;
  }
  if (lastIdx < text.length) {
    nodes.push(<span key={`${keyPrefix}-e${pi}`}>{text.slice(lastIdx)}</span>);
  }
  return nodes;
}

/* ── Table detection ───────────────────────────────────────────────── */
function isTableRow(line: string): boolean {
  const t = line.trim();
  if (!t.startsWith("|")) return false;
  return t.indexOf("|", 1) !== -1;
}

function isSeparatorRow(line: string): boolean {
  const t = line.trim();
  if (!t.startsWith("|")) return false;
  const inner = t.replace(/\|/g, "");
  return /^[\s:\-]+$/.test(inner) && inner.includes("-");
}

function parseCells(line: string): string[] {
  let t = line.trim();
  if (t.startsWith("|")) t = t.slice(1);
  if (t.endsWith("|")) t = t.slice(0, -1);
  return t.split("|").map((c) => c.trim());
}

/* ── Render a markdown table block ─────────────────────────────────── */
function renderTable(lines: string[], keyPrefix: string): ReactNode {
  const headerCells = parseCells(lines[0]);
  const hasSep = lines.length > 1 && isSeparatorRow(lines[1]);
  const startIdx = hasSep ? 2 : 1;
  const bodyRows = lines.slice(startIdx).filter((l) => !isSeparatorRow(l));

  return (
    <div key={keyPrefix} className="overflow-x-auto my-2 rounded-lg border border-white/10">
      <table className="w-full text-xs border-collapse">
        <thead>
          <tr className="bg-white/[0.04]">
            {headerCells.map((cell, ci) => (
              <th key={ci} className="px-3 py-2 text-left font-semibold text-brand-300 border-b border-white/10 whitespace-nowrap">
                {renderInline(cell, `${keyPrefix}-th${ci}`)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {bodyRows.map((row, ri) => {
            const cells = parseCells(row);
            return (
              <tr key={ri} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                {headerCells.map((_, ci) => (
                  <td key={ci} className="px-3 py-1.5 text-dark-200">
                    {renderInline(cells[ci] || "", `${keyPrefix}-r${ri}c${ci}`)}
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

/* ── Detect bullet list item: -, •, or * ──────────────────────────── */
function matchUl(line: string): string | null {
  const m = line.match(/^[\s]*(?:[-•]|\*(?!\*))\s+(.+)$/);
  return m ? m[1] : null;
}

/* ── Detect ordered list item: 1. or 1) ───────────────────────────── */
function matchOl(line: string): [string, string] | null {
  const m = line.match(/^[\s]*(\d+)[.)]\s+(.+)$/);
  return m ? [m[1], m[2]] : null;
}

/* ── Full markdown renderer ────────────────────────────────────────── */
function renderMarkdown(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  const lines = text.split("\n");
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // --- Markdown table block ---
    if (isTableRow(line)) {
      const tableLines: string[] = [line];
      let j = i + 1;
      while (j < lines.length) {
        const next = lines[j];
        if (isTableRow(next) || isSeparatorRow(next)) {
          tableLines.push(next);
          j++;
        } else if (next.trim() === "") {
          // allow a single blank line within table (some models add spacing)
          if (j + 1 < lines.length && isTableRow(lines[j + 1])) {
            j++;
          } else {
            break;
          }
        } else {
          break;
        }
      }
      if (tableLines.length >= 2) {
        nodes.push(renderTable(tableLines, `tbl-${i}`));
        i = j;
        continue;
      }
    }

    // --- Heading (### / ## / #) ---
    const headingMatch = line.match(/^(#{1,3})\s+(.+)$/);
    if (headingMatch) {
      const level = headingMatch[1].length;
      const cls = level === 1 ? "text-base font-bold" : level === 2 ? "text-sm font-bold" : "text-sm font-semibold";
      if (i > 0) nodes.push(<br key={`br-${i}`} />);
      nodes.push(
        <div key={`h-${i}`} className={`${cls} text-dark-100 mt-1 mb-0.5`}>
          {renderInline(headingMatch[2], `h-${i}`)}
        </div>
      );
      i++;
      continue;
    }

    // --- Unordered list item (-, •, *) ---
    const ulContent = matchUl(line);
    if (ulContent !== null) {
      nodes.push(
        <div key={`ul-${i}`} className="flex gap-1.5 pl-1">
          <span className="text-brand-400 shrink-0">•</span>
          <span>{renderInline(ulContent, `ul-${i}`)}</span>
        </div>
      );
      i++;
      continue;
    }

    // --- Ordered list item (1. 2. 3.) ---
    const olResult = matchOl(line);
    if (olResult) {
      nodes.push(
        <div key={`ol-${i}`} className="flex gap-1.5 pl-1">
          <span className="text-brand-400 shrink-0">{olResult[0]}.</span>
          <span>{renderInline(olResult[1], `ol-${i}`)}</span>
        </div>
      );
      i++;
      continue;
    }

    // --- Empty line → spacing ---
    if (line.trim() === "") {
      nodes.push(<div key={`sp-${i}`} className="h-1.5" />);
      i++;
      continue;
    }

    // --- Regular text line ---
    if (i > 0 && lines[i - 1]?.trim() !== "" && !isTableRow(lines[i - 1])) {
      nodes.push(<br key={`br-${i}`} />);
    }
    nodes.push(<span key={`ln-${i}`}>{renderInline(line, `ln-${i}`)}</span>);
    i++;
  }

  return nodes;
}

/* ── ChatBubble component ──────────────────────────────────────────── */
interface Props {
  message: ChatMessage;
}

export default function ChatBubble({ message }: Props) {
  const isUser = message.role === "user";
  const isAgent = message.isAgent;

  return (
    <div className={clsx("flex animate-fade-in-up", isUser ? "justify-end" : "justify-start")}>
      {!isUser && (
        <div className={clsx(
          "w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold mr-2 mt-1 shrink-0",
          isAgent ? "bg-emerald-600" : "bg-brand-500"
        )}>
          {isAgent ? "CS" : "S"}
        </div>
      )}
      <div
        className={clsx(
          "max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
          isUser
            ? "bg-brand-500 text-white rounded-tr-sm"
            : isAgent
              ? "bg-emerald-900/40 text-dark-100 border border-emerald-500/20 rounded-tl-sm"
              : "bg-dark-800 text-dark-100 border border-white/5 rounded-tl-sm"
        )}
      >
        {isAgent && (
          <div className="text-[10px] text-emerald-400 font-medium mb-1">Sales Representative</div>
        )}
        {isUser ? message.content : renderMarkdown(message.content)}
        {message.isStreaming && <span className="inline-block w-1.5 h-4 bg-brand-400 ml-0.5 animate-pulse" />}
      </div>
    </div>
  );
}
