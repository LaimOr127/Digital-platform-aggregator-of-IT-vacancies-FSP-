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
  work_format: null,
  city: "Москва",
  salary_min: null,
  salary_max: null,
  verification_tier: "self_declared",
  is_hidden: false,
  search_status: "open",
  industries: [],
  roles: [],
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
  unknown_skills: ["Rust"],
  notes: ["Поля заполнены алгоритмом по тексту резюме — проверьте перед сохранением"],
};

const json = (body: unknown) => new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  fetchMock = vi.fn(async (url: string) =>
    String(url).endsWith("/capabilities") ? json({ ai_available: true, max_file_mb: 5 }) : json(draft),
  );
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
    expect(within(dialog).getByText(/Нет в справочнике.*Rust/)).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole("button", { name: "Перенести в профиль" }));

    expect(screen.getByPlaceholderText("Backend-разработчик")).toHaveValue("Backend-разработчик");
    expect(screen.getByDisplayValue("Москва")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Убрать Go" })).toBeInTheDocument();
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
    fetchMock.mockImplementation(async (_url: string, init?: RequestInit) =>
      init?.method === "PATCH"
        ? json({ ...profile, ...JSON.parse(String(init.body)), contacts: profile.contacts, skills: profile.skills })
        : json({ ai_available: false, max_file_mb: 5 }),
    );
    renderForm();
    await userEvent.type(screen.getByPlaceholderText("Backend-разработчик"), "QA");
    expect(screen.getByText("Есть несохранённые изменения")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Сохранить" }));
    expect(await screen.findByText("Все изменения сохранены")).toBeInTheDocument();
  });
});
