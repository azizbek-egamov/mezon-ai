/**
 * Server-Sent Events o'quvchi: `fetch` javobining ReadableStream ini hodisalarga ajratadi.
 * Brauzerda oddiy `fetch`, Expo da `expo/fetch` (oqimni qo'llaydi) bilan ishlaydi.
 */

export interface SseEvent {
  event: string;
  data: string;
}

/** Bufer -> to'liq hodisalar va qoldiq (oxirgi to'liq bo'lmagan blok). */
export function splitEvents(buffer: string): { events: SseEvent[]; rest: string } {
  const events: SseEvent[] = [];
  const normalized = buffer.replace(/\r\n/g, "\n");
  const blocks = normalized.split("\n\n");
  const rest = blocks.pop() ?? "";
  for (const block of blocks) {
    let event = "message";
    const data: string[] = [];
    for (const line of block.split("\n")) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""));
    }
    if (data.length) events.push({ event, data: data.join("\n") });
  }
  return { events, rest };
}

/** Javob oqimini oxirigacha o'qib, har bir hodisani `onEvent` ga beradi (data JSON sifatida). */
/** Oqimli UTF-8 dekoder: TextDecoder bo'lmasa (ba'zi JS dvijoklarda), bo'laklar orasida uzilgan ko'p baytli
 * belgilarni keyingi bo'lakka qoldiradi. */
export function createUtf8Decoder(): { decode(bytes: Uint8Array, opts?: { stream?: boolean }): string } {
  if (typeof TextDecoder !== "undefined") return new TextDecoder();
  let pending: number[] = [];
  return {
    decode(bytes, opts) {
      const all = pending.concat(Array.from(bytes));
      let end = all.length;
      if (opts?.stream) {
        // oxiridagi to'liq bo'lmagan belgi (lead bayt + yetishmagan davomi) keyingi bo'lakka
        for (let back = 1; back <= Math.min(3, all.length); back++) {
          const b = all[all.length - back];
          if ((b & 0xc0) === 0x80) continue;
          const need = b >= 0xf0 ? 4 : b >= 0xe0 ? 3 : b >= 0xc0 ? 2 : 1;
          if (need > back) end = all.length - back;
          break;
        }
      }
      pending = all.slice(end);
      let out = "";
      for (let i = 0; i < end; ) {
        const b = all[i];
        const n = b >= 0xf0 ? 4 : b >= 0xe0 ? 3 : b >= 0xc0 ? 2 : 1;
        let cp = n === 1 ? b : b & (0xff >> (n + 1));
        for (let k = 1; k < n; k++) cp = (cp << 6) | (all[i + k] & 0x3f);
        out += String.fromCodePoint(cp);
        i += n;
      }
      return out;
    },
  };
}

export async function readEventStream(
  response: Response,
  onEvent: (name: string, data: unknown) => void,
): Promise<void> {
  if (!response.body) throw new Error("Javobda oqim yoʻq");
  const reader = response.body.getReader();
  const decoder = createUtf8Decoder();
  let buffer = "";
  // Bitta buzuq `data:` butun oqimni uzmasin: o'qib bo'lmaydigan hodisa o'tkazib yuboriladi
  const dispatch = (e: { event: string; data: string }) => {
    let data: unknown;
    try {
      data = JSON.parse(e.data);
    } catch {
      return;
    }
    onEvent(e.event, data);
  };
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const { events, rest } = splitEvents(buffer);
      buffer = rest;
      events.forEach(dispatch);
    }
    splitEvents(buffer + "\n\n").events.forEach(dispatch);
  } finally {
    reader.cancel().catch(() => undefined); // xato/abort bo'lganda ham tarmoq ulanishi yopilsin
  }
}
