import { cleanup, fireEvent, render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DatePicker } from "@mezon/web-kit";

afterEach(cleanup);

describe("DatePicker", () => {
  it("bo'sh bo'lganda placeholder matnini ko'rsatadi", () => {
    const view = render(
      <DatePicker
        value=""
        placeholder="Sanani tanlang"
        aria-label="Sana tanlagich"
      />,
    );
    expect(view.getByText("Sanani tanlang")).toBeTruthy();
  });

  it("ISO sanani ('2026-11-19') formatlangan ko'rinishda ('19.11.2026') chiqaradi", () => {
    const view = render(
      <DatePicker
        value="2026-11-19"
        aria-label="Sana tanlagich"
      />,
    );
    expect(view.getByText("19.11.2026")).toBeTruthy();
  });

  it("size='sm' rejimida ixcham o'lchamda bo'ladi", () => {
    const view = render(
      <DatePicker
        value="2026-11-19"
        size="sm"
        aria-label="Sana"
      />,
    );
    const btn = view.getByRole("button", { name: "Sana" });
    expect(btn.className).toContain("h-8");
  });

  it("size='md' rejimida forma inputiga mos to'liq kenglikda (w-full) bo'ladi", () => {
    const view = render(
      <DatePicker
        value="2026-11-19"
        size="md"
        aria-label="Sana"
      />,
    );
    const btn = view.getByRole("button", { name: "Sana" });
    expect(btn.className).toContain("h-11");
    expect(btn.className).toContain("w-full");
  });

  it("tozalash tugmasi bosilganda onChange('') chaqiriladi", () => {
    const onChange = vi.fn();
    const view = render(
      <DatePicker
        value="2026-11-19"
        onChange={onChange}
        aria-label="Sana"
      />,
    );
    const clearBtn = view.getByRole("button", { name: "Tozalash" });
    fireEvent.click(clearBtn);
    expect(onChange).toHaveBeenCalledWith("");
  });

  it("kalendar ochilganda maxsus dizayndagi Oy va Yil selektorlari mavjud bo'ladi", () => {
    const view = render(
      <DatePicker
        value="2026-11-19"
        aria-label="Sana"
      />,
    );
    const triggerBtn = view.getByRole("button", { name: "Sana" });
    fireEvent.click(triggerBtn);

    // Oy tanlash tugmasi
    const monthBtn = view.getByRole("button", { name: "Oy tanlash" });
    expect(monthBtn.textContent).toContain("Noyabr");

    // Yil tanlash tugmasi
    const yearBtn = view.getByRole("button", { name: "Yil tanlash" });
    expect(yearBtn.textContent).toContain("2026");

    // Oy bosilganda maxsus dropdown ochiladi (native select emas)
    fireEvent.click(monthBtn);
    expect(view.getByRole("listbox")).toBeTruthy();
    expect(view.getByRole("option", { name: "Mart" })).toBeTruthy();
  });
});
