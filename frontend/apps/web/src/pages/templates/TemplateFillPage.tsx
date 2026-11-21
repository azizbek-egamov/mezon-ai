/** Shablonni to'ldirish: sxemadan forma, "qog'oz" ko'rinishi (DOCX/PDF bilan bir xil bloklar), yuklab olish (kvota). */
import { ApiError, unwrap, type Schemas } from "@mezon/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircleIcon,
  ArrowLeftIcon,
  CrownIcon,
  DownloadIcon,
  EyeIcon,
  GlobeIcon,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router";

import {
  api,
  Badge,
  Button,
  Card,
  cn,
  DatePicker,
  Empty,
  ErrorNote,
  FadeIn,
  FieldError,
  Input,
  Label,
  NativeSelect,
  saveBlob,
  Spinner,
  Textarea,
} from "@mezon/web-kit";

import { keys, notifyError, useUsage } from "@/lib/queries";

interface FieldSpec {
  name: string;
  label: string;
  type?: "text" | "textarea" | "date" | "number" | "money" | "select" | "phone" | "jshshir";
  required?: boolean;
  options?: string[];
  help?: string;
}

type Block = Schemas["Block"];

const LANGUAGE_OPTIONS = [
  { code: "uz-Latn", label: "Oʻzbekcha", sub: "Lotin" },
  { code: "uz-Cyrl", label: "Ўзбекча", sub: "Кирилл" },
  { code: "ru", label: "Русский", sub: "Русский" },
] as const;

function Paper({ blocks }: { blocks: Block[] }) {
  return (
    <div className="paper">
      {blocks.map((b, i) => {
        if (b.kind === "sign") {
          const [left, ...right] = b.text.split("|");
          return (
            <div key={i} className="b-sign">
              <span>{left.trim()}</span>
              <span>{right.join("|").trim()}</span>
            </div>
          );
        }
        return (
          <div key={i} className={`b-${b.kind}`}>
            {b.text}
          </div>
        );
      })}
    </div>
  );
}

function Field({
  spec,
  value,
  onChange,
  errors,
}: {
  spec: FieldSpec;
  value: string;
  onChange(v: string): void;
  errors?: string[];
}) {
  const id = `f-${spec.name}`;
  const common = { id, value, "aria-invalid": !!errors, required: spec.required !== false };
  let input;
  switch (spec.type) {
    case "textarea":
      input = <Textarea {...common} rows={4} maxLength={5000} onChange={(e) => onChange(e.target.value)} />;
      break;
    case "select":
      input = (
        <NativeSelect {...common} onChange={(e) => onChange(e.target.value)}>
          <option value="">—</option>
          {(spec.options ?? []).map((o) => (
            <option key={o} value={o}>
              {o}
            </option>
          ))}
        </NativeSelect>
      );
      break;
    case "date":
      input = (
        <DatePicker
          id={common.id}
          value={value}
          onChange={onChange}
          size="md"
          required={common.required}
          aria-invalid={common["aria-invalid"]}
          placeholder={spec.label || undefined}
        />
      );
      break;
    case "number":
    case "money":
      input = (
        <Input
          {...common}
          type="number"
          min={0}
          step={spec.type === "money" ? "0.01" : "any"}
          className="tabular-nums"
          onChange={(e) => onChange(e.target.value)}
        />
      );
      break;
    case "phone":
      input = (
        <Input
          {...common}
          type="tel"
          placeholder="+998 90 123 45 67"
          className="tabular-nums"
          onChange={(e) => onChange(e.target.value)}
        />
      );
      break;
    case "jshshir":
      input = (
        <Input
          {...common}
          inputMode="numeric"
          maxLength={14}
          pattern="[0-9]{14}"
          className="tabular-nums"
          onChange={(e) => onChange(e.target.value.replace(/\D/g, ""))}
        />
      );
      break;
    default:
      input = <Input {...common} maxLength={500} onChange={(e) => onChange(e.target.value)} />;
  }
  return (
    <div>
      <Label htmlFor={id}>
        {spec.label}
        {spec.required !== false && <span className="text-red"> *</span>}
      </Label>
      {input}
      {spec.help && <div className="mt-1 text-xs text-muted">{spec.help}</div>}
      <FieldError messages={errors} />
    </div>
  );
}

