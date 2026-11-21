/** Hujjatlar konstruktori: 6 ta asosiy toifa va bo'limlar bo'yicha shablonlar katalogi. TZ §5.1.1. */
import { unwrap, type Schemas } from "@mezon/api-client";
import { useQuery } from "@tanstack/react-query";
import {
  Building2Icon,
  ChevronDownIcon,
  ChevronRightIcon,
  FileSignatureIcon,
  FileTextIcon,
  LayersIcon,
  ScaleIcon,
  SearchIcon,
  StampIcon,
  UsersIcon,
  XIcon,
} from "lucide-react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import {
  api,
  Badge,
  Button,
  cn,
  Empty,
  FadeIn,
  Input,
  Skeleton,
  staggerDelay,
  staggerStyle,
} from "@mezon/web-kit";

import { keys } from "@/lib/queries";

type TemplateItem = Schemas["Template"];

interface CategoryMeta {
  code: string;
  labels: Record<string, string>;
  icon: React.ComponentType<{ className?: string }>;
}

const CATEGORY_CONFIG: Record<string, CategoryMeta> = {
  CONTRACTS: {
    code: "CONTRACTS",
    labels: {
      "uz-Latn": "Shartnomalar",
      "uz-Cyrl": "Шартномалар",
      ru: "Договоры",
    },
    icon: FileSignatureIcon,
  },
  STATEMENTS: {
    code: "STATEMENTS",
    labels: {
      "uz-Latn": "Arizalar",
      "uz-Cyrl": "Аризалар",
      ru: "Заявления",
    },
    icon: FileTextIcon,
  },
  PERSONAL: {
    code: "PERSONAL",
    labels: {
      "uz-Latn": "Shaxsiy tarkibga oid hujjatlar",
      "uz-Cyrl": "Шахсий таркибга оид ҳужжатлар",
      ru: "Документы по личному составу",
    },
    icon: UsersIcon,
  },
  NOTARIAL: {
    code: "NOTARIAL",
    labels: {
      "uz-Latn": "Notarial tasdiqlanadigan hujjatlar",
      "uz-Cyrl": "Нотариал тасдиқланадиган ҳужжатлар",
      ru: "Нотариально удостоверяемые документы",
    },
    icon: StampIcon,
  },
  COURT: {
    code: "COURT",
    labels: {
      "uz-Latn": "Sudga oid hujjatlar",
      "uz-Cyrl": "Судга оид ҳужжатлар",
      ru: "Судебные документы",
    },
    icon: ScaleIcon,
  },
  CORPORATE: {
    code: "CORPORATE",
    labels: {
      "uz-Latn": "Korporativ hujjatlar",
      "uz-Cyrl": "Корпоратив ҳужжатлар",
      ru: "Корпоративные документы",
    },
    icon: Building2Icon,
  },
};

const ORDERED_CATEGORIES = [
  "CONTRACTS",
  "STATEMENTS",
  "PERSONAL",
  "NOTARIAL",
  "COURT",
  "CORPORATE",
] as const;

const LANG_BADGES: Record<string, { label: string; name: string }> = {
  "uz-Latn": { label: "UZ", name: "Oʻzbekcha (lotin)" },
  "uz-Cyrl": { label: "ЎЗ", name: "Ўзбекча (кирилл)" },
  ru: { label: "RU", name: "Русский" },
};

const PAGE_SIZE = 40;

function resolveLangKey(lang: string): string {
  const norm = (lang || "uz-Latn").toLowerCase();
  if (norm.includes("cyrl")) return "uz-Cyrl";
  if (norm.startsWith("ru")) return "ru";
  return "uz-Latn";
}

function getLocalizedTitle(tpl: TemplateItem, langKey: string): string {
  const trans = (tpl.title_translations ?? {}) as Record<string, string>;
  return trans[langKey] || trans["uz-Latn"] || tpl.title;
}

