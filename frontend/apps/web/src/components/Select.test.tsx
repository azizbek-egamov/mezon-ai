import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { CustomSelect } from "@mezon/web-kit";

afterEach(cleanup);

describe("CustomSelect", () => {
  it("options massividan tanlangan qiymatni to'g'ri ko'rsatadi", () => {
    const view = render(
      <CustomSelect
        value="uz"
        aria-label="Til"
        options={[
          { value: "uz", label: "O'zbekcha" },
          { value: "ru", label: "Русский" },
        ]}
      />,
    );
    expect(view.getByText("O'zbekcha")).toBeTruthy();
  });

  it("option bolalarini ham qabul qilib qiymatni chiqaradi", () => {
    const view = render(
      <CustomSelect value="medium" aria-label="Effort">
        <option value="low">Tez</option>
        <option value="medium">O'rta</option>
        <option value="high">Chuqur</option>
      </CustomSelect>,
    );
    expect(view.getByText("O'rta")).toBeTruthy();
  });

  it("size='sm' bo'lganda w-auto qabul qilib to'liq kenglikka cho'zilib ketmaydi", () => {
    const view = render(
      <CustomSelect
        value="uz"
        size="sm"
        aria-label="Til"
        options={[{ value: "uz", label: "O'zbekcha" }]}
      />,
    );
    const trigger = view.getByRole("combobox");
    expect(trigger.className).toContain("w-auto");
    expect(trigger.className).not.toContain("w-full");
  });

  it("size='md' yoki forma selectida sukut bo'yicha w-full bo'ladi", () => {
    const view = render(
      <CustomSelect
        value="1"
        size="md"
        aria-label="Forma"
        options={[{ value: "1", label: "Variant" }]}
      />,
    );
    const trigger = view.getByRole("combobox");
    expect(trigger.className).toContain("w-full");
  });
});

