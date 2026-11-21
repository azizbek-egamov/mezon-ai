import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CostChart } from "./CostChart";

const days = [
  { date: "2026-10-27", usd: 0.5, cases: 1, chat: 2, pages: 10 },
  { date: "2026-10-28", usd: 1.25, cases: 2, chat: 0, pages: 40 },
  { date: "2026-10-29", usd: 0, cases: 0, chat: 1, pages: 0 },
];

describe("CostChart", () => {
  it("har kunga ustun, jami va ekran o'quvchi uchun jadval", () => {
    const { container } = render(<CostChart days={days} />);
    expect(screen.getAllByRole("row")).toHaveLength(4); // sarlavha + 3 kun (sr-only jadval)
    expect(screen.getByText("Jami: $1.75 · 3 kun")).toBeTruthy();
    expect(screen.getByLabelText("2026-10-28: $1.3")).toBeTruthy();
    // eng baland ustun — shkalaning 2 dan 62.5% i; nol kun — ustunsiz
    const bars = [...container.querySelectorAll<HTMLDivElement>(".bg-primary")].map((b) => b.style.height);
    expect(bars).toEqual(["25%", "62.5%", "0%"]);
  });
});
