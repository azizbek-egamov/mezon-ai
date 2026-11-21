/** Tarif va limitlar (TZ §8.1): joriy tarif, sarf, tariflar ro'yxati. To'lov (Payme/Click) — keyingi bosqich. */
import { unwrap, type Schemas } from "@mezon/api-client";
import { useQuery } from "@tanstack/react-query";
import type { TFunction } from "i18next";
import { CheckIcon, CrownIcon, GraduationCapIcon } from "lucide-react";
import { useTranslation } from "react-i18next";

import { api, Badge, Card, cn, formatDate, formatMoney, FadeIn, PageHeader, Progress, Skeleton, staggerDelay, staggerStyle, useAuth, useLanguage } from "@mezon/web-kit";

import { keys, useUsage } from "@/lib/queries";

function planFeatures(t: TFunction, p: Schemas["Plan"]): string[] {
  const out = [t("Bitta ish — {{n}} varaqgacha", { n: p.max_pages_per_case })];
  if (p.lifetime_case_limit) out.push(t("Ish tahlili — jami {{n}} marta", { n: p.lifetime_case_limit }));
  else if (p.daily_case_limit) {
    out.push(t("Ish tahlili — kuniga {{n}} tagacha", { n: p.daily_case_limit }) +
      (p.monthly_case_limit ? `, ${t("oyiga {{n}} tagacha", { n: p.monthly_case_limit })}` : ""));
  } else out.push(t("Ish tahlili — cheklovsiz"));
  if (p.lifetime_chat_limit) out.push(t("Savol-javob — jami {{n}} ta savol", { n: p.lifetime_chat_limit }));
  else if (p.daily_chat_limit) out.push(t("Savol-javob — kuniga {{n}} tagacha", { n: p.daily_chat_limit }));
  else out.push(t("Savol-javob — cheklovsiz"));
  const tpl = p.lifetime_template_limit
    ? t("Hujjat yuklab olish — jami {{n}} ta", { n: p.lifetime_template_limit })
    : p.daily_template_limit
      ? t("Hujjat yuklab olish — kuniga {{n}} ta", { n: p.daily_template_limit })
      : t("Hujjatlar — cheklovsiz");
  out.push(p.watermark ? `${tpl} · ${t("tarif belgisi bilan")}` : tpl);
  if (p.priority_queue) out.push(t("Ish tahlili navbatida oldinda"));
  return out;
}

export function BillingPage() {
  const { t } = useTranslation();
  const { language } = useLanguage();
  const { user } = useAuth();
  const usage = useUsage();
  const plans = useQuery({ queryKey: keys.plans, queryFn: () => unwrap(api.client.GET("/api/v1/billing/plans")) });
  const u = usage.data;

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6 px-5 py-10 sm:px-8">
      <PageHeader title={t("Tarif va limitlar")} className="mb-2" />
      {!u ? (
        <Skeleton className="h-48" />
      ) : (
        <Card className="animate-in-up p-7">
          <div className="label-code text-muted">{t("Joriy tarifingiz")}</div>
          <div className="mt-1 font-serif text-2xl font-semibold">{u.plan_name}</div>
          {u.unlimited ? (
            <p className="mt-1 text-sm text-muted">{t("Cheklovlarsiz rejim (xodim akkaunti yoki kvotalar oʻchirilgan).")}</p>
          ) : (
            u.expires_at && <p className="mt-1 text-sm text-muted">{t("Obuna {{d}} gacha amal qiladi.", { d: formatDate(u.expires_at, language) })}</p>
          )}
          <p className="text-sm text-muted">{t("Bitta ish hajmi: {{n}} varaqgacha.", { n: u.max_pages })}</p>
          <div className="mt-6 grid gap-x-8 gap-y-4 sm:grid-cols-2">
            {u.usage.map((row, i) => (
              <FadeIn key={row.label} delay={staggerDelay(i, 60)}>
                <div className="flex justify-between gap-2 text-sm">
                  <span>{row.label}</span>
                  <span className="tabular-nums">{row.used} / {row.limit}</span>
                </div>
                <Progress className="mt-1.5" value={(row.used / Math.max(1, row.limit)) * 100} tone={row.used >= row.limit ? "red" : "blue"} />
              </FadeIn>
            ))}
          </div>
        </Card>
      )}

      <h2 className="mt-4 text-xl font-semibold">{t("Tariflar")}</h2>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {(plans.data ?? []).map((p, i) => {
          const current = p.code === u?.plan;
          const isStudent = p.code === "STUDENT";
          const premium = p.code.startsWith("ENTERPRISE");
          return (
            <Card
              key={p.code}
              className={cn(
                "animate-in-up flex flex-col p-6",
                current && "border-primary ring-1 ring-primary",
                isStudent && !current && "border-amber-500/30 bg-amber-500/[0.02]"
              )}
              style={staggerStyle(i, 70)}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-serif text-lg font-semibold">{p.name}</span>
                {current ? (
                  <Badge tone="info">{t("Joriy tarifingiz")}</Badge>
                ) : isStudent ? (
                  <div className="flex items-center gap-1.5">
                    {user?.role === "STUDENT" && <Badge tone="gold" className="text-[10px]">{t("Sizga tavsiya etiladi")}</Badge>}
                    <span className="flex items-center gap-1 text-xs font-medium text-amber-700 dark:text-amber-400">
                      <GraduationCapIcon className="size-4" />
                      {t("Talabalar uchun")}
                    </span>
                  </div>
                ) : (
                  premium && <CrownIcon className="size-4 text-gold" />
                )}
              </div>
              <div className="mt-3 text-[28px] font-semibold tabular-nums text-ink">
                {p.price_uzs ? (
                  <>
                    {formatMoney(p.price_uzs)} <span className="text-sm font-normal text-muted">{t("soʻm")}</span>
                  </>
                ) : p.code === "FREE" ? (
                  "0"
                ) : (
                  <span className="text-sm font-normal text-muted">{t("narx belgilanmagan")}</span>
                )}
              </div>
              <ul className="mt-5 flex flex-col gap-2.5 border-t border-line pt-5 text-sm">
                {planFeatures(t, p).map((f) => (
                  <li key={f} className="flex gap-2">
                    <CheckIcon className="mt-0.5 size-4 shrink-0 text-green" />
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
            </Card>
          );
        })}
      </div>
      <p className="text-sm text-muted">{t("Obunani Payme va Click orqali rasmiylashtirish tez orada qoʻshiladi. Hozircha tarifni oʻzgartirish uchun administrator bilan bogʻlaning.")}</p>
    </div>
  );
}
