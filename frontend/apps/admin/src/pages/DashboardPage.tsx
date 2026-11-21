/** SuperAdmin Radar (designs/superadmin_anti_fraud_radar): asosiy ko'rsatkichlar, AI xarajati, shubhali faollik, jurnal. */
import { Badge, Card, CardContent, CardHeader, CardTitle, Empty, formatDateTime, Spinner, staggerStyle, useLanguage } from "@mezon/web-kit";
import { useQuery } from "@tanstack/react-query";
import { ActivityIcon, AlertTriangleIcon, BriefcaseIcon, CoinsIcon, CreditCardIcon, RefreshCwIcon, UsersIcon } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { PageHeader } from "@/components/AdminShell";
import { AuditList, StatTile } from "@/components/common";
import { CostChart } from "@/components/CostChart";
import { adminKeys, getJson, usd, type AntiFraud, type Dashboard } from "@/lib/admin";

export function syncTone(status?: string) {
  return status === "OK" ? "ok" : status === "RUNNING" ? "info" : status === "PARTIAL" ? "warn" : "bad";
}

export function DashboardPage() {
  const { t } = useTranslation();
  const { language } = useLanguage();
  const { data, isLoading } = useQuery({ queryKey: adminKeys.dashboard, queryFn: () => getJson<Dashboard>("/admin/dashboard"), refetchInterval: 60_000 });
  const fraud = useQuery({ queryKey: adminKeys.antifraud(3), queryFn: () => getJson<AntiFraud>("/admin/antifraud?min=3") });

  if (isLoading || !data) return <Empty><Spinner className="size-6" /></Empty>;
  const sync = data.last_sync;

  return (
    <div className="mx-auto max-w-7xl">
      <PageHeader title={t("Boshqaruv paneli")} />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile index={0} icon={UsersIcon} tone="gold" label={t("Foydalanuvchilar")} value={data.users.total.toLocaleString()}
          note={`${t("Advokat / yurist")}: ${data.users.lawyers} · ${t("Fuqaro")}: ${data.users.clients} · +${data.users.new_today} ${t("bugun")}`} />
        <StatTile index={1} icon={ActivityIcon} tone="green" label={t("Faol (7 kun)")} value={data.users.active_7d.toLocaleString()}
          note={`${t("Savollar — bugun")}: ${data.chat_today}`} />
        <StatTile index={2} icon={CoinsIcon} tone="gold" label={t("AI xarajati — bugun")} value={usd(data.cost.today)}
          note={`${t("shu oy")}: ${usd(data.cost.month)}`} />
        <StatTile index={3} icon={BriefcaseIcon} label={t("Ish tahlili — bugun")} value={data.cases.today}
          note={`${t("navbatda")}: ${data.cases.active} · ${t("xato")}: ${data.cases.failed_today} · ${t("shu oy")}: ${data.cases.month}`} />
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>{t("Kunlik AI xarajati")} · 30 {t("kun")}</CardTitle>
            <Link to="/costs" className="text-xs text-primary hover:underline">{t("AI xarajatlari")} →</Link>
          </CardHeader>
          <CardContent><CostChart days={data.cost.by_day} /></CardContent>
        </Card>

        <div className="flex flex-col gap-4">
          <Card accent={data.fraud_signals ? "red" : "green"} className="p-4">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 font-semibold"><AlertTriangleIcon className="size-4 text-red" /> {t("Shubhali faollik")}</div>
              <Badge tone={data.fraud_signals ? "bad" : "ok"}>{data.fraud_signals}</Badge>
            </div>
            <div className="mt-3 flex flex-col gap-2">
              {(fraud.data?.shared_ips ?? []).slice(0, 3).map((g, i) => (
                <Link key={g.ip} to={`/users?ip=${encodeURIComponent(g.ip)}`} style={staggerStyle(i, 50)}
                  className="animate-in-up rounded-lg border border-line px-3 py-2 text-sm hover:border-red/50">
                  <div className="tabular-nums text-xs">IP: {g.ip}</div>
                  <div className="text-xs text-red">{t("{{n}} ta akkaunt bitta IP dan", { n: g.count })}</div>
                </Link>
              ))}
              {fraud.data && !fraud.data.shared_ips.length && <div className="text-sm text-muted">{t("Shubhali faollik topilmadi")}</div>}
              <Link to="/antifraud" className="text-xs text-primary hover:underline">{t("Shubhali faollik")} →</Link>
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 font-semibold"><RefreshCwIcon className="size-4 text-green" /> {t("lex.uz sinxronizatsiyasi")}</div>
              {sync && <Badge tone={syncTone(sync.status)}>{sync.status_label}</Badge>}
            </div>
            {sync ? (
              <div className="mt-2 grid grid-cols-2 gap-2 text-center">
                <div className="rounded border border-line bg-canvas p-2">
                  <div className="text-xs text-muted">{t("Yangi hujjatlar")}</div>
                  <div className="text-lg font-bold text-green">{Number(sync.summary.new_documents ?? 0)}</div>
                </div>
                <div className="rounded border border-line bg-canvas p-2">
                  <div className="text-xs text-muted">{t("Qayta yuklangan")}</div>
                  <div className="text-lg font-bold text-gold">{Number(sync.summary.refreshed ?? 0)}</div>
                </div>
                <div className="col-span-2 tabular-nums text-xs text-muted">{formatDateTime(sync.started_at, language)}</div>
              </div>
            ) : <div className="mt-2 text-sm text-muted">{t("Hali sinxronizatsiya boʻlmagan")}</div>}
            <Link to="/sync" className="mt-2 block text-xs text-primary hover:underline">{t("lex.uz sinxronizatsiyasi")} →</Link>
          </Card>

          <Card className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 font-semibold"><CreditCardIcon className="size-4 text-primary" /> {t("Faol obunalar")}</div>
              <Link to="/payments" className="text-xs text-primary hover:underline">{t("Kutilayotgan toʻlovlar")}: {data.payments_pending}</Link>
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {data.subscriptions.length ? data.subscriptions.map((s) => <Badge key={s.plan__code}>{s.plan__name}: {s.count}</Badge>)
                : <span className="text-sm text-muted">—</span>}
            </div>
          </Card>
        </div>
      </div>

      <Card className="mt-4">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>{t("Soʻnggi amallar")}</CardTitle>
          <Link to="/audit" className="text-xs text-primary hover:underline">{t("Amallar jurnali")} →</Link>
        </CardHeader>
        <CardContent><AuditList events={data.recent_audit} compact /></CardContent>
      </Card>
    </div>
  );
}
