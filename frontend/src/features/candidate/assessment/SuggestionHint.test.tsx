import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { json, renderWithApp, serveRoutes } from "../../../test/render";
import { SuggestionHint } from "./SuggestionHint";

afterEach(() => vi.unstubAllGlobals());

describe("SuggestionHint", () => {
  it("shows the model's suggestion and applies it to the survey", async () => {
    serveRoutes({
      "/candidate/assessment/suggestion": () =>
        json({ specialization: "data", grade: "junior", reason: "Python и SQL", source: "ai", provider: "Модель" }),
    });
    const onApply = vi.fn();
    renderWithApp(<SuggestionHint onApply={onApply} />);
    await userEvent.click(screen.getByRole("button", { name: "Подсказать" }));
    expect(await screen.findByText(/Данные и машинное обучение · Junior/)).toBeInTheDocument();
    expect(screen.getByText(/модель: Модель/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Применить" }));
    expect(onApply).toHaveBeenCalledWith("data", "junior");
  });
});
