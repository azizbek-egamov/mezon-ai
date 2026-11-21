/**
 * Interfeys tillari (TZ §5.4). Matnlar manbasi — backend: `mezon_backend/locale/<til>/LC_MESSAGES/django.po`.
 * Kalit — o'zbek lotin matnning o'zi: `t("Fayl tanlang")`, o'rinbosar `t("{{n}} varaq", { n })`.
 * Yangi matn qo'shish: kodda o'zbek lotin matnni t() ga bering → `manage.py i18n_sync` (frontend ham skanerlanadi) → tarjima →
 * `manage.py i18n_export_json`. Tarjimasi yo'q kalit o'zbek lotinda ko'rinadi.
 */
import i18next, { type i18n as I18n } from "i18next";

import en from "../locales/en.json";
import kaa from "../locales/kaa.json";
import languages from "../locales/languages.json";
import ru from "../locales/ru.json";
import uzCyrl from "../locales/uz-Cyrl.json";
import uzLatn from "../locales/uz-Latn.json";
import uzLatn2026 from "../locales/uz-Latn-2026.json";

export type LanguageCode = "uz-Latn" | "uz-Latn-2026" | "uz-Cyrl" | "ru" | "kaa" | "en";

export interface LanguageInfo {
  code: LanguageCode;
  django_code: string;
  name: string;
}

export const LANGUAGES = languages as LanguageInfo[];
export const DEFAULT_LANGUAGE: LanguageCode = "uz-Latn";

const resources = {
  "uz-Latn": { translation: uzLatn },
  "uz-Latn-2026": { translation: uzLatn2026 },
  "uz-Cyrl": { translation: uzCyrl },
  ru: { translation: ru },
  kaa: { translation: kaa },
  en: { translation: en },
};

/** TZ kodi (uz-Latn) yoki Django kodi (uz-latn) -> TZ kodi; noma'lum — null. */
export function normalizeLanguage(code: string | null | undefined): LanguageCode | null {
  if (!code) return null;
  const found = LANGUAGES.find((l) => l.code === code || l.django_code === code.toLowerCase());
  return found ? found.code : null;
}

/** Brauzer/qurilma tillaridan mosini tanlaydi (uz-Cyrl, ru, en …), aks holda o'zbek lotin. */
export function detectLanguage(preferred: readonly string[] = []): LanguageCode {
  for (const tag of preferred) {
    const exact = normalizeLanguage(tag);
    if (exact) return exact;
    const lower = tag.toLowerCase();
    if (lower.startsWith("uz")) {
      if (lower.includes("2026")) return "uz-Latn-2026";
      return lower.includes("cyrl") ? "uz-Cyrl" : "uz-Latn";
    }
    if (lower.startsWith("ru")) return "ru";
    if (lower.startsWith("kaa")) return "kaa";
    if (lower.startsWith("en")) return "en";
  }
  return DEFAULT_LANGUAGE;
}

export function createI18n(lng: LanguageCode): I18n {
  const instance = i18next.createInstance();
  void instance.init({
    resources,
    lng,
    fallbackLng: false, // tarjima yo'q — kalitning o'zi (o'zbek lotin)
    keySeparator: false,
    nsSeparator: false,
    returnEmptyString: false,
    load: "currentOnly",
    cleanCode: false,
    lowerCaseLng: false,
    interpolation: { escapeValue: false }, // React o'zi ekranlaydi
    initAsync: false,
  });
  return instance;
}
