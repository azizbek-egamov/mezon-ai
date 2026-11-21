/**
 * Interfeys tili (TZ §5.4): kirgan foydalanuvchining profil tili > shu brauzerda tanlangan til > brauzer tili.
 * Tanlov serverga ham yoziladi (`POST /auth/language`: profil va `django_language` cookie).
 */
import { createI18n, detectLanguage, LANGUAGES, normalizeLanguage, type LanguageCode } from "@mezon/i18n";
import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { I18nextProvider } from "react-i18next";

import { api, setApiLanguage } from "./api";
import { useAuth } from "./auth";

const STORAGE_KEY = "mezon.lang";
const initial: LanguageCode =
  normalizeLanguage(localStorage.getItem(STORAGE_KEY)) ?? detectLanguage(navigator.languages ?? []);
const i18n = createI18n(initial);

function apply(code: LanguageCode) {
  void i18n.changeLanguage(code);
  document.documentElement.lang = code;
  setApiLanguage(LANGUAGES.find((l) => l.code === code)?.django_code ?? "uz-latn");
}
apply(initial);

export interface LanguageContextValue {
  language: LanguageCode;
  setLanguage(code: LanguageCode): void;
}

export const LanguageContext = createContext<LanguageContextValue | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const { user, reloadUser } = useAuth();
  const queryClient = useQueryClient();
  const [language, setLang] = useState<LanguageCode>(initial);

  // Kirganda profil tili ustun
  useEffect(() => {
    const profile = normalizeLanguage(user?.language_tz);
    if (profile && profile !== i18n.language) {
      apply(profile);
      setLang(profile);
      localStorage.setItem(STORAGE_KEY, profile);
      // kirish javobi brauzer tilida kelgan bo'lishi mumkin — server matnlarini (rol nomi va h.k.) profil tilida qayta o'qiymiz
      void reloadUser();
      void queryClient.invalidateQueries();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- faqat profil tili o'zgarganda
  }, [user?.language_tz]);

  const setLanguage = useCallback((code: LanguageCode) => {
    apply(code);
    setLang(code);
    localStorage.setItem(STORAGE_KEY, code);
    void api
      .raw("/auth/language", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ language: code }),
      })
      // server matnlari (rol, holat, limit yorliqlari) endi yangi tilda — qayta o'qiladi
      .then(() => Promise.all([reloadUser(), queryClient.invalidateQueries()]))
      .catch(() => undefined);
  }, [reloadUser, queryClient]);

  const value = useMemo(() => ({ language, setLanguage }), [language, setLanguage]);
  return (
    <LanguageContext.Provider value={value}>
      <I18nextProvider i18n={i18n}>{children}</I18nextProvider>
    </LanguageContext.Provider>
  );
}

export function useLanguage(): LanguageContextValue {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error("useLanguage LanguageProvider ichida ishlatilsin");
  return ctx;
}
