/**
 * Kunlik AI xarajati (bitta seriya — ustunli grafik). dataviz qoidalari: bitta rang (Electric Blue, qorong'i fonda
 * ≥ 3:1), ustun ≤ 24px, 4px yumaloq uch, 2px oraliq, nozik grid, har ustunga hover tooltip, legend yo'q
 * (sarlavha nomlaydi), ekran o'quvchi uchun jadval.
 */
import { cn } from "@mezon/web-kit";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { CostDay } from "@/lib/admin";

function niceMax(v: number): number {
  if (v <= 0) return 1;
  const exp = 10 ** Math.floor(Math.log10(v));
  const f = v / exp;
  return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * exp;
}

const fmtUsd = (v: number) => (v >= 100 ? `$${Math.round(v)}` : v >= 1 ? `$${v.toFixed(1)}` : `$${v.toFixed(2)}`);
const dayLabel = (iso: string) => iso.slice(8, 10) + "." + iso.slice(5, 7);

export function CostChart({ days, height = 180 }: { days: CostDay[]; height?: number }) {
  const { t } = useTranslation();
  const [hover, setHover] = useState<number | null>(null);
  const max = niceMax(Math.max(...days.map((d) => d.usd), 0));
  const ticks = [max, max / 2, 0];
  const total = days.reduce((s, d) => s + d.usd, 0);
  const peak = days.reduce((best, d, i) => (d.usd > days[best].usd ? i : best), 0);
  const h = hover !== null ? days[hover] : null;

  return (
    <figure className="relative">
      <div className="flex gap-2">
        {/* Y o'qi */}
        <div className="flex flex-col justify-between pb-5 text-right tabular-nums text-xs text-muted" style={{ height }}>
          {ticks.map((v) => <span key={v} className="-translate-y-1/2 leading-none first:translate-y-0 last:translate-y-0">{fmtUsd(v)}</span>)}
        </div>
        <div className="relative min-w-0 flex-1">
          {/* gridlar: hairline, solid, recessive */}
          <div className="pointer-events-none absolute inset-x-0 top-0 flex flex-col justify-between" style={{ height: height - 20 }}>
            {ticks.map((v) => <div key={v} className="h-px bg-line/70" />)}
          </div>
          <div className="relative flex items-end gap-[2px]" style={{ height: height - 20 }} onMouseLeave={() => setHover(null)}>
            {days.map((d, i) => (
              <div key={d.date} className="group relative flex h-full flex-1 items-end justify-center" onMouseEnter={() => setHover(i)}
                onFocus={() => setHover(i)} tabIndex={0} aria-label={`${d.date}: ${fmtUsd(d.usd)}`}>
                <div className={cn("w-full max-w-6 rounded-t bg-primary transition-opacity", hover !== null && hover !== i && "opacity-45")}
                  style={{ height: `${d.usd > 0 ? Math.max((d.usd / max) * 100, 1.5) : 0}%` }} />
                {i === peak && d.usd > 0 && hover === null && (
                  <span className="absolute -translate-y-1 tabular-nums text-xs text-ink" style={{ bottom: `${(d.usd / max) * 100}%` }}>
                    {fmtUsd(d.usd)}
                  </span>
                )}
              </div>
            ))}
          </div>
          {/* X o'qi: boshi, o'rtasi, oxiri */}
          <div className="mt-1 flex justify-between tabular-nums text-xs text-muted">
            <span>{dayLabel(days[0]?.date ?? "")}</span>
            <span>{dayLabel(days[Math.floor(days.length / 2)]?.date ?? "")}</span>
            <span>{dayLabel(days[days.length - 1]?.date ?? "")}</span>
          </div>
          {h && (
            <div className="pointer-events-none absolute top-0 z-10 -translate-x-1/2 rounded-lg border border-line border-t-primary/30 bg-subtle px-3 py-2 text-xs shadow-overlay"
              style={{ left: `${((hover! + 0.5) / days.length) * 100}%` }}>
              <div className="tabular-nums text-muted">{h.date}</div>
              <div className="mt-0.5 text-sm font-semibold">{`$${h.usd.toFixed(4)}`}</div>
              <div className="text-muted">{t("Ish tahlili")}: {h.cases} · {t("Savollar")}: {h.chat}</div>
            </div>
          )}
        </div>
      </div>
      <figcaption className="mt-2 tabular-nums text-xs text-muted">
        {t("Jami")}: ${total.toFixed(2)} · {days.length} {t("kun")}
      </figcaption>
      <table className="sr-only">
        <caption>{t("Kunlik AI xarajati")}</caption>
        <thead><tr><th>{t("Sana")}</th><th>USD</th><th>{t("Ish tahlili")}</th><th>{t("Savollar")}</th></tr></thead>
        <tbody>{days.map((d) => <tr key={d.date}><td>{d.date}</td><td>{d.usd}</td><td>{d.cases}</td><td>{d.chat}</td></tr>)}</tbody>
      </table>
    </figure>
  );
}
