import { describe, expect, it } from "vitest";
import type { Profile } from "../../api/types";
import { formToUpdate, profileSchema, profileToForm } from "./schemas";

const profile: Profile = {
  anon_id: "a1",
  full_name: "Анна",
  contacts: { phone: null, telegram: "@anna", email: null },
  title: null,
  about: null,
  grade: "junior",
  work_format: null,
  city: null,
  salary_min: 100000,
  salary_max: null,
  verification_tier: "self_declared",
  is_hidden: false,
  search_status: "open",
  industries: [],
  roles: [],
  show_fsp: true,
  show_salary: true,
  show_about: true,
  skills: [{ slug: "python", name: "Python" }],
};

describe("profile form", () => {
  it("round-trips API profile -> form -> update payload", () => {
    const update = formToUpdate(profileSchema.parse(profileToForm(profile)));
    expect(update).toEqual({
      full_name: "Анна",
      title: null,
      about: null,
      grade: "junior",
      work_format: null,
      city: null,
      salary_min: 100000,
      salary_max: null,
      skills: ["python"],
      is_hidden: false,
      search_status: "open",
      contacts: { phone: null, telegram: "@anna", email: null },
    });
  });

  it("validates salary range", () => {
    const form = { ...profileToForm(profile), salary_min: "300000", salary_max: "100000" };
    expect(profileSchema.safeParse(form).success).toBe(false);
  });
});
