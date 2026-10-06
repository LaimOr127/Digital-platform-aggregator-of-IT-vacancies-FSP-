import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Profile, ProfileDraft } from "../../../api/types";
import { ToastProvider } from "../../../ui/Toast";
import { ProfileForm } from "../ProfileForm";

const profile: Profile = {
  anon_id: "a1",
  full_name: "Анна",
  contacts: { phone: null, telegram: null, email: null },
  title: null,
  about: null,
  grade: null,
  work_formats: [],
  city: "Москва",
  relocation: false,
  education: null,
  custom_skills: [],
  salary_min: null,
  salary_max: null,
  verification_tier: "self_declared",
  is_hidden: false,
  search_status: "open",
  industries: [],
  roles: [],
  soft_skills: [],
  experience_years: null,
  show_fsp: true,
  show_salary: true,
  show_about: true,
  skills: [{ slug: "python", name: "Python" }],
};
const skills = [
  { slug: "python", name: "Python" },
  { slug: "go", name: "Go" },
];
const draft: ProfileDraft = {
  source: "resume",
  full_name: "Анна Смирнова",
  title: "Backend-разработчик",
  about: null,
  grade: "senior",
  work_format: null,
  city: "Казань",
  salary_min: null,
  salary_max: null,
  contacts: { email: null, phone: null, telegram: "@anna" },
  skills: [{ slug: "go", name: "Go" }],
  experience_years: 5,
  roles: ["mentor"],
  soft_skills: ["teamwork"],
  unknown_skills: ["Rust"],
  notes: ["Поля заполнены алгоритмом по тексту резюме — проверьте перед сохранением"],
};

const dictionaries = {
  specializations: [],
  industries: [],
  roles: [{ value: "mentor", label: "Наставничество" }],
  soft_skills: [{ value: "teamwork", label: "Работа в команде" }],
};
const json = (body: unknown) => new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  fetchMock = vi.fn(async (url: string) => {
    if (String(url).endsWith("/capabilities")) return json({ ai_available: true, max_file_mb: 5 });
    return String(url).endsWith("/dictionaries") ? json(dictionaries) : json(draft);
  });
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => vi.unstubAllGlobals());

function renderForm() {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ToastProvider>
        <ProfileForm profile={profile} skills={skills} fspLinked={false} />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

describe("profile autofill", () => {
  it("uploads a resume, lets the candidate choose fields and fills the form", async () => {
    renderForm();
    expect(screen.getByRole("button", { name: /Из анкеты ФСП/ })).toBeDisabled();
    await userEvent.click(await screen.findByLabelText(/Разобрать резюме с помощью ИИ/));
    const file = new File(["%PDF-1.4"], "cv.pdf", { type: "application/pdf" });
    await userEvent.upload(screen.getByLabelText("Файл резюме"), file);

    const dialog = await screen.findByRole("dialog");
    const [, init] = fetchMock.mock.calls.find(([url]) => String(url).endsWith("/import/resume"))!;
    expect((init.body as FormData).get("use_ai")).toBe("true");
    // пустые поля отмечены, заполненные (город, имя) — нет
    expect(within(dialog).getByRole("checkbox", { name: /Должность/ })).toBeChecked();
    expect(within(dialog).getByRole("checkbox", { name: /Город/ })).not.toBeChecked();
    expect(within(dialog).getByText(/Нет в справочнике — добавятся как свои навыки: Rust/)).toBeInTheDocument();
    expect(await within(dialog).findByText("Наставничество, Работа в команде")).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole("button", { name: "Перенести в профиль" }));

    expect(screen.getByPlaceholderText("Backend-разработчик")).toHaveValue("Backend-разработчик");
    expect(screen.getByDisplayValue("Москва")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Убрать Go" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Убрать свой навык Rust" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Наставничество", pressed: true })).toBeInTheDocument();
    expect(screen.getByLabelText("Опыт в профессии, лет")).toHaveValue(5);
    expect(screen.getByText("Есть несохранённые изменения")).toBeInTheDocument();
  });

  it("rejects a too large file before uploading", async () => {
    renderForm();
    const big = new File([new Uint8Array(6 * 1024 * 1024)], "cv.pdf", { type: "application/pdf" });
    await userEvent.upload(screen.getByLabelText("Файл резюме"), big);
    expect(await screen.findByText("Файл больше 5 МБ")).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith("/import/resume"))).toBe(false);
  });

  it("treats the saved profile as the new baseline", async () => {
    fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
      if (init?.method === "PATCH")
        return json({ ...profile, ...JSON.parse(String(init.body)), contacts: profile.contacts, skills: profile.skills });
      return String(url).endsWith("/dictionaries") ? json(dictionaries) : json({ ai_available: false, max_file_mb: 5 });
    });
    renderForm();
    await userEvent.type(screen.getByPlaceholderText("Backend-разработчик"), "QA");
    expect(screen.getByText("Есть несохранённые изменения")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Сохранить" }));
    expect(await screen.findByText("Все изменения сохранены")).toBeInTheDocument();
    // кнопка — только когда есть что сохранять
    expect(screen.queryByRole("button", { name: "Сохранить" })).not.toBeInTheDocument();
  });
});
