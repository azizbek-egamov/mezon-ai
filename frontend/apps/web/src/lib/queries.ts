/** Veb so'rovlari (TanStack Query kalitlari). Xato xabarlari — @mezon/web-kit `notifyError`. */
import { unwrap, type Schemas } from "@mezon/api-client";
import { api } from "@mezon/web-kit";
import { useQuery } from "@tanstack/react-query";

export { notifyError } from "@mezon/web-kit";

export const keys = {
  usage: ["billing", "usage"] as const,
  plans: ["billing", "plans"] as const,
  cases: (page: number) => ["cases", "list", page] as const,
  caseOptions: ["cases", "options"] as const,
  case: (id: string) => ["cases", id] as const,
  report: (id: string) => ["cases", id, "report"] as const,
  confirmation: (id: string) => ["cases", id, "confirmation"] as const,
  templates: ["templates"] as const,
  template: (id: string) => ["templates", id] as const,
};

export function useUsage() {
  return useQuery({
    queryKey: keys.usage,
    queryFn: () => unwrap(api.client.GET("/api/v1/billing/usage")) as Promise<Schemas["Usage"]>,
  });
}
