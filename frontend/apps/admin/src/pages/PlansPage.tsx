/** Tariflar konstruktori (TZ §8.1): limitlar, narx, muddat. Bo'sh limit — cheklovsiz. O'chirish yo'q — faolsizlantirish. */
import { unwrap } from "@mezon/api-client";
import {
  api, Badge, Button, Card, Checkbox, Dialog, DialogContent, DialogDescription, DialogTitle, FieldError, fieldErrors,
  formatMoney, Input, Label, notifyError, Skeleton, Spinner, staggerStyle,
} from "@mezon/web-kit";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PlusIcon, SaveIcon } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { PageHeader } from "@/components/AdminShell";
import { adminKeys, sendJson, type Plan } from "@/lib/admin";

type NumField = "price_uzs" | "duration_days" | "daily_case_limit" | "monthly_case_limit" | "lifetime_case_limit"
  | "max_pages_per_case" | "daily_chat_limit" | "lifetime_chat_limit" | "daily_template_limit" | "lifetime_template_limit" | "sort_order";

function usePlanFields() {
  const { t } = useTranslation();
  return [
    { title: t("Narx va muddat"), fields: [["price_uzs", t("Narx, soʻm")], ["duration_days", t("Muddat, kun")], ["sort_order", t("Tartib")]] },
    { title: t("Ish tahlili"), fields: [["daily_case_limit", t("kuniga")], ["monthly_case_limit", t("oyiga")], ["lifetime_case_limit", t("jami")], ["max_pages_per_case", t("Bitta ish, varaq")]] },
    { title: t("Savol-javob"), fields: [["daily_chat_limit", t("kuniga")], ["lifetime_chat_limit", t("jami")]] },
    { title: t("Hujjat yuklab olish"), fields: [["daily_template_limit", t("kuniga")], ["lifetime_template_limit", t("jami")]] },
  ] as { title: string; fields: [NumField, string][] }[];
}

function PlanCard({ plan, index = 0 }: { plan: Plan; index?: number }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const groups = usePlanFields();
  const [form, setForm] = useState<Plan>(plan);
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  const dirty = JSON.stringify(form) !== JSON.stringify(plan);
  const save = useMutation({
    mutationFn: () => {
      const { id, code, subscribers, display_name, ...patch } = form;
      void id; void code; void subscribers; void display_name;
      return sendJson<Plan>(`/admin/plans/${plan.id}`, "PATCH", patch);
    },
    onSuccess: () => {
      setErrors({});
      toast.success(t("Saqlandi"));
      void queryClient.invalidateQueries({ queryKey: adminKeys.plans });
    },
    onError: (err) => {
      setErrors(fieldErrors(err));
      notifyError(err, t);
    },
  });
  const setNum = (k: NumField, v: string) => setForm((f) => ({ ...f, [k]: v === "" ? (k === "max_pages_per_case" || k === "sort_order" ? 0 : null) : Number(v) }));

  return (
    <Card className={`animate-in-up flex flex-col p-5 ${plan.is_active ? "" : "opacity-60"}`} style={staggerStyle(index, 70)} accent={plan.code.startsWith("ENTERPRISE") ? "gold" : "blue"}>
      <div className="flex items-center justify-between gap-2">
        <span className="label-code text-muted">{plan.code}</span>
        <Badge mono>{t("{{n}} obunachi", { n: plan.subscribers })}</Badge>
      </div>
      <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="mt-2 font-semibold" aria-label={t("Nomi")} />
      <div className="mt-1 tabular-nums text-xs text-muted">{plan.display_name} · {form.price_uzs ? `${formatMoney(form.price_uzs)} ${t("soʻm")}` : t("narx belgilanmagan")}</div>
      {groups.map((g) => (
        <div key={g.title} className="mt-4">
          <div className="label-code mb-1.5 text-muted">{g.title}</div>
          <div className="grid grid-cols-2 gap-2">
            {g.fields.map(([k, label]) => (
              <div key={k}>
                <Label htmlFor={`${plan.code}-${k}`} className="mb-1 text-xs">{label}</Label>
                <Input id={`${plan.code}-${k}`} type="number" min={0} value={form[k] ?? ""} placeholder="∞" className="h-8 tabular-nums text-xs"
                  onChange={(e) => setNum(k, e.target.value)} aria-invalid={!!errors[k]} />
                <FieldError messages={errors[k]} />
              </div>
            ))}
          </div>
        </div>
      ))}
      <div className="mt-4 flex flex-col gap-2 text-sm">
        {([["watermark", t("Shablonlarga tarif belgisi")], ["priority_queue", t("Ish tahlili navbatida oldinda")], ["is_active", t("Faol (yangi obunaga beriladi)")]] as const).map(([k, label]) => (
          <label key={k} className="flex items-start gap-3">
            <Checkbox checked={!!form[k]} onCheckedChange={(v) => setForm({ ...form, [k]: v === true })} />
            <span>{label}</span>
          </label>
        ))}
      </div>
      <Button className="mt-4" disabled={!dirty || save.isPending} onClick={() => save.mutate()}>
        {save.isPending ? <Spinner className="text-primary-foreground" /> : <SaveIcon />} {t("Saqlash")}
      </Button>
    </Card>
  );
}

