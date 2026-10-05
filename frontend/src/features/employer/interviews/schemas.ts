// Формы собеседований: приглашение (1-3 варианта времени), результат, оффер по итогам.
import { z } from "zod";
import { requiredMoney, salaryRangeIssue } from "../../../lib/fields";

const HOUR_MS = 3_600_000;
const MAX_AHEAD_MS = 30 * 24 * HOUR_MS;

/** Значение <input type="datetime-local"> (местное время) -> ISO с часовым поясом. */
export function localToIso(value: string): string {
  return new Date(value).toISOString();
}

const slot = (required: boolean) =>
  z
    .string()
    .trim()
    .refine((v) => !required || v !== "", "Укажите время")
    .refine((v) => v === "" || !Number.isNaN(new Date(v).getTime()), "Некорректная дата")
    .refine((v) => v === "" || new Date(v).getTime() >= Date.now() + HOUR_MS, "Не раньше чем через час")
    .refine((v) => v === "" || new Date(v).getTime() <= Date.now() + MAX_AHEAD_MS, "Не позже чем через 30 дней");

export const inviteSchema = z
  .object({
    slot1: slot(true),
    slot2: slot(false),
    slot3: slot(false),
    duration_minutes: z.coerce.number().int().min(15).max(240),
    format: z.enum(["online", "office"]),
    location: z.string().trim().min(3, "Укажите ссылку или адрес").max(500),
    interviewer: z.string().trim().min(2, "Кто проводит собеседование").max(120),
    message: z.string().trim().max(2000, "Не длиннее 2000 символов"),
  })
  .superRefine((v, ctx) => {
    if (v.format === "online" && !v.location.startsWith("https://")) {
      ctx.addIssue({ code: "custom", path: ["location"], message: "Для онлайн-встречи — ссылка https://" });
    }
  })
  .transform(({ slot1, slot2, slot3, ...rest }) => ({
    ...rest,
    slots: [...new Set([slot1, slot2, slot3].filter(Boolean))].map(localToIso),
  }));

export type InviteFormInput = z.input<typeof inviteSchema>;
export type InviteFormOutput = z.output<typeof inviteSchema>;

export const completeSchema = z.object({
  result: z.enum(["passed", "failed"], "Выберите результат"),
  feedback: z.string().trim().max(2000, "Не длиннее 2000 символов"),
});
export type CompleteForm = z.infer<typeof completeSchema>;

export const offerSchema = z
  .object({
    salary_min: requiredMoney,
    salary_max: requiredMoney,
    message: z.string().trim().max(2000, "Не длиннее 2000 символов"),
  })
  .superRefine(salaryRangeIssue);

export type OfferFormInput = z.input<typeof offerSchema>;
export type OfferFormOutput = z.output<typeof offerSchema>;
