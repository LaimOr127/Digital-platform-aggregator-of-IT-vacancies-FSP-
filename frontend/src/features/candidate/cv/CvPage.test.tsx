import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { json, renderWithApp, serveRoutes } from "../../../test/render";
import CvPage from "./CvPage";

const profile = {
  anon_id: "a1",
  full_name: "Анна Смирнова",
  contacts: { phone: null, telegram: "@anna", email: null },
  title: "Backend-разработчик",
  about: "Строю платёжные сервисы",
  grade: "middle",
  work_formats: ["remote"],
  city: "Казань",
  relocation: false,
  education: null,
  custom_skills: [],
  salary_min: 250000,
  salary_max: null,
  verification_tier: "self_declared",
  is_hidden: false,
  search_status: "open",
  industries: [],
  roles: ["mentor"],
  soft_skills: ["teamwork"],
  experience_years: 4,
  show_fsp: true,
  show_salary: true,
  show_about: true,
  skills: [
    { slug: "python", name: "Python" },
    { slug: "go", name: "Go" },
  ],
};
const assessment = {
  survey: null,
  category: { slug: "backend:middle", title: "Бэкенд-разработчики · Middle", specialization: "backend", grade: "middle", score: 78, confirmed_at: "2026-10-05T09:00:00Z", next_change_at: null },
  confirmed_skills: ["python"],
  active: null,
  history: [],
  options: [],
};
const dictionaries = {
  specializations: [],
  industries: [],
  roles: [{ value: "mentor", label: "Наставничество" }],
  soft_skills: [{ value: "teamwork", label: "Работа в команде" }],
};

afterEach(() => vi.unstubAllGlobals());

describe("standardized profile", () => {
  it("separates confirmed facts and handles a profile without FSP history", async () => {
    serveRoutes({
      "/candidate/profile": () => json(profile),
      "/candidate/assessment": () => json(assessment),
      "/candidate/fsp": () => json({ linked: false, verification_tier: "self_declared", achievements: [], categories: [] }),
      "/public/dictionaries": () => json(dictionaries),
    });
    renderWithApp(<CvPage />);
    expect(await screen.findByRole("heading", { name: "Анна Смирнова" })).toBeInTheDocument();
    expect(screen.getByText("Бэкенд-разработчики · Middle")).toBeInTheDocument();
    // подтверждённые тестом навыки выделены, заявленные — обычным текстом
    expect([...document.querySelectorAll("strong")].map((el) => el.textContent)).toEqual(["Python"]);
    expect(screen.getByText(/, Go/)).toBeInTheDocument();
    expect(screen.getByText(/Нет данных ФСП/)).toBeInTheDocument();
    expect(await screen.findByText("Роли: Наставничество")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Сохранить PDF" })).toBeEnabled();
  });
});
