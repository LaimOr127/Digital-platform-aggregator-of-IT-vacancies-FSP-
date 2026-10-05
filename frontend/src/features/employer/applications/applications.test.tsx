import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { bodyOf, json, renderWithApp, serveRoutes } from "../../../test/render";
import { ApplicationsPage } from "./ApplicationsPage";
import { InvitationDialog } from "./InvitationDialog";

const response = {
  id: "r1",
  direction: "response",
  status: "viewed",
  vacancy_id: "v1",
  title: "Backend",
  description: "",
  grade: "middle",
  work_format: "remote",
  city: null,
  salary_min: 200000,
  salary_max: 300000,
  message: "Хочу к вам",
  decline_reason: null,
  expires_at: "2099-01-01T00:00:00Z",
  viewed_at: null,
  responded_at: null,
  created_at: "2026-10-05T09:00:00Z",
  contact_method: null,
  contacts_available: true,
  candidate: null,
};
const vacancy = {
  id: "v1",
  company_id: "c1",
  title: "Backend-разработчик",
  description: "Платёжная платформа",
  grade: "senior",
  specialization: "backend",
  work_format: "hybrid",
  city: "Казань",
  salary_min: 300000,
  salary_max: 400000,
  status: "active",
  expires_at: null,
  created_at: "2026-10-01T00:00:00Z",
  skills: [],
};
const company = { id: "c1", name: "ООО", inn: null, website: null, status: "approved", created_at: "", contact_telegram: "@hr" };
const card = { anon_id: "abcdef12-0000-0000-0000-000000000000", category: null };

afterEach(() => vi.unstubAllGlobals());

describe("employer contact flow", () => {
  it("answers a response with a contact and reveals candidate contacts", async () => {
    const fetchMock = serveRoutes({
      "/employer/applications": () => json({ items: [response], next_cursor: null }),
      "/employer/applications/r1/accept": () => json({ ...response, status: "accepted" }),
      "/employer/applications/r1/contacts": () => json({ full_name: "Анна", phone: null, telegram: "@anna", email: null }),
    });
    renderWithApp(<ApplicationsPage />);
    await userEvent.click(await screen.findByRole("radio", { name: "Отклики" }));
    expect(await screen.findByText("Письмо кандидата: Хочу к вам")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Показать контакты" }));
    expect(await screen.findByText("@anna")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Ответить и дать контакт" }));
    const dialog = screen.getByRole("dialog");
    await userEvent.type(within(dialog).getByLabelText(/Как кандидату связаться/), "hr@naim.ru");
    await userEvent.click(within(dialog).getByRole("button", { name: "Отправить" }));
    expect(await screen.findByText("Кандидат получит ваш контакт")).toBeInTheDocument();
    expect(bodyOf(fetchMock, "/employer/applications/r1/accept")).toEqual({ contact_method: "hr@naim.ru" });
  });

  it("prefills the invitation from the vacancy and company contacts", async () => {
    const fetchMock = serveRoutes({ "/employer/applications": () => json({ ...response, direction: "invitation" }, 201) });
    renderWithApp(
      <InvitationDialog candidate={card as never} vacancies={[vacancy as never]} vacancyId="v1" company={company as never} onClose={() => undefined} />,
    );
    expect(screen.getByLabelText("Должность")).toHaveValue("Backend-разработчик");
    expect(screen.getByLabelText("Как связаться с вами")).toHaveValue("@hr");
    await userEvent.click(screen.getByRole("button", { name: "Отправить приглашение" }));
    expect(await screen.findByText(/Приглашение отправлено/)).toBeInTheDocument();
    expect(bodyOf(fetchMock, "/employer/applications")).toMatchObject({
      anon_id: card.anon_id,
      vacancy_id: "v1",
      grade: "senior",
      salary_min: 300000,
      salary_max: 400000,
      contact_method: "@hr",
    });
  });
});
