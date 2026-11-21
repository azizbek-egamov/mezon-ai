/**
 * Shablon moderatsiyasi (TZ §5.1.1): yurist-moderator shablon yozadi, sinab ko'radi va tasdiqlaydi.
 * Matn yoki sxema o'zgarsa — versiya oshadi, tasdiq bekor bo'ladi (backend). Qator belgilari: >> o'ngga, ## markaz,
 * ### bo'lim, - band, ~ chap | o'ng (imzo).
 */
import { ApiError, type Schemas } from "@mezon/api-client";
import {
  Badge, Button, Card, Checkbox, Empty, ErrorNote, FadeIn, FieldError, fieldErrors, formatDateTime, Input, Label, NativeSelect,
  notifyError, Skeleton, Spinner, staggerStyle, Textarea, useLanguage,
} from "@mezon/web-kit";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { TFunction } from "i18next";
import { ArrowLeftIcon, BadgeCheckIcon, EyeIcon, PlusIcon, SaveIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router";
import { toast } from "sonner";

import { PageHeader } from "@/components/AdminShell";
import { adminKeys, getJson, sendJson, type AdminTemplate } from "@/lib/admin";

type ListItem = Schemas["TemplateListItem"];
type Block = Schemas["Block"];
interface FieldSpec { name: string; label: string; type?: string; required?: boolean; options?: string[] }

const CATEGORIES = [
  "CONTRACTS",
  "STATEMENTS",
  "PERSONAL",
  "NOTARIAL",
  "COURT",
  "CORPORATE",
  "ADVOCATE_REQUEST",
  "MOTION",
  "CLAIM",
  "APPEAL",
  "POWER_OF_ATTORNEY",
  "CONTRACT",
  "OTHER",
] as const;

function categoryLabel(t: TFunction, code: string): string {
  switch (code) {
    case "CONTRACTS": return t("Shartnomalar");
    case "STATEMENTS": return t("Arizalar");
    case "PERSONAL": return t("Shaxsiy tarkibga oid hujjatlar");
    case "NOTARIAL": return t("Notarial tasdiqlanadigan hujjatlar");
    case "COURT": return t("Sudga oid hujjatlar");
    case "CORPORATE": return t("Korporativ hujjatlar");
    case "ADVOCATE_REQUEST": return t("Advokat soʻrovi");
    case "MOTION": return t("Iltimosnoma");
    case "CLAIM": return t("Daʼvo arizasi");
    case "APPEAL": return t("Shikoyat");
    case "POWER_OF_ATTORNEY": return t("Ishonchnoma");
    case "CONTRACT": return t("Shartnoma");
    default: return t("Boshqa");
  }
}

export function TemplatesPage() {
  const { t } = useTranslation();
  const { language } = useLanguage();
  const [pending, setPending] = useState(false);
  const { data, isLoading } = useQuery({
    queryKey: adminKeys.templates(pending),
    queryFn: () => getJson<ListItem[]>(`/admin/templates/${pending ? "?pending=1" : ""}`),
  });
  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader title={t("Shablon moderatsiyasi")} subtitle={t("Yurist-moderator shablonni yozadi, sinab koʻradi va tasdiqlaydi")}
        actions={<Button asChild variant="gold"><Link to="/templates/new"><PlusIcon /> {t("Yangi shablon")}</Link></Button>} />
      <label className="mb-3 flex items-center gap-2 text-sm text-muted">
        <Checkbox checked={pending} onCheckedChange={(v) => setPending(v === true)} /> {t("Faqat tasdiqlanmaganlar")}
      </label>
      <Card>
        {isLoading ? (
          <div className="flex flex-col gap-2 p-4">
            {[0, 1, 2].map((i) => <Skeleton key={i} className="h-12" style={staggerStyle(i, 60)} />)}
          </div>
        ) : !data?.length ? <Empty>{t("Hozircha shablon yoʻq.")}</Empty> : (
          <ul className="divide-y divide-line">
            {data.map((tpl, i) => (
              <li key={tpl.id} className="animate-in-up" style={staggerStyle(i, 35)}>
                <Link to={`/templates/${tpl.id}`} className="flex flex-wrap items-center gap-3 px-4 py-3 hover:bg-subtle/40">
                  <span className="min-w-0 flex-1">
                    <span className="block font-medium">{tpl.title}</span>
                    <span className="tabular-nums text-xs text-muted">{categoryLabel(t, tpl.category)} · v{tpl.version} · {formatDateTime(tpl.updated_at, language)}</span>
                  </span>
                  {tpl.is_published ? <Badge tone="info">{t("eʼlon qilingan")}</Badge> : <Badge>{t("qoralama")}</Badge>}
                  {tpl.approved_at ? <Badge tone="ok">✓ {tpl.approved_by_name}</Badge> : <Badge tone="warn">{t("tasdiqlanmagan")}</Badge>}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

function Paper({ blocks }: { blocks: Block[] }) {
  return (
    <div className="paper text-[13px]">
      {blocks.map((b, i) => {
        if (b.kind === "sign") {
          const [left, ...right] = b.text.split("|");
          return <div key={i} className="b-sign"><span>{left.trim()}</span><span>{right.join("|").trim()}</span></div>;
        }
        return <div key={i} className={`b-${b.kind}`}>{b.text}</div>;
      })}
    </div>
  );
}

/** Sxemadan sinov qiymatlari: matn — yorliq, sana — bugun, son — 1000000, select — birinchi variant */
function sampleValues(schema: FieldSpec[]): Record<string, string> {
  const today = new Date().toISOString().slice(0, 10);
  return Object.fromEntries(schema.map((f) => [f.name,
    f.type === "date" ? today : f.type === "number" || f.type === "money" ? "1000000" : f.type === "select" ? f.options?.[0] ?? ""
      : f.type === "phone" ? "+998901234567" : f.type === "jshshir" ? "12345678901234" : `[${f.label}]`]));
}

const EMPTY: Partial<AdminTemplate> = {
  title: "", category: "MOTION", language: "uz-Latn", description: "", legal_basis: "",
  form_schema: [{ name: "fio", label: "F.I.Sh.", type: "text", required: true }] as never, body: "## SARLAVHA\n{{ fio }}", is_published: false,
};

export function TemplateEditPage() {
  const { id = "new" } = useParams();
  const isNew = id === "new";
  const { t } = useTranslation();
  const { language } = useLanguage();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const tpl = useQuery({ queryKey: adminKeys.template(id), queryFn: () => getJson<AdminTemplate>(`/admin/templates/${id}`), enabled: !isNew });
  const [form, setForm] = useState<Partial<AdminTemplate>>(EMPTY);
  const [schemaText, setSchemaText] = useState(JSON.stringify(EMPTY.form_schema, null, 2));
  const [schemaError, setSchemaError] = useState("");
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  const [blocks, setBlocks] = useState<Block[] | null>(null);
  const [previewError, setPreviewError] = useState("");

  useEffect(() => {
    if (tpl.data) {
      setForm(tpl.data);
      setSchemaText(JSON.stringify(tpl.data.form_schema, null, 2));
    }
  }, [tpl.data]);

  const parsedSchema = (): FieldSpec[] | null => {
    try {
      const v = JSON.parse(schemaText);
      setSchemaError("");
      return v;
    } catch (e) {
      setSchemaError(`JSON: ${(e as Error).message}`);
      return null;
    }
  };

  const save = useMutation({
    mutationFn: async () => {
      const schema = parsedSchema();
      if (!schema) throw new Error("schema");
      const body = { title: form.title, category: form.category, language: form.language, description: form.description,
        legal_basis: form.legal_basis, form_schema: schema, body: form.body, is_published: form.is_published };
      return isNew ? sendJson<AdminTemplate>("/admin/templates/", "POST", body) : sendJson<AdminTemplate>(`/admin/templates/${id}`, "PATCH", body);
    },
    onSuccess: (saved) => {
      setErrors({});
      toast.success(t("Saqlandi"));
      void queryClient.invalidateQueries({ queryKey: ["admin"] });
      if (isNew) navigate(`/templates/${saved.id}`, { replace: true });
      else queryClient.setQueryData(adminKeys.template(id), saved);
    },
    onError: (err) => {
      if (err instanceof ApiError) setErrors(fieldErrors(err));
      else if ((err as Error).message !== "schema") notifyError(err, t);
    },
  });

  const approve = useMutation({
    mutationFn: () => sendJson<AdminTemplate>(`/admin/templates/${id}/approve`, "POST"),
    onSuccess: (saved) => {
      toast.success(t("Shablon tasdiqlandi"));
      queryClient.setQueryData(adminKeys.template(id), saved);
      void queryClient.invalidateQueries({ queryKey: ["admin", "templates"] });
    },
    onError: (err) => notifyError(err, t),
  });

  const preview = useMutation({
    mutationFn: () => sendJson<{ blocks: Block[] }>(`/admin/templates/${id}/preview`, "POST", { values: sampleValues((tpl.data?.form_schema ?? []) as unknown as FieldSpec[]) }),
    onSuccess: (d) => { setBlocks(d.blocks); setPreviewError(""); },
    onError: (err) => setPreviewError(err instanceof ApiError ? Object.entries(err.fields).map(([k, v]) => `${k}: ${v.join(" ")}`).join("; ") || err.message : String(err)),
  });

  if (!isNew && tpl.isLoading) return <Empty><Spinner className="size-6" /></Empty>;
  const saved = tpl.data;
  const dirty = !isNew && saved && (JSON.stringify({ ...saved, form_schema: undefined }) !== JSON.stringify({ ...form, form_schema: undefined })
    || JSON.stringify(saved?.form_schema, null, 2) !== schemaText);

  return (
    <div className="mx-auto max-w-7xl">
      <Link to="/templates" className="mb-3 inline-flex items-center gap-1 text-xs text-muted hover:text-ink"><ArrowLeftIcon className="size-3.5" /> {t("Shablon moderatsiyasi")}</Link>
      <PageHeader title={isNew ? t("Yangi shablon") : form.title || "—"}
        subtitle={saved ? `v${saved.version} · ${formatDateTime(saved.updated_at, language)}` : undefined}
        actions={<div className="flex flex-wrap items-center gap-2">
          {saved && (saved.approved_at
            ? <Badge tone="ok">{t("moderator tasdiqlagan · v{{v}}", { v: saved.version })} · {saved.approved_by_name}</Badge>
            : <Badge tone="warn">{t("tasdiqlanmagan")}</Badge>)}
          <Button onClick={() => save.mutate()} disabled={save.isPending || (!isNew && !dirty)}>
            {save.isPending ? <Spinner className="text-primary-foreground" /> : <SaveIcon />} {t("Saqlash")}
          </Button>
          {saved && !saved.approved_at && (
            <Button variant="success" onClick={() => approve.mutate()} disabled={approve.isPending || !!dirty}
              title={dirty ? t("Avval oʻzgarishlarni saqlang") : undefined}>
              <BadgeCheckIcon /> {t("Tasdiqlash va eʼlon qilish")}
            </Button>
          )}
        </div>} />
      {!isNew && dirty && <div className="mb-3 text-xs text-amber">{t("Matn yoki sxema oʻzgarsa — yangi versiya, moderator qayta tasdiqlashi kerak.")}</div>}

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <Card className="flex flex-col gap-3 p-5">
          {errors.non_field_errors && <ErrorNote>{errors.non_field_errors.join(" ")}</ErrorNote>}
          <div>
            <Label htmlFor="title">{t("Nomi")}</Label>
            <Input id="title" value={form.title ?? ""} onChange={(e) => setForm({ ...form, title: e.target.value })} aria-invalid={!!errors.title} />
            <FieldError messages={errors.title} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="cat">{t("Turi")}</Label>
              <NativeSelect id="cat" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value as AdminTemplate["category"] })}>
                {CATEGORIES.map((c) => <option key={c} value={c}>{categoryLabel(t, c)}</option>)}
              </NativeSelect>
            </div>
            <div>
              <Label htmlFor="lang">{t("Til")}</Label>
              <NativeSelect id="lang" value={form.language} onChange={(e) => setForm({ ...form, language: e.target.value })}>
                {["uz-Latn", "uz-Cyrl", "ru"].map((l) => <option key={l} value={l}>{l}</option>)}
              </NativeSelect>
            </div>
          </div>
          <div>
            <Label htmlFor="desc">{t("Qachon ishlatiladi")}</Label>
            <Textarea id="desc" rows={2} value={form.description ?? ""} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <div>
            <Label htmlFor="basis">{t("Qonuniy asoslar (har biri yangi qatorda)")}</Label>
            <Textarea id="basis" rows={3} className="tabular-nums text-xs" value={form.legal_basis ?? ""} onChange={(e) => setForm({ ...form, legal_basis: e.target.value })} />
          </div>
          <div>
            <Label htmlFor="schema">{t("Forma sxemasi (JSON)")}</Label>
            <Textarea id="schema" rows={8} className="tabular-nums text-xs" value={schemaText} onChange={(e) => setSchemaText(e.target.value)}
              onBlur={() => parsedSchema()} aria-invalid={!!(schemaError || errors.form_schema)} spellCheck={false} />
            <FieldError messages={schemaError ? [schemaError] : errors.form_schema} />
            <div className="mt-1 tabular-nums text-xs text-muted">type: text | textarea | date | number | money | select | phone | jshshir</div>
          </div>
          <div>
            <Label htmlFor="body">{t("Hujjat matni")}</Label>
            <Textarea id="body" rows={14} className="tabular-nums text-xs leading-relaxed" value={form.body ?? ""} spellCheck={false}
              onChange={(e) => setForm({ ...form, body: e.target.value })} aria-invalid={!!errors.body} />
            <FieldError messages={errors.body} />
            <div className="mt-1 tabular-nums text-xs text-muted">{"{{ maydon }}  {% if maydon %}…{% endif %}  {{ bugun }}"} · {">> "}o'ng · ## markaz · ### bo'lim · - band · ~ chap | o'ng</div>
          </div>
          <label className="flex items-start gap-3 text-sm">
            <Checkbox checked={!!form.is_published} onCheckedChange={(v) => setForm({ ...form, is_published: v === true })} />
            <span>{t("Foydalanuvchilarga koʻrinadi (eʼlon qilingan)")}</span>
          </label>
        </Card>

        <div>
          <div className="mb-2 flex items-center justify-between">
            <span className="label-code text-muted">{t("Hujjat koʻrinishi")} · {t("sinov qiymatlari")}</span>
            <Button size="sm" variant="outline" disabled={isNew || preview.isPending || !!dirty} onClick={() => preview.mutate()}
              title={dirty ? t("Avval oʻzgarishlarni saqlang") : undefined}>
              {preview.isPending ? <Spinner /> : <EyeIcon />} {t("Koʻrib chiqish")}
            </Button>
          </div>
          {previewError && <ErrorNote className="mb-2">{previewError}</ErrorNote>}
          {blocks ? <FadeIn><Paper blocks={blocks} /></FadeIn> : (
            <Card className="p-6 text-sm text-muted">{isNew ? t("Avval shablonni saqlang") : t("“Koʻrib chiqish” — sxemadagi maydonlar sinov qiymatlari bilan toʻldiriladi.")}</Card>
          )}
        </div>
      </div>
    </div>
  );
}
