import { z } from "zod";
import type { Profile, ProfileUpdate } from "../../api/types";
import { GRADES, SEARCH_STATUSES, WORK_FORMATS, optionalEnum, optionalMoney, optionalText, optionalYears, salaryRangeIssue } from "../../lib/fields";

export const profileSchema = z
  .object({
    full_name: z.string().trim().min(2, "Минимум 2 символа").max(120),
    title: optionalText(120),
    about: optionalText(4000),
    grade: optionalEnum(GRADES),
    work_format: optionalEnum(WORK_FORMATS),
    city: optionalText(100),
    salary_min: optionalMoney,
    salary_max: optionalMoney,
    phone: optionalText(32),
    telegram: optionalText(64),
    contact_email: optionalText(254).refine(
      (v) => v === null || z.email().safeParse(v).success,
      "Некорректный email",
    ),
    skills: z.array(z.string()).max(50, "Не больше 50 навыков"),
    experience_years: optionalYears,
    roles: z.array(z.string()).max(5, "Не больше 5 ролей"),
    soft_skills: z.array(z.string()).max(8, "Не больше 8 качеств"),
    is_hidden: z.boolean(),
    search_status: z.enum(SEARCH_STATUSES),
  })
  .superRefine(salaryRangeIssue);

export type ProfileFormInput = z.input<typeof profileSchema>;
export type ProfileFormOutput = z.output<typeof profileSchema>;

export function profileToForm(p: Profile): ProfileFormInput {
  return {
    full_name: p.full_name ?? "",
    title: p.title ?? "",
    about: p.about ?? "",
    grade: p.grade ?? "",
    work_format: p.work_format ?? "",
    city: p.city ?? "",
    salary_min: p.salary_min ?? "",
    salary_max: p.salary_max ?? "",
    phone: p.contacts.phone ?? "",
    telegram: p.contacts.telegram ?? "",
    contact_email: p.contacts.email ?? "",
    skills: p.skills.map((s) => s.slug),
    experience_years: p.experience_years ?? "",
    roles: p.roles,
    soft_skills: p.soft_skills,
    is_hidden: p.is_hidden,
    search_status: p.search_status,
  };
}

export function formToUpdate(f: ProfileFormOutput): ProfileUpdate {
  const { phone, telegram, contact_email, ...rest } = f;
  return { ...rest, contacts: { phone, telegram, email: contact_email } };
}
