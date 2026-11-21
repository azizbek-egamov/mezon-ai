import { cleanup, fireEvent, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { PasswordInput } from "@mezon/web-kit";

afterEach(cleanup);

describe("PasswordInput", () => {
  it("ko'z tugmasi bosib turilgandagina parolni ko'rsatadi", () => {
    const view = render(<PasswordInput aria-label="Parol" revealLabel="Ko'rsatish" value="maxfiy" readOnly />);
    const input = view.getByLabelText("Parol") as HTMLInputElement;
    const reveal = view.getByRole("button", { name: "Ko'rsatish" });

    expect(input.type).toBe("password");
    fireEvent.pointerDown(reveal);
    expect(input.type).toBe("text");
    fireEvent.pointerUp(reveal);
    expect(input.type).toBe("password");
  });

  it("tugma hududidan chiqilganda va klaviatura qo'yib yuborilganda parolni yashiradi", () => {
    const view = render(<PasswordInput aria-label="Parol" revealLabel="Ko'rsatish" value="maxfiy" readOnly />);
    const input = view.getByLabelText("Parol") as HTMLInputElement;
    const reveal = view.getByRole("button", { name: "Ko'rsatish" });

    fireEvent.pointerDown(reveal);
    fireEvent.pointerLeave(reveal);
    expect(input.type).toBe("password");
    fireEvent.keyDown(reveal, { key: " " });
    expect(input.type).toBe("text");
    fireEvent.keyUp(reveal, { key: " " });
    expect(input.type).toBe("password");
  });
});
