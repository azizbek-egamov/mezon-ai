import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** ?next= faqat ilova ichidagi yo'l bo'lsin (ochiq redirect yo'q) */
export function safeNext(value: string | null | undefined, fallback = "/"): string {
  return value && value.startsWith("/") && !value.startsWith("//") ? value : fallback;
}

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Blob ni fayl sifatida saqlash (eksport, shablon). */
export function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Sana va vaqt interfeys tilida (Intl; uz-Cyrl/kaa bo'lmasa — brauzer zaxirasi). */
export function formatDateTime(iso: string | null | undefined, lang: string): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat(lang, { dateStyle: "short", timeStyle: "short" }).format(new Date(iso));
}

/** Sana: 28.11.2026 (hujjatlardagi kabi; "28 нояб. 2026 г." gap ichida noqulay) */
export function formatDate(iso: string | null | undefined, _lang?: string): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return [d.getDate(), d.getMonth() + 1].map((n) => String(n).padStart(2, "0")).join(".") + `.${d.getFullYear()}`;
}

/** 1250000 -> "1 250 000" (bo'shliq — oddiy probel, rus formatidagi NBSP emas) */
export function formatMoney(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "";
  return Math.round(Number(value))
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, " ");
}
