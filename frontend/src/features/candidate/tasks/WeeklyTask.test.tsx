import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { bodyOf, json, renderWithApp, serveRoutes } from "../../../test/render";
import { WeeklyTask } from "./WeeklyTask";

const offered = {
  id: "t1",
  title: "Медленная лента",
  body: "Лента грузится 3 секунды",
  specialization: "backend",
  grade: null,
  company_name: "ООО Найм",
};
const ANSWER = "Сниму план запроса и добавлю индекс по user_id";

afterEach(() => vi.unstubAllGlobals());

describe("weekly task", () => {
  it("sends an answer once it is long enough", async () => {
    const fetchMock = serveRoutes({
      "/candidate/tasks/current": () => json({ task: offered, next_at: null, reason: null }),
      "/candidate/tasks/answers": () => json({ items: [], next_cursor: null }),
      "/candidate/tasks/t1/answers": () => json({ id: "a1" }, 201),
    });
    renderWithApp(<WeeklyTask />);
    expect(await screen.findByText("ООО Найм")).toBeInTheDocument();
    const send = screen.getByRole("button", { name: "Отправить ответ" });
    expect(send).toBeDisabled();
    await userEvent.type(screen.getByLabelText(/Ваш ответ/), ANSWER);
    await userEvent.click(send);
    expect(await screen.findByText("Ответ отправлен компании")).toBeInTheDocument();
    expect(bodyOf(fetchMock, "/candidate/tasks/t1/answers")).toEqual({ answer: ANSWER });
  });

  it("shows when the next task opens and past ratings", async () => {
    serveRoutes({
      "/candidate/tasks/current": () => json({ task: null, next_at: "2026-10-12T09:00:00Z", reason: null }),
      "/candidate/tasks/answers": () =>
        json({
          items: [
            {
              id: "a1",
              task_title: "Лента",
              task_body: "Лента грузится 3 секунды",
              company_name: "ООО Найм",
              answer: "Добавлю индекс",
              rating: 4,
              created_at: "2026-10-05T09:00:00Z",
            },
          ],
          next_cursor: null,
        }),
    });
    renderWithApp(<WeeklyTask />);
    expect(await screen.findByText(/Следующая задача — с 12 окт/)).toBeInTheDocument();
    expect(screen.getByText("оценка 4 из 5")).toBeInTheDocument();
    // своё задание и ответ можно перечитать
    await userEvent.click(screen.getByText(/Задача «Лента»/));
    expect(screen.getByText("Лента грузится 3 секунды")).toBeVisible();
    expect(screen.getByText("Добавлю индекс")).toBeVisible();
  });

  it("closes the task after a screenshot and blocks copying its text", async () => {
    const fetchMock = serveRoutes({
      "/candidate/tasks/current": () => json({ task: offered, next_at: null, reason: null }),
      "/candidate/tasks/answers": () => json({ items: [], next_cursor: null }),
      "/candidate/tasks/t1/violation": () => new Response(null, { status: 204 }),
    });
    renderWithApp(<WeeklyTask />);
    const body = await screen.findByText("Лента грузится 3 секунды");
    const copy = new Event("copy", { bubbles: true, cancelable: true });
    body.dispatchEvent(copy);
    expect(copy.defaultPrevented).toBe(true);
    await userEvent.keyboard("{PrintScreen}");
    expect(await screen.findByText(/Задача закрыта: во время решения был сделан снимок экрана/)).toBeInTheDocument();
    const calls = fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/candidate/tasks/t1/violation"));
    expect(calls).toHaveLength(1); // keydown и keyup одного нажатия — одно нарушение
  });
});
