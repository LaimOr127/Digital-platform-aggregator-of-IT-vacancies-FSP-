import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { bodyOf, json, renderWithApp, serveRoutes } from "../../../test/render";
import { ApplicationsInbox } from "./ApplicationsInbox";
import { VacancyBoard } from "./VacancyBoard";

const company = { name: "ООО Найм", industry: "Финтех", website: null, description: "Платежи" };
const invitation = {
  id: "a1",
  direction: "invitation",
  status: "viewed",
  vacancy_id: null,
  title: "Backend-разработчик",
  description: "Команда платформы",
  grade: "middle",
  work_format: "remote",
  city: null,
  salary_min: 250000,
  salary_max: 320000,
  message: "",
  decline_reason: null,
  expires_at: "2099-01-01T00:00:00Z",
  viewed_at: "2026-10-05T10:00:00Z",
  responded_at: null,
  created_at: "2026-10-05T09:00:00Z",
  company,
  contact_method: "Telegram @hr",
};
const vacancy = {
  id: "v1",
  title: "QA-инженер",
  description: "",
  specialization: "qa",
  grade: "junior",
  work_format: "office",
  city: "Казань",
  salary_min: 100000,
  salary_max: 150000,
  skills: ["Автотесты"],
  expires_at: null,
  company,
  match: { score: 64, factors: [] },
  application_status: null,
};

afterEach(() => vi.unstubAllGlobals());

describe("candidate contact flow", () => {
  it("shows the offer terms and accepts with explicit consent", async () => {
    const fetchMock = serveRoutes({
      "/candidate/applications": () => json({ items: [invitation], next_cursor: null }),
      "/candidate/applications/a1/accept": () => json({ ...invitation, status: "accepted" }),
    });
    renderWithApp(<ApplicationsInbox />);
    expect(await screen.findByText("Просмотрено")).toBeInTheDocument();
    expect(screen.getByText("Telegram @hr")).toBeInTheDocument();
    expect(screen.getByText(/250.000/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Принять" }));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText(/получит ваше имя и контакты/)).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole("button", { name: "Принять и передать контакты" }));
    expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith("/candidate/applications/a1/accept"))).toBe(true);
  });

  it("responds to a vacancy with a cover letter", async () => {
    const fetchMock = serveRoutes({
      "/candidate/vacancies": () => json({ items: [vacancy], next_cursor: null }),
      "/candidate/vacancies/v1/respond": () => json({ ...invitation, direction: "response" }, 201),
    });
    renderWithApp(<VacancyBoard />);
    expect(await screen.findByText("64%", { exact: false })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Откликнуться" }));
    await userEvent.type(screen.getByLabelText(/Сопроводительное письмо/), "Готова");
    await userEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Откликнуться" }));
    expect(await screen.findByText("Отклик отправлен")).toBeInTheDocument();
    expect(bodyOf(fetchMock, "/candidate/vacancies/v1/respond")).toEqual({ message: "Готова" });
  });
});
