// Черновик профиля (из ФСП или резюме) -> список предлагаемых изменений формы.
// Кандидат сам выбирает, что перенести: по умолчанию отмечены только пустые поля.
import type { ProfileDraft } from "../../../api/types";
import { labels } from "../../../lib/format";
import type { ProfileFormInput } from "../schemas";

type TextField = "full_name" | "title" | "about" | "city" | "phone" | "telegram" | "contact_email";
type ChoiceField = "grade" | "work_format";
type MoneyField = "salary_min" | "salary_max";
export type DraftField = TextField | ChoiceField | MoneyField;

export type FieldChange = {
  field: DraftField;
  label: string;
  current: string;
  suggested: string;
  /** значение для формы */
  value: string | number;
  /** поле пустое — переносим по умолчанию; заполненное — только если кандидат отметит */
  preselected: boolean;
};

const TEXT_LABELS: Record<DraftField, string> = {
  full_name: "Имя и фамилия",
  title: "Должность",
  grade: "Грейд",
  work_format: "Формат работы",
  city: "Город",
  salary_min: "Зарплата от",
  salary_max: "Зарплата до",
  about: "О себе",
  telegram: "Telegram",
  phone: "Телефон",
  contact_email: "Email для связи",
};

function suggestedValues(draft: ProfileDraft): Partial<Record<DraftField, string | number>> {
  return {
    full_name: draft.full_name ?? undefined,
    title: draft.title ?? undefined,
    grade: draft.grade ?? undefined,
    work_format: draft.work_format ?? undefined,
    city: draft.city ?? undefined,
    salary_min: draft.salary_min ?? undefined,
    salary_max: draft.salary_max ?? undefined,
    about: draft.about ?? undefined,
    telegram: draft.contacts.telegram ?? undefined,
    phone: draft.contacts.phone ?? undefined,
    contact_email: draft.contacts.email ?? undefined,
  };
}

function display(field: DraftField, value: unknown): string {
  if (value === "" || value === null || value === undefined) return "";
  if (field === "grade") return labels.grade[value as keyof typeof labels.grade] ?? String(value);
  if (field === "work_format") return labels.workFormat[value as keyof typeof labels.workFormat] ?? String(value);
  return String(value);
}

export function fieldChanges(draft: ProfileDraft, form: ProfileFormInput): FieldChange[] {
  const changes: FieldChange[] = [];
  for (const [field, value] of Object.entries(suggestedValues(draft)) as [DraftField, string | number | undefined][]) {
    if (value === undefined || value === "") continue;
    const current = display(field, form[field]);
    const suggested = display(field, value);
    if (current === suggested) continue;
    changes.push({ field, label: TEXT_LABELS[field], current, suggested, value, preselected: current === "" });
  }
  return changes;
}

/** Навыки из черновика, которых ещё нет в профиле (в пределах лимита). */
export function newSkills(draft: ProfileDraft, form: ProfileFormInput, max = 50): string[] {
  const have = new Set(form.skills);
  return draft.skills
    .map((s) => s.slug)
    .filter((slug) => !have.has(slug))
    .slice(0, Math.max(0, max - have.size));
}
