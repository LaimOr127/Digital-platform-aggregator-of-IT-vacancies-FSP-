import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ToastProvider } from "../../ui/Toast";
import { UsersPage } from "./UsersPage";

const me = { id: "me", email: "mod@example.org", role: "admin", is_superadmin: false, company_id: null };
vi.mock("../../auth/AuthProvider", () => ({ useAuth: () => ({ status: "authenticated", user: me }) }));

const user = (id: string, role: string, extra = {}) => ({
  id,
  email: `${id}@example.org`,
  role,
  is_active: true,
  is_superadmin: false,
  totp_enabled: role === "admin",
  created_at: "2026-10-01T00:00:00Z",
  ...extra,
});
const users = [user("me", "admin"), user("other-admin", "admin"), user("anna", "candidate"), user("hr", "employer", { is_active: false })];

const json = (body: unknown) => new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  fetchMock = vi.fn(async (url: string) =>
    url.includes("/moderation") ? json({ ...users[2], is_active: false }) : json({ items: users, next_cursor: null }),
  );
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => vi.unstubAllGlobals());

const row = (email: string) => screen.getByRole("heading", { name: email }).closest("article") as HTMLElement;

describe("UsersPage", () => {
  it("hides actions a moderator is not allowed to take", async () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <ToastProvider>
          <UsersPage />
        </ToastProvider>
      </QueryClientProvider>,
    );
    await screen.findByText("anna@example.org");
    expect(within(row("me@example.org")).queryByRole("button")).not.toBeInTheDocument();
    expect(within(row("other-admin@example.org")).queryByRole("button")).not.toBeInTheDocument();
    expect(within(row("hr@example.org")).getByRole("button", { name: "Разблокировать" })).toBeInTheDocument();

    await userEvent.click(within(row("anna@example.org")).getByRole("button", { name: "Заблокировать" }));
    const dialog = screen.getByRole("dialog");
    await userEvent.type(within(dialog).getByLabelText(/Причина/), "фейковый профиль");
    await userEvent.click(within(dialog).getByRole("button", { name: "Заблокировать" }));
    const [, init] = fetchMock.mock.calls.find(([url]) => String(url).endsWith("/admin/users/anna/moderation"))!;
    expect(JSON.parse(init.body)).toEqual({ action: "block", reason: "фейковый профиль" });
  });
});
