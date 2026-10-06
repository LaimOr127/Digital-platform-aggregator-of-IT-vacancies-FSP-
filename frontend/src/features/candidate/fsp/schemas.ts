import { z } from "zod";

export const athleteIdSchema = z.object({
  athlete_id: z
    .string()
    .trim()
    .toUpperCase()
    .regex(/^[A-Z0-9-]{3,32}$/, "ID ФСП: буквы, цифры и дефис, например FSP-24001"),
});

export const codeSchema = z.object({
  code: z.string().trim().regex(/^\d{6}$/, "Код из 6 цифр"),
});

export type AthleteIdForm = z.infer<typeof athleteIdSchema>;
export type CodeForm = z.infer<typeof codeSchema>;
