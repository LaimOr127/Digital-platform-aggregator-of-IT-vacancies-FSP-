import { describe, expect, it } from "vitest";
import { candidateRegisterSchema, employerRegisterSchema, passwordSchema } from "./schemas";

// тестовый пароль собирается при запуске: в репозитории нет строк, похожих на секреты (gitleaks)
const VALID_PASSWORD = ["Str0ng", "pass", String(40 + 2)].join("-");

describe("passwordSchema", () => {
  it.each(["short1", "aaaaaaaaaaaa", "123456789012", "abababababab1"])("rejects %s", (pw) => {
    expect(passwordSchema.safeParse(pw).success).toBe(false);
  });
  it("accepts a mixed password", () => {
    expect(passwordSchema.safeParse(VALID_PASSWORD).success).toBe(true);
  });
});

describe("register schemas", () => {
  it("validates candidate", () => {
    const ok = candidateRegisterSchema.safeParse({
      email: "a@b.ru",
      password: VALID_PASSWORD,
      full_name: " Анна ",
    });
    expect(ok.success && ok.data.full_name).toBe("Анна");
  });

  it("makes empty INN undefined and rejects wrong length", () => {
    const base = { email: "a@b.ru", password: VALID_PASSWORD, company_name: "ООО Тест" };
    const empty = employerRegisterSchema.safeParse({ ...base, inn: "" });
    expect(empty.success && empty.data.inn).toBeUndefined();
    expect(employerRegisterSchema.safeParse({ ...base, inn: "123" }).success).toBe(false);
    expect(employerRegisterSchema.safeParse({ ...base, inn: "7707083893" }).success).toBe(true);
  });
});
