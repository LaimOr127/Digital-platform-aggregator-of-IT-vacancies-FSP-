import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ToastProvider } from "../../../ui/Toast";
import { OffersInbox } from "./OffersInbox";

const offer = {
  id: "o1",
  status: "sent",
  company_name: "ООО Демо Софт",
  vacancy_title: "Backend",
  grade: "middle",
  work_format: "remote",
  city: null,
  salary_min: 300000,
  salary_max: 380000,
  message: "Привет",
  decline_reason: null,
  expires_at: "2099-01-01T00:00:00Z",
  responded_at: null,
  created_at: "2026-10-01T00:00:00Z",
};

const json = (body: unknown) => new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  fetchMock = vi.fn(async (url: string) =>
    url.includes("/accept") ? json({ ...offer, status: "accepted" }) : json({ items: [offer], next_cursor: null }),
  );
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => vi.unstubAllGlobals());

describe("OffersInbox", () => {
  it("asks for explicit consent before sharing contacts", async () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <ToastProvider>
          <OffersInbox />
        </ToastProvider>
      </QueryClientProvider>,
    );
    await userEvent.click(await screen.findByRole("button", { name: "Принять" }));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText(/получит ваше имя и контакты/)).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes("/accept"))).toBe(false);
    await userEvent.click(within(dialog).getByRole("button", { name: "Принять и передать контакты" }));
    expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith("/candidate/offers/o1/accept"))).toBe(true);
  });
});
