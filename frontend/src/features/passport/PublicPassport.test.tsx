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
  holder: { name: null, source: null },
  demo: false,
  expires_at: "2027-10-01T10:00:00+00:00",
  title: "Backend",
  grade: "middle",
  skills: ["Python"],
  verification_tier: "verified_fsp",
  fsp: { athlete_id: null, rank: "КМС", achievements: [{ discipline: "Продуктовое программирование", summary: "2 место — Чемпионат" }] },
  categories: ["Продуктовое программирование: призёры"],
};

function passport(overrides: object) {
  return {
    id: "p1",
    issued_at: "2026-10-01T10:00:00Z",
    revoked_at: null,
    status: "valid",
    payload,
    signature: "sig",
    key_id: "k1",
    valid: true,
    public_key: "pk",
    ...overrides,
  };
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
    expect(await screen.findByText("Подпись подлинная, паспорт действует")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Имя скрыто владельцем" })).toBeInTheDocument();
    expect(screen.getByText(/не удостоверяет личность/)).toBeInTheDocument();
    expect(screen.getByText(/заявлено кандидатом/)).toBeInTheDocument();
    expect(screen.getByText("Подтверждено ФСП")).toBeInTheDocument();
    expect(screen.getByText(/2 место — Чемпионат/)).toBeInTheDocument();
  });

  it("shows only the revocation for a revoked passport", async () => {
    vi.stubGlobal(
      "fetch",
      respond(passport({ valid: false, status: "revoked", revoked_at: "2026-10-02T10:00:00Z", payload: null, signature: null })),
    );
    renderPage();
    expect(await screen.findByText("Паспорт отозван")).toBeInTheDocument();
    expect(screen.queryByText(/Чемпионат/)).not.toBeInTheDocument();
  });

  it.each([
    ["bad_signature", "Подпись не совпадает"],
    ["expired", "Срок действия истёк"],
    ["unknown_key", "Подписан неактуальным ключом"],
  ])("explains status %s", async (status, text) => {
    vi.stubGlobal("fetch", respond(passport({ valid: false, status })));
    renderPage();
    expect(await screen.findByText(text)).toBeInTheDocument();
  });

  it("marks a verified name and the demo stand", async () => {
    vi.stubGlobal(
      "fetch",
      respond(passport({ payload: { ...payload, demo: true, holder: { name: "Анна Смирнова", source: "fsp" } } })),
    );
    renderPage();
    expect(await screen.findByText("Имя подтверждено ФСП")).toBeInTheDocument();
    expect(screen.getByText(/демо-стенде/)).toBeInTheDocument();
  });

  it("reports unknown passport", async () => {
    vi.stubGlobal("fetch", respond({ error: { code: "not_found", message: "нет" } }, 404));
    renderPage();
    expect(await screen.findByText(/Паспорт не найден/)).toBeInTheDocument();
  });
});
