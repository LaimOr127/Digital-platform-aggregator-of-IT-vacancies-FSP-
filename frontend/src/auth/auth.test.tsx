import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import { session } from "../api/session";
import { AuthProvider, useAuth } from "./AuthProvider";
import { RequireRole } from "./RequireRole";

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

const me = { id: "u1", email: "anna@example.org", role: "candidate", is_superadmin: false, company_id: null };

function Where() {
  const location = useLocation();
  return <p data-testid="where">{location.pathname + location.search}</p>;
}

function SignOut() {
  const auth = useAuth();
  return (
    <button type="button" onClick={() => auth.signOut()}>
      {auth.status}
    </button>
  );
}

function renderAt(path: string) {
  const client = new QueryClient();
  return render(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/app" element={<RequireRole role="candidate"><SignOut /></RequireRole>} />
            <Route path="/company" element={<RequireRole role="employer"><p>company</p></RequireRole>} />
            <Route path="*" element={<Where />} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  );
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
    expect(await screen.findByTestId("where")).toHaveTextContent("/login?next=%2Fapp");
    expect(fetchMock).not.toHaveBeenCalled(); // нет csrf-cookie — refresh не пробуем
  });

  it("restores the session from refresh cookie and renders the portal", async () => {
    document.cookie = "csrf_token=c; path=/";
    fetchMock.mockResolvedValueOnce(json({ access_token: "t", token_type: "bearer", expires_in: 900 }));
    fetchMock.mockResolvedValueOnce(json(me));
    renderAt("/app");
    expect(await screen.findByRole("button", { name: "authenticated" })).toBeInTheDocument();
  });

  it("redirects a user with another role to own portal", async () => {
    session.set("t");
    fetchMock.mockResolvedValueOnce(json(me));
    renderAt("/company");
    // оказался в своём кабинете /app (там отрисован SignOut со статусом)
    expect(await screen.findByRole("button", { name: "authenticated" })).toBeInTheDocument();
    expect(screen.queryByText("company")).not.toBeInTheDocument();
  });

  it("becomes anonymous when /me fails", async () => {
    session.set("t");
    fetchMock.mockResolvedValue(json({ error: { code: "unauthorized", message: "x" } }, 401));
    renderAt("/app");
    expect(await screen.findByTestId("where")).toHaveTextContent("/login");
  });

  it("signs out: calls logout and returns to login", async () => {
    session.set("t");
    fetchMock.mockResolvedValueOnce(json(me)).mockResolvedValueOnce(new Response(null, { status: 204 }));
    renderAt("/app");
    await userEvent.click(await screen.findByRole("button", { name: "authenticated" }));
    await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent("/login"));
    expect(fetchMock.mock.calls[1][0]).toBe("/api/v1/auth/logout");
    expect(session.get()).toBeNull();
  });
});
