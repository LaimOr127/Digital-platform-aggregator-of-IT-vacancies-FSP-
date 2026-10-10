// Черновик профиля (из ФСП или резюме) -> список предлагаемых изменений формы.
// Кандидат сам выбирает, что перенести; по умолчанию отмечено всё найденное.
import type { ProfileDraft } from "../../../api/types";
import { formatYears, labels } from "../../../lib/format";
import type { ProfileFormInput } from "../schemas";

export type DraftField =
  | "full_name"
  | "title"
  | "grade"
  | "specialization"
  | "work_formats"
  | "city"
  | "relocation"
  | "education"
  | "salary_min"
  | "salary_max"
  | "experience_years"
  | "about"
  | "telegram"
  | "phone"
  | "contact_email";

/** Заявленные значения: только подсказка для опроса — грейд и категорию подтверждает тест. */
export const CLAIMED_FIELDS: readonly DraftField[] = ["grade", "specialization"];

type DraftValue = string | number | boolean | string[];

export type FieldChange = {
  field: DraftField;
  label: string;
  current: string;
  suggested: string;
  /** значение для формы */
  value: DraftValue;
};

const LABELS: Record<DraftField, string> = {
  full_name: "Имя и фамилия",
  title: "Должность",
  grade: "Грейд",
  specialization: "Специализация",
  work_formats: "Формат работы",
  city: "Город",
  relocation: "Готовность к переезду",
  education: "Образование",
  salary_min: "Зарплата от",
  salary_max: "Зарплата до",
  experience_years: "Стаж",
  about: "О себе",
  telegram: "Telegram",
  phone: "Телефон",
  contact_email: "Email для связи",
};

function suggestedValues(draft: ProfileDraft): Partial<Record<DraftField, DraftValue | null | undefined>> {
  return {
    full_name: draft.full_name,
    title: draft.title,
    grade: draft.grade,
    specialization: draft.specialization,
    work_formats: draft.work_formats.length ? draft.work_formats : undefined,
    city: draft.city,
    relocation: draft.relocation ?? undefined,
    education: draft.education,
    salary_min: draft.salary_min,
    salary_max: draft.salary_max,
    experience_years: draft.experience_years,
    about: draft.about,
    telegram: draft.contacts.telegram,
    phone: draft.contacts.phone,
    contact_email: draft.contacts.email,
  };
}

function display(field: DraftField, value: unknown): string {
  if (value === "" || value === null || value === undefined || (Array.isArray(value) && !value.length)) return "";
  if (field === "work_formats" && Array.isArray(value))
    return value.map((v) => labels.workFormat[v as keyof typeof labels.workFormat] ?? v).join(", ");
  if (field === "relocation") return value ? "готов(а) к переезду" : "";
  if (field === "experience_years") return formatYears(Number(value));
  const dictionary = { grade: labels.grade, specialization: labels.specialization, education: labels.education }[
    field as "grade" | "specialization" | "education"
  ] as Record<string, string> | undefined;
  return dictionary?.[String(value)] ?? String(value);
}

export function fieldChanges(draft: ProfileDraft, form: ProfileFormInput): FieldChange[] {
  const changes: FieldChange[] = [];
  for (const [field, value] of Object.entries(suggestedValues(draft)) as [DraftField, DraftValue | null | undefined][]) {
    if (value === undefined || value === null || value === "") continue;
    const current = display(field, form[field]);
    const suggested = display(field, value);
    if (current === suggested) continue;
    changes.push({ field, label: LABELS[field], current, suggested, value });
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
