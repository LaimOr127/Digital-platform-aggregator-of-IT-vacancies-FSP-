import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { FspStatus } from "../../../api/types";
import { ToastProvider } from "../../../ui/Toast";
import { FspLinkCard } from "./FspLinkCard";

const base: FspStatus = {
  linked: false,
  verification_tier: "self_declared",
  demo_mode: true,
  achievements: [],
  categories: [],
};

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => vi.unstubAllGlobals());

function renderCard(status: FspStatus) {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ToastProvider>
        <MemoryRouter>
          <FspLinkCard status={status} />
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  );
}

describe("FspLinkCard", () => {
  it("requests a code, shows server error inline, then confirms", async () => {
    fetchMock.mockResolvedValueOnce(json({ email_masked: "a***@x.ru", expires_in: 600, demo_code: "123456" }));
    renderCard(base);
    await userEvent.click(screen.getByRole("button", { name: "FSP-24001" }));
    await userEvent.click(screen.getByRole("button", { name: "Получить код" }));
    expect(await screen.findByText(/a\*\*\*@x\.ru/)).toBeInTheDocument();
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ athlete_id: "FSP-24001" });

    fetchMock.mockResolvedValueOnce(json({ error: { code: "fsp_verification_failed", message: "неверный код" } }, 400));
    await userEvent.type(screen.getByLabelText("Код из письма"), "000000");
    await userEvent.click(screen.getByRole("button", { name: "Подтвердить" }));
    expect(await screen.findByText("Неверный код")).toBeInTheDocument();

    fetchMock.mockResolvedValueOnce(json({ ...base, linked: true, athlete_id: "FSP-24001" }));
    await userEvent.clear(screen.getByLabelText("Код из письма"));
    await userEvent.click(screen.getByRole("button", { name: "Подставить" }));
    await userEvent.click(screen.getByRole("button", { name: "Подтвердить" }));
    expect(JSON.parse(fetchMock.mock.calls[2][1].body)).toEqual({ code: "123456" });
  });

  it("validates athlete id before calling the API", async () => {
    renderCard(base);
    await userEvent.type(screen.getByLabelText("ID спортсмена в ФСП"), "../x");
    await userEvent.click(screen.getByRole("button", { name: "Получить код" }));
    expect(await screen.findByText(/буквы, цифры и дефис/)).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("resumes a pending request after reload", () => {
    renderCard({ ...base, pending_athlete_id: "FSP-24003" });
    expect(screen.getByText(/FSP-24003/)).toBeInTheDocument();
    expect(screen.getByLabelText("Код из письма")).toBeInTheDocument();
  });

  it("shows linked account details", () => {
    renderCard({ ...base, linked: true, athlete_id: "FSP-24002", rank: "МС", region: "Томск" });
    expect(screen.getByText("Аккаунт ФСП FSP-24002")).toBeInTheDocument();
    expect(screen.getByText("МС")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Заполнить профиль из анкеты ФСП/ })).toHaveAttribute("href", "/app?import=fsp");
  });
});
