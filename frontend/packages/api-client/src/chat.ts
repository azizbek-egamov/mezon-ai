/** Huquqiy savol (POST /chat/ask) — SSE hodisalari tiplari va oqimni o'qish. */
import type { MezonApi, Schemas } from "./client";
import { readEventStream } from "./sse";

export interface Aspect {
  topic: string;
  queries: string[];
}

export interface AsOf {
  state?: "same" | "changed" | "unknown";
  date?: string;
  note?: string;
}

export interface ChatSource {
  key: string;
  topic: string;
  doc_title: string;
  label: string;
  lex_url: string;
  edition: string;
  exact: boolean;
  as_of?: AsOf;
}

export interface VerificationIssue {
  severity: "error" | "warning" | "info";
  kind: string;
  detail: string;
}

export interface Verification {
  ok: boolean;
  citations: string[];
  quotes_checked: number;
  issues: VerificationIssue[];
}

export interface ChatDone {
  timings: { search_s: number; first_token_s: number; answer_s: number };
  usage: { input_tokens?: number; output_tokens?: number; cost_usd?: number };
}

export interface ChatHandlers {
  aspects?(list: Aspect[]): void;
  sources?(list: ChatSource[]): void;
  delta?(text: string): void;
  verification?(v: Verification): void;
  done?(d: ChatDone): void;
  error?(message: string): void;
  /** Server LLM oqimi uzilgani uchun javobni boshidan qayta yozmoqda — shu vaqtgacha yig'ilgan matn tashlanadi. */
  reset?(): void;
  /** Oqim `done` yoki `error` hodisasisiz tugadi (tunnel/server uzildi) — javob to'liq va tekshirilgan emas. */
  incomplete?(): void;
}

export type AskRequest = Schemas["AskRequest"];

/** Savol yuboradi va hodisalarni handlers ga uzatadi. 400/429 — ApiError (oqim boshlanmaydi). */
export async function ask(api: MezonApi, body: AskRequest, handlers: ChatHandlers, signal?: AbortSignal): Promise<void> {
  const response = await api.raw("/chat/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(body),
    signal,
  });
  let finished = false;
  await readEventStream(response, (name, data) => {
    if (name === "done" || name === "error") finished = true;
    switch (name) {
      case "aspects":
        return handlers.aspects?.(data as Aspect[]);
      case "sources":
        return handlers.sources?.(data as ChatSource[]);
      case "delta":
        return handlers.delta?.((data as { text: string }).text);
      case "reset":
        return handlers.reset?.();
      case "verification":
        return handlers.verification?.(data as Verification);
      case "done":
        return handlers.done?.(data as ChatDone);
      case "error":
        return handlers.error?.((data as { message: string }).message);
    }
  });
  // Tunnel/server oqim o'rtasida uzilsa readEventStream jim tugaydi — "to'liq javob" bo'lib ko'rinmasin
  if (!finished && !signal?.aborted) handlers.incomplete?.();
}
