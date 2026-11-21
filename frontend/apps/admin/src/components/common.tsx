import { Badge, Card, cn, formatDateTime, staggerStyle, useLanguage } from "@mezon/web-kit";
import type { TFunction } from "i18next";
import type { ComponentType, ReactNode } from "react";
import { useTranslation } from "react-i18next";

import type { AuditEvent } from "@/lib/admin";

/** Ko'rsatkich plitkasi: yorliq, qiymat, izoh (dizayn: "Faol Advokatlar 1,284") */
export function StatTile({ label, value, note, icon: Icon, tone, index = 0 }: {
  label: string; value: ReactNode; note?: ReactNode; icon?: ComponentType<{ className?: string }>; tone?: "gold" | "green" | "red" | "blue"; index?: number;
}) {
  const iconTone = { gold: "text-gold", green: "text-green", red: "text-red", blue: "text-primary" }[tone ?? "blue"];
  return (
    <Card className="animate-in-up p-4" style={staggerStyle(index, 60)}>
      <div className="flex items-start justify-between gap-2 text-xs text-muted">
        <span>{label}</span>
        {Icon && <Icon className={cn("size-4", iconTone)} />}
      </div>
      <div className="mt-1.5 text-2xl font-semibold">{value}</div>
      {note && <div className="mt-0.5 tabular-nums text-xs text-muted">{note}</div>}
    </Card>
  );
}

export function auditLabel(t: TFunction, action: string): string {
  switch (action) {
    case "user.update": return t("Foydalanuvchi oʻzgartirildi");
    case "subscription.grant": return t("Obuna berildi");
    case "subscription.cancel": return t("Obuna bekor qilindi");
    case "plan.create": return t("Tarif yaratildi");
    case "plan.update": return t("Tarif oʻzgartirildi");
    case "payment.create": return t("Toʻlov yaratildi");
    case "payment.mark_paid": return t("Toʻlov tasdiqlandi");
    case "payment.cancel": return t("Toʻlov bekor qilindi");
    case "sync.start": return t("Sinxronizatsiya boshlandi");
    case "template.create": return t("Shablon yaratildi");
    case "template.update": return t("Shablon oʻzgartirildi");
    case "template.approve": return t("Shablon tasdiqlandi");
    default: return action;
  }
}

export function AuditList({ events, compact = false }: { events: AuditEvent[]; compact?: boolean }) {
  const { t } = useTranslation();
  const { language } = useLanguage();
  if (!events.length) return <div className="py-4 text-sm text-muted">{t("Hali amal yoʻq")}</div>;
  return (
    <ul className="divide-y divide-line">
      {events.map((e, i) => (
        <li key={e.id} className="animate-in-up flex flex-wrap items-baseline gap-x-3 gap-y-0.5 py-2 text-sm" style={staggerStyle(i, 35)}>
          <span className="tabular-nums text-xs text-muted">{formatDateTime(e.created_at, language)}</span>
          <span className="font-medium">{auditLabel(t, e.action)}</span>
          <span className="text-muted">{e.actor_name || "—"}</span>
          {!compact && <span className="tabular-nums text-xs text-muted">{e.target}</span>}
          {!compact && Object.keys(e.details ?? {}).length > 0 && (
            <code className="w-full truncate tabular-nums text-xs text-muted">{JSON.stringify(e.details)}</code>
          )}
        </li>
      ))}
    </ul>
  );
}

export function RoleBadge({ role = "", label }: { role?: string; label?: string }) {
  const tone = role === "SUPERADMIN" ? "gold" : role === "MODERATOR" ? "info" : role === "LAWYER" ? "neutral" : "neutral";
  return <Badge tone={tone}>{label ?? role}</Badge>;
}

export function Pager({ page, count, pageSize = 20, onPage }: { page: number; count: number; pageSize?: number; onPage(p: number): void }) {
  const pages = Math.max(1, Math.ceil(count / pageSize));
  if (pages <= 1) return null;
  return (
    <div className="mt-3 flex items-center justify-end gap-2 tabular-nums text-xs text-muted">
      <button className="rounded border border-line px-2 py-1 hover:text-ink disabled:opacity-40" disabled={page <= 1} onClick={() => onPage(page - 1)}>←</button>
      <span>{page} / {pages}</span>
      <button className="rounded border border-line px-2 py-1 hover:text-ink disabled:opacity-40" disabled={page >= pages} onClick={() => onPage(page + 1)}>→</button>
    </div>
  );
}
