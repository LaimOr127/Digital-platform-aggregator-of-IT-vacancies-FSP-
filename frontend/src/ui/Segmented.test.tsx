import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";
import { Segmented } from "./Segmented";

function Harness() {
  const [value, setValue] = useState<"a" | "b" | "c">("a");
  return (
    <Segmented
      label="Фильтр"
      value={value}
      onChange={setValue}
      options={[
        { value: "a", label: "Первый" },
        { value: "b", label: "Второй" },
        { value: "c", label: "Третий" },
      ]}
    />
  );
}

describe("Segmented", () => {
  it("is a single tab stop and moves selection with arrows", async () => {
    render(<Harness />);
    await userEvent.tab();
    expect(screen.getByRole("radio", { name: "Первый" })).toHaveFocus();
    await userEvent.keyboard("{ArrowRight}");
    expect(screen.getByRole("radio", { name: "Второй" })).toHaveFocus();
    expect(screen.getByRole("radio", { name: "Второй" })).toHaveAttribute("aria-checked", "true");
    await userEvent.keyboard("{ArrowLeft}{ArrowLeft}");
    expect(screen.getByRole("radio", { name: "Третий" })).toHaveAttribute("aria-checked", "true");
    await userEvent.keyboard("{Home}");
    expect(screen.getByRole("radio", { name: "Первый" })).toHaveAttribute("aria-checked", "true");
    expect(screen.getAllByRole("radio").filter((r) => r.tabIndex === 0)).toHaveLength(1);
  });

  it("marks nothing when the value is not among the options", () => {
    render(<Segmented label="Оценка" value="" options={[{ value: "1", label: "1" }, { value: "2", label: "2" }]} onChange={() => undefined} />);
    expect(screen.getAllByRole("radio").filter((r) => r.getAttribute("aria-checked") === "true")).toHaveLength(0);
    expect(screen.getByRole("radio", { name: "1" })).toHaveAttribute("tabindex", "0");
  });
});
