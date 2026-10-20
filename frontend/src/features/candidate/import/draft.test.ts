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
  specialization: "",
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
  specialization: null,
  work_formats: ["remote", "hybrid"],
  relocation: true,
  education: null,
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
  it("lists only real changes, all of them as separate fields", () => {
    const changes = fieldChanges({ ...draft, experience_years: 3.4 }, form);
    expect(changes.map((c) => c.field)).toEqual([
      "title",
      "grade",
      "work_formats",
      "city",
      "relocation",
      "salary_min",
      "experience_years",
      "telegram",
    ]);
    // все найденные форматы переносятся списком
    expect(changes.find((c) => c.field === "work_formats")).toMatchObject({
      current: "Офис",
      suggested: "Удалённо, Гибрид",
      value: ["remote", "hybrid"],
    });
    expect(changes.find((c) => c.field === "city")).toMatchObject({ current: "Москва", suggested: "Казань" });
    expect(changes.find((c) => c.field === "experience_years")).toMatchObject({ suggested: "3,4 года", value: 3.4 });
    expect(changes.find((c) => c.field === "grade")).toMatchObject({ suggested: "Senior", value: "senior" });
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
