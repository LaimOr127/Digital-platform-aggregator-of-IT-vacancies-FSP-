import { describe, expect, it } from "vitest";
import { daysLeft, formatDate, formatSalaryRange, labels, options } from "./format";

describe("formatSalaryRange", () => {
  it("formats full range with non-breaking thousands", () => {
    expect(formatSalaryRange(200000, 300000)).toBe("200\u00a0000 – 300\u00a0000\u00a0₽");
  });
  it("formats open ranges", () => {
    expect(formatSalaryRange(150000, null)).toMatch(/^от 150/);
    expect(formatSalaryRange(null, 90000)).toMatch(/^до 90/);
  });
  it("handles missing salary", () => {
    expect(formatSalaryRange(null, null)).toBe("Не указана");
  });
});

describe("daysLeft", () => {
  const now = new Date("2026-10-01T12:00:00Z");
  it("counts whole days until expiry", () => {
    expect(daysLeft("2026-10-15T12:00:00Z", now)).toBe(14);
    expect(daysLeft("2026-10-01T13:00:00Z", now)).toBe(1);
  });
  it("never goes negative and handles null", () => {
    expect(daysLeft("2026-09-01T00:00:00Z", now)).toBe(0);
    expect(daysLeft(null, now)).toBeNull();
  });
});

describe("labels", () => {
  it("covers every enum value", () => {
    expect(labels.grade.middle).toBe("Middle");
    expect(labels.vacancyStatus.active).toBe("Опубликована");
    expect(labels.companyStatus.pending).toBe("На модерации");
    expect(labels.tier.verified_fsp).toBe("Подтверждено ФСП");
  });
  it("builds select options in declared order", () => {
    expect(options(labels.workFormat).map((o) => o.value)).toEqual(["office", "hybrid", "remote"]);
  });
});

describe("formatDate", () => {
  it("formats in Russian", () => {
    expect(formatDate("2026-10-15T12:00:00Z")).toMatch(/15 окт/);
  });
});
