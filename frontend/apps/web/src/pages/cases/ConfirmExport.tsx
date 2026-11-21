/**
 * TZ §12 Human-in-the-Loop: rasmiy DOCX/PDF faqat advokat "tanishdim" tasdig'idan keyin.
 * Tasdiq oynasi: keltirilgan moddalar (holati bilan), tekshiruvdan o'tmagan baholar, tekshiruv ro'yxati, format.
 */
import type { CaseReport, Confirmation } from "@mezon/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { TFunction } from "i18next";
import { BookOpenCheckIcon, DownloadIcon, FileTextIcon, ShieldCheckIcon } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api, Badge, Button, Card, cn, Dialog, DialogContent, DialogDescription, DialogTitle, formatDateTime, saveBlob, Spinner, staggerStyle, useLanguage, Checkbox } from "@mezon/web-kit";

import { keys, notifyError } from "@/lib/queries";

type Format = "docx" | "pdf";

/** Server holat kalitlari (o'zbekcha) -> tarjima */
function statusLabel(t: TFunction, status: string): [string, "ok" | "bad" | "warn"] {
  switch (status) {
    case "kuchda":
      return [t("kuchda"), "ok"];
    case "kuchini yoʻqotgan":
      return [t("kuchini yoʻqotgan"), "bad"];
    case "kuchga kirmagan":
      return [t("kuchga kirmagan"), "bad"];
    default:
      return [t("nomaʼlum"), "warn"];
  }
}

async function download(caseId: string, fmt: Format) {
  const { blob, filename } = await api.download(`/cases/${caseId}/export/${fmt}`);
  saveBlob(blob, filename);
}

function Metric({ label, value, note, tone }: { label: string; value: number | string; note: string; tone: string }) {
  return (
    <div className="rounded-lg border border-line bg-surface p-3">
      <div className="text-xs text-muted">{label}</div>
      <div className={cn("mt-1 text-2xl font-bold", tone)}>{value}</div>
      <div className="tabular-nums text-xs text-muted">{note}</div>
    </div>
  );
}

