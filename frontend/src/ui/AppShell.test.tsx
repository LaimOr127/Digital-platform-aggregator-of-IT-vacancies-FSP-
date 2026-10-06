import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { renderWithApp } from "../test/render";
import { AppShell, type NavItem } from "./AppShell";

vi.mock("../auth/AuthProvider", () => ({ useAuth: () => ({ status: "anonymous", user: null }) }));

const NAV: NavItem[] = [
  { to: "/app", label: "Профиль", children: [{ to: "/app", label: "Основная информация", end: true }, { to: "/app/fsp", label: "ФСП" }] },
  {
    to: "/app/vacancies",
    label: "Поиск работы",
    children: [
      { to: "/app/vacancies", label: "Вакансии" },
      { to: "/app/offers", label: "Офферы", dot: true },
    ],
  },
];

describe("AppShell navigation", () => {
  it("shows subtabs of the open section and marks news on both levels", () => {
    renderWithApp(<AppShell nav={NAV}>контент</AppShell>, "/app/vacancies");
    expect(screen.getByRole("link", { name: "Поиск работы, есть новое" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Вакансии" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Офферы, есть новое" })).toBeInTheDocument();
    // подвкладки закрытого раздела не показываются
    expect(screen.queryByRole("link", { name: "ФСП" })).not.toBeInTheDocument();
  });
});
