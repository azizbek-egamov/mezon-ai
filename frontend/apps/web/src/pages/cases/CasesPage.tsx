/** Ishlar: hujjat yuklash (bir nechta PDF/DOCX/JPG/PNG -> bitta PDF) va ishlar ro'yxati. */
import { unwrap, type Schemas } from "@mezon/api-client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircleIcon, CrownIcon, FileUpIcon, ShieldCheckIcon, UploadCloudIcon, XIcon } from "lucide-react";
import { useRef, useState, type DragEvent, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router";

import { api, Button, Card, CardContent, CardHeader, CardTitle, cn, Empty, FadeIn, formatDateTime, Input, Label, NativeSelect, PageHeader, Skeleton, Spinner, staggerDelay, staggerStyle, useLanguage, Checkbox } from "@mezon/web-kit";

import { keys, notifyError } from "@/lib/queries";

import { CaseStatusBadge, isActive } from "./common";

const ACCEPT = ".pdf,.docx,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png";

function UploadCard() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("criminal");
  const [zeroRetention, setZeroRetention] = useState(false);
  const [dragging, setDragging] = useState(false);
  const options = useQuery({
    queryKey: keys.caseOptions,
    queryFn: () => unwrap(api.client.GET("/api/v1/cases/options")),
    staleTime: Infinity,
  });

  const upload = useMutation({
    mutationFn: async () => {
      const form = new FormData();
      files.forEach((f) => form.append("files", f, f.name));
      form.append("category", category);
      form.append("title", title);
      if (zeroRetention) form.append("zero_retention", "true");
      return (await (await api.raw("/cases/", { method: "POST", body: form })).json()) as Schemas["CaseDetail"];
    },
    onSuccess: (run) => {
      void queryClient.invalidateQueries({ queryKey: ["cases"] });
      void queryClient.invalidateQueries({ queryKey: keys.usage });
      navigate(`/cases/${run.id}`);
    },
    onError: (err) => notifyError(err, t, () => navigate("/billing")),
  });

  const addFiles = (list: FileList | null) => list && setFiles((old) => [...old, ...Array.from(list)]);
  const totalMb = files.reduce((s, f) => s + f.size, 0) / 1024 / 1024;
  const limits = options.data;

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDragging(false);
    addFiles(e.dataTransfer.files);
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    if (files.length) upload.mutate();
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("Ish hujjatini yuklash")}</CardTitle>
        {limits && (
          <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-[14px] text-muted">
            <span>{t("PDF, DOCX, JPG yoki PNG — bir nechta faylni birga yuklash mumkin.")}</span>
            <span className="font-medium text-ink">
              {limits.unlimited
                ? t("Cheklovsiz rejim ({{mb}} MB gacha)", { mb: limits.max_mb })
                : t("Tarifingiz ({{plan}}): {{pages}} varaqgacha, {{mb}} MB", {
                    plan: limits.plan_name ?? t("Bepul"),
                    pages: limits.max_pages,
                    mb: limits.max_mb,
                  })}
            </span>
            {limits.cases_remaining !== null && limits.cases_remaining !== undefined && (
              <span
                className={cn(
                  "rounded px-1.5 py-0.5 text-xs font-semibold tabular-nums",
                  limits.cases_exhausted
                    ? "bg-red/10 text-red"
                    : limits.cases_remaining <= 1
                      ? "bg-amber/10 text-amber"
                      : "bg-subtle text-muted"
                )}
              >
                {t("qolgan ishlar: {{n}} ta", { n: limits.cases_remaining })}
              </span>
            )}
          </div>
        )}
      </CardHeader>
      <CardContent>
        {limits?.cases_exhausted && (
          <div className="mb-5 flex flex-col gap-2 rounded-xl border border-amber/40 bg-amber/10 p-4 text-sm sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="flex items-center gap-1.5 font-semibold text-amber">
                <AlertCircleIcon className="size-4 shrink-0" />
                {t("Ish tahlili limitingiz tugagan")}
              </div>
              <p className="mt-1 text-xs text-muted">
                {limits.plan_code === "FREE"
                  ? t("Siz bepul tarifdagi 1 ta ish tahlili limitingizdan foydalangansiz. Yangi ishlarni tahlil qilish uchun Pro tarifiga oʻting.")
                  : t("Ushbu davr uchun ish tahlili limitingiz tugadi. Yangi ishlarni tahlil qilish uchun tarifingizni yangilang.")}
              </p>
            </div>
            <Button
              type="button"
              variant="gold"
              size="sm"
              onClick={() => navigate("/billing")}
              className="self-start sm:self-auto shrink-0"
            >
              <CrownIcon className="size-4" /> {t("Tarifni yangilash")}
            </Button>
          </div>
        )}
        <form onSubmit={submit} className="flex flex-col gap-5">
          <div
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            onClick={() => inputRef.current?.click()}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && inputRef.current?.click()}
            className={cn("flex cursor-pointer flex-col items-center gap-2 rounded-xl border-2 border-dashed border-line bg-subtle/40 px-4 py-10 text-center text-sm text-muted outline-none transition-colors hover:border-primary/50 hover:bg-subtle focus-visible:shadow-glow",
              dragging && "border-primary bg-primary/5")}
          >
            <UploadCloudIcon className="size-9 text-primary" />
            <span className="text-[15px] font-medium text-ink">{t("Fayllarni shu yerga tashlang yoki tanlang")}</span>
            <span className="tabular-nums text-xs">PDF · DOCX · JPG · PNG</span>
            <input ref={inputRef} type="file" multiple accept={ACCEPT} className="hidden"
              onChange={(e) => { addFiles(e.target.files); e.target.value = ""; }} />
          </div>
          {files.length > 0 && (
            <ul className="flex flex-col gap-1">
              {files.map((f, i) => (
                <li key={`${f.name}-${i}`} className="flex items-center gap-3 rounded-lg border border-line px-3 py-2 text-sm">
                  <FileUpIcon className="size-4 text-primary" />
                  <span className="min-w-0 flex-1 truncate">{f.name}</span>
                  <span className="tabular-nums text-xs text-muted">{(f.size / 1024 / 1024).toFixed(1)} MB</span>
                  <button type="button" onClick={() => setFiles((all) => all.filter((_, j) => j !== i))} className="text-muted hover:text-red" aria-label="×">
                    <XIcon className="size-4" />
                  </button>
                </li>
              ))}
              <li className="text-right tabular-nums text-xs text-muted">
                {files.length} · {totalMb.toFixed(1)} / {limits?.max_mb ?? "…"} MB
              </li>
            </ul>
          )}
          <div className="grid gap-4 sm:grid-cols-[1fr_240px]">
            <div>
              <Label htmlFor="title">{t("Ish nomi (ixtiyoriy)")}</Label>
              <Input id="title" value={title} onChange={(e) => setTitle(e.target.value)} maxLength={255} />
            </div>
            <div>
              <Label htmlFor="category">{t("Ish turi")}</Label>
              <NativeSelect id="category" value={category} onChange={(e) => setCategory(e.target.value)}>
                {(limits?.case_types ?? []).map((c) => <option key={c.code} value={c.code}>{c.label}</option>)}
              </NativeSelect>
            </div>
          </div>
          <label className="flex items-start gap-3 text-sm text-muted">
            <Checkbox checked={zeroRetention} onCheckedChange={(v) => setZeroRetention(v === true)} />
            <span>{t("Tahlil tugagach fayllarni serverdan oʻchirish (hisobot qoladi, lekin varaqlarni koʻrib boʻlmaydi)")}</span>
          </label>
          <div className="flex flex-wrap items-center justify-between gap-4 border-t border-line pt-5">
            <p className="flex max-w-md items-start gap-2 text-[13px] text-muted">
              <ShieldCheckIcon className="mt-0.5 size-4 shrink-0 text-green" aria-hidden />
              {t("Shaxsiy maʼlumotlar tahlilga yuborilishidan oldin niqoblanadi; fayl va hisobot serverda shifrlangan holda saqlanadi.")}
            </p>
            {limits?.cases_exhausted ? (
              <Button type="button" variant="gold" size="lg" onClick={() => navigate("/billing")}>
                <CrownIcon className="size-4" /> {t("Obunani yangilash")}
              </Button>
            ) : (
              <Button type="submit" size="lg" disabled={!files.length || upload.isPending}>
                {upload.isPending && <Spinner className="text-primary-foreground" />}
                {t("Tahlilga yuborish")}
              </Button>
            )}
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

