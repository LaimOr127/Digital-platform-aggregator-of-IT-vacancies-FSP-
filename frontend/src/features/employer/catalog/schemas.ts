import { z } from "zod";
import { requiredMoney, salaryRangeIssue } from "../../../lib/fields";

export const offerSchema = z
  .object({
    vacancy_id: z.string().min(1, "Выберите вакансию"),
    salary_min: requiredMoney,
    salary_max: requiredMoney,
    message: z.string().trim().max(2000, "Не длиннее 2000 символов"),
  })
  .superRefine(salaryRangeIssue);

export type OfferFormInput = z.input<typeof offerSchema>;
export type OfferFormOutput = z.output<typeof offerSchema>;
