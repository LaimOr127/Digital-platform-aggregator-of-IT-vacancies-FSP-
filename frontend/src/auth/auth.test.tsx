import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import { session } from "../api/session";
import AuthPage from "../features/auth/AuthPage";
import { AuthProvider, useAuth } from "./AuthProvider";
import { RequireRole } from "./RequireRole";

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
const tokens = (t: string) => json({ access_token: t, token_type: "bearer", expires_in: 900 });

const anna = { id: "u1", email: "anna@example.org", role: "candidate", is_superadmin: false, company_id: null };
const boris = { ...anna, id: "u2", email: "boris@example.org" };

function Where() {
  const location = useLocation();
  return <p data-testid="where">{location.pathname + location.search}</p>;
}

/** Кабинет-заглушка: показывает статус и кэшированные данные «профиля». */
function Cabinet() {
  const auth = useAuth();
  const profile = useQuery({ queryKey: ["profile"], queryFn: async () => `профиль ${auth.user?.email}`, staleTime: Infinity });
  return (
    <div>
      <p data-testid="profile">{profile.data}</p>
      <button type="button" onClick={() => auth.signOut().catch(() => undefined)}>
        {auth.status}
      </button>
      <button type="button" onClick={() => auth.signIn({ access_token: "b", token_type: "bearer", expires_in: 900 })}>
        войти как другой
      </button>
    </div>
  );
}

function renderAt(path: string) {
  const client = new QueryClient();
  render(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/app/*" element={<RequireRole role="candidate"><Cabinet /></RequireRole>} />
            <Route path="/company" element={<RequireRole role="employer"><p>company</p></RequireRole>} />
            <Route path="/login" element={<AuthPage mode="login" />} />
            <Route path="*" element={<Where />} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  );
  return client;
}

let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  session.clear();
  fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
  document.cookie = "csrf_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
});

describe("RequireRole + AuthProvider", () => {
  it("sends guests to login with next parameter", async () => {
    renderAt("/app");
    expect(await screen.findByRole("heading", { name: "Вход" })).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled(); // нет csrf-cookie — refresh не пробуем
  });

  it("restores the session from refresh cookie and renders the portal", async () => {
    document.cookie = "csrf_token=c; path=/";
    fetchMock.mockResolvedValueOnce(tokens("t")).mockResolvedValueOnce(json(anna));
    renderAt("/app");
    expect(await screen.findByRole("button", { name: "authenticated" })).toBeInTheDocument();
  });

  it("redirects a user with another role to own portal", async () => {
    session.set("t");
    fetchMock.mockResolvedValueOnce(json(anna));
    renderAt("/company");
    expect(await screen.findByRole("button", { name: "authenticated" })).toBeInTheDocument();
    expect(screen.queryByText("company")).not.toBeInTheDocument();
  });

  it("logs in on /login and returns to the page from ?next=", async () => {
    fetchMock.mockResolvedValueOnce(tokens("t")).mockResolvedValueOnce(json(anna));
    renderAt("/login?next=%2Fapp%2Fpassport");
    await userEvent.type(await screen.findByLabelText("Email"), "anna@example.org");
    await userEvent.type(screen.getByLabelText("Пароль"), "Str0ng-pass-42");
    await userEvent.click(screen.getByRole("button", { name: "Войти" }));
    expect(await screen.findByRole("button", { name: "authenticated" })).toBeInTheDocument();
  });

  it("drops cached data of the previous user when another user signs in", async () => {
    session.set("a");
    fetchMock.mockResolvedValueOnce(json(anna));
    const client = renderAt("/app");
    await waitFor(() => expect(screen.getByTestId("profile")).toHaveTextContent("профиль anna@example.org"));
    fetchMock.mockResolvedValueOnce(json(boris));
    await userEvent.click(screen.getByRole("button", { name: "войти как другой" }));
    await waitFor(() => expect(screen.getByTestId("profile")).toHaveTextContent("профиль boris@example.org"));
    expect(client.getQueryData(["profile"])).toBe("профиль boris@example.org");
  });

  it("clears cache when the session is lost", async () => {
    session.set("t");
    fetchMock.mockResolvedValueOnce(json(anna));
    const client = renderAt("/app");
    await screen.findByTestId("profile");
    session.clear();
    await waitFor(() => expect(client.getQueryData(["profile"])).toBeUndefined());
  });

  it("becomes anonymous when /me fails", async () => {
    session.set("t");
    fetchMock.mockResolvedValue(json({ error: { code: "unauthorized", message: "x" } }, 401));
    renderAt("/app");
    expect(await screen.findByRole("heading", { name: "Вход" })).toBeInTheDocument();
  });

  it("signs out only after the server confirmed it", async () => {
    document.cookie = "csrf_token=c; path=/";
    session.set("t");
    fetchMock.mockResolvedValueOnce(json(anna)).mockResolvedValueOnce(json({ error: { code: "x", message: "x" } }, 500));
    renderAt("/app");
    await userEvent.click(await screen.findByRole("button", { name: "authenticated" }));
    expect(session.get()).toBe("t"); // сервер не подтвердил — сессия не сброшена
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));
    await userEvent.click(screen.getByRole("button", { name: "authenticated" }));
    await waitFor(() => expect(session.get()).toBeNull());
    expect(fetchMock.mock.calls[2][0]).toBe("/api/v1/auth/logout");
  });
});