function NewPlanDialog({ open, onOpenChange }: { open: boolean; onOpenChange(v: boolean): void }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  const create = useMutation({
    mutationFn: () => sendJson("/admin/plans/", "POST", { code, name, max_pages_per_case: 15, is_active: false }),
    onSuccess: () => {
      onOpenChange(false);
      setCode(""); setName(""); setErrors({});
      void queryClient.invalidateQueries({ queryKey: adminKeys.plans });
    },
    onError: (err) => setErrors(fieldErrors(err)),
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    create.mutate();
  };
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-[min(440px,94vw)]">
        <DialogTitle>{t("Yangi tarif")}</DialogTitle>
        <DialogDescription>{t("Tarif faolsiz holda yaratiladi — limitlarni toʻldirib, keyin faollashtiring.")}</DialogDescription>
        <form onSubmit={submit} className="mt-4 flex flex-col gap-3">
          <div>
            <Label htmlFor="code">{t("Kod")}</Label>
            <Input id="code" value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} placeholder="PRO_YEARLY" className="tabular-nums" />
            <FieldError messages={errors.code} />
          </div>
          <div>
            <Label htmlFor="name">{t("Nomi")}</Label>
            <Input id="name" value={name} onChange={(e) => setName(e.target.value)} />
            <FieldError messages={errors.name} />
          </div>
          <Button type="submit" disabled={!code || !name || create.isPending}>{create.isPending ? <Spinner className="text-primary-foreground" /> : <PlusIcon />} {t("Yaratish")}</Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function PlansPage() {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const { data, isLoading } = useQuery({ queryKey: adminKeys.plans, queryFn: () => unwrap(api.client.GET("/api/v1/admin/plans/")) });
  return (
    <div className="mx-auto max-w-7xl">
      <PageHeader title={t("Tariflar")} subtitle={t("Boʻsh limit — cheklovsiz. Tarif oʻchirilmaydi, faolsizlantiriladi (obunalar saqlanadi).")}
        actions={<Button variant="gold" onClick={() => setOpen(true)}><PlusIcon /> {t("Yangi tarif")}</Button>} />
      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {[0, 1, 2].map((i) => <Skeleton key={i} className="h-72" style={staggerStyle(i, 70)} />)}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {(data ?? []).map((p, i) => <PlanCard key={`${p.id}-${JSON.stringify(p)}`} plan={p} index={i} />)}
        </div>
      )}
      <NewPlanDialog open={open} onOpenChange={setOpen} />
    </div>
  );
}
