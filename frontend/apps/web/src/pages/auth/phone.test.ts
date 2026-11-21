import { describe, expect, it } from "vitest";

import { extractUzPhoneDigits, formatUzPhone, formatUzPhoneDisplay } from "@mezon/web-kit";

describe("Oʻzbekiston telefon formati", () => {
  it("turli kiritish shakllaridan 9 ta mahalliy raqamni ajratadi", () => {
    expect(extractUzPhoneDigits("+998 (90) 123-45-67")).toBe("901234567");
    expect(extractUzPhoneDigits("998901234567")).toBe("901234567");
    expect(extractUzPhoneDigits("8901234567")).toBe("901234567");
  });

  it("yozish davomida XX XXX XX XX formatini qoʻllaydi", () => {
    expect(formatUzPhoneDisplay("90123")).toBe("90 123");
    expect(formatUzPhoneDisplay("901234567")).toBe("90 123 45 67");
  });

  it("serverga yuboriladigan qiymatni +998 bilan normallashtiradi", () => {
    expect(formatUzPhone("90 123 45 67")).toEqual({
      digits: "901234567",
      display: "90 123 45 67",
      normalized: "+998901234567",
    });
  });
});
