import { describe, expect, it } from "vitest";
import { bandValues, compactMoney, domainOf, labeledTicks, niceStep, percentOf, ticks } from "./scale";

describe("salary scale", () => {
  it("picks a round step for about four ticks", () => {
    expect(niceStep(30_000)).toBe(10_000);
    expect(niceStep(180_000)).toBe(50_000);
    expect(niceStep(700_000)).toBe(250_000);
    expect(niceStep(50_000_000)).toBe(25_000_000);
  });

  it("keeps the number of ticks small for any range", () => {
    // огромная вилка из формы не должна рождать сотни тысяч делений
    for (const high of [1_000_000, 10_000_000, 500_000_000_000]) {
      expect(ticks(domainOf([100_000, high])!).length).toBeLessThanOrEqual(7);
    }
  });

  it("pads the domain by half a step and rounds to the step", () => {
    const domain = domainOf([180_000, 250_000, 320_000]);
    expect(domain).toEqual({ min: 150_000, max: 350_000, step: 50_000 });
    expect(ticks(domain!)).toEqual([150_000, 200_000, 250_000, 300_000, 350_000]);
  });

  it("never goes below zero and ignores empty values", () => {
    expect(domainOf([5_000, 20_000])?.min).toBe(0);
    expect(domainOf([])).toBeNull();
    expect(domainOf([0, Number.NaN])).toBeNull();
  });

  it("clamps positions outside the domain", () => {
    const domain = { min: 100_000, max: 300_000, step: 50_000 };
    expect(percentOf(200_000, domain)).toBe(50);
    expect(percentOf(50_000, domain)).toBe(0);
    expect(percentOf(900_000, domain)).toBe(100);
  });

  it("collects band values and skips missing bands", () => {
    const band = { count: 5, p25: 1, median: 2, p75: 3 };
    expect(bandValues([band, null, undefined])).toEqual([1, 2, 3]);
  });

  it("labels every other tick when they are dense", () => {
    expect(labeledTicks([1, 2, 3, 4, 5])).toEqual([1, 2, 3, 4, 5]);
    expect(labeledTicks([1, 2, 3, 4, 5, 6, 7])).toEqual([1, 3, 5, 7]);
    expect(labeledTicks([1, 2, 3, 4, 5, 6])).toEqual([1, 3, 6]);
  });

  it("formats compact money", () => {
    expect(compactMoney(0)).toBe("0");
    expect(compactMoney(400)).toBe("0");
    expect(compactMoney(999_600)).toBe("1 млн");
    expect(compactMoney(250_000)).toBe("250 тыс");
    expect(compactMoney(1_250_000)).toBe("1,3 млн");
    expect(compactMoney(1_000_000)).toBe("1 млн");
  });
});
