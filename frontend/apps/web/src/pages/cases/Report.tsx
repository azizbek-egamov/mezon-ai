/** Tahlil hisoboti: xulosa, ko'rsatkichlar, OCR eslatmasi, protsessual muammolar / ziddiyatlar / xronologiya / faktlar. */
import type { CaseReport, Finding } from "@mezon/api-client";
import type { TFunction } from "i18next";
import { AlertTriangleIcon, ClockIcon, GavelIcon, ListIcon } from "lucide-react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { Badge, Card, cn, Empty, staggerStyle, Tabs, TabsContent, TabsList, TabsTrigger } from "@mezon/web-kit";

import { inline } from "@/components/legal/markdown";

import { PageButton } from "./common";

export function verdictLabel(t: TFunction, verdict: string): [string, "bad" | "warn" | "info" | "neutral"] {
  switch (verdict) {
    case "qonun_buzilishi":
      return [t("Qonun buzilishi"), "bad"];
    case "buzilish_ehtimoli":
      return [t("Buzilish ehtimoli"), "warn"];
    case "huquqiy_ahamiyatli":
      return [t("Huquqiy ahamiyatli"), "info"];
    case "asossiz":
      return [t("Asossiz"), "neutral"];
    default:
      return [verdict, "neutral"];
  }
}

function importanceLabel(t: TFunction, importance: string): string {
  return importance === "high" ? t("yuqori") : importance === "medium" ? t("oʻrta") : importance === "low" ? t("past") : importance;
}

function Pages({ pages, onPage }: { pages: (number | null | undefined)[]; onPage?: (n: number) => void }) {
  return <>{pages.filter((p): p is number => !!p).map((p, i) => <PageButton key={`${p}-${i}`} page={p} onPage={onPage} />)}</>;
}

function FindingCard({ f, onPage, index = 0 }: { f: Finding; onPage?: (n: number) => void; index?: number }) {
  const { t } = useTranslation();
  const L = f.legal ?? {};
  const ctx = { sources: Object.fromEntries((L.sources ?? []).map((s) => [s.key, s])), missingTitle: t("Bunday manba berilmagan") };
  let legal: ReactNode = null;
  if (L.skipped) legal = <div className="text-sm text-muted">{t("Huquqiy asoslash oʻtkazib yuborildi (muhimligi past).")}</div>;
  else if (L.verdict) {
    const [label, tone] = verdictLabel(t, L.verdict);
    const v = L.verification;
    legal = (
      <>
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={tone}>{label}</Badge>
          <Badge tone={v?.ok ? "ok" : "bad"}>{v?.ok ? t("✓ manbalar tekshirildi") : t("⚠ tekshiruvdan oʻtmagan")}</Badge>
          {L.retried && <span className="text-xs text-muted">{t("qayta baholangan")}</span>}
        </div>
        <p className="mt-3 text-[15px] leading-[1.75]">{inline(L.assessment ?? "", ctx)}</p>
        {L.correction_needed && L.corrections && (
          <p className="mt-1 text-sm"><b>{t("Tuzatish:")}</b> {inline(L.corrections, ctx)}</p>
        )}
        {L.defense_action && <p className="mt-1 text-sm"><b>{t("Himoyachi uchun:")}</b> {L.defense_action}</p>}
        {(v?.issues ?? []).map((issue, i) => (
          <div key={i} className={cn("mt-1 tabular-nums text-xs", issue.severity === "error" ? "text-red" : issue.severity === "info" ? "text-muted" : "text-amber")}>
            {issue.severity === "error" ? "✗" : issue.severity === "info" ? "ℹ" : "!"} {issue.detail}
          </div>
        ))}
      </>
    );
  } else if (L.error) legal = <div className="text-sm text-red">{t("Huquqiy baho olinmadi:")} {L.error}</div>;

  return (
    <Card accent={f.importance === "high" ? "red" : f.importance === "medium" ? "amber" : "none"} className="animate-in-up mb-4 px-6 py-5" style={staggerStyle(index, 60)}>
      <div className="flex items-start gap-3">
        <h3 className="flex-1 text-[17px] font-semibold leading-snug">{f.topic}</h3>
        <Badge tone={f.importance === "high" ? "bad" : f.importance === "medium" ? "warn" : "neutral"}>{importanceLabel(t, f.importance)}</Badge>
      </div>
      <div className="mt-2"><Pages pages={f.pages} onPage={onPage} /></div>
      <p className="mt-3 text-[15px] leading-[1.75]">{f.explanation}</p>
      {legal && <div className="mt-4 border-t border-line pt-4">{legal}</div>}
    </Card>
  );
}

