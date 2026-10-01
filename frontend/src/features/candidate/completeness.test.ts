import { describe, expect, it } from "vitest";
import type { Profile } from "../../api/types";
import { completeness } from "./completeness";

const empty: Profile = {
  anon_id: "x",
  full_name: "Анна",
  contacts: { phone: null, telegram: null, email: null },
  title: null,
  about: null,
  grade: null,
  work_format: null,
  city: null,
  salary_min: null,
  salary_max: null,
  verification_tier: "self_declared",
  is_hidden: false,
  search_status: "open",
  skills: [],
};

describe("completeness", () => {
  it("is zero for an empty profile and lists what is missing", () => {
    const r = completeness(empty);
    expect(r.percent).toBe(0);
    expect(r.missing).toContain("Грейд");
  });

  it("is 100 for a filled profile", () => {
    const skills = ["a", "b", "c"].map((slug) => ({ slug, name: slug }));
    const full: Profile = {
      ...empty,
      title: "Backend",
      grade: "middle",
      work_format: "remote",
      salary_min: 1,
      about: "о себе",
      skills,
      contacts: { phone: null, telegram: "@a", email: null },
    };
    expect(completeness(full)).toEqual({ percent: 100, missing: [] });
  });
});
