import { cleanup, fireEvent, render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PhoneInput } from "@mezon/web-kit";

afterEach(cleanup);

describe("PhoneInput", () => {
  it("+998 prefiksini alohida, raqamni formatlangan ko'rinishda chiqaradi", () => {
    const view = render(<PhoneInput aria-label="Telefon" value="+998901234567" onChangePhone={() => undefined} />);
    expect(view.getByText("+998")).toBeTruthy();
    expect((view.getByLabelText("Telefon") as HTMLInputElement).value).toBe("90 123 45 67");
  });

  it("kiritilgan raqamni server uchun normallashtiradi", () => {
    const changed = vi.fn();
    const view = render(<PhoneInput aria-label="Telefon" value="" onChangePhone={changed} />);
    fireEvent.change(view.getByLabelText("Telefon"), { target: { value: "90 123 45 67" } });
    expect(changed).toHaveBeenLastCalledWith("+998901234567", "90 123 45 67");
  });
});
