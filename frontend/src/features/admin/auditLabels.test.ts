import { describe, expect, it } from "vitest";
import { auditDetails, auditLabel } from "./auditLabels";

describe("audit labels", () => {
  it("translates known actions and keeps unknown codes as is", () => {
    expect(auditLabel("admin.user_block")).toBe("Пользователь заблокирован");
    expect(auditLabel("future.event")).toBe("future.event");
  });

  it("summarises status change and reason, ignoring other meta", () => {
    expect(auditDetails({ from: "active", to: "blocked", reason: "спам" })).toBe("Опубликована → Заблокирована · причина: спам");
    expect(auditDetails({ from: "pending", to: "approved", reason: "" })).toBe("На модерации → Одобрена");
    expect(auditDetails({ role: "candidate" })).toBe("");
  });
});
