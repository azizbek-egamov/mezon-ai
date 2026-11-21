/** Ish sahifasi: chapda PDF (varaqlar), o'ngda holat/progress va tahlil hisoboti; mobilda — tablar. */
import { unwrap, type CaseReport } from "@mezon/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeftIcon, FileIcon, RotateCcwIcon, Trash2Icon } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router";

import { api, Button, cn, Empty, ErrorNote, FadeIn, Progress, staggerStyle, Spinner } from "@mezon/web-kit";

import { PdfViewer } from "@/components/legal/PdfViewer";
import { keys, notifyError } from "@/lib/queries";

import { CaseStatusBadge, isActive } from "./common";
import { ExportPanel } from "./ConfirmExport";
import { ReportView } from "./Report";

export function CaseDetailPage() {
  const { id = "" } = useParams();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [mobileTab, setMobileTab] = useState<"report" | "pdf">("report");

  const run = useQuery({
    queryKey: keys.case(id),
    queryFn: () => unwrap(api.client.GET("/api/v1/cases/{run_id}", { params: { path: { run_id: id } } })),
    refetchInterval: (q) => (q.state.data && isActive(q.state.data.status) ? 2000 : false),
  });
  const done = run.data?.status === "DONE";
  const status = run.data?.status;
  // Tahlil tugadi (yoki xato — kvota qaytariladi): sarf va ro'yxat yangilansin
  useEffect(() => {
    if (status === "DONE" || status === "FAILED") {
      void queryClient.invalidateQueries({ queryKey: keys.usage });
      void queryClient.invalidateQueries({ queryKey: ["cases", "list"] });
    }
  }, [status, queryClient]);
  const report = useQuery({
    queryKey: keys.report(id),
    queryFn: async () => (await (await api.raw(`/cases/${id}/report`, { cache: "no-store" })).json()) as CaseReport,
    enabled: done,
    staleTime: Infinity,
  });

  const retry = useMutation({
    mutationFn: () => unwrap(api.client.POST("/api/v1/cases/{run_id}/retry", { params: { path: { run_id: id } } })),
    onSuccess: (data) => queryClient.setQueryData(keys.case(id), data),
    onError: (err) => notifyError(err, t, () => navigate("/billing")),
  });
  const remove = useMutation({
    mutationFn: () => api.raw(`/cases/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: keys.case(id) });
      void queryClient.invalidateQueries({ queryKey: ["cases"] });
      navigate("/cases", { replace: true });
    },
    onError: (err) => notifyError(err, t),
  });

  if (run.isLoading) return <Empty><Spinner className="size-6" /></Empty>;
  if (run.error || !run.data) return <Empty>{run.error?.message ?? t("Topilmadi")}</Empty>;
  const r = run.data;

  const goPage = (n: number) => {
    setPage(n);
    setMobileTab("pdf");
  };

  const pdfPane = r.has_pdf ? (
    <PdfViewer caseId={id} page={page} onPageChange={setPage} />
  ) : (
    <div className="p-6 text-sm text-muted">{t("PDF tahlildan keyin serverdan oʻchirilgan (siz tanlagan rejim). Varaq raqamlari hisobotda qoladi.")}</div>
  );

  return (
    <div className="flex h-[calc(100dvh-7.5rem)] flex-col lg:h-dvh">
      <div className="flex items-center gap-4 border-b border-line bg-surface px-5 py-4">
        <Link to="/cases" className="grid size-9 place-items-center rounded-lg text-muted hover:bg-subtle hover:text-ink" aria-label={t("Ishlar")}><ArrowLeftIcon className="size-4" /></Link>
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-xl font-semibold">{r.title}</h1>
          <div className="mt-1 flex items-center gap-3 text-[13px] text-muted">
            <CaseStatusBadge run={r} />
            <span>{r.category_label}</span>
            <span className="tabular-nums">{t("{{n}} varaq", { n: r.pages })}</span>
          </div>
        </div>
        <Button variant="destructive" size="sm" disabled={r.status === "RUNNING" || remove.isPending}
          onClick={() => window.confirm(t("Ish, PDF va hisobot butunlay oʻchiriladi. Davom etasizmi?")) && remove.mutate()}>
          <Trash2Icon /> <span className="hidden sm:inline">{t("Ishni oʻchirish")}</span>
        </Button>
      </div>

      <div className="flex border-b border-line lg:hidden">
        {(["report", "pdf"] as const).map((tab) => (
          <button key={tab} onClick={() => setMobileTab(tab)}
            className={cn("flex-1 border-b-2 border-transparent py-3 text-sm font-medium text-muted", mobileTab === tab && "border-primary text-ink")}>
            {tab === "report" ? t("Tahlil") : t("Ish hujjati")}
          </button>
        ))}
      </div>

      <div className="grid min-h-0 flex-1 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
        <div className={cn("min-h-0 border-r border-line", mobileTab === "pdf" ? "block" : "hidden lg:block")}>{pdfPane}</div>
        <div className={cn("min-h-0 overflow-y-auto bg-canvas px-5 py-6 lg:px-8", mobileTab === "report" ? "block" : "hidden lg:block")}>
          {r.sources.length > 1 && (
            <div className="mb-4 flex flex-wrap items-center gap-2 text-[13px] text-muted">
              {t("Fayllar:")}
              {r.sources.map((s, i) => (
                <button key={s.name} onClick={() => goPage(s.first_page)} style={staggerStyle(i, 40)}
                  className="animate-in-up inline-flex items-center gap-1.5 rounded-lg border border-line bg-surface px-2 py-0.5 tabular-nums hover:border-primary">
                  <FileIcon className="size-3" /> {s.name} ({s.first_page}{s.last_page !== s.first_page ? `–${s.last_page}` : ""})
                </button>
              ))}
            </div>
          )}

          {isActive(r.status) && (
            <FadeIn className="mb-4">
              <div className="text-sm text-muted">{r.status_label} · {r.stage || "…"}</div>
              <Progress value={r.progress} className="mt-2" />
            </FadeIn>
          )}

          {r.status === "FAILED" && (
            <FadeIn className="flex flex-col items-start gap-3">
              <ErrorNote>{t("Xato:")} {r.error}</ErrorNote>
              <Button onClick={() => retry.mutate()} disabled={retry.isPending}>
                {retry.isPending ? <Spinner className="text-primary-foreground" /> : <RotateCcwIcon />} {t("Qayta urinish")}
              </Button>
            </FadeIn>
          )}

          {done && (report.data ? (
            <FadeIn>
              <ReportView report={report.data} onPage={r.has_pdf ? goPage : undefined} exportSlot={<ExportPanel caseId={id} report={report.data} />} />
            </FadeIn>
          ) : report.error ? (
            <ErrorNote>{report.error.message}</ErrorNote>
          ) : (
            <Empty><Spinner /></Empty>
          ))}
        </div>
      </div>
    </div>
  );
}
