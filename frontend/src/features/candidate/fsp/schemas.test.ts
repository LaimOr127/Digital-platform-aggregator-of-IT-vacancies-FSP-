import { describe, expect, it } from "vitest";
import { athleteIdSchema, codeSchema } from "./schemas";

describe("FSP link forms", () => {
  it("normalizes athlete id", () => {
    expect(athleteIdSchema.parse({ athlete_id: " fsp-24001 " }).athlete_id).toBe("FSP-24001");
  });
  it.each(["", "a", "FSP 1", "../x"])("rejects id %s", (value) => {
    expect(athleteIdSchema.safeParse({ athlete_id: value }).success).toBe(false);
  });
  it("accepts only 6 digits as code", () => {
    expect(codeSchema.safeParse({ code: "123456" }).success).toBe(true);
    expect(codeSchema.safeParse({ code: "12345a" }).success).toBe(false);
  });
});
