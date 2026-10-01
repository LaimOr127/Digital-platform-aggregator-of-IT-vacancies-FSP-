import { describe, expect, it } from "vitest";
import type { ProfileDraft } from "../../../api/types";
import type { ProfileFormInput } from "../schemas";
import { fieldChanges, newSkills } from "./draft";

const form: ProfileFormInput = {
  full_name: "Анна",
  title: "",
  about: "",
  grade: "",
  work_format: "",
  city: "Москва",
  salary_min: "",
  salary_max: "",
  phone: "",
  telegram: "",
  contact_email: "",
  skills: ["python"],
  is_hidden: false,
  search_status: "open",
};

const draft: ProfileDraft = {
  source: "resume",
  full_name: "Анна",
  title: "Backend-разработчик",
  about: null,
  grade: "senior",
  work_format: null,
  city: "Казань",
  salary_min: 350000,
  salary_max: null,
  contacts: { email: null, phone: null, telegram: "@anna" },
  skills: [
    { slug: "python", name: "Python" },
    { slug: "go", name: "Go" },
  ],
  unknown_skills: [],
  notes: [],
};

describe("profile draft", () => {
  it("lists only real changes and preselects empty fields", () => {
    const changes = fieldChanges(draft, form);
    expect(changes.map((c) => c.field)).toEqual(["title", "grade", "city", "salary_min", "telegram"]);
    const city = changes.find((c) => c.field === "city");
    expect(city).toMatchObject({ current: "Москва", suggested: "Казань", preselected: false });
    expect(changes.find((c) => c.field === "grade")).toMatchObject({ suggested: "Senior", value: "senior", preselected: true });
  });

  it("adds only missing skills within the limit", () => {
    expect(newSkills(draft, form)).toEqual(["go"]);
    expect(newSkills(draft, form, 1)).toEqual([]);
  });
});
