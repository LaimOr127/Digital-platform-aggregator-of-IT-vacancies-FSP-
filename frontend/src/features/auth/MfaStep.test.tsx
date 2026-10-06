import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router";
import { session } from "../../api/session";
import { AuthProvider } from "../../auth/AuthProvider";
import AuthPage from "./AuthPage";

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
const admin = { id: "a1", email: "admin@example.org", role: "admin", is_superadmin: true, company_id: null };
const SECRET = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP";

type Routes = Record<string, () => Response>;
let fetchMock: ReturnType<typeof vi.fn>;
const calls = (path: string) => fetchMock.mock.calls.filter(([url]) => String(url).endsWith(path));

function serve(routes: Routes) {
  fetchMock = vi.fn(async (url: string) => {
    const path = Object.keys(routes).find((p) => String(url).endsWith(p));
    return path ? routes[path]() : json({ error: { code: "not_found", message: "нет" } }, 404);
  });
  vi.stubGlobal("fetch", fetchMock);
}

function renderLogin() {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <AuthProvider>
        <MemoryRouter initialEntries={["/login"]}>
          <Routes>
            <Route path="/login" element={<AuthPage mode="login" />} />
            <Route path="/admin" element={<p>кабинет администратора</p>} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

async function submitPassword() {
  await userEvent.type(await screen.findByLabelText("Email"), "admin@example.org");
  await userEvent.type(screen.getByLabelText("Пароль"), "Str0ng-pass-42");
  await userEvent.click(screen.getByRole("button", { name: "Войти" }));
}

beforeEach(() => session.clear());
afterEach(() => vi.unstubAllGlobals());

describe("admin two-factor login", () => {
  it("enrolls the authenticator on first login, then signs in with a code", async () => {
    serve({
      "/auth/login": () => json({ mfa_required: true, mfa_token: "mfa-1", enrolled: false }),
      "/auth/2fa/setup": () => json({ secret: SECRET, otpauth_uri: `otpauth://totp/IT%20Match:admin?secret=${SECRET}` }),
      "/auth/2fa/verify": () => json({ access_token: "t", token_type: "bearer", expires_in: 900 }),
      "/auth/me": () => json(admin),
    });
    renderLogin();
    await submitPassword();
    await userEvent.type(await screen.findByLabelText("Код подключения"), "enroll-code-1");
    await userEvent.click(screen.getByRole("button", { name: "Продолжить" }));
    // ключ показан группами по 4 символа для ручного ввода
    expect(await screen.findByText(/JBSW Y3DP EHPK/)).toBeInTheDocument();
    expect(session.get()).toBeNull(); // пароль сам по себе сессию не даёт
    await userEvent.type(screen.getByLabelText("Код из приложения"), "123456");
    await userEvent.click(screen.getByRole("button", { name: "Войти" }));
    expect(await screen.findByText("кабинет администратора")).toBeInTheDocument();
    expect(JSON.parse(calls("/auth/2fa/verify")[0][1].body)).toEqual({ mfa_token: "mfa-1", code: "123456" });
    expect(calls("/auth/2fa/setup")).toHaveLength(1);
    expect(JSON.parse(calls("/auth/2fa/setup")[0][1].body)).toEqual({ mfa_token: "mfa-1", enrollment_code: "enroll-code-1" });
  });

  it("explains a wrong enrollment code and stays on the step", async () => {
    serve({
      "/auth/login": () => json({ mfa_required: true, mfa_token: "mfa-5", enrolled: false }),
      "/auth/2fa/setup": () =>
        json({ error: { code: "unauthorized", message: "неверный или просроченный код подключения" } }, 401),
    });
    renderLogin();
    await submitPassword();
    await userEvent.type(await screen.findByLabelText("Код подключения"), "short");
    await userEvent.click(screen.getByRole("button", { name: "Продолжить" }));
    expect(await screen.findByText(/не короче 8 символов/)).toBeInTheDocument();
    expect(calls("/auth/2fa/setup")).toHaveLength(0);
    await userEvent.type(screen.getByLabelText("Код подключения"), "-wrong-code");
    await userEvent.click(screen.getByRole("button", { name: "Продолжить" }));
    expect(await screen.findByText(/неверный или просроченный код подключения/i)).toBeInTheDocument();
    expect(screen.queryByLabelText("Код из приложения")).not.toBeInTheDocument();
  });

  it("skips setup for an enrolled admin and validates the code format", async () => {
    serve({ "/auth/login": () => json({ mfa_required: true, mfa_token: "mfa-2", enrolled: true }) });
    renderLogin();
    await submitPassword();
    await userEvent.type(await screen.findByLabelText("Код из приложения"), "12a");
    await userEvent.click(screen.getByRole("button", { name: "Войти" }));
    expect(await screen.findByText("Код из 6 цифр")).toBeInTheDocument();
    expect(calls("/auth/2fa/setup")).toHaveLength(0);
    expect(calls("/auth/2fa/verify")).toHaveLength(0);
  });

  it("offers to start over when the login step expired", async () => {
    serve({
      "/auth/login": () => json({ mfa_required: true, mfa_token: "mfa-3", enrolled: true }),
      "/auth/2fa/verify": () => json({ error: { code: "mfa_expired", message: "сессия входа истекла — войдите заново" } }, 401),
    });
    renderLogin();
    await submitPassword();
    await userEvent.type(await screen.findByLabelText("Код из приложения"), "654321");
    await userEvent.click(screen.getByRole("button", { name: "Войти" }));
    await userEvent.click(await screen.findByRole("button", { name: "Войти заново" }));
    expect(await screen.findByLabelText("Пароль")).toBeInTheDocument();
  });

  it("keeps the code step for a wrong code without the restart offer", async () => {
    serve({
      "/auth/login": () => json({ mfa_required: true, mfa_token: "mfa-4", enrolled: true }),
      "/auth/2fa/verify": () => json({ error: { code: "unauthorized", message: "неверный или уже использованный код" } }, 401),
    });
    renderLogin();
    await submitPassword();
    const input = await screen.findByLabelText("Код из приложения");
    await userEvent.type(input, "000000");
    await userEvent.click(screen.getByRole("button", { name: "Войти" }));
    expect(await screen.findByText(/неверный или уже использованный код/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Войти заново" })).not.toBeInTheDocument();
    await waitFor(() => expect(input).toHaveValue(""));
  });
});
