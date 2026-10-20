import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";
import { CookieBanner } from "./CookieBanner";

describe("CookieBanner", () => {
  beforeEach(() => localStorage.clear());

  it("remembers the choice and does not show again", async () => {
    const { unmount } = render(<CookieBanner />);
    await userEvent.click(screen.getByRole("button", { name: "Только обязательные" }));
    expect(screen.queryByRole("region", { name: "Cookie" })).toBeNull();
    expect(localStorage.getItem("itmatch.cookie-consent")).toBe("necessary");
    unmount();
    render(<CookieBanner />);
    expect(screen.queryByRole("region", { name: "Cookie" })).toBeNull();
  });

  it("offers all three choices until one is made", () => {
    render(<CookieBanner />);
    for (const name of ["Принять все", "Только обязательные", "Отказаться"]) {
      expect(screen.getByRole("button", { name })).toBeInTheDocument();
    }
  });
});
