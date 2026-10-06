import type { Profile } from "../../api/types";

/** Что влияет на попадание в категории: пункты чек-листа заполненности профиля. */
export const CHECKS: { label: string; done: (p: Profile) => boolean }[] = [
  { label: "Должность", done: (p) => Boolean(p.title) },
  { label: "Грейд", done: (p) => Boolean(p.grade) },
  { label: "Формат работы", done: (p) => p.work_formats.length > 0 },
  { label: "Ожидания по зарплате", done: (p) => Boolean(p.salary_min || p.salary_max) },
  { label: "Минимум 3 навыка", done: (p) => p.skills.length >= 3 },
  { label: "О себе", done: (p) => Boolean(p.about) },
  { label: "Контакт для связи", done: (p) => Boolean(p.contacts.phone || p.contacts.telegram || p.contacts.email) },
];

export function completeness(p: Profile): { percent: number; missing: string[] } {
  const missing = CHECKS.filter((c) => !c.done(p)).map((c) => c.label);
  return { percent: Math.round(((CHECKS.length - missing.length) / CHECKS.length) * 100), missing };
}
