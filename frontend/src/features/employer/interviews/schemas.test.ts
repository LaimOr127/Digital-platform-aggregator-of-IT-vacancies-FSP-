import { describe, expect, it } from "vitest";
import { inviteSchema, offerSchema } from "./schemas";

const local = (hours: number) => {
  const d = new Date(Date.now() + hours * 3_600_000);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
};

const valid = {
  vacancy_id: "v1",
  slot1: local(3),
  slot2: "",
  slot3: local(27),
  duration_minutes: "60",
  format: "online" as const,
  location: "https://meet.example.org/x",
  interviewer: "Иван, CTO",
  message: "",
};

describe("inviteSchema", () => {
  it("collects filled slots as ISO time", () => {
    const out = inviteSchema.parse(valid);
    expect(out.slots).toHaveLength(2);
    expect(out.slots[0]).toMatch(/Z$/);
    expect(out.duration_minutes).toBe(60);
  });

  it("rejects past or too early slots and non-https online links", () => {
    expect(inviteSchema.safeParse({ ...valid, slot1: local(0.2) }).success).toBe(false);
    expect(inviteSchema.safeParse({ ...valid, slot1: "" }).success).toBe(false);
    const r = inviteSchema.safeParse({ ...valid, location: "zoom.us/j/1" });
    expect(r.error?.issues[0].path).toEqual(["location"]);
    expect(inviteSchema.safeParse({ ...valid, format: "office", location: "Казань, Баумана 1" }).success).toBe(true);
  });
});

describe("offerSchema", () => {
  it("requires an honest salary range", () => {
    expect(offerSchema.parse({ salary_min: "250000", salary_max: "300000", message: " Привет " })).toEqual({
      salary_min: 250000,
      salary_max: 300000,
      message: "Привет",
    });
    expect(offerSchema.safeParse({ salary_min: "400000", salary_max: "300000", message: "" }).success).toBe(false);
  });
});
