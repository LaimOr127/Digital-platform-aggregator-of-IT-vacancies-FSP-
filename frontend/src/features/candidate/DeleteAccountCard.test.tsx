import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { bodyOf, json, renderWithApp, serveRoutes } from "../../test/render";
import { DeleteAccountCard } from "./DeleteAccountCard";

const signOut = vi.fn(async () => undefined);
vi.mock("../../auth/AuthProvider", () => ({ useAuth: () => ({ signOut }) }));

const DELETE = "/candidate/account/delete";

async function confirmWith(password: string) {
  await userEvent.click(screen.getByRole("button", { name: "Удалить аккаунт" }));
  const dialog = screen.getByRole("dialog");
  if (password) await userEvent.type(within(dialog).getByLabelText("Пароль для подтверждения"), password);
  await userEvent.click(within(dialog).getByRole("button", { name: "Удалить навсегда" }));
  return dialog;
}

beforeEach(() => signOut.mockClear());
afterEach(() => vi.unstubAllGlobals());

describe("DeleteAccountCard", () => {
  it("requires the password before sending anything", async () => {
    const fetchMock = serveRoutes({});
    renderWithApp(<DeleteAccountCard />);
    const dialog = await confirmWith("");
    expect(within(dialog).getByText("Введите пароль")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("shows a wrong password next to the field and keeps the session", async () => {
    serveRoutes({ [DELETE]: () => json({ error: { code: "wrong_password", message: "неверный пароль" } }, 403) });
    renderWithApp(<DeleteAccountCard />);
    const dialog = await confirmWith("not-my-password");
    expect(await within(dialog).findByText("Неверный пароль")).toBeInTheDocument();
    expect(signOut).not.toHaveBeenCalled();
  });

  it("deletes the account and signs out", async () => {
    const fetchMock = serveRoutes({ [DELETE]: () => json(null, 204) });
    renderWithApp(<DeleteAccountCard />);
    await confirmWith("my-password");
    expect(await screen.findByText("Аккаунт и данные удалены")).toBeInTheDocument();
    expect(bodyOf(fetchMock, DELETE)).toEqual({ password: "my-password" });
    expect(signOut).toHaveBeenCalledOnce();
  });
});
