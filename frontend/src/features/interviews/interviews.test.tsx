import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { EmployerInterview } from "../../api/types";
import { bodyOf, json, renderWithApp, serveRoutes } from "../../test/render";
import { InterviewsInbox } from "../candidate/interviews/InterviewsInbox";
import { MatchPanel } from "../employer/catalog/MatchPanel";
import { InterviewsPage } from "../employer/interviews/InterviewsPage";

const hours = (h: number) => new Date(Date.now() + h * 3_600_000).toISOString();

const base: EmployerInterview = {
  id: "i1",
  status: "invited",
  result: null,
  company_name: "ООО Найм",
  vacancy_title: "Backend",
  vacancy_id: "v1",
  slots: [hours(-2), hours(3), hours(27)],
  duration_minutes: 60,
  scheduled_at: null,
  format: "online",
  location: "https://meet.example.org/x",
  interviewer: "Иван, CTO",
  message: "",
  decline_reason: null,
  feedback: null,
  expires_at: hours(48),
  responded_at: null,
  completed_at: null,
  created_at: hours(-5),
  offer_id: null,
  candidate: null,
};

afterEach(() => vi.unstubAllGlobals());

describe("match panel", () => {
  it("explains the score by factors on demand", async () => {
    renderWithApp(
      <MatchPanel match={{ score: 82, factors: [{ key: "skills", label: "Навыки", weight: 40, share: 0.75, detail: "3 из 4" }] }} />,
    );
    expect(screen.getByText("82%")).toBeInTheDocument();
    expect(screen.queryByText("3 из 4")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Почему/ }));
    expect(screen.getByText("30 из 40")).toBeInTheDocument();
    expect(screen.getByText("3 из 4")).toBeInTheDocument();
  });
});

describe("candidate interviews", () => {
  it("offers only future slots and confirms the chosen one", async () => {
    const mock = serveRoutes({
      "/candidate/interviews": () => json({ items: [base], next_cursor: null }),
      "/candidate/interviews/i1/accept": () => json({ ...base, status: "scheduled" }),
    });
    renderWithApp(<InterviewsInbox />);
    await screen.findByRole("button", { name: "Подтвердить время" });
    const radios = screen.getAllByRole("radio", { name: /мин$/ });
    expect(radios).toHaveLength(2); // прошедший вариант не предлагается
    await userEvent.click(radios[1]);
    await userEvent.click(screen.getByRole("button", { name: "Подтвердить время" }));
    expect(bodyOf(mock, "/accept")).toEqual({ slot: base.slots[2] });
  });
});

describe("employer interviews", () => {
  it("shows the next step for each status", async () => {
    const held = { ...base, id: "h", status: "scheduled" as const, scheduled_at: hours(-1) };
    const passed = { ...base, id: "p", status: "completed" as const, result: "passed" as const };
    const offered = { ...passed, id: "o", offer_id: "off1" };
    serveRoutes({ "/employer/interviews": () => json({ items: [base, held, passed, offered], next_cursor: null }) });
    renderWithApp(<InterviewsPage />);
    const rows = await screen.findAllByRole("article");
    expect(within(rows[0]).getByRole("button", { name: "Отменить" })).toBeInTheDocument();
    expect(within(rows[0]).queryByRole("button", { name: "Отметить итог" })).not.toBeInTheDocument();
    expect(within(rows[1]).getByRole("button", { name: "Отметить итог" })).toBeInTheDocument();
    expect(within(rows[2]).getByRole("button", { name: "Отправить оффер" })).toBeInTheDocument();
    expect(within(rows[3]).getByRole("link", { name: /Оффер отправлен/ })).toHaveAttribute("href", "/company/offers");
  });
});