function CaseList() {
  const { t } = useTranslation();
  const { language } = useLanguage();
  const [page, setPage] = useState(1);
  const { data, isLoading } = useQuery({
    queryKey: keys.cases(page),
    queryFn: () => unwrap(api.client.GET("/api/v1/cases/", { params: { query: { page } } })),
    // tahlil ketayotgan ish bo'lsa — holat 3 s da yangilanadi
    refetchInterval: (q) => (q.state.data?.results.some((r) => isActive(r.status)) ? 3000 : false),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("Ishlar")}</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex flex-col gap-2">
            {[0, 1, 2].map((i) => <Skeleton key={i} className="h-14" style={staggerStyle(i, 60)} />)}
          </div>
        ) : !data?.results.length ? (
          <Empty>{t("Hali ish yuklanmagan.")}</Empty>
        ) : (
          <>
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-[13px] text-muted">
                    <th className="pb-3 pr-4 font-medium">{t("Ish")}</th>
                    <th className="pb-3 pr-4 font-medium">{t("Ish turi")}</th>
                    <th className="pb-3 pr-4 font-medium">{t("Varaq")}</th>
                    <th className="pb-3 pr-4 font-medium">{t("Holat")}</th>
                    <th className="pb-3 font-medium">{t("Sana")}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.results.map((r, i) => (
                    <tr key={r.id} className="animate-in-up border-t border-line" style={staggerStyle(i)}>
                      <td className="max-w-80 py-3.5 pr-4">
                        <Link to={`/cases/${r.id}`} className="block truncate font-medium hover:text-primary">{r.title}</Link>
                      </td>
                      <td className="py-3.5 pr-4 text-muted">{r.category_label}</td>
                      <td className="py-3.5 pr-4 tabular-nums">{r.pages}</td>
                      <td className="py-3.5 pr-4"><CaseStatusBadge run={r} /></td>
                      <td className="py-3.5 tabular-nums text-[13px] text-muted">{formatDateTime(r.created_at, language)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <ul className="flex flex-col gap-2 md:hidden">
              {data.results.map((r, i) => (
                <FadeIn as="li" key={r.id} delay={staggerDelay(i)}>
                  <Link to={`/cases/${r.id}`} className="block rounded-xl border border-line p-4">
                    <div className="truncate font-medium">{r.title}</div>
                    <div className="mt-1.5 flex flex-wrap items-center gap-2 text-xs text-muted">
                      <CaseStatusBadge run={r} />
                      <span>{r.category_label}</span>
                      <span className="tabular-nums">{t("{{n}} varaq", { n: r.pages })}</span>
                    </div>
                  </Link>
                </FadeIn>
              ))}
            </ul>
            {(data.next || data.previous) && (
              <div className="mt-4 flex items-center justify-end gap-2">
                <Button variant="outline" size="sm" disabled={!data.previous} onClick={() => setPage((p) => p - 1)}>←</Button>
                <span className="tabular-nums text-xs text-muted">{page} / {Math.ceil(data.count / 20)}</span>
                <Button variant="outline" size="sm" disabled={!data.next} onClick={() => setPage((p) => p + 1)}>→</Button>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

export function CasesPage() {
  const { t } = useTranslation();
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6 px-5 py-10 sm:px-8">
      <PageHeader title={t("Ish tahlili")} className="mb-2" />
      <FadeIn><UploadCard /></FadeIn>
      <FadeIn delay={70}><CaseList /></FadeIn>
    </div>
  );
}
