/**
 * Veb uchun API klienti. Access token faqat xotirada (sahifa yangilansa — yo'qoladi), refresh — HttpOnly cookie da
 * (JS ko'rmaydi, `/api/v1/auth/` yo'li): sahifa ochilganda `restoreSession()` cookie orqali yangi access oladi.
 */
import { ApiError, createApi, errorFromResponse, type Schemas } from "@mezon/api-client";

let accessToken: string | null = null;
let currentLanguage = "uz-latn";
const expiredListeners = new Set<() => void>();

export const tokenStore = {
  get: () => accessToken,
  set(token: string | null) {
    accessToken = token;
  },
  /** Sessiya tugadi (refresh rad etildi) — ilova login sahifasiga o'tadi. */
  onExpired(listener: () => void) {
    expiredListeners.add(listener);
    return () => {
      expiredListeners.delete(listener);
    };
  },
};

/** Server xabarlari tanlangan tilda bo'lsin (kirmagan foydalanuvchi uchun ham): Accept-Language. */
export function setApiLanguage(djangoCode: string) {
  currentLanguage = djangoCode;
}

export async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "Accept-Language": currentLanguage },
    body: JSON.stringify(body),
    credentials: "same-origin",
  });
  if (!response.ok) throw await errorFromResponse(response);
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

let refreshing: Promise<string | null> | null = null;

async function requestRefresh(): Promise<string | null> {
  try {
    accessToken = (await postJson<Schemas["Access"]>("/auth/refresh", {})).access;
  } catch (error) {
    // Faqat server cookie ni rad etsa (4xx) sessiya tugagan. Tarmoq xatosi/5xx (tunnel beqaror) — xato otiladi:
    // yaroqli cookie turgan foydalanuvchi bekorga chiqarib yuborilmasin.
    if (error instanceof ApiError && error.status >= 400 && error.status < 500) accessToken = null;
    else throw error;
  }
  return accessToken;
}

/** Cookie dagi refresh bilan yangi access; cookie yo'q/rad etildi — null; tarmoq/server xatosi — xato otadi.
 * Refresh rotatsiyalanadi (eskisi bekor), shuning uchun bir vaqtda ikki so'rov bo'lmasligi shart: bitta tab ichida —
 * umumiy promise (StrictMode ikki marta ishga tushirgan restoreSession ham), tablar orasida — Web Locks
 * (ikkinchi tab navbat kutadi va brauzer yangilagan cookie bilan boradi). */
function refreshFromCookie(): Promise<string | null> {
  if (!refreshing) {
    const run = async (): Promise<string | null> =>
      typeof navigator !== "undefined" && navigator.locks
        ? await navigator.locks.request("mezon-refresh", () => requestRefresh())
        : requestRefresh();
    refreshing = run().finally(() => {
      refreshing = null;
    });
  }
  return refreshing;
}

export const api = createApi({
  origin: "",
  auth: {
    getAccessToken: () => accessToken,
    async refreshAccessToken() {
      const token = await refreshFromCookie();
      if (!token) expiredListeners.forEach((l) => l());
      return token;
    },
  },
  headers: () => ({ "Accept-Language": currentLanguage }),
});

/** Sahifa ochilganda: refresh cookie bo'lsa — sessiyani tiklaydi. */
export async function restoreSession(): Promise<Schemas["User"] | null> {
  if (!(await refreshFromCookie())) return null;
  return (await (await api.raw("/auth/me")).json()) as Schemas["User"];
}
