/** Admin API (`/api/v1/admin/*`) so'rovlari va javob tiplari. */
import { unwrap, type Schemas } from "@mezon/api-client";
import { api } from "@mezon/web-kit";
import { useQuery } from "@tanstack/react-query";

export type AdminUser = Schemas["AdminUser"];
export type Plan = Schemas["AdminPlan"];
export type Payment = Schemas["Payment"];
export type Subscription = Schemas["Subscription"];
export type SyncRun = Schemas["SyncRun"];
export type AdminTemplate = Schemas["AdminTemplate"];
export type AuditEvent = Schemas["AuditEvent"];
/** Ish metama'lumoti (nomi va mazmuni yo'q — advokatlik siri) */
export interface AdminCase {
  id: string;
  created_at: string;
  owner: string | null;
  owner_phone: string;
  category: string;
  status: string;
  pages: number;
  cost_usd: number;
  quota_refunded: boolean;
}

export interface CostDay {
  date: string;
  usd: number;
  cases: number;
  chat: number;
  pages: number;
}

export interface Dashboard {
  users: { total: number; lawyers: number; clients: number; staff: number; active_7d: number; new_today: number; flagged: number };
  subscriptions: { plan__code: string; plan__name: string; count: number }[];
  cases: { today: number; month: number; active: number; failed_today: number };
  cost: { today: number; month: number; by_day: CostDay[] };
  chat_today: number;
  payments_pending: number;
  fraud_signals: number;
  last_sync: SyncRun | null;
  recent_audit: AuditEvent[];
}

export interface UserDetail {
  user: AdminUser;
  usage: { label: string; used: number; limit: number }[];
  max_pages: number;
  cost_total_usd: number;
  subscriptions: Subscription[];
  payments: Payment[];
  cases: AdminCase[];
  audit: AuditEvent[];
}

export interface Costs {
  by_day: CostDay[];
  top_users: { user: string; phone_number: string; full_name: string; usd: number; cases: number; chat: number }[];
  expensive_cases: AdminCase[];
}

export interface SharedIpGroup {
  ip: string;
  count: number;
  flagged: number;
  accounts: { id: string; phone_number: string; full_name: string; role: string; date_joined: string; is_fraud_flagged: boolean; is_active: boolean }[];
}

export interface AntiFraud {
  shared_ips: SharedIpGroup[];
  flagged: AdminUser[];
}

export const adminKeys = {
  me: ["admin", "me"] as const,
  dashboard: ["admin", "dashboard"] as const,
  users: (params: Record<string, string | number>) => ["admin", "users", params] as const,
  user: (id: string) => ["admin", "user", id] as const,
  plans: ["admin", "plans"] as const,
  payments: (params: Record<string, string | number>) => ["admin", "payments", params] as const,
  costs: (days: number) => ["admin", "costs", days] as const,
  antifraud: (min: number) => ["admin", "antifraud", min] as const,
  sync: ["admin", "sync"] as const,
  templates: (pending: boolean) => ["admin", "templates", pending] as const,
  template: (id: string) => ["admin", "template", id] as const,
  audit: (page: number) => ["admin", "audit", page] as const,
};

/** Tiplanmagan JSON (OpenAPI da `object`) */
export async function getJson<T>(path: string): Promise<T> {
  return (await (await api.raw(path)).json()) as T;
}

export async function sendJson<T>(path: string, method: "POST" | "PATCH", body?: unknown): Promise<T> {
  const response = await api.raw(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  return (response.status === 204 ? undefined : await response.json()) as T;
}

export function useStaff(enabled = true) {
  return useQuery({
    queryKey: adminKeys.me,
    queryFn: () => unwrap(api.client.GET("/api/v1/admin/me")),
    enabled,
    retry: false,
    staleTime: Infinity,
  });
}

export const usd = (v: number | null | undefined, digits = 2) => `$${(v ?? 0).toFixed(digits)}`;
