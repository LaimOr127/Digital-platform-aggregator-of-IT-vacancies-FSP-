import { z } from "zod";
import type { Vacancy, VacancyCreate } from "../../api/types";
import { GRADES, SPECIALIZATIONS, WORK_FORMATS, optionalText, requiredMoney, salaryRangeIssue } from "../../lib/fields";

export const vacancySchema = z
  .object({
    title: z.string().trim().min(3, "Минимум 3 символа").max(160),
    description: z.string().trim().max(10_000),
    grade: z.enum(GRADES, "Выберите грейд"),
    specialization: z.enum(SPECIALIZATIONS, "Выберите специализацию"),
    work_formats: z.array(z.enum(WORK_FORMATS)).min(1, "Выберите хотя бы один формат"),
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
  specialization: "backend",
  work_formats: ["remote"],
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
    specialization: v.specialization ?? "backend",
    work_formats: v.work_formats,
    city: v.city ?? "",
    salary_min: v.salary_min,
    salary_max: v.salary_max,
    skills: v.skills.map((s) => s.slug),
  };
}