function ConfirmDialog({ caseId, report, info, open, onOpenChange }: {
  caseId: string; report: CaseReport; info: Confirmation; open: boolean; onOpenChange(v: boolean): void;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [checks, setChecks] = useState([false, false, false, false]);
  const [format, setFormat] = useState<Format>("docx");
  const inForce = info.articles.filter((a) => a.in_force).length;
  const items = [
    t("Faktlar, sanalar va ishtirokchilar asl ish materiallariga mosligini koʻrib chiqdim."),
    t("Qonun moddalarining voqea paytidagi tahriri va amaldaligini tekshirdim."),
    t("Ziddiyatlar va tekshiruvdan oʻtmagan baholarni koʻrib chiqdim."),
    t("Asosiy dalillar va qonun moddalari bilan tanishdim. Hujjat yuridik maslahat emasligini va yakuniy pozitsiyani oʻzim belgilashimni tushunaman."),
  ];

  const confirm = useMutation({
    mutationFn: async () => {
      await api.raw(`/cases/${caseId}/confirmation`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ acknowledged: true }),
      });
      await download(caseId, format);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: keys.confirmation(caseId) });
      void queryClient.invalidateQueries({ queryKey: keys.case(caseId) });
      onOpenChange(false);
    },
    onError: (err) => notifyError(err, t),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <div className="label-code mb-2 text-gold">MEZON HITL · TZ §12</div>
        <DialogTitle>{t("Yuridik tasdiqlash")}</DialogTitle>
        <DialogDescription>{t("Rasmiy hisobotni yaratishdan oldin xulosada ishlatilgan qonun moddalari va tekshiruvdan oʻtmagan baholarni koʻrib chiqing.")}</DialogDescription>

        <div className="mt-4 grid grid-cols-3 gap-2">
          <Metric label={t("Varaq")} value={report.pages} note={t("{{n}} varaq", { n: report.pages })} tone="" />
          <Metric label={t("Modda")} value={info.articles.length} note={`${t("kuchda")}: ${inForce}`} tone="text-gold" />
          <Metric label={t("Tekshiruvdan oʻtmagan baholar:")} value={info.unverified.length} note={info.unverified.length ? "⚠" : "✓"}
            tone={info.unverified.length ? "text-red" : "text-green"} />
        </div>

        {info.unverified.length > 0 ? (
          <Card accent="red" className="mt-4 px-4 py-3">
            <b className="text-sm text-red">{t("Tekshiruvdan oʻtmagan baholar:")} {info.unverified.length}</b>
            {info.unverified.map((u, i) => (
              <div key={i} className="mt-1 tabular-nums text-xs text-red">✗ {u.topic} — {u.reason}</div>
            ))}
            <div className="mt-1.5 text-xs text-muted">{t("Hujjatda ular “TASDIQLANMAGAN” deb belgilanadi.")}</div>
          </Card>
        ) : (
          <Badge tone="ok" className="mt-4">{t("barcha huquqiy baholar tekshiruvdan oʻtgan")}</Badge>
        )}

        <h3 className="label-code mb-2 mt-5 text-muted">{t("Keltirilgan qonun moddalari")}</h3>
        <div className="max-h-64 overflow-auto rounded-lg border border-line">
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-surface">
              <tr className="text-left text-muted">
                <th className="px-3 py-2 font-semibold">{t("Hujjat")}</th>
                <th className="px-3 py-2 font-semibold">{t("Modda")}</th>
                <th className="px-3 py-2 font-semibold">{t("Tahrir")}</th>
                <th className="px-3 py-2 font-semibold">{t("Holati")}</th>
              </tr>
            </thead>
            <tbody>
              {info.articles.length ? info.articles.map((a, i) => {
                const [label, tone] = statusLabel(t, a.status);
                return (
                  <tr key={a.lex_url} className="animate-in-up border-t border-line" style={staggerStyle(i, 35)}>
                    <td className="px-3 py-1.5">{a.doc_title}</td>
                    <td className="px-3 py-1.5"><a href={a.lex_url} target="_blank" rel="noopener noreferrer" className="text-gold hover:underline">{a.label}</a></td>
                    <td className="px-3 py-1.5 tabular-nums">{a.edition}</td>
                    <td className="px-3 py-1.5"><Badge tone={tone}>{label}</Badge></td>
                  </tr>
                );
              }) : (
                <tr><td colSpan={4} className="px-3 py-3 text-muted">{t("Modda keltirilmagan")}</td></tr>
              )}
            </tbody>
          </table>
        </div>

        <h3 className="label-code mb-2 mt-5 flex items-center justify-between text-muted">
          <span>{t("Advokat tekshiruvi")}</span>
          <span className="text-green">{checks.filter(Boolean).length}/{checks.length}</span>
        </h3>
        <div className="flex flex-col gap-2">
          {items.map((text, i) => (
            <label key={i} className="animate-in-up flex items-start gap-3 rounded-lg border border-line bg-surface p-3 text-sm" style={staggerStyle(i, 70)}>
              <Checkbox checked={checks[i]} onCheckedChange={(v) => setChecks((c) => c.map((x, j) => (j === i ? v === true : x)))} />
              <span>{text}</span>
            </label>
          ))}
        </div>

        <h3 className="label-code mb-2 mt-5 text-muted">{t("Eksport formati")}</h3>
        <div className="grid gap-2 sm:grid-cols-2">
          {(["docx", "pdf"] as const).map((fmt, i) => (
            <button key={fmt} type="button" onClick={() => setFormat(fmt)} aria-pressed={format === fmt} style={staggerStyle(i, 70)}
              className={cn("animate-in-up flex items-center gap-3 rounded-lg border border-line bg-surface p-3 text-left", format === fmt && "border-primary shadow-glow")}>
              <FileTextIcon className={cn("size-5", fmt === "docx" ? "text-primary" : "text-gold")} />
              <span>
                <span className="block text-sm font-semibold">{fmt === "docx" ? "Microsoft Word (.DOCX)" : "PDF (.PDF)"}</span>
                <span className="block text-xs text-muted">{fmt === "docx" ? t("Tahrirlanadigan rasmiy hujjat") : t("Sudga taqdim etish uchun")}</span>
              </span>
            </button>
          ))}
        </div>

        <Button variant="success" size="lg" className="mt-5 w-full" disabled={!checks.every(Boolean) || confirm.isPending} onClick={() => confirm.mutate()}>
          {confirm.isPending ? <Spinner className="text-canvas" /> : <ShieldCheckIcon />}
          {t("Tasdiqlayman va hujjatni yuklab olaman")}
        </Button>
      </DialogContent>
    </Dialog>
  );
}

/** Hisobot ustidagi eksport paneli */
export function ExportPanel({ caseId, report }: { caseId: string; report: CaseReport }) {
  const { t } = useTranslation();
  const { language } = useLanguage();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState<Format | null>(null);
  const info = useQuery({
    queryKey: keys.confirmation(caseId),
    queryFn: async () => (await (await api.raw(`/cases/${caseId}/confirmation`)).json()) as Confirmation,
  });

  async function get(fmt: Format) {
    setBusy(fmt);
    try {
      await download(caseId, fmt);
    } catch (err) {
      notifyError(err, t);
    } finally {
      setBusy(null);
    }
  }

  if (!info.data) return null;
  if (info.data.confirmed_at) {
    return (
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="ok"><BookOpenCheckIcon className="size-3.5" />{t("✓ tasdiqlangan:")} {formatDateTime(info.data.confirmed_at, language)}</Badge>
        {(["docx", "pdf"] as const).map((fmt) => (
          <Button key={fmt} variant="outline" size="sm" onClick={() => void get(fmt)} disabled={busy !== null}>
            {busy === fmt ? <Spinner /> : <DownloadIcon />}
            {fmt === "docx" ? t("DOCX yuklab olish") : t("PDF yuklab olish")}
          </Button>
        ))}
      </div>
    );
  }
  return (
    <div className="flex flex-wrap items-center gap-3">
      <Button variant="gold" onClick={() => setOpen(true)}>
        <ShieldCheckIcon />
        {t("Rasmiy hisobot (DOCX / PDF)…")}
      </Button>
      <span className="text-xs text-muted">{t("avval yuridik tasdiq talab qilinadi")}</span>
      <ConfirmDialog caseId={caseId} report={report} info={info.data} open={open} onOpenChange={setOpen} />
    </div>
  );
}
