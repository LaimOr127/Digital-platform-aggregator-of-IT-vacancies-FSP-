import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router";
import { session } from "../../api/session";
import { AuthProvider } from "../../auth/AuthProvider";
import AuthPage from "./AuthPage";
import ForgotPasswordPage from "./ForgotPasswordPage";
import ResetPasswordPage from "./ResetPasswordPage";
import VerifyEmailPage from "./VerifyEmailPage";

const TOKEN = "t".repeat(43);
const json = (body: unknown, status = 200) =>
  new Response(status === 204 ? null : JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
const accepted = () => json({ detail: "ok" }, 202);
const error = (code: string, message: string, status = 400) => json({ error: { code, message } }, status);

let fetchMock: ReturnType<typeof vi.fn>;
const bodyOf = (path: string) =>
  JSON.parse(fetchMock.mock.calls.find(([url]) => String(url).endsWith(path))?.[1].body ?? "null");

function serve(routes: Record<string, () => Response>) {
  fetchMock = vi.fn(async (url: string) => {
    const path = Object.keys(routes).find((p) => String(url).endsWith(p));
    return path ? routes[path]() : error("not_found", "нет", 404);
  });
  vi.stubGlobal("fetch", fetchMock);
}

function renderAt(element: ReactElement, hash = "") {
  window.history.replaceState(null, "", `/page${hash}`);
  render(
    <QueryClientProvider client={new QueryClient()}>
      <AuthProvider>
        <MemoryRouter>{element}</MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => session.clear());
afterEach(() => vi.unstubAllGlobals());

describe("registration", () => {
  it("shows the check-email screen and limits resending", async () => {
    serve({ "/auth/register/candidate": accepted, "/auth/verify-email/resend": accepted });
    renderAt(<AuthPage mode="register" />);
    await userEvent.type(await screen.findByLabelText("Имя и фамилия"), "Анна Смирнова");
    await userEvent.type(screen.getByLabelText("Email"), "anna@example.org");
    await userEvent.type(screen.getByLabelText("Пароль"), "Str0ng-pass-42");
    // без согласия на обработку данных аккаунт не создаётся
    await userEvent.click(screen.getByRole("button", { name: "Создать аккаунт" }));
    expect(await screen.findByText("Нужно согласие на обработку персональных данных")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("checkbox", { name: /Согласен на обработку/ }));
    await userEvent.click(screen.getByRole("button", { name: "Создать аккаунт" }));
    expect(await screen.findByText("Проверьте почту")).toBeInTheDocument();
    expect(bodyOf("/auth/register/candidate").consent).toBe(true);
    expect(screen.getByText("anna@example.org")).toBeInTheDocument();
    expect(session.get()).toBeNull(); // до подтверждения почты сессии нет
    await userEvent.click(screen.getByRole("button", { name: "Отправить письмо ещё раз" }));
    // успех — по кнопке с отсчётом, без отдельной плашки
    expect(await screen.findByRole("button", { name: /Письмо отправлено · ещё раз через \d+ с/ })).toBeDisabled();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(bodyOf("/auth/verify-email/resend")).toEqual({ email: "anna@example.org" });
  });
});

describe("pitch next to the form", () => {
  it("speaks to the side that registers", async () => {
    serve({});
    renderAt(<AuthPage mode="register" />);
    expect(await screen.findByText("Каждое предложение — с зарплатной вилкой")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("radio", { name: "Я нанимаю" }));
    expect(screen.getByText("Только подтверждённые профили, без накрутки")).toBeInTheDocument();
    expect(screen.queryByText("Каждое предложение — с зарплатной вилкой")).not.toBeInTheDocument();
  });
});

describe("login with unconfirmed email", () => {
  it("offers to resend the confirmation instead of a generic error", async () => {
    serve({
      "/auth/login": () => error("email_not_verified", "подтвердите почту", 403),
      "/auth/verify-email/resend": accepted,
    });
    renderAt(<AuthPage mode="login" />);
    await userEvent.type(await screen.findByLabelText("Email"), "anna@example.org");
    await userEvent.type(screen.getByLabelText("Пароль"), "Str0ng-pass-42");
    await userEvent.click(screen.getByRole("button", { name: "Войти" }));
    expect(await screen.findByText(/Подтвердите почту: откройте ссылку/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Отправить письмо ещё раз" }));
    expect(bodyOf("/auth/verify-email/resend")).toEqual({ email: "anna@example.org" });
    expect(screen.getByRole("link", { name: "Забыли пароль?" })).toHaveAttribute("href", "/forgot-password");
  });
});

describe("verify email page", () => {
  it("confirms only after an explicit click and clears the token from the address", async () => {
    serve({ "/auth/verify-email": () => json(null, 204) });
    renderAt(<VerifyEmailPage />, `#token=${TOKEN}`);
    const confirm = await screen.findByRole("button", { name: "Подтвердить почту" });
    expect(window.location.hash).toBe("");
    expect(fetchMock).not.toHaveBeenCalled();
    await userEvent.click(confirm);
    expect(await screen.findByText("Почта подтверждена")).toBeInTheDocument();
    expect(bodyOf("/auth/verify-email")).toEqual({ token: TOKEN });
  });

  it("explains an expired link", async () => {
    serve({ "/auth/verify-email": () => error("invalid_link", "ссылка недействительна или устарела") });
    renderAt(<VerifyEmailPage />, `#token=${TOKEN}`);
    await userEvent.click(await screen.findByRole("button", { name: "Подтвердить почту" }));
    expect(await screen.findByText("Не удалось подтвердить")).toBeInTheDocument();
  });

  it("rejects a page opened without a token", async () => {
    serve({});
    renderAt(<VerifyEmailPage />);
    expect(await screen.findByText("Ссылка неполная")).toBeInTheDocument();
  });
});

describe("password recovery", () => {
  it("answers the same way for any address", async () => {
    serve({ "/auth/password/forgot": accepted });
    renderAt(<ForgotPasswordPage />);
    await userEvent.type(await screen.findByLabelText("Email"), "who@example.org");
    await userEvent.click(screen.getByRole("button", { name: "Отправить ссылку" }));
    expect(await screen.findByText(/Если адрес зарегистрирован/)).toBeInTheDocument();
  });

  it("sets a new password after validating the confirmation", async () => {
    serve({ "/auth/password/reset": () => json(null, 204) });
    renderAt(<ResetPasswordPage />, `#token=${TOKEN}`);
    await userEvent.type(await screen.findByLabelText("Новый пароль"), "N3w-strong-pass");
    await userEvent.type(screen.getByLabelText("Повторите пароль"), "другой-пароль");
    await userEvent.click(screen.getByRole("button", { name: "Сохранить пароль" }));
    expect(await screen.findByText("Пароли не совпадают")).toBeInTheDocument();
    await userEvent.clear(screen.getByLabelText("Повторите пароль"));
    await userEvent.type(screen.getByLabelText("Повторите пароль"), "N3w-strong-pass");
    await userEvent.click(screen.getByRole("button", { name: "Сохранить пароль" }));
    expect(await screen.findByText("Пароль изменён")).toBeInTheDocument();
    expect(bodyOf("/auth/password/reset")).toEqual({ token: TOKEN, password: "N3w-strong-pass" });
  });

  it("sends the user for a new link when the old one is used up", async () => {
    serve({ "/auth/password/reset": () => error("invalid_link", "ссылка недействительна") });
    renderAt(<ResetPasswordPage />, `#token=${TOKEN}`);
    await userEvent.type(await screen.findByLabelText("Новый пароль"), "N3w-strong-pass");
    await userEvent.type(screen.getByLabelText("Повторите пароль"), "N3w-strong-pass");
    await userEvent.click(screen.getByRole("button", { name: "Сохранить пароль" }));
    expect(await screen.findByRole("link", { name: "Запросить новую ссылку" })).toHaveAttribute("href", "/forgot-password");
  });
});
