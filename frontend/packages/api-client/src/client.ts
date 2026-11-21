/**
 * API v1 klienti. Tiplar `schema.d.ts` da (openapi.yaml dan generatsiya: `npm run api:generate`).
 *
 * Token: access har so'rovga `Authorization: Bearer` qo'shiladi; 401 kelsa — bir marta yangilanadi
 * (`refreshAccessToken`, parallel so'rovlar uchun bitta) va so'rov takrorlanadi. Refresh qayerda saqlanishi
 * ilovaga bog'liq: veb — HttpOnly cookie, mobil — secure store.
 */
import createClient from "openapi-fetch";

import type { components, paths } from "./schema";

export type Schemas = components["schemas"];

/** Server xatosi: {"detail", "code"} yoki validatsiya {maydon: [xabar]}. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly fields: Record<string, string[]>;

  constructor(status: number, message: string, code = "error", fields: Record<string, string[]> = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.fields = fields;
  }

  /** Tarif limiti — mijoz tariflar sahifasiga yo'naltiradi. */
  get isQuota(): boolean {
    return this.status === 429 && this.code.startsWith("quota_");
  }
}

export function toApiError(status: number, body: unknown): ApiError {
  if (body && typeof body === "object") {
    const obj = body as Record<string, unknown>;
    if (typeof obj.detail === "string") return new ApiError(status, obj.detail, String(obj.code ?? "error"));
    const fields: Record<string, string[]> = {};
    for (const [key, value] of Object.entries(obj)) {
      fields[key] = Array.isArray(value) ? value.map(String) : [String(value)];
    }
    const first = fields.non_field_errors?.[0] ?? Object.values(fields)[0]?.[0] ?? `HTTP ${status}`;
    return new ApiError(status, first, "invalid", fields);
  }
  return new ApiError(status, typeof body === "string" && body ? body : `HTTP ${status}`);
}

export async function errorFromResponse(response: Response): Promise<ApiError> {
  const text = await response.text();
  try {
    return toApiError(response.status, JSON.parse(text));
  } catch {
    return toApiError(response.status, text);
  }
}

export interface AuthHooks {
  getAccessToken(): string | null;
  /** Yangi access token; sessiya tugagan bo'lsa — null. */
  refreshAccessToken(): Promise<string | null>;
}

const NO_AUTH_PATHS = ["/auth/login", "/auth/register", "/auth/refresh", "/auth/logout"];

export type FetchFn = (input: Request) => Promise<Response>;

export function createAuthFetch(hooks: AuthHooks, baseFetch: typeof fetch = globalThis.fetch.bind(globalThis)): FetchFn {
  let refreshing: Promise<string | null> | null = null;
  const refreshOnce = () => {
    refreshing ??= hooks.refreshAccessToken().finally(() => {
      refreshing = null;
    });
    return refreshing;
  };
  const withToken = (request: Request, token: string | null) => {
    const req = request.clone();
    if (token) req.headers.set("Authorization", `Bearer ${token}`);
    return req;
  };
  return async (request: Request) => {
    if (NO_AUTH_PATHS.some((p) => new URL(request.url).pathname.endsWith(p))) return baseFetch(request);
    const backup = request.clone(); // tana bir marta o'qiladi — takrorlash uchun nusxa
    const sent = hooks.getAccessToken();
    const response = await baseFetch(withToken(request, sent));
    if (response.status !== 401) return response;
    // Shu orada boshqa so'rov tokenni yangilagan bo'lsa — qayta yangilamasdan yangisini ishlatamiz
    const current = hooks.getAccessToken();
    const token = current && current !== sent ? current : await refreshOnce();
    return token ? baseFetch(withToken(backup, token)) : response;
  };
}

export const API_PREFIX = "/api/v1";

export interface ApiOptions {
  /** Server manzili: "" (veb, Vite proxy orqali shu origin) yoki "http://localhost:8010" (mobil, adb reverse). */
  origin: string;
  auth: AuthHooks;
  fetch?: typeof fetch;
  /** Har so'rovga qo'shiladigan sarlavhalar (masalan, Accept-Language). */
  headers?: () => Record<string, string>;
}

export function createApi({ origin, auth, fetch: baseFetch, headers }: ApiOptions) {
  const baseUrl = origin + API_PREFIX;
  const authFetch = createAuthFetch(auth, baseFetch);
  const fetchWithHeaders: FetchFn = (request) => {
    for (const [k, v] of Object.entries(headers?.() ?? {})) request.headers.set(k, v);
    return authFetch(request);
  };
  // OpenAPI yo'llari to'liq ("/api/v1/cases/") — tiplangan klientga faqat origin beriladi
  const client = createClient<paths>({ baseUrl: origin, fetch: fetchWithHeaders });

  /** Tiplanmagan so'rov (multipart, fayl, SSE), yo'l API_PREFIX siz: raw("/cases/"). Xato bo'lsa — ApiError. */
  async function raw(path: string, init: RequestInit = {}): Promise<Response> {
    const response = await fetchWithHeaders(new Request(baseUrl + path, init));
    if (!response.ok) throw await errorFromResponse(response);
    return response;
  }

  /** Faylni yuklab olish: {blob, filename}. */
  async function download(path: string, init: RequestInit = {}): Promise<{ blob: Blob; filename: string }> {
    const response = await raw(path, init);
    const disposition = response.headers.get("Content-Disposition") ?? "";
    const utf8 = /filename\*=UTF-8''([^;]+)/i.exec(disposition);
    const plain = /filename="?([^";]+)"?/i.exec(disposition);
    const filename = utf8 ? decodeURIComponent(utf8[1]) : plain ? plain[1] : "mezon";
    return { blob: await response.blob(), filename };
  }

  return { client, raw, download, fetch: fetchWithHeaders, baseUrl };
}

export type MezonApi = ReturnType<typeof createApi>;

/** openapi-fetch natijasi -> ma'lumot yoki ApiError. */
export async function unwrap<T>(promise: Promise<{ data?: T; error?: unknown; response: Response }>): Promise<T> {
  const { data, error, response } = await promise;
  if (error !== undefined || !response.ok) throw toApiError(response.status, error);
  return data as T;
}
