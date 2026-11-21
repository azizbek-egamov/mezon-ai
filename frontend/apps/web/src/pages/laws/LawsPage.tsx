/**
 * Qonunlar bazasi (lex.uz korpusi): hujjat nomi bo'yicha qidiruv -> moddalar ro'yxati -> modda matni (lotin/kirill/rus);
 * semantik qidiruv (LLM siz — pul ketmaydi, GPU va Qdrant ishlaydi). Holat URL da: ?doc=&article=&lang=
 */
import { unwrap } from "@mezon/api-client";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { ExternalLinkIcon, SearchIcon, SparklesIcon } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router";
import { api, Badge, Button, Card, CiteChip, cn, Empty, ErrorNote, FadeIn, formatDate, Input, Spinner, staggerDelay, staggerStyle, Tabs, TabsContent, TabsList, TabsTrigger, useLanguage } from "@mezon/web-kit";

type CorpusLang = "lat" | "cyr" | "ru";
const CORPUS_LANGS: { code: CorpusLang; name: string }[] = [
  { code: "lat", name: "Oʻzbekcha" },
  { code: "cyr", name: "Ўзбекча" },
  { code: "ru", name: "Русский" },
];
const UI_TO_CORPUS: Record<string, CorpusLang> = { "uz-Latn": "lat", "uz-Cyrl": "cyr", ru: "ru", kaa: "lat", en: "lat" };

function useDebounced<T>(value: T, ms = 350): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setV(value), ms);
    return () => clearTimeout(timer);
  }, [value, ms]);
  return v;
}

function ArticleView({ articleId, lang }: { articleId: number; lang: CorpusLang }) {
  const { t } = useTranslation();
  const { data, isLoading, error } = useQuery({
    queryKey: ["laws", "article", articleId, lang],
    queryFn: () => unwrap(api.client.GET("/api/v1/laws/articles/{article_id}", { params: { path: { article_id: articleId }, query: { lang } } })),
  });
  if (isLoading) return <Empty><Spinner /></Empty>;
  if (error || !data) return <ErrorNote>{error?.message}</ErrorNote>;
  return (
    <Card accent="gold" className="animate-in-up p-5">
      <div className="label-code text-muted">{data.doc_title}</div>
      <h2 className="mt-1 text-lg font-semibold">{data.label}</h2>
      {data.section_path && <div className="mt-0.5 text-xs text-muted">{data.section_path}</div>}
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <Badge mono tone={data.is_current ? "ok" : "warn"}>{t("tahrir")} {data.edition}</Badge>
        {data.lang !== lang && <Badge tone="warn">{CORPUS_LANGS.find((l) => l.code === data.lang)?.name}</Badge>}
        <CiteChip href={data.lex_url}>lex.uz <ExternalLinkIcon className="inline size-3" /></CiteChip>
      </div>
      <div className="mt-4 space-y-2 text-[15px] leading-relaxed">
        {data.parts.length
          ? data.parts.map((p, i) => <p key={i}>{p.text}</p>)
          : data.text.split("\n").map((line, i) => <p key={i}>{line}</p>)}
      </div>
    </Card>
  );
}

