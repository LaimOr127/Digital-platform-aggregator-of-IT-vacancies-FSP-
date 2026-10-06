import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { SkillPicker } from "./SkillPicker";

const skills = [
  { slug: "python", name: "Python" },
  { slug: "postgresql", name: "PostgreSQL" },
  { slug: "go", name: "Go" },
];

function Harness({ onSubmit, max = 5 }: { onSubmit: () => void; max?: number }) {
  const [value, setValue] = useState<string[]>([]);
  return (
    <form onSubmit={(e) => { e.preventDefault(); onSubmit(); }}>
      <SkillPicker skills={skills} value={value} onChange={setValue} max={max} />
    </form>
  );
}

describe("SkillPicker", () => {
  it("adds by click, clears search and removes by chip", async () => {
    render(<Harness onSubmit={vi.fn()} />);
    const search = screen.getByLabelText("Найти навык");
    await userEvent.type(search, "pos");
    await userEvent.click(screen.getByRole("button", { name: "PostgreSQL" }));
    expect(search).toHaveValue("");
    await userEvent.click(screen.getByRole("button", { name: "Убрать PostgreSQL" }));
    expect(screen.getByText("Навыки не выбраны")).toBeInTheDocument();
  });

  it("Enter adds the first match and does not submit the form", async () => {
    const onSubmit = vi.fn();
    render(<Harness onSubmit={onSubmit} />);
    await userEvent.type(screen.getByLabelText("Найти навык"), "py{Enter}");
    expect(screen.getByRole("button", { name: "Убрать Python" })).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("respects the maximum", async () => {
    render(<Harness onSubmit={vi.fn()} max={1} />);
    await userEvent.click(screen.getByRole("button", { name: "Go" }));
    expect(screen.getByRole("button", { name: "Python" })).toBeDisabled();
  });

  it("adds an own skill that is not in the dictionary", async () => {
    function OwnHarness() {
      const [value, setValue] = useState<string[]>([]);
      const [own, setOwn] = useState<string[]>([]);
      return <SkillPicker skills={skills} value={value} onChange={setValue} max={5} custom={own} onCustomChange={setOwn} />;
    }
    render(<OwnHarness />);
    const search = screen.getByLabelText("Найти навык");
    await userEvent.type(search, "Camunda");
    await userEvent.click(screen.getByRole("button", { name: "Добавить «Camunda» как свой навык" }));
    expect(screen.getByRole("button", { name: "Убрать свой навык Camunda" })).toBeInTheDocument();
    // название из справочника своим не добавляется
    await userEvent.type(search, "go");
    expect(screen.queryByRole("button", { name: /как свой навык/ })).not.toBeInTheDocument();
  });
});
