import { z } from "zod";
import type { Vacancy, VacancyCreate } from "../../api/types";
import { GRADES, WORK_FORMATS, optionalText, requiredMoney, salaryRangeIssue } from "../../lib/fields";

export const vacancySchema = z
  .object({
    title: z.string().trim().min(3, "Минимум 3 символа").max(160),
    description: z.string().trim().max(10_000),
    grade: z.enum(GRADES, "Выберите грейд"),
    work_format: z.enum(WORK_FORMATS, "Выберите формат"),
    city: optionalText(100),
    salary_min: requiredMoney,
    salary_max: requiredMoney,
    skills: z.array(z.string()).max(30, "Не больше 30 навыков"),
  })
  .superRefine(salaryRangeIssue);

export type VacancyFormInput = z.input<typeof vacancySchema>;
export type VacancyFormOutput = z.output<typeof vacancySchema> & VacancyCreate;

export const emptyVacancy: VacancyFormInput = {
  title: "",
  description: "",
  grade: "middle",
  work_format: "remote",
  city: "",
  salary_min: "",
  salary_max: "",
  skills: [],
};

export function vacancyToForm(v: Vacancy): VacancyFormInput {
  return {
    title: v.title,
    description: v.description,
    grade: v.grade,
    work_format: v.work_format,
    city: v.city ?? "",
    salary_min: v.salary_min,
    salary_max: v.salary_max,
    skills: v.skills.map((s) => s.slug),
  };
}