export function TemplateFillPage() {
  const { id = "" } = useParams();
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [selectedLang, setSelectedLang] = useState<string>("uz-Latn");
  const [values, setValues] = useState<Record<string, string>>({});
  const [blocks, setBlocks] = useState<Block[] | null>(null);
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  const [general, setGeneral] = useState("");
  const live = useRef(false); // birinchi "Ko'rib chiqish"dan keyin ko'rinish avtomatik yangilanadi

  const usage = useUsage();
  const u = usage.data;
  const tplUsage =
    u?.usage.find((r) => r.kind === "template") ??
    u?.usage.find((r) => r.label.toLowerCase().includes("hujjat"));
  const tplExhausted = !u?.unlimited && !!tplUsage && tplUsage.used >= tplUsage.limit;
  const isFree = u?.plan === "FREE";

  const tpl = useQuery({
    queryKey: [...keys.template(id), selectedLang],
    queryFn: () =>
      unwrap(
        api.client.GET("/api/v1/templates/{template_id}", {
          params: { path: { template_id: id }, query: { lang: selectedLang } },
        })
      ),
  });

  const availableLangs = useMemo(() => {
    return (tpl.data?.available_languages as string[] | undefined) ?? ["uz-Latn"];
  }, [tpl.data?.available_languages]);

  // Agar hozirgi interfeys tili mavjud bo'lsa va selectedLang hali o'rnatilmagan bo'lsa, moslashtirish
  useEffect(() => {
    if (!tpl.data?.available_languages) return;
    const avail = tpl.data.available_languages as string[];
    if (!avail.includes(selectedLang)) {
      if (avail.includes(i18n.language)) {
        setSelectedLang(i18n.language);
      } else if (avail.length > 0) {
        setSelectedLang(avail[0]);
      }
    }
  }, [tpl.data?.available_languages]);

  const preview = useMutation({
    mutationFn: () =>
      unwrap(
        api.client.POST("/api/v1/templates/{template_id}/preview", {
          params: { path: { template_id: id } },
          body: { values, lang: selectedLang },
        })
      ),
    onSuccess: (data) => {
      setBlocks(data.blocks);
      setErrors({});
      setGeneral("");
    },
    onError: (err) => {
      if (err instanceof ApiError && err.status === 400) {
        setErrors(err.fields);
        setGeneral(err.fields.non_field_errors?.join(" ") ?? "");
      } else notifyError(err, t);
    },
  });

  const download = useMutation({
    mutationFn: async (fmt: "docx" | "pdf") => {
      const { blob, filename } = await api.download(`/templates/${id}/render/${fmt}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ values, lang: selectedLang }),
      });
      saveBlob(blob, filename);
    },
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: keys.usage }),
    onError: (err) => {
      if (err instanceof ApiError && err.status === 400) setErrors(err.fields);
      else notifyError(err, t, () => navigate("/billing"));
    },
  });

  function handleDownload(fmt: "docx" | "pdf") {
    if (tplExhausted) {
      notifyError(
        {
          message: t(
            "Bu tarifdagi hujjat yuklab olish limiti tugadi. Davom etish uchun obuna rasmiylashtiring."
          ),
        },
        t,
        () => navigate("/billing")
      );
      return;
    }
    download.mutate(fmt);
  }

  // Qiymatlar o'zgarganda yoki til almashganda preview avtomatik yangilanadi
  useEffect(() => {
    if (!live.current) return;
    const timer = setTimeout(() => preview.mutate(), 500);
    return () => clearTimeout(timer);
  }, [values, selectedLang]);

  if (tpl.isLoading) {
    return (
      <Empty>
        <Spinner className="size-6" />
      </Empty>
    );
  }

  if (!tpl.data) {
    return <Empty>{tpl.error?.message ?? t("Topilmadi")}</Empty>;
  }

  const schema = tpl.data.form_schema as unknown as FieldSpec[];

  return (
    <div className="mx-auto grid max-w-7xl gap-6 px-4 py-8 sm:px-6 lg:grid-cols-[minmax(0,5.5fr)_minmax(0,6.5fr)] lg:px-8">
      {/* Chap ustun: Hujjat ma'lumotlari, Til tanlagich va Forma */}
      <Card className="animate-in-up h-fit p-5 sm:p-6">
        <Link
          to="/templates"
          className="mb-3 inline-flex items-center gap-1.5 text-xs text-muted hover:text-ink transition-colors"
        >
          <ArrowLeftIcon className="size-3.5" /> {t("Hujjatlar katalogi")}
        </Link>

        <div className="label-code text-gold">
          {tpl.data.category_label}
          {tpl.data.subcategory ? ` · ${tpl.data.subcategory}` : ""} · v{tpl.data.version}
        </div>

        <h1 className="mt-1 font-serif text-xl sm:text-2xl font-semibold leading-snug text-ink">
          {tpl.data.title}
        </h1>

        {tpl.data.description && (
          <p className="mt-1.5 text-sm text-muted leading-relaxed">{tpl.data.description}</p>
        )}

        <div className="mt-3 flex flex-wrap items-center gap-2">
          {tpl.data.is_approved ? (
            <Badge tone="ok">{t("moderator tasdiqlagan · v{{v}}", { v: tpl.data.version })}</Badge>
          ) : (
            <Badge tone="warn">
              {t("namuna · moderator tasdiqlamagan — matnni tekshirib foydalaning")}
            </Badge>
          )}
          {tpl.data.doc_id ? (
            <Badge tone="neutral" mono>
              #{tpl.data.doc_id}
            </Badge>
          ) : null}
        </div>

        {/* HUJJAT TILI TANLAGICH */}
        <div className="mt-4 rounded-xl border border-line bg-subtle/60 p-3.5">
          <div className="mb-2 flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-xs font-semibold text-ink">
              <GlobeIcon className="size-3.5 text-primary" />
              {t("Hujjatni shakllantirish tili:")}
            </span>
            <span className="text-[11px] text-muted">
              {t("Mavjud tillar: {{n}} ta", { n: availableLangs.length })}
            </span>
          </div>

          <div className="grid grid-cols-3 gap-2">
            {LANGUAGE_OPTIONS.map((opt) => {
              const isAvailable = availableLangs.includes(opt.code);
              const isSelected = selectedLang === opt.code;

              return (
                <button
                  key={opt.code}
                  type="button"
                  disabled={!isAvailable}
                  onClick={() => setSelectedLang(opt.code)}
                  className={cn(
                    "flex flex-col items-center justify-center rounded-lg border px-2 py-2 text-center transition-all",
                    isSelected
                      ? "border-primary bg-surface font-semibold text-primary shadow-xs ring-1 ring-primary"
                      : isAvailable
                        ? "border-line bg-surface/70 text-ink hover:border-primary/40 hover:bg-surface"
                        : "cursor-not-allowed border-dashed border-line/60 bg-transparent opacity-40 text-muted"
                  )}
                >
                  <span className="text-[13px] leading-tight">{opt.label}</span>
                  <span className="mt-0.5 text-[10px] text-muted leading-tight">
                    {isAvailable ? opt.sub : t("mavjud emas")}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {tpl.data.legal_basis.length > 0 && (
          <div className="mt-3.5 rounded-lg bg-subtle/50 p-2.5 text-xs text-muted">
            <span className="font-semibold text-ink">{t("Qonuniy asos:")}</span>
            {tpl.data.legal_basis.map((line) => (
              <div key={line} className="mt-0.5 tabular-nums">
                · {line}
              </div>
            ))}
          </div>
        )}

        {tplUsage && !u?.unlimited && (
          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
            <span
              className={cn("font-medium tabular-nums", tplExhausted ? "text-red" : "text-muted")}
            >
              {t("Yuklab olish kvotasi: {{rem}}/{{lim}} ta qoldi", {
                rem: Math.max(0, tplUsage.limit - tplUsage.used),
                lim: tplUsage.limit,
              })}
            </span>
            {isFree && <span className="text-amber">({t("suv belgisi bilan")})</span>}
          </div>
        )}

        {tplExhausted && (
          <div className="mt-3 rounded-xl border border-amber/40 bg-amber/10 p-3 text-xs text-ink">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-1.5">
                <AlertCircleIcon className="size-4 shrink-0 text-amber" />
                <span>
                  <b>{t("Yuklab olish limiti tugagan.")}</b>{" "}
                  {t(
                    "Koʻrib chiqish bepul, lekin faylni yuklab olish uchun tarifni yangilang."
                  )}
                </span>
              </div>
              <Button
                type="button"
                variant="gold"
                size="sm"
                onClick={() => navigate("/billing")}
                className="h-7 shrink-0 text-xs"
              >
                <CrownIcon className="size-3.5" /> {t("Tarifni yangilash")}
              </Button>
            </div>
          </div>
        )}

        <form
          className="mt-5 flex flex-col gap-4"
          noValidate
          onSubmit={(e) => {
            e.preventDefault();
            live.current = true;
            preview.mutate();
          }}
        >
          {general && <ErrorNote>{general}</ErrorNote>}
          {schema.map((spec) => (
            <Field
              key={spec.name}
              spec={spec}
              value={values[spec.name] ?? ""}
              errors={errors[spec.name]}
              onChange={(v) => setValues((all) => ({ ...all, [spec.name]: v }))}
            />
          ))}

          <div className="sticky bottom-20 flex flex-col gap-2 border-t border-line bg-surface py-3 lg:bottom-0">
            <div className="flex flex-wrap gap-2">
              <Button type="submit" variant="outline" disabled={preview.isPending}>
                {preview.isPending ? <Spinner /> : <EyeIcon />} {t("Koʻrib chiqish")}
              </Button>
              <Button
                type="button"
                variant="gold"
                disabled={download.isPending}
                onClick={() => handleDownload("docx")}
              >
                <DownloadIcon /> {t("DOCX yuklab olish")}
              </Button>
              <Button
                type="button"
                variant="gold"
                disabled={download.isPending}
                onClick={() => handleDownload("pdf")}
              >
                <DownloadIcon /> {t("PDF yuklab olish")}
              </Button>
            </div>
            {isFree && (
              <p className="text-[11px] text-muted">
                {t(
                  "Eslatma: Bepul tarifda yuklab olingan hujjatlarga “Bepul tarif” belgisi qoʻshiladi. Belgisiz toza hujjat olish uchun Pro tarifiga oʻting."
                )}
              </p>
            )}
          </div>
        </form>
      </Card>

      {/* O'ng ustun: Hujjatning jonli "qog'oz" ko'rinishi */}
      <div>
        <div className="label-code mb-2 flex items-center justify-between text-muted">
          <span>{t("Hujjat koʻrinishi")}</span>
          <span className="font-mono">
            A4 · {LANGUAGE_OPTIONS.find((l) => l.code === selectedLang)?.label ?? selectedLang}
          </span>
        </div>

        {blocks ? (
          <FadeIn>
            <Paper blocks={blocks} />
            <p className="mt-2 text-xs text-muted">
              {t("Hujjat yuridik maslahat emas — topshirishdan oldin advokat tekshiradi.")}
            </p>
          </FadeIn>
        ) : (
          <Card className="animate-in-fade p-6 text-sm text-muted">
            {t("Formani toʻldirib “Koʻrib chiqish”ni bosing — hujjat shu yerda koʻrinadi.")}
          </Card>
        )}
      </div>
    </div>
  );
}
