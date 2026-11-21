/** Anti-fraud radari (TZ §8.2, hozircha oddiy qoida): bitta IP dan ko'p akkaunt; shubhali deb belgilash / bloklash. */
import { Badge, Button, Card, CustomSelect, formatDate, notifyError, Skeleton, staggerStyle } from "@mezon/web-kit";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BanIcon, FlagIcon, RadarIcon, ShieldCheckIcon } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { PageHeader } from "@/components/AdminShell";
import { adminKeys, getJson, sendJson, type AntiFraud } from "@/lib/admin";

export function AntiFraudPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [min, setMin] = useState(3);
  const { data, isLoading } = useQuery({ queryKey: adminKeys.antifraud(min), queryFn: () => getJson<AntiFraud>(`/admin/antifraud?min=${min}`) });
  const patch = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Record<string, boolean> }) => sendJson(`/admin/users/${id}`, "PATCH", body),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["admin"] }),
    onError: (err) => notifyError(err, t),
  });

  return (
    <div className="mx-auto max-w-7xl">
      <PageHeader title={t("Shubhali faollik")} subtitle={t("Bitta IP manzildan roʻyxatdan oʻtgan yoki kirgan koʻp akkaunt")}
        actions={<label className="flex items-center gap-2 text-sm text-muted">
          {t("Kamida akkaunt")}
          <CustomSelect
            value={String(min)}
            onValueChange={(val) => setMin(Number(val))}
            size="sm"
            className="w-20 tabular-nums text-xs"
            options={[2, 3, 5, 10].map((n) => ({ value: String(n), label: String(n) }))}
          />
        </label>} />
      {isLoading || !data ? (
        <div className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
          <div className="flex flex-col gap-3">
            {[0, 1, 2].map((i) => <Skeleton key={i} className="h-24" style={staggerStyle(i, 70)} />)}
          </div>
          <Skeleton className="h-48" />
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
          <div className="flex flex-col gap-3">
            {data.shared_ips.length ? data.shared_ips.map((g, gi) => {
              const high = g.count >= 5;
              return (
                <Card key={g.ip} accent={high ? "red" : "amber"} className="animate-in-up p-4" style={staggerStyle(gi, 70)}>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={high ? "bad" : "warn"} mono>{high ? t("XAVF: YUQORI") : t("XAVF: OʻRTA")}</Badge>
                    <span className="tabular-nums text-sm">IP: {g.ip}</span>
                    <span className="ml-auto tabular-nums text-xs text-muted">{t("{{n}} ta akkaunt bitta IP dan", { n: g.count })} · {t("shubhali")}: {g.flagged}</span>
                  </div>
                  <ul className="mt-3 divide-y divide-line rounded border border-line bg-canvas">
                    {g.accounts.map((a) => (
                      <li key={a.id} className="flex flex-wrap items-center gap-2 px-3 py-2 text-sm">
                        <Link to={`/users/${a.id}`} className="min-w-0 flex-1 truncate hover:text-primary">{a.full_name}
                          <span className="ml-2 tabular-nums text-xs text-muted">{a.phone_number} · {formatDate(a.date_joined)}</span></Link>
                        {a.is_fraud_flagged && <Badge tone="bad">{t("shubhali")}</Badge>}
                        {!a.is_active && <Badge tone="bad">{t("bloklangan")}</Badge>}
                        <Button size="sm" variant="outline" disabled={patch.isPending} title={t("Shubhali deb belgilash (anti-fraud)")}
                          onClick={() => patch.mutate({ id: a.id, body: { is_fraud_flagged: !a.is_fraud_flagged } })}>
                          {a.is_fraud_flagged ? <ShieldCheckIcon /> : <FlagIcon />}
                        </Button>
                        {a.is_active && (
                          <Button size="sm" variant="destructive" disabled={patch.isPending} title={t("Bloklash")}
                            onClick={() => window.confirm(t("Akkaunt bloklansinmi? Foydalanuvchi tizimga kira olmaydi.")) && patch.mutate({ id: a.id, body: { is_active: false, is_fraud_flagged: true } })}>
                            <BanIcon />
                          </Button>
                        )}
                      </li>
                    ))}
                  </ul>
                </Card>
              );
            }) : (
              <Card accent="green" className="p-6 text-center">
                <RadarIcon className="mx-auto size-8 text-green" />
                <div className="mt-2 text-sm text-muted">{t("Shubhali faollik topilmadi")}</div>
              </Card>
            )}
          </div>
          <Card className="h-fit p-4">
            <div className="label-code mb-2 text-muted">{t("Shubhali deb belgilanganlar")} · {data.flagged.length}</div>
            {data.flagged.length ? (
              <ul className="divide-y divide-line">
                {data.flagged.map((u, i) => (
                  <li key={u.id} className="animate-in-up py-2 text-sm" style={staggerStyle(i, 35)}>
                    <Link to={`/users/${u.id}`} className="hover:text-primary">{u.full_name}</Link>
                    <div className="tabular-nums text-xs text-muted">{u.phone_number} · {u.last_login_ip ?? u.registered_ip ?? "—"}</div>
                  </li>
                ))}
              </ul>
            ) : <div className="text-sm text-muted">—</div>}
            <p className="mt-3 text-xs text-muted">{t("Qurilma barmoq izi va SMS tasdiqlash keyingi bosqichda (TZ §8.2).")}</p>
          </Card>
        </div>
      )}
    </div>
  );
}
