import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { bodyOf, json, renderWithApp, serveRoutes } from "../../../test/render";
import { AssessmentPage } from "./AssessmentPage";

const dictionaries = {
  specializations: [
    { slug: "backend", title: "Бэкенд-разработка", group: "Бэкенд-разработчики", skills: ["python"] },
    { slug: "qa", title: "Тестирование", group: "Инженеры по тестированию", skills: [] },
  ],
  industries: [{ value: "fintech", label: "Финтех и банки" }],
  roles: [{ value: "developer", label: "Разработка" }],
};
const skills = [{ slug: "python", name: "Python" }];
const survey = {
  specialization: "backend",
  grade: "middle",
  experience_years: 3,
  industries: [],
  roles: [],
  skills,
  answered_at: "2026-10-05T10:00:00Z",
};
const option = (grade: string, allowed = true, reason = "", retry_at: string | null = null) => ({
  grade,
  allowed,
  reason,
  retry_at,
});
const base = { survey: null, category: null, confirmed_skills: [], active: null, history: [], options: [] };
const attempt = {
  id: "a1",
  specialization: "backend",
  grade: "middle",
  status: "in_progress",
  started_at: "2026-10-05T10:00:00Z",
  deadline_at: new Date(Date.now() + 20 * 60_000).toISOString(),
  questions: [
    { index: 0, topic: "HTTP", level: 2, kind: "choice", prompt: "Какой код?", code: null, options: ["200", "201", "404", "500"] },
    { index: 1, topic: "Кэш", level: 3, kind: "number", prompt: "Сколько запросов?", code: "ttl = 60", options: [] },
  ],
};
const result = {
  id: "a1",
  specialization: "backend",
  grade: "middle",
  status: "completed",
  result: "passed",
  theta: 3.4,
  correct: 2,
  total: 2,
  score: 45,
  confident: false,
  topics: [{ topic: "HTTP", correct: 1, total: 1 }],
  started_at: "2026-10-05T10:00:00Z",
  finished_at: "2026-10-05T10:10:00Z",
};

afterEach(() => vi.unstubAllGlobals());

describe("AssessmentPage", () => {
  it("starts with the survey and saves the answers", async () => {
    const fetchMock = serveRoutes({
      "/candidate/assessment": () => json(base),
      "/candidate/assessment/survey": () => json({ ...base, survey, options: [option("middle")] }),
      "/public/dictionaries": () => json(dictionaries),
      "/public/skills": () => json(skills),
    });
    renderWithApp(<AssessmentPage />);
    expect(await screen.findByText("Шаг 1. Расскажите о себе")).toBeInTheDocument();
    await userEvent.click(await screen.findByRole("button", { name: "Бэкенд-разработка" }));
    await userEvent.type(screen.getByLabelText("Опыт в профессии, лет"), "3");
    await userEvent.click(screen.getByRole("button", { name: "Python" }));
    await userEvent.click(screen.getByRole("button", { name: "Финтех и банки" }));
    await userEvent.click(screen.getByRole("button", { name: "Сохранить ответы" }));
    expect(await screen.findByText("Ответы сохранены — можно проходить тест")).toBeInTheDocument();
    expect(bodyOf(fetchMock, "/candidate/assessment/survey")).toEqual({
      specialization: "backend",
      grade: "middle",
      experience_years: 3,
      industries: ["fintech"],
      roles: [],
      skills: ["python"],
    });
  });

  it("explains why a grade is not available yet", async () => {
    serveRoutes({
      "/candidate/assessment": () =>
        json({
          ...base,
          survey,
          options: [option("middle", false, "повторить тест на этот грейд можно позже", "2026-10-19T10:00:00Z"), option("junior")],
        }),
    });
    renderWithApp(<AssessmentPage />);
    expect(await screen.findByText(/повторить тест на этот грейд можно позже/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Начать тест на грейд Middle" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Начать тест на грейд Junior" })).toBeEnabled();
  });

  it("runs the test without answers in the browser and shows the result", async () => {
    let current: object = { ...base, survey, active: attempt };
    const fetchMock = serveRoutes({
      "/candidate/assessment": () => json(current),
      "/candidate/assessment/attempts/a1/submit": () => {
        current = { ...base, survey, history: [result] };
        return json(result);
      },
    });
    renderWithApp(<AssessmentPage />);
    const first = await screen.findByRole("group", { name: "Какой код?" });
    expect(document.body.textContent).not.toContain("answer");
    await userEvent.click(within(first).getByLabelText("201"));
    await userEvent.type(screen.getByLabelText("Ответ на задание 2"), "60");
    expect(screen.getByText("Отвечено 2 из 2")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Завершить тест" }));
    expect(await screen.findByText("Грейд Middle подтверждён")).toBeInTheDocument();
    expect(screen.getByText("3.4 из 5")).toBeInTheDocument();
    expect(bodyOf(fetchMock, "/candidate/assessment/attempts/a1/submit")).toEqual({ responses: ["1", "60"] });
  });

  it("asks before submitting with unanswered tasks", async () => {
    serveRoutes({ "/candidate/assessment": () => json({ ...base, survey, active: attempt }) });
    renderWithApp(<AssessmentPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Завершить тест" }));
    expect(within(screen.getByRole("dialog")).getByText(/Без ответа осталось заданий: 2/)).toBeInTheDocument();
  });
});
