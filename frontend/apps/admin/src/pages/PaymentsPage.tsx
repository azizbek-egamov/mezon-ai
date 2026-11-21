/** To'lovlar: holat bo'yicha filtr, qo'lda to'lov (naqd/bank), "to'langan deb belgilash" → obuna yoqiladi (quota.mark_paid). */
import { unwrap } from "@mezon/api-client";
import {
  api, Badge, Button, Card, Dialog, DialogContent, DialogDescription, DialogTitle, Empty, FadeIn, FieldError, fieldErrors,
  formatDateTime, formatMoney, Input, Label, NativeSelect, notifyError, Skeleton, Spinner, staggerStyle, useLanguage,
} from "@mezon/web-kit";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircleIcon, PlusIcon, XCircleIcon } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { toast } from "sonner";

import { PageHeader } from "@/components/AdminShell";
import { Pager } from "@/components/common";
import { adminKeys, sendJson, type Payment } from "@/lib/admin";

const STATUS_TONE = { PENDING: "warn", PAID: "ok", FAILED: "bad", CANCELED: "neutral" } as const;

function NewPaymentDialog({ open, onOpenChange }: { open: boolean; onOpenChange(v: boolean): void }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [phone, setPhone] = useState("");
  const [userId, setUserId] = useState("");
  const [plan, setPlan] = useState("");
  const [amount, setAmount] = useState("");
  const [externalId, setExternalId] = useState("");
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  const digits = phone.replace(/\D/g, "");
  const users = useQuery({
    queryKey: adminKeys.users({ q: digits, page: 1 }),
    queryFn: () => unwrap(api.client.GET("/api/v1/admin/users/", { params: { query: { q: digits } } })),
    enabled: digits.length >= 4,
  });
  const plans = useQuery({ queryKey: adminKeys.plans, queryFn: () => unwrap(api.client.GET("/api/v1/admin/plans/")) });
  const create = useMutation({
    mutationFn: () => sendJson<Payment>("/admin/payments/", "POST", {
      user: userId, plan_code: plan, provider: "MANUAL", amount_uzs: Number(amount), external_id: externalId,
    }),
    onSuccess: () => {
      onOpenChange(false);
      toast.success(t("Toʻlov yaratildi"));
      void queryClient.invalidateQueries({ queryKey: ["admin"] });
    },
    onError: (err) => setErrors(fieldErrors(err)),
  });
  const chosenPlan = plans.data?.find((p) => p.code === plan);
  const submit = (e: FormEvent) => {
    e.preventDefault();
    create.mutate();
  };
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-[min(480px,94vw)]">
        <DialogTitle>{t("Qoʻlda toʻlov")}</DialogTitle>
        <DialogDescription>{t("Naqd yoki bank oʻtkazmasi. Pul tushgach “Toʻlandi” tugmasi obunani yoqadi.")}</DialogDescription>
        <form onSubmit={submit} className="mt-4 flex flex-col gap-3">
          <div>
            <Label htmlFor="pphone">{t("Telefon")}</Label>
            <Input id="pphone" value={phone} onChange={(e) => { setPhone(e.target.value); setUserId(""); }} placeholder="+998 90 123 45 67" className="tabular-nums" />
            {digits.length >= 4 && (
              <div className="mt-1 max-h-36 overflow-y-auto rounded border border-line">
                {(users.data?.results ?? []).map((u, i) => (
                  <button type="button" key={u.id} onClick={() => setUserId(u.id)} style={staggerStyle(i, 30)}
                    className={`animate-in-up block w-full px-3 py-1.5 text-left text-sm hover:bg-subtle ${userId === u.id ? "bg-subtle text-gold" : ""}`}>
                    {u.full_name} <span className="tabular-nums text-xs text-muted">{u.phone_number}</span>
                  </button>
                ))}
                {users.data && !users.data.results.length && <div className="px-3 py-1.5 text-sm text-muted">{t("Topilmadi.")}</div>}
              </div>
            )}
            <FieldError messages={errors.user} />
          </div>
          <div>
            <Label htmlFor="pplan">{t("Tarif")}</Label>
            <NativeSelect id="pplan" value={plan} onChange={(e) => {
              setPlan(e.target.value);
              const p = plans.data?.find((x) => x.code === e.target.value);
              if (p?.price_uzs) setAmount(String(p.price_uzs));
            }}>
              <option value="">—</option>
              {(plans.data ?? []).filter((p) => p.code !== "FREE").map((p) => <option key={p.code} value={p.code}>{p.display_name}</option>)}
            </NativeSelect>
            <FieldError messages={errors.plan_code} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="pamount">{t("Summa, soʻm")}</Label>
              <Input id="pamount" type="number" min={0} value={amount} onChange={(e) => setAmount(e.target.value)} className="tabular-nums" />
              <FieldError messages={errors.amount_uzs} />
            </div>
            <div>
              <Label htmlFor="pext">{t("Hujjat raqami (ixtiyoriy)")}</Label>
              <Input id="pext" value={externalId} onChange={(e) => setExternalId(e.target.value)} className="tabular-nums" />
            </div>
          </div>
          {chosenPlan && !chosenPlan.price_uzs && <div className="text-xs text-amber">{t("Bu tarif narxi belgilanmagan")}</div>}
          <Button type="submit" disabled={!userId || !plan || amount === "" || create.isPending}>
            {create.isPending ? <Spinner className="text-primary-foreground" /> : <PlusIcon />} {t("Yaratish")}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function PaymentsPage() {
  const { t } = useTranslation();
  const { language } = useLanguage();
  const queryClient = useQueryClient();
  const [status, setStatus] = useState("PENDING");
  const [page, setPage] = useState(1);
  const [open, setOpen] = useState(false);
  const { data, isLoading } = useQuery({
    queryKey: adminKeys.payments({ status, page }),
    queryFn: () => unwrap(api.client.GET("/api/v1/admin/payments/", { params: { query: { status: (status || undefined) as never, page } } })),
    placeholderData: keepPreviousData,
  });
  const act = useMutation({
    mutationFn: ({ id, action }: { id: number; action: "mark-paid" | "cancel" }) => sendJson<Payment>(`/admin/payments/${id}/${action}`, "POST"),
    onSuccess: (p) => {
      toast.success(p.status === "PAID" ? t("Toʻlov tasdiqlandi") : t("Toʻlov bekor qilindi"));
      void queryClient.invalidateQueries({ queryKey: ["admin"] });
    },
    onError: (err) => notifyError(err, t),
  });

  return (
    <div className="mx-auto max-w-7xl">
      <PageHeader title={t("Toʻlovlar")} subtitle={t("Payme / Click webhooklari keyingi bosqichda; hozircha qoʻlda tasdiqlash")}
        actions={<Button variant="gold" onClick={() => setOpen(true)}><PlusIcon /> {t("Qoʻlda toʻlov")}</Button>} />
      <FadeIn className="mb-3 flex flex-wrap gap-2">
        {[["PENDING", t("Kutilmoqda")], ["PAID", t("Toʻlangan")], ["CANCELED", t("Bekor qilingan")], ["", t("Barchasi")]].map(([code, label]) => (
          <button key={code} onClick={() => { setStatus(code); setPage(1); }}
            className={`rounded-full border border-line px-3 py-1 text-[13px] ${status === code ? "border-primary bg-primary/15 text-ink" : "text-muted hover:text-ink"}`}>
            {label}
          </button>
        ))}
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
                  <th className="px-4 py-3 font-semibold">{t("Sana")}</th>
                  <th className="px-2 py-3 font-semibold">{t("Foydalanuvchi")}</th>
                  <th className="px-2 py-3 font-semibold">{t("Tarif")}</th>
                  <th className="px-2 py-3 font-semibold">{t("Summa, soʻm")}</th>
                  <th className="px-2 py-3 font-semibold">{t("Usul")}</th>
                  <th className="px-2 py-3 font-semibold">{t("Holat")}</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody>
                {data.results.map((p, i) => (
                  <tr key={p.id} className="animate-in-up border-t border-line" style={staggerStyle(i)}>
                    <td className="px-4 py-2.5 tabular-nums text-xs text-muted">{formatDateTime(p.created_at, language)}</td>
                    <td className="px-2 py-2.5">
                      <Link to={`/users/${p.user}`} className="hover:text-primary">{p.user_name}</Link>
                      <div className="tabular-nums text-xs text-muted">{p.user_phone}</div>
                    </td>
                    <td className="px-2 py-2.5 tabular-nums text-xs">{p.plan_code}</td>
                    <td className="px-2 py-2.5 tabular-nums">{formatMoney(p.amount_uzs)}</td>
                    <td className="px-2 py-2.5 text-xs">{p.provider_label}{p.external_id && <div className="tabular-nums text-xs text-muted">{p.external_id}</div>}</td>
                    <td className="px-2 py-2.5"><Badge tone={STATUS_TONE[p.status as keyof typeof STATUS_TONE] ?? "neutral"}>{p.status_label}</Badge></td>
                    <td className="px-4 py-2.5 text-right">
                      {p.status === "PENDING" && (
                        <div className="flex justify-end gap-2">
                          <Button size="sm" variant="success" disabled={act.isPending}
                            onClick={() => window.confirm(t("Toʻlov tushganini tasdiqlaysizmi? Obuna darhol yoqiladi.")) && act.mutate({ id: p.id, action: "mark-paid" })}>
                            <CheckCircleIcon /> {t("Toʻlandi")}
                          </Button>
                          <Button size="sm" variant="destructive" disabled={act.isPending} onClick={() => act.mutate({ id: p.id, action: "cancel" })}>
                            <XCircleIcon />
                          </Button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      {data && <Pager page={page} count={data.count} onPage={setPage} />}
      <NewPaymentDialog open={open} onOpenChange={setOpen} />
    </div>
  );
}
