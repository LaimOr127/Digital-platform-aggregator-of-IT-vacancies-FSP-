import { describe, expect, it } from "vitest";
import { positionOf } from "./position";

describe("positionOf", () => {
  const band = { count: 5, p25: 200_000, median: 250_000, p75: 300_000 };

  it("treats the quartiles as part of the typical range (as the backend does)", () => {
    expect(positionOf(200_000, band)).toBe("within");
    expect(positionOf(300_000, band)).toBe("within");
  });

  it("detects values outside the typical range", () => {
    expect(positionOf(199_999, band)).toBe("below");
    expect(positionOf(300_001, band)).toBe("above");
  });
});
