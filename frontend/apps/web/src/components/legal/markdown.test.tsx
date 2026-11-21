import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Markdown } from "./markdown";

const ctx = {
  sources: { M1: { key: "M1", doc_title: "Jinoyat kodeksi", label: "168-modda", lex_url: "https://lex.uz/docs/-111453" } },
  verified: true,
  cited: new Set(["M1"]),
};

describe("Markdown", () => {
  it("manba havolalari, iqtibos va qalin matn", () => {
    render(<Markdown text={"**Javob:** «aldash» [M1] va [M9]"} ctx={ctx} />);
    expect(screen.getByText("Javob:").tagName).toBe("STRONG");
    expect(screen.getByText("«aldash»")).toBeTruthy();
    expect(screen.getByRole("link", { name: "M1" }).getAttribute("href")).toBe("https://lex.uz/docs/-111453");
    expect(screen.getByText("M9").tagName).toBe("SPAN"); // berilmagan manba — havola emas
  });

  it("HTML matn sifatida qoladi (XSS yo'q)", () => {
    const { container } = render(<Markdown text={'<img src=x onerror="alert(1)">'} ctx={ctx} />);
    expect(container.querySelector("img")).toBeNull();
  });

  it("jadval va ro'yxat", () => {
    const { container } = render(<Markdown text={"| A | B |\n|---|---|\n| 1 | 2 |\n\n- bir\n- ikki"} ctx={ctx} />);
    expect(container.querySelectorAll("tr")).toHaveLength(2);
    expect(container.querySelectorAll("li")).toHaveLength(2);
  });
});
