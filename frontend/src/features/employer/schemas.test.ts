import { describe, expect, it } from "vitest";
import { emptyVacancy, vacancySchema } from "./schemas";

describe("vacancySchema", () => {
  const valid = { ...emptyVacancy, title: "Backend", salary_min: "200000", salary_max: "300000" };

  it("coerces salary strings and nulls empty city", () => {
    const r = vacancySchema.parse(valid);
    expect(r).toMatchObject({ salary_min: 200000, salary_max: 300000, city: null });
  });

  it("requires salary range (honest hiring)", () => {
    const r = vacancySchema.safeParse({ ...valid, salary_min: "" });
    expect(r.success).toBe(false);
  });

  it("rejects inverted range on salary_max", () => {
    const r = vacancySchema.safeParse({ ...valid, salary_min: "300000", salary_max: "100000" });
    expect(r.success).toBe(false);
    expect(r.error?.issues[0].path).toEqual(["salary_max"]);
  });
});

describe("vacancyToForm", () => {
  it("maps API vacancy to form values", async () => {
    const { vacancyToForm } = await import("./schemas");
    const form = vacancyToForm({
      id: "v1",
      company_id: "c1",
      title: "Backend",
      description: "",
      grade: "senior",
      work_format: "office",
      city: null,
      salary_min: 1,
      salary_max: 2,
      status: "draft",
      expires_at: null,
      created_at: "2026-10-01T00:00:00Z",
      skills: [{ slug: "go", name: "Go" }],
    });
    expect(form).toMatchObject({ city: "", skills: ["go"], grade: "senior" });
  });
});
