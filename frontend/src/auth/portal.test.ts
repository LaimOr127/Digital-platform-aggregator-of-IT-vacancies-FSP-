import { describe, expect, it } from "vitest";
import { portalPath, safeNext } from "./portal";

describe("safeNext", () => {
  it("keeps paths inside own portal", () => {
    expect(safeNext("/company/vacancies", "employer")).toBe("/company/vacancies");
  });
  it.each(["https://evil.example", "//evil.example", "/admin", null, "relative"])(
    "falls back to portal home for %s",
    (next) => {
      expect(safeNext(next, "employer")).toBe("/company");
    },
  );
  it("maps roles to portals", () => {
    expect(portalPath("candidate")).toBe("/app");
    expect(portalPath("admin")).toBe("/admin");
  });
});
