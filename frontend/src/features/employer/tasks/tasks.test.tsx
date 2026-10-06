import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { bodyOf, json, renderWithApp, serveRoutes } from "../../../test/render";
import { TasksPage } from "./TasksPage";

const company = { id: "c1", name: "ООО", inn: null, website: null, status: "approved", created_at: "" };
const task = {
  id: "t1",
  title: "Медленная лента",
  body: "Лента грузится 3 секунды — что проверите?",
  specialization: "backend",
  grade: null,
  is_active: true,
  created_at: "2026-10-05T09:00:00Z",
  answers_count: 1,
};
const answer = {
  id: "a1",
  answer: "Посмотрю план запроса и добавлю индекс",
  rating: null,
  created_at: "2026-10-05T10:00:00Z",
  candidate: { anon_id: "abcdef12-0000-0000-0000-000000000000", category: { slug: "backend:middle", title: "Бэкенд · Middle" } },
};

afterEach(() => vi.unstubAllGlobals());

describe("employer tasks", () => {
  it("publishes a task for a specialization", async () => {
    const fetchMock = serveRoutes({
      "/employer/tasks": () => json({ items: [], next_cursor: null }),
    });
    renderWithApp(<TasksPage company={company as never} />);
    expect(await screen.findByText("Задач пока нет")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Новая задача" }));
    const dialog = screen.getByRole("dialog");
    await userEvent.type(within(dialog).getByLabelText("Название"), "Очередь писем");
    await userEvent.selectOptions(within(dialog).getByLabelText("Специализация"), "backend");
    await userEvent.type(within(dialog).getByLabelText(/Условие/), "Как не потерять письмо при падении?");
    await userEvent.click(within(dialog).getByRole("button", { name: "Опубликовать" }));
    expect(bodyOf(fetchMock, "/employer/tasks")).toEqual({
      title: "Очередь писем",
      specialization: "backend",
      grade: null,
      body: "Как не потерять письмо при падении?",
    });
  });

  it("rates an answer and invites its author", async () => {
    const fetchMock = serveRoutes({
      "/employer/tasks": () => json({ items: [task], next_cursor: null }),
      "/employer/tasks/t1/answers": () => json({ items: [answer], next_cursor: null }),
      "/employer/tasks/t1/answers/a1/rate": () => json({ ...answer, rating: 5 }),
    });
    renderWithApp(<TasksPage company={company as never} />);
    await userEvent.click(await screen.findByRole("button", { name: "Ответы: 1" }));
    const dialog = await screen.findByRole("dialog", { name: /Ответы/ });
    expect(await within(dialog).findByText(/Кандидат #ABCDEF · Бэкенд · Middle/)).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole("radio", { name: "5" }));
    expect(bodyOf(fetchMock, "/employer/tasks/t1/answers/a1/rate")).toEqual({ rating: 5 });
    await userEvent.click(within(dialog).getByRole("button", { name: "Пригласить" }));
    expect(await screen.findByRole("dialog", { name: "Пригласить кандидата" })).toBeInTheDocument();
  });
});
