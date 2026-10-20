// Общие zod-поля форм: пустой ввод -> null, числа из <input> -> number.
import { z } from "zod";

const empty = (v: unknown) => v === "" || v === undefined || v === null || Number.isNaN(v);

export const optionalText = (max: number) =>
  z.preprocess((v) => (typeof v === "string" && v.trim() === "" ? null : v), z.string().trim().max(max).nullable());

export const optionalEnum = <T extends readonly [string, ...string[]]>(values: T) =>
  z.preprocess((v) => (empty(v) ? null : v), z.enum(values).nullable());

const moneyNumber = z.number("Введите число").int("Целое число").positive("Больше нуля").max(10_000_000, "Слишком много");

export const optionalMoney = z.preprocess((v) => (empty(v) ? null : Number(v)), moneyNumber.nullable());
// стаж — годы с одной десятой (3 года 5 месяцев = 3,4); запятая допустима
const yearsNumber = z
  .number("Укажите стаж")
  .min(0, "Не меньше 0")
  .max(50, "Не больше 50")
  .transform((v) => Math.round(v * 10) / 10);
const toYears = (v: unknown) => Number(String(v).replace(",", "."));

export const requiredYears = z.preprocess((v) => (empty(v) ? undefined : toYears(v)), yearsNumber);
export const optionalYears = z.preprocess((v) => (empty(v) ? null : toYears(v)), yearsNumber.nullable());
export const requiredMoney = z.preprocess((v) => (empty(v) ? undefined : Number(v)), moneyNumber);

type Range = { salary_min?: number | null; salary_max?: number | null };

/** Вилка: max не меньше min (та же проверка, что на бэке). */
export function salaryRangeIssue(value: Range, ctx: z.RefinementCtx) {
  if (value.salary_min && value.salary_max && value.salary_max < value.salary_min) {
    ctx.addIssue({ code: "custom", path: ["salary_max"], message: "Не меньше нижней границы" });
  }
}

export const GRADES = ["intern", "junior", "middle", "senior", "lead"] as const;
export const WORK_FORMATS = ["office", "hybrid", "remote"] as const;
export const EDUCATION_LEVELS = ["secondary", "vocational", "incomplete_higher", "bachelor", "specialist", "master", "phd"] as const;
export const SEARCH_STATUSES = ["active", "open", "closed"] as const;
export const SPECIALIZATIONS = ["backend", "frontend", "mobile", "data", "devops", "qa", "security"] as const;
