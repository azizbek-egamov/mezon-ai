import { describe, expect, it, vi } from "vitest";

import { ask } from "./chat";
import { ApiError, createAuthFetch, toApiError } from "./client";
import { readEventStream, splitEvents } from "./sse";

describe("splitEvents", () => {
  it("to'liq hodisalarni ajratadi, qoldiqni saqlaydi", () => {
    const { events, rest } = splitEvents('event: delta\ndata: {"text":"a"}\n\nevent: done\ndata: {"x"');
    expect(events).toEqual([{ event: "delta", data: '{"text":"a"}' }]);
    expect(rest).toBe('event: done\ndata: {"x"');
  });

  it("CRLF va ko'p qatorli data", () => {
    const { events } = splitEvents("event: e\r\ndata: 1\r\ndata: 2\r\n\r\n");
    expect(events).toEqual([{ event: "e", data: "1\n2" }]);
  });
});

describe("readEventStream", () => {
  it("bo'laklarga bo'lingan oqimni o'qiydi", async () => {
    const chunks = ['event: delta\ndata: {"te', 'xt":"Salom"}\n\nevent: done\n', 'data: {"ok":true}\n\n'];
    const body = new ReadableStream({
      start(c) {
        chunks.forEach((s) => c.enqueue(new TextEncoder().encode(s)));
        c.close();
      },
    });
    const seen: [string, unknown][] = [];
    await readEventStream(new Response(body), (n, d) => seen.push([n, d]));
    expect(seen).toEqual([["delta", { text: "Salom" }], ["done", { ok: true }]]);
  });
});

function sseResponse(text: string) {
  return new Response(
    new ReadableStream({
      start(c) {
        c.enqueue(new TextEncoder().encode(text));
        c.close();
      },
    }),
  );
}

describe("readEventStream: buzuq hodisa", () => {
  it("o'qib bo'lmaydigan data oqimni uzmaydi", async () => {
    const seen: string[] = [];
    await readEventStream(sseResponse('event: a\ndata: {buzuq\n\nevent: b\ndata: {"ok":1}\n\n'), (n) => seen.push(n));
    expect(seen).toEqual(["b"]);
  });
});

describe("ask", () => {
  const fakeApi = (text: string) => ({ raw: async () => sseResponse(text) }) as unknown as Parameters<typeof ask>[0];
  const body = { question: "q" } as Parameters<typeof ask>[1];

  it("done siz tugagan oqim incomplete deb xabar qilinadi", async () => {
    const incomplete = vi.fn();
    const done = vi.fn();
    await ask(fakeApi('event: delta\ndata: {"text":"Qis"}\n\n'), body, { incomplete, done });
    expect(incomplete).toHaveBeenCalledOnce();
    expect(done).not.toHaveBeenCalled();
  });

  it("done kelsa incomplete chaqirilmaydi", async () => {
    const incomplete = vi.fn();
    await ask(fakeApi('event: delta\ndata: {"text":"a"}\n\nevent: done\ndata: {}\n\n'), body, { incomplete });
    expect(incomplete).not.toHaveBeenCalled();
  });
});

describe("toApiError", () => {
  it("detail/code va maydon xatolari", () => {
    const quota = toApiError(429, { detail: "Limit", code: "quota_daily" });
    expect(quota.isQuota).toBe(true);
    const form = toApiError(400, { phone_number: ["Notoʻgʻri"], non_field_errors: ["Umumiy"] });
    expect(form.message).toBe("Umumiy");
    expect(form.fields.phone_number).toEqual(["Notoʻgʻri"]);
  });
});

describe("createAuthFetch", () => {
  it("401 da bir marta yangilaydi va so'rovni takrorlaydi (tana bilan)", async () => {
    let token = "eski";
    const refresh = vi.fn(async () => (token = "yangi"));
    const calls: [string | null, string][] = [];
    const base = vi.fn(async (req: Request) => {
      calls.push([req.headers.get("Authorization"), await req.text()]);
      return new Response(null, { status: req.headers.get("Authorization") === "Bearer yangi" ? 200 : 401 });
    });
    const f = createAuthFetch({ getAccessToken: () => token, refreshAccessToken: refresh }, base as unknown as typeof fetch);
    const [a, b] = await Promise.all([
      f(new Request("http://x/api/v1/cases/", { method: "POST", body: "tana" })),
      f(new Request("http://x/api/v1/billing/usage")),
    ]);
    expect([a.status, b.status]).toEqual([200, 200]);
    expect(refresh).toHaveBeenCalledTimes(1); // parallel so'rovlar uchun bitta yangilash
    expect(calls).toContainEqual(["Bearer yangi", "tana"]);
  });

  it("auth yo'llariga token qo'shilmaydi", async () => {
    const base = vi.fn(async (req: Request) => new Response(String(req.headers.get("Authorization"))));
    const f = createAuthFetch({ getAccessToken: () => "t", refreshAccessToken: async () => null }, base as unknown as typeof fetch);
    expect(await (await f(new Request("http://x/api/v1/auth/login", { method: "POST" }))).text()).toBe("null");
  });

  it("ApiError — Error", () => {
    expect(new ApiError(400, "x")).toBeInstanceOf(Error);
  });
});

describe("createUtf8Decoder (TextDecoder siz zaxira)", () => {
  it("bo'laklar orasida uzilgan kirill va emoji belgilarini to'g'ri yig'adi", async () => {
    const original = globalThis.TextDecoder;
    // @ts-expect-error: zaxira yo'lni sinash uchun vaqtincha olib tashlaymiz
    delete globalThis.TextDecoder;
    try {
      const { createUtf8Decoder } = await import("./sse");
      const bytes = new TextEncoder().encode("Ўзбек ʻ 🙂 ok");
      const d = createUtf8Decoder();
      let out = "";
      for (let i = 0; i < bytes.length; i += 3) out += d.decode(bytes.slice(i, i + 3), { stream: true });
      expect(out).toBe("Ўзбек ʻ 🙂 ok");
    } finally {
      globalThis.TextDecoder = original;
    }
  });
});