function DocumentBrowser({ lang }: { lang: CorpusLang }) {
  const { t } = useTranslation();
  const { language } = useLanguage();
  const [params, setParams] = useSearchParams();
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState("");
  const query = useDebounced(q);
  const docId = Number(params.get("doc")) || null;
  const articleId = Number(params.get("article")) || null;
  const setParam = (patch: Record<string, string | null>) =>
    setParams((p) => {
      Object.entries(patch).forEach(([k, v]) => (v === null ? p.delete(k) : p.set(k, v)));
      return p;
    });

  const docs = useQuery({
    queryKey: ["laws", "documents", query, lang],
    queryFn: () => unwrap(api.client.GET("/api/v1/laws/documents", { params: { query: { q: query || undefined, lang } } })),
    placeholderData: keepPreviousData,
  });
  const doc = useQuery({
    queryKey: ["laws", "document", docId, lang],
    queryFn: () => unwrap(api.client.GET("/api/v1/laws/documents/{doc_id}", { params: { path: { doc_id: docId! }, query: { lang } } })),
    enabled: !!docId,
  });
  // Filtr: yorliq matni yoki modda raqami ("168", "168-", "Статья 168" — tildan qat'i nazar)
  const needle = filter.trim().toLowerCase();
  const number = /^\d+/.exec(needle)?.[0];
  const articles = (doc.data?.articles ?? []).filter((a) =>
    !needle || a.label.toLowerCase().includes(needle) || (!!number && a.article_number.startsWith(number)));

  return (
    <div className="grid gap-4 lg:grid-cols-[320px_minmax(0,1fr)]">
      <div className="flex flex-col gap-2">
        <div className="relative">
          <SearchIcon className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("Hujjat nomi yoki raqami")} className="pl-9" aria-label={t("Hujjat nomi yoki raqami")} />
        </div>
        <div className="max-h-[70vh] overflow-y-auto rounded-lg border border-line bg-surface">
          {docs.isLoading ? <Empty><Spinner /></Empty> : (docs.data?.results ?? []).map((d, i) => (
            <button key={d.id} onClick={() => setParam({ doc: String(d.id), article: null })} style={staggerStyle(i, 35)}
              className={cn("animate-in-up block w-full border-b border-line px-3 py-2.5 text-left last:border-0 hover:bg-subtle", d.id === docId && "bg-subtle shadow-[inset_2px_0_0_var(--color-gold)]")}>
              <span className="line-clamp-2 text-sm font-medium">{d.title}</span>
              <span className="mt-1 flex flex-wrap gap-1.5 tabular-nums text-xs text-muted">
                <span>{d.doc_type_label}</span>
                {d.official_number && <span>№ {d.official_number}</span>}
                {d.adoption_date && <span>{formatDate(d.adoption_date, language)}</span>}
              </span>
            </button>
          ))}
          {docs.data && !docs.data.results.length && <Empty>{t("Topilmadi.")}</Empty>}
        </div>
        {docs.data && <div className="text-right tabular-nums text-xs text-muted">{docs.data.count}</div>}
      </div>

      <div className="min-w-0">
        {!docId ? (
          <Empty>{t("Hujjatni tanlang")}</Empty>
        ) : doc.isLoading ? (
          <Empty><Spinner /></Empty>
        ) : doc.error || !doc.data ? (
          <ErrorNote>{doc.error?.message}</ErrorNote>
        ) : (
          <div className="grid gap-4 xl:grid-cols-[280px_minmax(0,1fr)]">
            <div className="flex flex-col gap-2">
              <Card className="p-3">
                <div className="text-sm font-semibold">{doc.data.title}</div>
                <div className="mt-1 flex flex-wrap gap-1.5">
                  <Badge mono tone={doc.data.status === "ACTIVE" ? "ok" : "bad"}>{doc.data.status_label}</Badge>
                  <Badge mono>{t("tahrir")} {doc.data.edition}</Badge>
                </div>
              </Card>
              <Input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder={t("Modda")} className="h-8 text-xs" aria-label={t("Modda")} />
              <div className="max-h-[60vh] overflow-y-auto rounded-lg border border-line bg-surface">
                {articles.map((a, i) => (
                  <button key={a.id} onClick={() => setParam({ article: String(a.id) })} title={a.section_path} style={staggerStyle(i, 25)}
                    className={cn("animate-in-up block w-full truncate border-b border-line px-3 py-1.5 text-left text-[13px] last:border-0 hover:bg-subtle", a.id === articleId && "bg-subtle text-gold")}>
                    {a.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="min-w-0">{articleId ? <ArticleView articleId={articleId} lang={lang} /> : <Empty>{t("Moddani tanlang")}</Empty>}</div>
          </div>
        )}
      </div>
    </div>
  );
}

function SemanticSearch({ lang }: { lang: CorpusLang }) {
  const { t } = useTranslation();
  const [input, setInput] = useState("");
  const [query, setQuery] = useState("");
  const { data, isFetching, error } = useQuery({
    queryKey: ["laws", "search", query, lang],
    queryFn: () => unwrap(api.client.GET("/api/v1/laws/search", { params: { query: { q: query, lang, limit: 10 } } })),
    enabled: !!query,
    staleTime: Infinity,
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    setQuery(input.trim());
  };
  return (
    <div className="flex flex-col gap-3">
      <form onSubmit={submit} className="flex gap-2">
        <Input value={input} onChange={(e) => setInput(e.target.value)} maxLength={500} placeholder={t("Masalan: firibgarlik uchun jazo")} aria-label={t("Masalan: firibgarlik uchun jazo")} />
        <Button type="submit" disabled={!input.trim() || isFetching}>{isFetching ? <Spinner className="text-primary-foreground" /> : <SparklesIcon />}{t("Qidirish")}</Button>
      </form>
      <p className="text-xs text-muted">{t("Maʼno boʻyicha qidiruv: AI javob yozmaydi, faqat mos moddalarni topadi.")}</p>
      {error && <ErrorNote>{error.message}</ErrorNote>}
      {(data ?? []).map((h, i) => (
        <Card key={h.article_id} accent={h.exact ? "gold" : "blue"} className="animate-in-up p-4" style={staggerStyle(i, 70)}>
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-semibold">{h.label}</span>
            <span className="text-xs text-muted">{h.doc_title}</span>
            <span className="ml-auto tabular-nums text-xs text-muted">{h.score.toFixed(3)}</span>
          </div>
          <p className="mt-2 line-clamp-4 text-sm text-ink/90">{h.text}</p>
          <div className="mt-2 flex gap-2">
            <CiteChip href={h.lex_url}>lex.uz · {t("tahrir")} {h.edition}</CiteChip>
          </div>
        </Card>
      ))}
      {data && !data.length && <Empty>{t("Mos qonun moddalari topilmadi.")}</Empty>}
    </div>
  );
}

export function LawsPage() {
  const { t } = useTranslation();
  const { language } = useLanguage();
  const [params, setParams] = useSearchParams();
  const lang = (params.get("lang") as CorpusLang) || UI_TO_CORPUS[language] || "lat";

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6 px-5 py-10 sm:px-8">
      <FadeIn className="flex flex-wrap items-end gap-3">
        <div className="flex-1">
          <h1 className="font-serif text-[30px] font-semibold leading-tight">{t("Qonunlar")}</h1>
          <p className="text-sm text-muted">{t("lex.uz yadro korpusi · iqtiboslar avtomatik tekshiriladi")}</p>
        </div>
        <div className="flex rounded-lg border border-line bg-canvas p-0.5">
          {CORPUS_LANGS.map((l) => (
            <button key={l.code} onClick={() => setParams((p) => { p.set("lang", l.code); return p; })}
              className={cn("rounded px-3 py-1 text-xs font-medium text-muted", lang === l.code && "bg-subtle text-ink")}>
              {l.name}
            </button>
          ))}
        </div>
      </FadeIn>
      <FadeIn delay={staggerDelay(1, 60)}>
      <Tabs defaultValue="docs">
        <TabsList>
          <TabsTrigger value="docs">{t("Hujjatlar")}</TabsTrigger>
          <TabsTrigger value="search"><SparklesIcon className="size-3.5" />{t("Maʼno boʻyicha qidiruv")}</TabsTrigger>
        </TabsList>
        <TabsContent value="docs"><DocumentBrowser lang={lang} /></TabsContent>
        <TabsContent value="search"><SemanticSearch lang={lang} /></TabsContent>
      </Tabs>
      </FadeIn>
    </div>
  );
}
