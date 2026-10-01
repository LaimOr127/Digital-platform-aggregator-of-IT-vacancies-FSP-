// Правила форм входа и регистрации — те же, что проверяет бэк (app/schemas/auth.py).
import { z } from "zod";

export const passwordSchema = z
  .string()
  .min(10, "Минимум 10 символов")
  .max(128, "Максимум 128 символов")
  .refine((v) => !/^\d+$/.test(v) && !/^\p{L}+$/u.test(v), "Нужны буквы и цифры или символы")
  .refine((v) => new Set(v).size >= 5, "Слишком однообразный пароль");

const email = z.email("Некорректный email");

export const loginSchema = z.object({
  email,
  password: z.string().min(1, "Введите пароль"),
});

export const candidateRegisterSchema = z.object({
  email,
  password: passwordSchema,
  full_name: z.string().trim().min(2, "Минимум 2 символа").max(120),
});

export const employerRegisterSchema = z.object({
  email,
  password: passwordSchema,
  company_name: z.string().trim().min(2, "Минимум 2 символа").max(200),
  inn: z
    .string()
    .trim()
    .regex(/^(\d{10}|\d{12})?$/, "ИНН — 10 или 12 цифр")
    .transform((v) => v || undefined)
    .optional(),
});

export type LoginForm = z.infer<typeof loginSchema>;
export type CandidateRegisterForm = z.infer<typeof candidateRegisterSchema>;
export type EmployerRegisterForm = z.input<typeof employerRegisterSchema>;

export const forgotPasswordSchema = z.object({ email });

export const resetPasswordSchema = z
  .object({ password: passwordSchema, confirm: z.string() })
  .refine((v) => v.password === v.confirm, { message: "Пароли не совпадают", path: ["confirm"] });

export type ForgotPasswordForm = z.infer<typeof forgotPasswordSchema>;
export type ResetPasswordForm = z.infer<typeof resetPasswordSchema>;
