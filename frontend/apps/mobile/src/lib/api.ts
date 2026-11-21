/**
 * Mobil API klienti. Access — xotirada; refresh — expo-secure-store da (javob tanasida keladi, cookie emas).
 * Manzil: EXPO_PUBLIC_API_URL (.env; USB `adb reverse` bilan telefondagi localhost = PC).
 * Global `fetch` — Expo SDK 58 da expo/fetch (oqimni qo'llaydi) — SSE chat shu bilan ishlaydi.
 */
import { ApiError, createApi, errorFromResponse, type Schemas } from "@mezon/api-client";

import { storage } from "./storage";

export const API_ORIGIN = (process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8010").replace(/\/$/, "");
const REFRESH_KEY = "mezon.refresh";

let accessToken: string | null = null;
let language = "uz-latn";
const expiredListeners = new Set<() => void>();

export function setApiLanguage(djangoCode: string) {
  language = djangoCode;
}

export function onSessionExpired(listener: () => void) {
  expiredListeners.add(listener);
  return () => {
    expiredListeners.delete(listener);
  };
}

export async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_ORIGIN}/api/v1${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "Accept-Language": language },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw await errorFromResponse(response);
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

export async function saveTokens(data: { access: string; refresh?: string }) {
  accessToken = data.access;
  if (data.refresh) await storage.set(REFRESH_KEY, data.refresh);
}

export async function clearTokens() {
  accessToken = null;
  await storage.remove(REFRESH_KEY);
}

/** Saqlangan refresh bilan yangi access (rotatsiya: yangi refresh ham saqlanadi); sessiya yo'q/rad etildi — null.
 * Server javob bermasa (kabel ulanmagan, server o'chiq) — xato otiladi va sessiya SAQLANADI: aks holda har safar
 * oflayn ochilganda foydalanuvchi qayta kirishga majbur bo'lardi. */
export function refreshSession(): Promise<string | null> {
  // Rotatsiya: refresh bir marta ishlatiladi. Ro'yxat polling, fayl yuklash va ilova ochilishi bir vaqtda
  // yangilasa, ikkinchisi 401 olib YANGI tokenni ham o'chirib yuborardi — shuning uchun hammasi bitta promise.
  inflight ??= doRefresh().finally(() => {
    inflight = null;
  });
  return inflight;
}

let inflight: Promise<string | null> | null = null;

async function doRefresh(): Promise<string | null> {
  const refresh = await storage.get(REFRESH_KEY);
  if (!refresh) return null;
  let data: Schemas["Access"];
  try {
    data = await postJson<Schemas["Access"]>("/auth/refresh", { refresh });
  } catch (error) {
    if (error instanceof ApiError && error.status < 500) {
      // Boshqa yo'l refreshni allaqachon yangilagan bo'lsa (saqlangan qiymat o'zgargan) — sessiya tirik, o'chirmaymiz
      if ((await storage.get(REFRESH_KEY)) !== refresh) return accessToken;
      await clearTokens(); // token muddati o'tgan yoki bekor qilingan
      return null;
    }
    throw error;
  }
  await saveTokens(data);
  return accessToken;
}

export const api = createApi({
  origin: API_ORIGIN,
  auth: {
    getAccessToken: () => accessToken,
    async refreshAccessToken() {
      const token = await refreshSession();
      if (!token) expiredListeners.forEach((l) => l());
      return token;
    },
  },
  headers: () => ({ "Accept-Language": language }),
});

/** Request obyektisiz to'g'ridan-to'g'ri so'rov (multipart yuklash): token + 401 da bir marta yangilash. */
export async function authedFetch(path: string, init: RequestInit): Promise<Response> {
  const go = (token: string | null) => fetch(`${API_ORIGIN}/api/v1${path}`, {
    ...init,
    headers: { ...(init.headers as Record<string, string>), "Accept-Language": language, ...(token ? { Authorization: `Bearer ${token}` } : {}) },
  });
  let response = await go(accessToken);
  if (response.status === 401) {
    const token = await refreshSession();
    if (!token) expiredListeners.forEach((l) => l());
    else response = await go(token);
  }
  if (!response.ok) throw await errorFromResponse(response);
  return response;
}

export async function logoutRemote() {
  const refresh = await storage.get(REFRESH_KEY);
  if (refresh) await postJson("/auth/logout", { refresh }).catch(() => undefined);
  await clearTokens();
}
