// Приглашение кандидату: предложение, вилка, способ связи (вакансия — по желанию).
import { z } from "zod";
import type { Company, Vacancy } from "../../../api/types";
import { GRADES, WORK_FORMATS, optionalText, requiredMoney, salaryRangeIssue } from "../../../lib/fields";

export const invitationSchema = z
  .object({
    vacancy_id: z.string().transform((v) => v || null),
    title: z.string().trim().min(3, "Минимум 3 символа").max(160),
    description: z.string().trim().min(10, "Опишите предложение: задачи, команда, условия").max(4000),
    grade: z.enum(GRADES),
    work_format: z.enum(WORK_FORMATS),
    city: optionalText(100),
    salary_min: requiredMoney,
    salary_max: requiredMoney,
    contact_method: z.string().trim().min(3, "Как кандидату связаться с вами").max(300),
  })
  .superRefine(salaryRangeIssue);

export type InvitationFormInput = z.input<typeof invitationSchema>;
export type InvitationFormOutput = z.output<typeof invitationSchema>;

/** Поля предложения: из выбранной вакансии, способ связи — из профиля компании. */
export function invitationDefaults(vacancy: Vacancy | undefined, company: Company | undefined): InvitationFormInput {
  const contact = [company?.contact_telegram, company?.contact_email, company?.contact_phone].filter(Boolean).join(", ");
  return {
    vacancy_id: vacancy?.id ?? "",
    title: vacancy?.title ?? "",
    description: vacancy?.description ?? "",
    grade: vacancy?.grade ?? "middle",
    work_format: vacancy?.work_format ?? "remote",
    city: vacancy?.city ?? "",
    salary_min: vacancy?.salary_min ?? "",
    salary_max: vacancy?.salary_max ?? "",
    contact_method: contact,
  };
}
