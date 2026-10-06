import { describe, expect, it } from "vitest";
import type { ProfileDraft } from "../../../api/types";
import type { ProfileFormInput } from "../schemas";
import { fieldChanges, newLists } from "./draft";

const form: ProfileFormInput = {
  full_name: "Анна",
  title: "",
  about: "",
  grade: "",
  work_formats: ["office"],
  city: "Москва",
  relocation: false,
  education: "",
  salary_min: "",
  salary_max: "",
  phone: "",
  telegram: "",
  contact_email: "",
  skills: ["python"],
  custom_skills: [],
  experience_years: "",
  roles: [],
  soft_skills: ["teamwork"],
  is_hidden: false,
  search_status: "open",
};

const draft: ProfileDraft = {
  source: "resume",
  full_name: "Анна",
  title: "Backend-разработчик",
  about: null,
  grade: "senior",
  work_format: "remote",
  city: "Казань",
  salary_min: 350000,
  salary_max: null,
  contacts: { email: null, phone: null, telegram: "@anna" },
  skills: [
    { slug: "python", name: "Python" },
    { slug: "go", name: "Go" },
  ],
  experience_years: 6,
  roles: ["mentor"],
  soft_skills: ["teamwork", "leadership"],
  unknown_skills: ["Camunda"],
  notes: [],
};

describe("profile draft", () => {
  it("lists only real changes and preselects empty fields", () => {
    const changes = fieldChanges(draft, form);
    expect(changes.map((c) => c.field)).toEqual(["title", "grade", "work_format", "city", "salary_min", "experience_years", "telegram"]);
    // в форме форматов несколько, в черновике — один: сравниваются подписи
    expect(changes.find((c) => c.field === "work_format")).toMatchObject({ current: "Офис", suggested: "Удалённо" });
    const city = changes.find((c) => c.field === "city");
    expect(city).toMatchObject({ current: "Москва", suggested: "Казань", preselected: false });
    expect(changes.find((c) => c.field === "grade")).toMatchObject({ suggested: "Senior", value: "senior", preselected: true });
  });

  it("adds only missing skills, roles and soft skills", () => {
    expect(newLists(draft, form)).toEqual({
      skills: ["go"],
      custom_skills: ["Camunda"],
      roles: ["mentor"],
      soft_skills: ["leadership"],
    });
  });

  it("respects list limits", () => {
    const full = { ...form, roles: ["developer", "team_lead", "tech_lead", "architect", "mentor"] };
    expect(newLists({ ...draft, roles: ["mentor", "x"] }, full).roles).toEqual([]);
  });
});
