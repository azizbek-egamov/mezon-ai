/** Foydalanuvchilar: qidiruv, filtrlar; profil — rol, holat, fraud belgisi, obuna berish, sarf, to'lovlar, ishlar (metama'lumot). */
import { unwrap } from "@mezon/api-client";
import {
  api, Badge, Button, Card, CardContent, CardHeader, CardTitle, Checkbox, Empty, FadeIn, formatDate, formatDateTime, Input, Label,
  NativeSelect, notifyError, Progress, Skeleton, Spinner, staggerStyle, useLanguage,
} from "@mezon/web-kit";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeftIcon, FlagIcon, GiftIcon, SaveIcon, SearchIcon } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams, useSearchParams } from "react-router";
import { toast } from "sonner";

import { PageHeader } from "@/components/AdminShell";
import { AuditList, Pager, RoleBadge } from "@/components/common";
import { adminKeys, getJson, sendJson, usd, type AdminUser, type UserDetail } from "@/lib/admin";

function useDebounced<T>(value: T, ms = 300): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setV(value), ms);
    return () => clearTimeout(id);
  }, [value, ms]);
  return v;
}

export function UsersPage() {
  const { t } = useTranslation();
  const { language } = useLanguage();
  const [params, setParams] = useSearchParams();
  const [q, setQ] = useState(params.get("q") ?? "");
  const query = useDebounced(q);
  const role = params.get("role") ?? "";
  const flagged = params.get("flagged") === "1";
  const ip = params.get("ip") ?? "";
  const page = Number(params.get("page") ?? 1);
  const set = (patch: Record<string, string | null>) => setParams((p) => {
    Object.entries(patch).forEach(([k, v]) => (v ? p.set(k, v) : p.delete(k)));
    if (!("page" in patch)) p.delete("page");
    return p;
  });

  const filters = { q: query, role, flagged: flagged ? "1" : "", ip, page };
  const { data, isLoading } = useQuery({
    queryKey: adminKeys.users(filters),
    queryFn: () => unwrap(api.client.GET("/api/v1/admin/users/", { params: { query: {
      q: query || undefined, role: role || undefined, flagged: flagged || undefined, ip: ip || undefined, page,
    } } })),
    placeholderData: keepPreviousData,
  });

  return (
    <div className="mx-auto max-w-7xl">
      <PageHeader title={t("Foydalanuvchilar")} subtitle={data ? `${data.count}` : undefined} />
      <FadeIn className="mb-4 flex flex-wrap items-center gap-2">
        <div className="relative min-w-64 flex-1">
          <SearchIcon className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("Telefon, F.I.Sh. yoki guvohnoma")} className="pl-9"
            aria-label={t("Telefon, F.I.Sh. yoki guvohnoma")} />
        </div>
        <NativeSelect value={role} onChange={(e) => set({ role: e.target.value })} className="w-48" aria-label={t("Rol")}>
          <option value="">{t("Barcha rollar")}</option>
          <option value="LAWYER">{t("Advokat / yurist")}</option>
          <option value="CLIENT">{t("Fuqaro")}</option>
          <option value="MODERATOR">{t("Yurist-moderator")}</option>
          <option value="SUPERADMIN">{t("Superadmin")}</option>
        </NativeSelect>
        <label className="flex items-center gap-2 text-sm text-muted">
          <Checkbox checked={flagged} onCheckedChange={(v) => set({ flagged: v === true ? "1" : null })} />
          {t("Faqat shubhalilar")}
        </label>
        {ip && <Badge tone="bad" mono>IP: {ip} <button onClick={() => set({ ip: null })} aria-label="×" className="ml-1">×</button></Badge>}
      </FadeIn>
      <Card>
        {isLoading ? (
          <div className="flex flex-col gap-2 p-4">
            {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-11" style={staggerStyle(i, 60)} />)}
          </div>
        ) : !data?.results.length ? <Empty>{t("Topilmadi.")}</Empty> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="label-code text-left text-muted">
                  <th className="px-4 py-3 font-semibold">{t("F.I.Sh.")}</th>
                  <th className="px-2 py-3 font-semibold">{t("Rol")}</th>
                  <th className="px-2 py-3 font-semibold">{t("Tarif")}</th>
                  <th className="px-2 py-3 font-semibold">{t("Ishlar")}</th>
                  <th className="px-2 py-3 font-semibold">{t("Roʻyxatdan oʻtgan")}</th>
                  <th className="px-2 py-3 font-semibold">{t("Oxirgi kirish")}</th>
                  <th className="px-4 py-3 font-semibold">IP</th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((u, i) => (
                  <tr key={u.id} className="animate-in-up border-t border-line hover:bg-subtle/40" style={staggerStyle(i)}>
                    <td className="px-4 py-2.5">
                      <Link to={`/users/${u.id}`} className="block font-medium hover:text-primary">{u.full_name}</Link>
                      <span className="tabular-nums text-xs text-muted">{u.phone_number}</span>
                      {!u.is_active && <Badge tone="bad" className="ml-2">{t("bloklangan")}</Badge>}
                      {u.is_fraud_flagged && <FlagIcon className="ml-2 inline size-3.5 text-red" aria-label={t("shubhali")} />}
                    </td>
                    <td className="px-2 py-2.5"><RoleBadge role={u.role} label={u.role_label} /></td>
                    <td className="px-2 py-2.5 tabular-nums text-xs">{u.plan}</td>
                    <td className="px-2 py-2.5 tabular-nums">{u.cases_count}</td>
                    <td className="px-2 py-2.5 tabular-nums text-xs text-muted">{formatDate(u.date_joined)}</td>
                    <td className="px-2 py-2.5 tabular-nums text-xs text-muted">{u.last_login ? formatDateTime(u.last_login, language) : "—"}</td>
                    <td className="px-4 py-2.5 tabular-nums text-xs text-muted">
                      {u.last_login_ip || u.registered_ip ? (
                        <button className="hover:text-red" onClick={() => set({ ip: (u.last_login_ip || u.registered_ip)! })}>{u.last_login_ip || u.registered_ip}</button>
                      ) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      {data && <Pager page={page} count={data.count} onPage={(p) => set({ page: String(p) })} />}
    </div>
  );
}

function EditUser({ user }: { user: AdminUser }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [role, setRole] = useState(user.role);
  const [active, setActive] = useState(!!user.is_active);
  const [flag, setFlag] = useState(!!user.is_fraud_flagged);
  const save = useMutation({
    mutationFn: () => sendJson<AdminUser>(`/admin/users/${user.id}`, "PATCH", { role, is_active: active, is_fraud_flagged: flag }),
    onSuccess: () => {
      toast.success(t("Saqlandi"));
      void queryClient.invalidateQueries({ queryKey: ["admin"] });
    },
    onError: (err) => notifyError(err, t),
  });
  return (
    <Card className="p-4">
      <div className="label-code mb-3 text-muted">{t("Huquqlar va holat")}</div>
      <div className="flex flex-col gap-3">
        <div>
          <Label htmlFor="role">{t("Rol")}</Label>
          <NativeSelect id="role" value={role} onChange={(e) => setRole(e.target.value as AdminUser["role"])}>
            <option value="CLIENT">{t("Fuqaro")}</option>
            <option value="LAWYER">{t("Advokat / yurist")}</option>
            <option value="MODERATOR">{t("Yurist-moderator")}</option>
            <option value="SUPERADMIN">{t("Superadmin")}</option>
          </NativeSelect>
        </div>
        <label className="flex items-start gap-3 text-sm">
          <Checkbox checked={active} onCheckedChange={(v) => setActive(v === true)} />
          <span>{t("Faol (tizimga kira oladi)")}</span>
        </label>
        <label className="flex items-start gap-3 text-sm">
          <Checkbox checked={flag} onCheckedChange={(v) => setFlag(v === true)} />
          <span>{t("Shubhali deb belgilash (anti-fraud)")}</span>
        </label>
        <Button onClick={() => save.mutate()} disabled={save.isPending} className="self-start">
          {save.isPending ? <Spinner className="text-primary-foreground" /> : <SaveIcon />} {t("Saqlash")}
        </Button>
      </div>
    </Card>
  );
}

function GrantPlan({ userId }: { userId: string }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const plans = useQuery({ queryKey: adminKeys.plans, queryFn: () => unwrap(api.client.GET("/api/v1/admin/plans/")) });
  const [plan, setPlan] = useState("");
  const [days, setDays] = useState("");
  const grant = useMutation({
    mutationFn: () => sendJson(`/admin/users/${userId}/subscriptions`, "POST", { plan, ...(days ? { days: Number(days) } : {}) }),
    onSuccess: () => {
      toast.success(t("Obuna berildi"));
      setDays("");
      void queryClient.invalidateQueries({ queryKey: ["admin"] });
    },
    onError: (err) => notifyError(err, t),
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (plan) grant.mutate();
  };
  const selectable = (plans.data ?? []).filter((p) => p.is_active && p.code !== "FREE");
  return (
    <Card className="p-4">
      <div className="label-code mb-3 text-muted">{t("Obuna berish")}</div>
      <form onSubmit={submit} className="flex flex-col gap-3">
        <NativeSelect value={plan} onChange={(e) => setPlan(e.target.value)} aria-label={t("Tarif")}>
          <option value="">— {t("Tarif")} —</option>
          {selectable.map((p) => <option key={p.code} value={p.code}>{p.display_name} ({p.duration_days ?? "∞"} {t("kun")})</option>)}
        </NativeSelect>
        <Input type="number" min={1} value={days} onChange={(e) => setDays(e.target.value)} placeholder={t("Muddat, kun (boʻsh — tarif muddati)")}
          aria-label={t("Muddat, kun (boʻsh — tarif muddati)")} className="tabular-nums" />
        <Button type="submit" variant="gold" disabled={!plan || grant.isPending} className="self-start">
          {grant.isPending ? <Spinner /> : <GiftIcon />} {t("Obuna berish")}
        </Button>
      </form>
    </Card>
  );
}

export function UserDetailPage() {
  const { id = "" } = useParams();
  const { t } = useTranslation();
  const { language } = useLanguage();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useQuery({ queryKey: adminKeys.user(id), queryFn: () => getJson<UserDetail>(`/admin/users/${id}`) });
  const cancel = useMutation({
    mutationFn: (subId: number) => sendJson(`/admin/subscriptions/${subId}/cancel`, "POST"),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["admin"] }),
    onError: (err) => notifyError(err, t),
  });

  if (isLoading) return <Empty><Spinner className="size-6" /></Empty>;
  if (!data) return <Empty>{error?.message ?? t("Topilmadi")}</Empty>;
  const u = data.user;

  return (
    <div className="mx-auto max-w-7xl">
      <button onClick={() => navigate(-1)} className="mb-3 inline-flex items-center gap-1 text-xs text-muted hover:text-ink">
        <ArrowLeftIcon className="size-3.5" /> {t("Foydalanuvchilar")}
      </button>
      <PageHeader title={u.full_name} subtitle={`${u.phone_number} · ${u.advocate_license_no || "—"}`}
        actions={<div className="flex flex-wrap gap-1.5">
          <RoleBadge role={u.role} label={u.role_label} />
          <Badge mono>{u.plan_name}</Badge>
          {!u.is_active && <Badge tone="bad">{t("bloklangan")}</Badge>}
          {u.is_fraud_flagged && <Badge tone="bad">{t("shubhali")}</Badge>}
        </div>} />

      <div className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(280px,1fr)]">
        <div className="flex flex-col gap-4">
          <Card>
            <CardHeader><CardTitle>{t("Sarf")}</CardTitle></CardHeader>
            <CardContent>
              <div className="grid gap-3 sm:grid-cols-2">
                {data.usage.map((row) => (
                  <div key={row.label}>
                    <div className="flex justify-between text-sm"><span>{row.label}</span><span className="tabular-nums">{row.used} / {row.limit}</span></div>
                    <Progress className="mt-1" value={(row.used / Math.max(1, row.limit)) * 100} tone={row.used >= row.limit ? "red" : "blue"} />
                  </div>
                ))}
              </div>
              <div className="mt-3 tabular-nums text-xs text-muted">
                {t("Bitta ish hajmi: {{n}} varaqgacha.", { n: data.max_pages })} · {t("AI xarajati — jami")}: {usd(data.cost_total_usd, 4)}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>{t("Obunalar")}</CardTitle></CardHeader>
            <CardContent>
              {data.subscriptions.length ? (
                <table className="w-full text-sm">
                  <tbody>
                    {data.subscriptions.map((s) => (
                      <tr key={s.id} className="border-t border-line first:border-0">
                        <td className="py-2 font-medium">{s.plan_name}</td>
                        <td className="py-2 tabular-nums text-xs text-muted">{formatDate(s.started_at)} → {s.expires_at ? formatDate(s.expires_at) : "∞"}</td>
                        <td className="py-2"><Badge tone={s.is_current ? "ok" : "neutral"} mono>{s.is_current ? t("faol") : s.status}</Badge></td>
                        <td className="py-2 tabular-nums text-xs text-muted">{s.source}</td>
                        <td className="py-2 text-right">
                          {s.is_current && <Button size="sm" variant="destructive" disabled={cancel.isPending}
                            onClick={() => window.confirm(t("Obunani bekor qilasizmi?")) && cancel.mutate(s.id)}>{t("Bekor qilish")}</Button>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : <div className="text-sm text-muted">—</div>}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{t("Ishlar")}</CardTitle>
              <p className="mt-0.5 text-xs text-muted">{t("Advokatlik siri: ish nomi va mazmuni admin panelda koʻrsatilmaydi")}</p>
            </CardHeader>
            <CardContent>
              {data.cases.length ? (
                <table className="w-full text-sm">
                  <tbody>
                    {data.cases.map((c) => (
                      <tr key={c.id} className="border-t border-line first:border-0 tabular-nums text-xs">
                        <td className="py-1.5 text-muted">{formatDateTime(c.created_at, language)}</td>
                        <td className="py-1.5">{c.category}</td>
                        <td className="py-1.5">{t("{{n}} varaq", { n: c.pages })}</td>
                        <td className="py-1.5">{c.status}</td>
                        <td className="py-1.5 text-right">{usd(c.cost_usd, 3)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : <div className="text-sm text-muted">{t("Hali ish yuklanmagan.")}</div>}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>{t("Amallar jurnali")}</CardTitle></CardHeader>
            <CardContent><AuditList events={data.audit} /></CardContent>
          </Card>
        </div>

        <div className="flex flex-col gap-4">
          <EditUser key={`${u.role}-${u.is_active}-${u.is_fraud_flagged}`} user={u} />
          <GrantPlan userId={u.id} />
          <Card className="p-4 tabular-nums text-xs text-muted">
            <div>{t("Roʻyxatdan oʻtgan")}: {formatDateTime(u.date_joined, language)} · {u.registered_ip ?? "—"}</div>
            <div className="mt-1">{t("Oxirgi kirish")}: {u.last_login ? formatDateTime(u.last_login, language) : "—"} · {u.last_login_ip ?? "—"}</div>
            {data.payments.length > 0 && <Link to="/payments" className="mt-2 block text-primary hover:underline">{t("Toʻlovlar")}: {data.payments.length} →</Link>}
          </Card>
        </div>
      </div>
    </div>
  );
}