function getLocalizedSubcategory(tpl: TemplateItem, langKey: string): string {
  const trans = (tpl.subcategory_translations ?? {}) as Record<string, string>;
  return trans[langKey] || trans["uz-Latn"] || tpl.subcategory || "";
}

function getCategoryName(categoryCode: string, langKey: string, fallback?: string): string {
  const config = CATEGORY_CONFIG[categoryCode];
  return config?.labels[langKey] || fallback || categoryCode;
}

export function TemplatesPage() {
  const { t, i18n } = useTranslation();
  const currentLang = resolveLangKey(i18n.language);

  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<string>("");
  const [subcategory, setSubcategory] = useState<string>("");
  const [visibleLimit, setVisibleLimit] = useState<number>(PAGE_SIZE);

  const { data, isLoading } = useQuery({
    queryKey: keys.templates,
    queryFn: () => unwrap(api.client.GET("/api/v1/templates/")),
  });

  const all = data ?? [];

  // 6 ta toifa va ularning ichki bo'limlari (counts bilan)
  const categoryStats = useMemo(() => {
    const stats: Record<string, { count: number; subcategories: { slug: string; name: string; count: number }[] }> = {};

    for (const catCode of ORDERED_CATEGORIES) {
      const catTemplates = all.filter((tpl) => tpl.category === catCode);
      const subMap = new Map<string, { slug: string; name: string; count: number }>();

      for (const tpl of catTemplates) {
        const slug = tpl.subcategory_slug || tpl.subcategory || "";
        const name = getLocalizedSubcategory(tpl, currentLang) || tpl.subcategory || slug;
        if (!slug) continue;
        if (!subMap.has(slug)) {
          subMap.set(slug, { slug, name, count: 0 });
        }
        subMap.get(slug)!.count++;
      }

      stats[catCode] = {
        count: catTemplates.length,
        subcategories: Array.from(subMap.values()).sort((a, b) => b.count - a.count),
      };
    }
    return stats;
  }, [all, currentLang]);

  // Filtrlar
  const q = query.trim().toLowerCase();
  const filtered = useMemo(() => {
    return all.filter((tpl) => {
      if (category && tpl.category !== category) return false;
      if (subcategory && tpl.subcategory_slug !== subcategory && tpl.subcategory !== subcategory) return false;

      if (q) {
        const title = getLocalizedTitle(tpl, currentLang).toLowerCase();
        const subcat = getLocalizedSubcategory(tpl, currentLang).toLowerCase();
        const desc = (tpl.description ?? "").toLowerCase();
        const docId = String(tpl.doc_id ?? "");
        if (!title.includes(q) && !subcat.includes(q) && !desc.includes(q) && !docId.includes(q)) {
          return false;
        }
      }
      return true;
    });
  }, [all, category, subcategory, q, currentLang]);

  const pagedItems = useMemo(() => filtered.slice(0, visibleLimit), [filtered, visibleLimit]);
  const hasMore = filtered.length > visibleLimit;

  function handleSelectCategory(catCode: string) {
    if (category === catCode) {
      // Ochiq toifa yoki strelka qayta bosilsa — bo'lim yopiladi va "Barcha hujjatlar"ga qaytiladi
      setCategory("");
      setSubcategory("");
      setVisibleLimit(PAGE_SIZE);
    } else {
      setCategory(catCode);
      setSubcategory("");
      setVisibleLimit(PAGE_SIZE);
    }
  }

  function handleResetFilters() {
    setCategory("");
    setSubcategory("");
    setQuery("");
    setVisibleLimit(PAGE_SIZE);
  }

  const activeCategoryMeta = category ? CATEGORY_CONFIG[category] : null;
  const activeSubcategoryMeta = category && subcategory
    ? categoryStats[category]?.subcategories.find((s) => s.slug === subcategory)
    : null;

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-8 sm:px-6 lg:px-8">
      {/* Sarlavha va tavsif */}
      <div className="flex flex-col gap-2">
        <h1 className="font-serif text-[28px] sm:text-[32px] font-semibold leading-tight text-ink">
          {t("Hujjatlar konstruktori")}
        </h1>
        <p className="max-w-3xl text-sm text-muted">
          {t(
            "Shablonni tanlang, formani toʻldiring — hujjat Times New Roman 14 pt bilan DOCX yoki PDF koʻrinishida tayyorlanadi. Kiritilgan maʼlumotlar serverda saqlanmaydi."
          )}
        </p>
      </div>

      {/* Qidiruv qatori */}
      <div className="relative">
        <SearchIcon className="absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-muted" />
        <Input
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setVisibleLimit(PAGE_SIZE);
          }}
          placeholder={t("Shablon nomi, boʻlimi yoki kalit soʻz boʻyicha qidirish…")}
          className="h-11 pl-10 pr-9 text-sm"
          aria-label={t("Shablon qidirish")}
        />
        {query && (
          <button
            type="button"
            onClick={() => setQuery("")}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-ink"
            aria-label={t("Tozalash")}
          >
            <XIcon className="size-4" />
          </button>
        )}
      </div>

      {/* Asosiy 2 ustunli tuzilma: Chapda 6 toifa va bo'limlar, O'ngda hujjatlar */}
      <div className="grid grid-cols-1 items-start gap-8 lg:grid-cols-[290px_1fr]">
        {/* Chap panel: 6 ta asosiy toifa va ularning bo'limlari */}
        <aside className="flex flex-col gap-2 rounded-2xl border border-line bg-surface p-3 shadow-xs">
          <div className="flex items-center justify-between px-3 py-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted">
              {t("Toifalar")}
            </span>
            <span className="text-xs text-muted">{all.length} ta</span>
          </div>

          {/* Barchasi tugmasi */}
          <button
            type="button"
            onClick={handleResetFilters}
            className={cn(
              "flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-left text-[13px] font-medium transition-colors",
              !category && !subcategory
                ? "bg-primary/10 text-primary font-semibold"
                : "text-ink hover:bg-subtle"
            )}
          >
            <span className="flex items-center gap-2.5">
              <LayersIcon className="size-4 text-muted" />
              <span>{t("Barcha hujjatlar")}</span>
            </span>
            <span className="rounded-full bg-subtle px-2 py-0.5 text-[11px] font-mono text-muted">
              {all.length}
            </span>
          </button>

          <div className="my-1 h-px bg-line" />

          {/* 6 ta asosiy toifa ro'yxati */}
          <div className="flex flex-col gap-1">
            {ORDERED_CATEGORIES.map((catCode) => {
              const config = CATEGORY_CONFIG[catCode];
              const Icon = config.icon;
              const stats = categoryStats[catCode];
              const isCatActive = category === catCode;
              const totalInCat = stats?.count ?? 0;
              const subcats = stats?.subcategories ?? [];

              return (
                <div key={catCode} className="flex flex-col">
                  {/* Toifa sarlavha tugmasi */}
                  <button
                    type="button"
                    onClick={() => handleSelectCategory(catCode)}
                    aria-expanded={isCatActive}
                    title={isCatActive ? t("Boʻlimni yopish") : t("Boʻlimni ochish")}
                    className={cn(
                      "group flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-left text-[13px] font-medium transition-colors cursor-pointer",
                      isCatActive
                        ? "bg-primary/10 text-primary font-semibold"
                        : "text-ink hover:bg-subtle"
                    )}
                  >
                    <span className="flex items-center gap-2.5 min-w-0 pr-2">
                      <Icon className={cn("size-4 shrink-0 transition-colors", isCatActive ? "text-primary" : "text-muted group-hover:text-ink")} />
                      <span className="truncate">{getCategoryName(catCode, currentLang)}</span>
                    </span>
                    <span className="flex items-center gap-1.5 shrink-0">
                      <span className="rounded-full bg-subtle px-2 py-0.5 text-[11px] font-mono text-muted">
                        {totalInCat}
                      </span>
                      <span
                        className={cn(
                          "flex size-5 items-center justify-center rounded transition-transform duration-200",
                          isCatActive ? "text-primary" : "text-muted group-hover:text-ink"
                        )}
                        title={isCatActive ? t("Yopish") : t("Ochish")}
                      >
                        {isCatActive ? (
                          <ChevronDownIcon className="size-3.5" />
                        ) : (
                          <ChevronRightIcon className="size-3.5" />
                        )}
                      </span>
                    </span>
                  </button>

                  {/* Agar toifa ochiq bo'lsa — uning ichki bo'limlari (subcategories tree) */}
                  {isCatActive && subcats.length > 0 && (
                    <div className="relative my-1 ml-4 flex flex-col gap-0.5 border-l border-line pl-2.5 pt-0.5 animate-in-fade">
                      {/* Barcha [toifa] bo'limi */}
                      <button
                        type="button"
                        onClick={() => {
                          setSubcategory("");
                          setVisibleLimit(PAGE_SIZE);
                        }}
                        className={cn(
                          "flex items-center justify-between rounded-lg px-2.5 py-1.5 text-left text-xs transition-colors",
                          !subcategory
                            ? "bg-primary/15 font-semibold text-primary"
                            : "text-muted hover:bg-subtle hover:text-ink"
                        )}
                      >
                        <span>{t("Barchasi")}</span>
                        <span className="text-[11px] font-mono opacity-80">{totalInCat}</span>
                      </button>

                      {/* Ichki bo'limlar */}
                      {subcats.map((sc) => {
                        const isSubActive = subcategory === sc.slug;
                        return (
                          <button
                            key={sc.slug}
                            type="button"
                            onClick={() => {
                              setSubcategory(sc.slug);
                              setVisibleLimit(PAGE_SIZE);
                            }}
                            className={cn(
                              "flex items-center justify-between rounded-lg px-2.5 py-1.5 text-left text-xs transition-colors",
                              isSubActive
                                ? "bg-primary/15 font-semibold text-primary"
                                : "text-muted hover:bg-subtle hover:text-ink"
                            )}
                          >
                            <span className="truncate pr-2">{sc.name}</span>
                            <span className="shrink-0 text-[11px] font-mono opacity-80">{sc.count}</span>
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </aside>

        {/* O'ng panel: Shablonlar ro'yxati va holat */}
        <main className="flex flex-col gap-4">
          {/* Breadcrumb va natijalar hisobi */}
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line pb-3">
            <div className="flex items-center gap-1.5 text-xs text-muted">
              <span>{t("Hujjatlar")}</span>
              {activeCategoryMeta && (
                <>
                  <ChevronRightIcon className="size-3 text-muted" />
                  <span className="font-medium text-ink">
                    {getCategoryName(activeCategoryMeta.code, currentLang)}
                  </span>
                </>
              )}
              {activeSubcategoryMeta && (
                <>
                  <ChevronRightIcon className="size-3 text-muted" />
                  <span className="font-semibold text-primary">{activeSubcategoryMeta.name}</span>
                </>
              )}
              <span className="ml-1 text-muted">({filtered.length} ta)</span>
            </div>

            {(category || subcategory || query) && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={handleResetFilters}
                className="h-7 text-xs text-muted hover:text-ink"
              >
                <XIcon className="mr-1 size-3" /> {t("Filtrni tozalash")}
              </Button>
            )}
          </div>

          {/* Shablonlar kartochkalari */}
          {isLoading ? (
            <div className="grid gap-3 sm:grid-cols-2">
              {[0, 1, 2, 3, 4, 5].map((i) => (
                <Skeleton key={i} className="h-32 rounded-xl" style={staggerStyle(i, 40)} />
              ))}
            </div>
          ) : !filtered.length ? (
            <Empty>
              <div className="flex flex-col items-center gap-2 text-center">
                <span>{t("Mos keluvchi shablon topilmadi.")}</span>
                {(query || category || subcategory) && (
                  <Button variant="outline" size="sm" onClick={handleResetFilters} className="mt-2 text-xs">
                    {t("Barcha shablonlarni koʻrsatish")}
                  </Button>
                )}
              </div>
            </Empty>
          ) : (
            <>
              <div className="grid gap-3 sm:grid-cols-2">
                {pagedItems.map((tpl, idx) => {
                  const title = getLocalizedTitle(tpl, currentLang);
                  const subcat = getLocalizedSubcategory(tpl, currentLang);
                  const available = (tpl.available_languages as string[] | undefined) ?? ["uz-Latn"];

                  return (
                    <FadeIn
                      as={Link}
                      key={tpl.id}
                      to={`/templates/${tpl.id}`}
                      delay={staggerDelay(idx % PAGE_SIZE, 20)}
                      className="group flex flex-col justify-between rounded-xl border border-line bg-surface p-4 transition-all hover:border-primary/60 hover:shadow-sm"
                    >
                      <div className="flex flex-col gap-2">
                        {/* Yuqori qator: Bo'lim yorlig'i va Mavjud tillar nishonlari */}
                        <div className="flex items-center justify-between gap-2">
                          <span className="truncate text-[11px] font-medium text-primary/90">
                            {subcat || getCategoryName(tpl.category, currentLang, tpl.category_label)}
                          </span>

                          {/* 3 xil til (UZ, ЎЗ, RU) indikatorlari */}
                          <div className="flex items-center gap-1 shrink-0" title={t("Mavjud tillar")}>
                            {available.map((l) => {
                              const badge = LANG_BADGES[l];
                              if (!badge) return null;
                              return (
                                <span
                                  key={l}
                                  title={badge.name}
                                  className="rounded border border-line bg-subtle px-1.5 py-0.5 font-mono text-[10px] font-semibold text-muted group-hover:text-ink transition-colors"
                                >
                                  {badge.label}
                                </span>
                              );
                            })}
                          </div>
                        </div>

                        {/* Hujjat nomi */}
                        <h2 className="font-serif text-[15px] font-semibold leading-snug text-ink transition-colors group-hover:text-primary">
                          {title}
                        </h2>

                        {/* Tavsifi */}
                        {tpl.description && (
                          <p className="line-clamp-2 text-xs text-muted leading-relaxed">
                            {tpl.description}
                          </p>
                        )}
                      </div>

                      {/* Pastki qator: Doc ID, Versiya va O'tish tugmasi */}
                      <div className="mt-4 flex items-center justify-between border-t border-line/60 pt-2.5 text-xs text-muted">
                        <div className="flex items-center gap-2">
                          {tpl.doc_id ? (
                            <span className="font-mono text-[11px] text-muted">#{tpl.doc_id}</span>
                          ) : null}
                          {tpl.is_approved ? (
                            <Badge tone="ok" mono className="text-[10px]">
                              ✓ {t("tasdiqlangan")}
                            </Badge>
                          ) : (
                            <Badge tone="warn" className="text-[10px]">
                              {t("namuna")}
                            </Badge>
                          )}
                        </div>

                        <span className="flex items-center gap-1 text-[12px] font-medium text-primary group-hover:translate-x-0.5 transition-transform">
                          <span>{t("Toʻldirish")}</span>
                          <ChevronRightIcon className="size-3.5" />
                        </span>
                      </div>
                    </FadeIn>
                  );
                })}
              </div>

              {/* Yana ko'rsatish tugmasi */}
              {hasMore && (
                <div className="mt-4 flex flex-col items-center gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setVisibleLimit((v) => v + PAGE_SIZE)}
                    className="text-xs"
                  >
                    {t("Yana {{n}} ta koʻrsatish", { n: Math.min(PAGE_SIZE, filtered.length - visibleLimit) })}
                  </Button>
                  <span className="text-[11px] text-muted">
                    {t("{{shown}} / {{total}} ta koʻrsatilmoqda", {
                      shown: Math.min(visibleLimit, filtered.length),
                      total: filtered.length,
                    })}
                  </span>
                </div>
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}
