import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router";
import PublicPassport from "./PublicPassport";

vi.mock("../../ui/QrCode", () => ({ QrCode: () => null }));

const payload = {
  version: 1,
  passport_id: "p1",
  issuer: "IT Match · ФСП",
  issued_at: "2026-10-01T10:00:00+00:00",
  holder: { name: null },
  title: "Backend",
  grade: "middle",
  skills: ["Python"],
  verification_tier: "verified_fsp",
  fsp: { athlete_id: null, rank: "КМС", achievements: [{ discipline: "Продуктовое программирование", summary: "2 место — Чемпионат" }] },
  categories: ["Продуктовое программирование: призёры"],
};

function passport(overrides: object) {
  return { id: "p1", issued_at: "2026-10-01T10:00:00Z", revoked_at: null, payload, signature: "sig", key_id: "k1", valid: true, public_key: "pk", ...overrides };
}

function renderPage() {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter initialEntries={["/passport/p1"]}>
        <Routes>
          <Route path="/passport/:id" element={<PublicPassport />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const respond = (body: unknown, status = 200) =>
  vi.fn(async () => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }));

beforeEach(() => vi.stubGlobal("fetch", respond(passport({}))));
afterEach(() => vi.unstubAllGlobals());

describe("PublicPassport", () => {
  it("shows a valid anonymous passport with FSP data", async () => {
    renderPage();
    expect(await screen.findByText("Подлинность подтверждена")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Имя скрыто владельцем" })).toBeInTheDocument();
    expect(screen.getByText("Подтверждено ФСП")).toBeInTheDocument();
    expect(screen.getByText(/2 место — Чемпионат/)).toBeInTheDocument();
  });

  it("warns about a revoked passport", async () => {
    vi.stubGlobal("fetch", respond(passport({ valid: false, revoked_at: "2026-10-02T10:00:00Z" })));
    renderPage();
    expect(await screen.findByText("Паспорт отозван")).toBeInTheDocument();
  });

  it("warns about a broken signature", async () => {
    vi.stubGlobal("fetch", respond(passport({ valid: false })));
    renderPage();
    expect(await screen.findByText("Подпись не совпадает")).toBeInTheDocument();
  });

  it("reports unknown passport", async () => {
    vi.stubGlobal("fetch", respond({ error: { code: "not_found", message: "нет" } }, 404));
    renderPage();
    expect(await screen.findByText(/Паспорт не найден/)).toBeInTheDocument();
  });
});
