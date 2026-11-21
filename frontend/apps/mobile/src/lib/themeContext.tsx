/**
 * Yorug' / qorong'i rejim: tanlov secure-store da ("mezon.theme": light | dark | system), sukut — telefon sozlamasi.
 * Rejim almashganda palitra va StyleSheet qayta quriladi, `version` o'zgaradi — _layout navigatorni shu kalit bilan
 * qayta chizadi (auth va til holati saqlanadi).
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useColorScheme } from "react-native";

import { rebuildStyles } from "@/components/ui";

import { storage } from "./storage";
import { setPalette, type Mode } from "./theme";

export type ThemePref = Mode | "system";
const KEY = "mezon.theme";

interface ThemeValue {
  pref: ThemePref;
  mode: Mode;
  setPref(pref: ThemePref): void;
}

const ThemeContext = createContext<ThemeValue | null>(null);

export function ThemeProvider({ children }: { children: (mode: Mode) => ReactNode }) {
  const system = useColorScheme() === "dark" ? "dark" : "light";
  const [pref, setPrefState] = useState<ThemePref>("system");

  useEffect(() => {
    void storage.get(KEY).then((saved) => {
      if (saved === "light" || saved === "dark") setPrefState(saved);
    });
  }, []);

  const mode: Mode = pref === "system" ? system : pref;
  // Palitra render paytida (bolalardan oldin) yangilanadi — birinchi chizishdayoq to'g'ri ranglar
  setPalette(mode);
  rebuildStyles();

  const setPref = useCallback((next: ThemePref) => {
    setPrefState(next);
    void (next === "system" ? storage.remove(KEY) : storage.set(KEY, next));
  }, []);

  const value = useMemo(() => ({ pref, mode, setPref }), [pref, mode, setPref]);
  return <ThemeContext.Provider value={value}>{children(mode)}</ThemeContext.Provider>;
}

export function useTheme(): ThemeValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme ThemeProvider ichida");
  return ctx;
}
