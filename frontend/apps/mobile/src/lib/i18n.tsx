/** Interfeys tili (TZ §5.4): profil tili > tanlangan til (secure-store) > qurilma tili (expo-localization). */
import { createI18n, detectLanguage, LANGUAGES, normalizeLanguage, type LanguageCode } from "@mezon/i18n";
import { useQueryClient } from "@tanstack/react-query";
import { getLocales } from "expo-localization";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { I18nextProvider } from "react-i18next";

import { api, setApiLanguage } from "./api";
import { useAuth } from "./auth";
import { storage } from "./storage";

const KEY = "mezon.lang";
const device = detectLanguage(getLocales().map((l) => l.languageTag));
const i18n = createI18n(device);

function apply(code: LanguageCode) {
  void i18n.changeLanguage(code);
  setApiLanguage(LANGUAGES.find((l) => l.code === code)?.django_code ?? "uz-latn");
}
apply(device);

interface LanguageValue {
  language: LanguageCode;
  setLanguage(code: LanguageCode): void;
}

const LanguageContext = createContext<LanguageValue | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const { user, reloadUser, status } = useAuth();
  const queryClient = useQueryClient();
  const [language, setLang] = useState<LanguageCode>(device);

  useEffect(() => {
    void storage.get(KEY).then((saved) => {
      const code = normalizeLanguage(saved);
      if (code) {
        apply(code);
        setLang(code);
      }
    });
  }, []);

  useEffect(() => {
    const profile = normalizeLanguage(user?.language_tz);
    if (profile && profile !== i18n.language) {
      apply(profile);
      setLang(profile);
      void storage.set(KEY, profile);
      void queryClient.invalidateQueries();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.language_tz]);

  const setLanguage = useCallback((code: LanguageCode) => {
    apply(code);
    setLang(code);
    void storage.set(KEY, code);
    if (status === "authenticated") {
      void api.raw("/auth/language", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ language: code }) })
        .then(() => Promise.all([reloadUser(), queryClient.invalidateQueries()]))
        .catch(() => undefined);
    }
  }, [status, reloadUser, queryClient]);

  const value = useMemo(() => ({ language, setLanguage }), [language, setLanguage]);
  return (
    <LanguageContext.Provider value={value}>
      <I18nextProvider i18n={i18n}>{children}</I18nextProvider>
    </LanguageContext.Provider>
  );
}

export function useLanguage(): LanguageValue {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error("useLanguage LanguageProvider ichida");
  return ctx;
}
