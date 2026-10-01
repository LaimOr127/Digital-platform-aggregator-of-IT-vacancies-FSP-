import { describe, expect, it } from "vitest";
import { offerSchema } from "./schemas";

describe("offerSchema", () => {
  const valid = { vacancy_id: "v1", salary_min: "250000", salary_max: "300000", message: " Привет " };

  it("requires vacancy and salary range (honest hiring)", () => {
    expect(offerSchema.parse(valid)).toEqual({ vacancy_id: "v1", salary_min: 250000, salary_max: 300000, message: "Привет" });
    expect(offerSchema.safeParse({ ...valid, vacancy_id: "" }).success).toBe(false);
    expect(offerSchema.safeParse({ ...valid, salary_max: "" }).success).toBe(false);
  });

  it("rejects inverted range", () => {
    const r = offerSchema.safeParse({ ...valid, salary_min: "400000" });
    expect(r.error?.issues[0].path).toEqual(["salary_max"]);
  });
});
