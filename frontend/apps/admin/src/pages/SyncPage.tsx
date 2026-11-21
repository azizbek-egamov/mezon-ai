/** lex.uz sinxronizatsiyasi (TZ §6.4): ishga tushirishlar jurnali, natijalar; superadmin — majburiy sinxronizatsiya. */
import { unwrap } from "@mezon/api-client";
import { api, Badge, Button, Card, Checkbox, Empty, FadeIn, formatDateTime, Input, Label, notifyError, Skeleton, Spinner, staggerStyle, useLanguage } from "@mezon/web-kit";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCwIcon } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { PageHeader } from "@/components/AdminShell";
import { adminKeys, sendJson, useStaff } from "@/lib/admin";

import { syncTone } from "./DashboardPage";

export function SyncPage() {
  const { t } = useTranslation();
  const { language } = useLanguage();
  const queryClient = useQueryClient();
  const staff = useStaff();
  const [days, setDays] = useState("7");
  const [checkCodes, setCheckCodes] = useState(false);
  const [openId, setOpenId] = useState<number | null>(null);
  const { data, isLoading } = useQuery({
    queryKey: adminKeys.sync,
    queryFn: () => unwrap(api.client.GET("/api/v1/admin/sync/")),
    refetchInterval: (q) => (q.state.data?.results.some((r) => r.status === "RUNNING") ? 5000 : false),
  });
  const start = useMutation({
    mutationFn: () => sendJson("/admin/sync/start", "POST", { days: Number(days) || 7, check_codes: checkCodes }),
    onSuccess: () => {
      toast.success(t("Sinxronizatsiya boshlandi"));
      setTimeout(() => void queryClient.invalidateQueries({ queryKey: adminKeys.sync }), 1500);
    },
    onError: (err) => notifyError(err, t),
  });
  const running = data?.results.some((r) => r.status === "RUNNING");

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader title={t("lex.uz sinxronizatsiyasi")} subtitle={t("Har kecha 02:00 da (tools/nightly_sync.ps1) — yangi hujjatlar, tahrirlar va indeks")} />
      {staff.data?.is_superadmin && (
        <Card accent="blue" className="animate-in-up mb-4 flex flex-wrap items-end gap-4 p-4">
          <div>
            <Label htmlFor="days">{t("Oxirgi necha kun")}</Label>
            <Input id="days" type="number" min={1} max={365} value={days} onChange={(e) => setDays(e.target.value)} className="h-9 w-28 tabular-nums" />
          </div>
          <label className="flex items-start gap-2 pb-2 text-sm">
            <Checkbox checked={checkCodes} onCheckedChange={(v) => setCheckCodes(v === true)} />
            {t("Barcha kodekslarni tekshirish (uzoq)")}
          </label>
          <Button onClick={() => window.confirm(t("lex.uz dan yuklash va qayta indekslash boshlansinmi? Bir necha daqiqa davom etadi.")) && start.mutate()}
            disabled={start.isPending || running}>
            {start.isPending || running ? <Spinner className="text-primary-foreground" /> : <RefreshCwIcon />} {t("Majburiy sinxronizatsiya")}
          </Button>
          <p className="w-full text-xs text-muted">{t("LLM chaqirilmaydi; lex.uz va Qdrant server ishlab turishi kerak.")}</p>
        </Card>
      )}
      <Card>
        {isLoading ? (
          <div className="flex flex-col gap-2 p-4">
            {[0, 1, 2].map((i) => <Skeleton key={i} className="h-10" style={staggerStyle(i, 60)} />)}
          </div>
        ) : !data?.results.length ? <Empty>{t("Hali sinxronizatsiya boʻlmagan")}</Empty> : (
          <ul className="divide-y divide-line">
            {data.results.map((r, i) => (
              <li key={r.id} className="animate-in-up px-4 py-3" style={staggerStyle(i, 40)}>
                <button className="flex w-full flex-wrap items-center gap-3 text-left" onClick={() => setOpenId(openId === r.id ? null : r.id)}>
                  <Badge tone={syncTone(r.status)}>{r.status_label}</Badge>
                  <span className="tabular-nums text-xs">{formatDateTime(r.started_at, language)}</span>
                  <span className="tabular-nums text-xs text-muted">{r.finished_at ? `→ ${formatDateTime(r.finished_at, language)}` : "…"}</span>
                  <span className="ml-auto flex flex-wrap gap-1.5">
                    {Object.entries(r.summary).filter(([, v]) => Number(v) > 0).map(([k, v]) => <Badge key={k} mono>{k}: {String(v)}</Badge>)}
                  </span>
                </button>
                {openId === r.id && (
                  <FadeIn as="pre" className="mt-3 max-h-80 overflow-auto rounded border border-line bg-canvas p-3 tabular-nums text-xs leading-relaxed text-muted">{r.log || "—"}</FadeIn>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
