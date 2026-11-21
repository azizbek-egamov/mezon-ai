/** AI xarajat radari: kunlik xarajat (ish tahlili + savol-javob), eng ko'p sarflagan foydalanuvchilar va qimmat ishlar. */
import { Card, CardContent, CardHeader, CardTitle, Empty, formatDateTime, Skeleton, staggerStyle, useLanguage } from "@mezon/web-kit";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { PageHeader } from "@/components/AdminShell";
import { StatTile } from "@/components/common";
import { CostChart } from "@/components/CostChart";
import { adminKeys, getJson, usd, type Costs } from "@/lib/admin";

export function CostsPage() {
  const { t } = useTranslation();
  const { language } = useLanguage();
  const [days, setDays] = useState(30);
  const { data, isLoading } = useQuery({ queryKey: adminKeys.costs(days), queryFn: () => getJson<Costs>(`/admin/costs?days=${days}`) });
  const total = (data?.by_day ?? []).reduce((s, d) => s + d.usd, 0);
  const cases = (data?.by_day ?? []).reduce((s, d) => s + d.cases, 0);
  const chat = (data?.by_day ?? []).reduce((s, d) => s + d.chat, 0);

  return (
    <div className="mx-auto max-w-7xl">
      <PageHeader title={t("AI xarajatlari")} subtitle={t("Ish tahlili va savol-javob uchun sarflangan mablagʻ")}
        actions={<div className="flex rounded-lg border border-line bg-canvas p-0.5">
          {[7, 30, 90].map((d) => (
            <button key={d} onClick={() => setDays(d)} className={`rounded px-3 py-1 tabular-nums text-xs ${days === d ? "bg-subtle text-ink" : "text-muted"}`}>
              {d} {t("kun")}
            </button>
          ))}
        </div>} />
      {isLoading || !data ? (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-20" style={staggerStyle(i, 60)} />)}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <StatTile index={0} label={t("Jami")} value={usd(total)} tone="gold" note={`${days} ${t("kun")}`} />
            <StatTile index={1} label={t("Oʻrtacha — kuniga")} value={usd(total / days)} />
            <StatTile index={2} label={t("Ish tahlili")} value={cases} note={cases ? `${usd(total / Math.max(1, cases + chat), 3)} / ${t("soʻrov")}` : undefined} />
            <StatTile index={3} label={t("Savollar")} value={chat} />
          </div>
          <Card className="mt-4">
            <CardHeader><CardTitle>{t("Kunlik AI xarajati")}</CardTitle></CardHeader>
            <CardContent><CostChart days={data.by_day} height={220} /></CardContent>
          </Card>
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader><CardTitle>{t("Eng koʻp sarflaganlar")}</CardTitle></CardHeader>
              <CardContent>
                {data.top_users.length ? (
                  <table className="w-full text-sm">
                    <tbody>
                      {data.top_users.map((u, i) => (
                        <tr key={u.user} className="animate-in-up border-t border-line first:border-0" style={staggerStyle(i, 40)}>
                          <td className="py-2"><Link to={`/users/${u.user}`} className="hover:text-primary">{u.full_name}</Link>
                            <div className="tabular-nums text-xs text-muted">{u.phone_number}</div></td>
                          <td className="py-2 tabular-nums text-xs text-muted">{t("Ish tahlili")}: {u.cases} · {t("Savollar")}: {u.chat}</td>
                          <td className="py-2 text-right tabular-nums font-semibold">{usd(u.usd, 3)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : <Empty>{t("Hali xarajat yoʻq")}</Empty>}
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>{t("Eng qimmat ish tahlillari")}</CardTitle>
                <p className="mt-0.5 text-xs text-muted">{t("Advokatlik siri: ish nomi va mazmuni admin panelda koʻrsatilmaydi")}</p>
              </CardHeader>
              <CardContent>
                {data.expensive_cases.length ? (
                  <table className="w-full tabular-nums text-xs">
                    <tbody>
                      {data.expensive_cases.map((c, i) => (
                        <tr key={c.id} className="animate-in-up border-t border-line first:border-0" style={staggerStyle(i, 40)}>
                          <td className="py-1.5 text-muted">{formatDateTime(c.created_at, language)}</td>
                          <td className="py-1.5"><Link to={`/users/${c.owner}`} className="hover:text-primary">{c.owner_phone}</Link></td>
                          <td className="py-1.5">{t("{{n}} varaq", { n: c.pages })}</td>
                          <td className="py-1.5">{c.status}</td>
                          <td className="py-1.5 text-right font-semibold">{usd(c.cost_usd, 3)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : <Empty>{t("Hali xarajat yoʻq")}</Empty>}
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
