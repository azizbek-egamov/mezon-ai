/**
 * Yorug' / qorong'i rejim (designs/mezon_klassik/DESIGN.md). Tanlov localStorage["mezon.theme"] da:
 * "light" | "dark" | "system" (sukut). <html data-theme> har doim aniq qiymatga qo'yiladi — Tailwind `dark:`
 * varianti va theme.css o'zgaruvchilari shundan. Birinchi chizishdan oldin index.html dagi kichik skript qo'yadi
 * (oq/qora "chaqnash" bo'lmasin), keyin shu provayder boshqaradi.
 */
import { MonitorIcon, MoonIcon, SunIcon } from "lucide-react";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Toaster } from "sonner";

import { cn } from "./utils";

export type ThemePref = "light" | "dark" | "system";
type Resolved = "light" | "dark";

const KEY = "mezon.theme";
const META_COLORS: Record<Resolved, string> = { light: "#F7F4EC", dark: "#17181B" };

function readPref(): ThemePref {
  try {
    const value = localStorage.getItem(KEY);
    return value === "light" || value === "dark" ? value : "system";
  } catch {
    return "system";
  }
}

function systemDark(): boolean {
  return typeof matchMedia === "function" && matchMedia("(prefers-color-scheme: dark)").matches;
}

function apply(resolved: Resolved) {
  document.documentElement.dataset.theme = resolved;
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", META_COLORS[resolved]);
}

interface ThemeValue {
  pref: ThemePref;
  resolved: Resolved;
  setPref(pref: ThemePref): void;
}

const ThemeContext = createContext<ThemeValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [pref, setPrefState] = useState<ThemePref>(readPref);
  const [dark, setDark] = useState(systemDark);

  useEffect(() => {
    const media = matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => setDark(media.matches);
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);

  const resolved: Resolved = pref === "system" ? (dark ? "dark" : "light") : pref;
  useEffect(() => apply(resolved), [resolved]);

  const setPref = useCallback((next: ThemePref) => {
    try {
      if (next === "system") localStorage.removeItem(KEY);
      else localStorage.setItem(KEY, next);
    } catch {
      /* xususiy rejim — faqat shu sessiya */
    }
    setPrefState(next);
  }, []);

  const value = useMemo(() => ({ pref, resolved, setPref }), [pref, resolved, setPref]);
  return (
    <ThemeContext.Provider value={value}>
      {children}
      <Toaster theme={resolved} position="top-center" richColors closeButton />
    </ThemeContext.Provider>
  );
}

export function useTheme(): ThemeValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme ThemeProvider ichida");
  return ctx;
}

/** Uch holatli almashtirgich: yorug' / qorong'i / tizim. `compact` — faqat ikonkalar (yon panel). */
export function ThemeSwitch({ className, compact = false }: { className?: string; compact?: boolean }) {
  const { t } = useTranslation();
  const { pref, setPref } = useTheme();
  const options = [
    { value: "light" as const, label: t("Yorugʻ"), icon: SunIcon },
    { value: "dark" as const, label: t("Qorongʻi"), icon: MoonIcon },
    { value: "system" as const, label: t("Tizim"), icon: MonitorIcon },
  ];
  return (
    <div role="radiogroup" aria-label={t("Koʻrinish")} className={cn("grid grid-cols-3 gap-1 rounded-lg bg-subtle p-1", compact && "inline-grid", className)}>
      {options.map(({ value, label, icon: Icon }) => (
        <button
          key={value}
          type="button"
          role="radio"
          aria-checked={pref === value}
          title={label}
          aria-label={label}
          onClick={() => setPref(value)}
          className={cn(
            "flex items-center justify-center gap-1.5 rounded-md px-2 py-1.5 text-xs font-medium text-muted transition-colors hover:text-ink",
            compact && "size-8 px-0",
            pref === value && "bg-surface text-ink shadow-card",
          )}
        >
          <Icon className="size-3.5" aria-hidden />
          {!compact && <span className="truncate">{label}</span>}
        </button>
      ))}
    </div>
  );
}
