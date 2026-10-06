import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ReasonDialog } from "./ReasonDialog";

describe("ReasonDialog", () => {
  it("requires a meaningful reason and passes it trimmed", async () => {
    const onConfirm = vi.fn();
    render(
      <ReasonDialog open title="Заблокировать?" confirmLabel="Заблокировать" pending={false} onConfirm={onConfirm} onClose={vi.fn()}>
        текст
      </ReasonDialog>,
    );
    const confirm = screen.getByRole("button", { name: "Заблокировать" });
    await userEvent.type(screen.getByLabelText(/Причина/), "  спам ");
    expect(confirm).toBeDisabled();
    await userEvent.type(screen.getByLabelText(/Причина/), "мер");
    await userEvent.click(confirm);
    expect(onConfirm).toHaveBeenCalledWith("спам мер");
  });
});
