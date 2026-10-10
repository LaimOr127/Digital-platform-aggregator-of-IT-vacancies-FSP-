import { z } from "zod";
import type { Profile, ProfileUpdate } from "../../api/types";
import {
  EDUCATION_LEVELS,
  GRADES,
  SEARCH_STATUSES,
  SPECIALIZATIONS,
  WORK_FORMATS,
  optionalEnum,
  optionalMoney,
  optionalText,
  optionalYears,
  salaryRangeIssue,
} from "../../lib/fields";

export const profileSchema = z
  .object({
    full_name: z.string().trim().min(2, "Минимум 2 символа").max(120),
    title: optionalText(120),
    about: optionalText(4000),
    grade: optionalEnum(GRADES),
    specialization: optionalEnum(SPECIALIZATIONS),
    work_formats: z.array(z.enum(WORK_FORMATS)).max(3),
    city: optionalText(100),
    relocation: z.boolean(),
    education: optionalEnum(EDUCATION_LEVELS),
    salary_min: optionalMoney,
    salary_max: optionalMoney,
    phone: optionalText(32),
    telegram: optionalText(64),
    contact_email: optionalText(254).refine(
      (v) => v === null || z.email().safeParse(v).success,
      "Некорректный email",
    ),
    skills: z.array(z.string()).max(50, "Не больше 50 навыков"),
    custom_skills: z.array(z.string()).max(20, "Не больше 20 своих навыков"),
    experience_years: optionalYears,
    roles: z.array(z.string()).max(5, "Не больше 5 ролей"),
    soft_skills: z.array(z.string()).max(10, "Не больше 10 качеств"),
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
    specialization: p.specialization ?? "",
    work_formats: p.work_formats,
    city: p.city ?? "",
    relocation: p.relocation,
    education: p.education ?? "",
    salary_min: p.salary_min ?? "",
    salary_max: p.salary_max ?? "",
    phone: p.contacts.phone ?? "",
    telegram: p.contacts.telegram ?? "",
    contact_email: p.contacts.email ?? "",
    skills: p.skills.map((s) => s.slug),
    custom_skills: p.custom_skills,
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