export function ReportView({ report, onPage, exportSlot }: { report: CaseReport; onPage?: (n: number) => void; exportSlot?: ReactNode }) {
  const { t } = useTranslation();
  const facts = Object.fromEntries(report.facts.map((f) => [f.id, f]));
  const verified = report.facts.filter((f) => f.verified).length;
  const contradictions = report.findings.filter((f) => f.kind === "contradiction");
  const procedural = report.findings.filter((f) => f.kind === "procedural");
  const ocr = report.ocr_pages ?? [];
  const lowOcr = ocr.filter((p) => p.low_quality).map((p) => p.page);

  return (
    <div className="flex flex-col gap-4">
      <Card className="px-6 py-5">
        <h2 className="text-lg font-semibold">{t("Xulosa.").replace(/\.$/, "")}</h2>
        <p className="mt-2 leading-[1.75]">{report.summary}</p>
        {/* Asosiy ko'rsatkichlar — oddiy matn (texnik ma'lumot: niqoblash soni, narx, vaqt — ko'rsatilmaydi) */}
        <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 border-t border-line pt-4 text-[13px] text-muted">
          <span>{t("{{n}} varaq", { n: report.pages })}</span>
          <span>{t("{{n}} fakt · {{v}} iqtibos tasdiqlandi", { n: report.facts.length, v: verified })}</span>
          {contradictions.length > 0 && <span className="text-red">{t("{{n}} ziddiyat", { n: contradictions.length })}</span>}
          {procedural.length > 0 && <span className="text-amber">{t("{{n}} protsessual muammo", { n: procedural.length })}</span>}
        </div>
      </Card>
      {exportSlot}
      {ocr.length > 0 && (
        <Card className="px-4 py-3 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="info">{t("OCR: {{n}} ta skaner varaq", { n: ocr.length })}</Badge>
            {ocr.some((p) => p.has_handwriting) && (
              <Badge tone="neutral">{t("qoʻlyozma mavjud")}</Badge>
            )}
            {lowOcr.length ? (
              <Badge tone="bad">{t("yomon oʻqilgan:")} <Pages pages={lowOcr} onPage={onPage} /></Badge>
            ) : (
              <Badge tone="ok">{t("barchasi yaxshi oʻqildi")}</Badge>
            )}
          </div>
          {ocr.filter((p) => p.warning).map((p) => (
            <div key={p.page} className="mt-1 tabular-nums text-xs text-amber">! {t("{{n}}-varaq:", { n: p.page })} {p.warning}</div>
          ))}
          <div className="mt-1.5 text-xs text-muted">{t("Skaner sahifalardagi matn avtomatik tanilgan — muhim iqtiboslarni asl varaq bilan solishtiring.")}</div>
        </Card>
      )}
      {(report.errors ?? []).map((e, i) => <div key={i} className="text-sm text-red">✗ {e}</div>)}

      <Tabs defaultValue="proc">
        <TabsList>
          <TabsTrigger value="proc"><GavelIcon className="size-3.5" />{t("Protsessual muammolar")}</TabsTrigger>
          <TabsTrigger value="contr"><AlertTriangleIcon className="size-3.5" />{t("Ziddiyatlar")}</TabsTrigger>
          <TabsTrigger value="time"><ClockIcon className="size-3.5" />{t("Xronologiya")}</TabsTrigger>
          <TabsTrigger value="facts"><ListIcon className="size-3.5" />{t("Faktlar")}</TabsTrigger>
        </TabsList>
        <TabsContent value="proc">
          {procedural.length ? procedural.map((f, i) => <FindingCard key={i} f={f} onPage={onPage} index={i} />) : <Empty>{t("Topilmadi.")}</Empty>}
        </TabsContent>
        <TabsContent value="contr">
          {contradictions.length ? contradictions.map((f, i) => <FindingCard key={i} f={f} onPage={onPage} index={i} />) : <Empty>{t("Topilmadi.")}</Empty>}
        </TabsContent>
        <TabsContent value="time">
          {report.timeline.map((id) => facts[id]).filter(Boolean).map((f, i) => (
            <div key={f.id} className="animate-in-up grid grid-cols-[140px_56px_1fr] gap-3 border-b border-line py-3 text-sm" style={staggerStyle(i, 40)}>
              <span className="tabular-nums text-[13px] text-muted">{f.date} {f.time}</span>
              <span><Pages pages={[f.verified_page || f.page]} onPage={onPage} /></span>
              <span>{f.summary}</span>
            </div>
          ))}
        </TabsContent>
        <TabsContent value="facts">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[13px] text-muted">
                  <th className="pb-3 pr-3 font-medium">{t("Varaq")}</th>
                  <th className="pb-3 pr-3 font-medium">{t("Manba")}</th>
                  <th className="pb-3 font-medium">{t("Fakt va iqtibos")}</th>
                </tr>
              </thead>
              <tbody>
                {report.facts.map((f, i) => (
                  <tr key={f.id} className="animate-in-up border-t border-line align-top" style={staggerStyle(i, 30)}>
                    <td className="py-3 pr-3"><Pages pages={[f.verified_page || f.page]} onPage={onPage} /></td>
                    <td className="py-3 pr-3 text-[13px] text-muted">{f.source}</td>
                    <td className="py-3 leading-relaxed">
                      {f.summary}
                      <br />
                      <span className="rounded-sm bg-primary/10 px-0.5 text-quote">«{f.quote}»</span>{" "}
                      {!f.verified && <Badge tone="bad">{t("iqtibos topilmadi")}</Badge>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
