// Черновик профиля (из ФСП или резюме) -> список предлагаемых изменений формы.
// Кандидат сам выбирает, что перенести: по умолчанию отмечены только пустые поля.
import type { ProfileDraft } from "../../../api/types";
import { labels } from "../../../lib/format";
import type { ProfileFormInput } from "../schemas";

type TextField = "full_name" | "title" | "about" | "city" | "phone" | "telegram" | "contact_email";
type ChoiceField = "grade" | "work_format";
type MoneyField = "salary_min" | "salary_max" | "experience_years";
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
  experience_years: "Опыт, лет",
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
    experience_years: draft.experience_years ?? undefined,
    about: draft.about ?? undefined,
    telegram: draft.contacts.telegram ?? undefined,
    phone: draft.contacts.phone ?? undefined,
    contact_email: draft.contacts.email ?? undefined,
  };
}

function display(field: DraftField, value: unknown): string {
  if (value === "" || value === null || value === undefined) return "";
  // в форме форматов может быть несколько, в черновике — один
  if (Array.isArray(value)) return value.map((v) => display(field, v)).join(", ");
  if (field === "grade") return labels.grade[value as keyof typeof labels.grade] ?? String(value);
  if (field === "work_format") return labels.workFormat[value as keyof typeof labels.workFormat] ?? String(value);
  return String(value);
}

export function fieldChanges(draft: ProfileDraft, form: ProfileFormInput): FieldChange[] {
  const changes: FieldChange[] = [];
  for (const [field, value] of Object.entries(suggestedValues(draft)) as [DraftField, string | number | undefined][]) {
    if (value === undefined || value === "") continue;
    const current = display(field, field === "work_format" ? form.work_formats : form[field]);
    const suggested = display(field, value);
    if (current === suggested) continue;
    changes.push({ field, label: TEXT_LABELS[field], current, suggested, value, preselected: current === "" });
  }
  return changes;
}

export type DraftLists = { skills: string[]; custom_skills: string[]; roles: string[]; soft_skills: string[] };

/** Значения из черновика, которых ещё нет в профиле (в пределах лимита). */
function added(suggested: string[], have: string[], max: number): string[] {
  const present = new Set(have);
  return suggested.filter((v) => !present.has(v)).slice(0, Math.max(0, max - present.size));
}

/** Навыки, роли и софт-скиллы, которые черновик добавит к профилю. */
export function newLists(draft: ProfileDraft, form: ProfileFormInput): DraftLists {
  return {
    skills: added(
      draft.skills.map((s) => s.slug),
      form.skills,
      50,
    ),
    // навыки, которых нет в справочнике, переносятся как свои
    custom_skills: added(draft.unknown_skills, form.custom_skills, 20),
    roles: added(draft.roles, form.roles, 5),
    soft_skills: added(draft.soft_skills, form.soft_skills, 10),
  };
}
