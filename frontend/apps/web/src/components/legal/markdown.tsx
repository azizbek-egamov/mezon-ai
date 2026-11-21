/**
 * Kichik markdown (javob va huquqiy baholar uchun): sarlavha, **qalin**, ro'yxat, jadval, chiziq;
 * [M#] -> manba havolasi (tekshiruvdan keyin yashil / qizil), «iqtibos» -> ajratilgan. HTML ishlatilmaydi.
 */
import type { ReactNode } from "react";
import { cn } from "@mezon/web-kit";

export interface CiteSource {
  key: string;
  doc_title: string;
  label: string;
  lex_url: string;
}

export interface CiteContext {
  sources: Record<string, CiteSource>;
  /** tekshiruv tugadimi (rang berish uchun) */
  verified?: boolean;
  cited?: Set<string>;
  missingTitle?: string;
}

const TOKEN_RE = /(\*\*[^*]+\*\*|«[^»]+»|\[M\d+\])/g;

export function Cite({ k, ctx }: { k: string; ctx: CiteContext }) {
  const src = ctx.sources[k];
  const base = "mx-px inline-block whitespace-nowrap rounded-full border px-1.5 tabular-nums text-xs font-medium no-underline align-baseline";
  if (!src) {
    return (
      <span className={cn(base, "border-red text-red")} title={ctx.missingTitle}>
        {k}
      </span>
    );
  }
  const ok = ctx.verified && ctx.cited?.has(k);
  return (
    <a href={src.lex_url} target="_blank" rel="noopener noreferrer" title={`${src.doc_title} — ${src.label}`}
      className={cn(base, ok ? "border-green/30 bg-green/8 text-green" : "border-gold/30 bg-gold/8 text-gold hover:border-gold/60")}>
      {k}
    </a>
  );
}

export function inline(text: string, ctx: CiteContext): ReactNode[] {
  return text.split(TOKEN_RE).map((part, i) => {
    if (!part) return null;
    if (part.startsWith("**") && part.endsWith("**")) return <strong key={i}>{part.slice(2, -2)}</strong>;
    if (part.startsWith("«")) {
      return (
        <span key={i} className="rounded-sm bg-primary/10 px-0.5 text-quote">
          {part}
        </span>
      );
    }
    const cite = /^\[(M\d+)\]$/.exec(part);
    if (cite) return <Cite key={i} k={cite[1]} ctx={ctx} />;
    return part;
  });
}

const isTableRow = (l: string) => /^\s*\|/.test(l);
const isListItem = (l: string) => /^\s*([-*]|\d+\.) /.test(l);

export function Markdown({ text, ctx, className }: { text: string; ctx: CiteContext; className?: string }) {
  const lines = text.split("\n");
  const out: ReactNode[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (isTableRow(line)) {
      const rows: string[] = [];
      while (i < lines.length && isTableRow(lines[i])) rows.push(lines[i++]);
      const body = rows.filter((r) => !/^\s*\|[\s:|-]+\|\s*$/.test(r));
      const cells = (r: string) => r.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
      out.push(
        <div key={i} className="my-2 overflow-x-auto">
          <table className="w-full border-collapse text-[13px]">
            <tbody>
              {body.map((r, n) => (
                <tr key={n}>
                  {cells(r).map((c, j) =>
                    n === 0 ? (
                      <th key={j} className="border border-line bg-subtle px-2 py-1.5 text-left align-top">{inline(c, ctx)}</th>
                    ) : (
                      <td key={j} className="border border-line px-2 py-1.5 align-top">{inline(c, ctx)}</td>
                    ),
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>,
      );
      continue;
    }
    if (isListItem(line)) {
      const ordered = /^\s*\d+\. /.test(line);
      const items: string[] = [];
      while (i < lines.length && isListItem(lines[i])) items.push(lines[i++].replace(/^\s*([-*]|\d+\.) /, ""));
      const List = ordered ? "ol" : "ul";
      out.push(
        <List key={i} className={cn("my-2 space-y-1 pl-5", ordered ? "list-decimal" : "list-disc")}>
          {items.map((it, n) => (
            <li key={n}>{inline(it, ctx)}</li>
          ))}
        </List>,
      );
      continue;
    }
    const heading = /^(#{1,3}) (.*)$/.exec(line);
    if (heading) out.push(<h3 key={i} className="mb-1.5 mt-4 text-[15px] font-semibold tracking-tight">{inline(heading[2], ctx)}</h3>);
    else if (/^-{3,}\s*$/.test(line)) out.push(<hr key={i} className="my-3 border-line" />);
    else if (line.trim()) out.push(<p key={i} className="my-1.5">{inline(line, ctx)}</p>);
    i++;
  }
  return <div className={className}>{out}</div>;
}
