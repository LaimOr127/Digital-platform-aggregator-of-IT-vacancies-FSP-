import { z } from "zod";
import type { AssessmentState, Profile, Specialization, SurveyInput } from "../../../api/types";
import { GRADES, SPECIALIZATIONS, requiredYears } from "../../../lib/fields";

export const surveySchema = z.object({
  specialization: z.enum(SPECIALIZATIONS, "Выберите специализацию"),
  grade: z.enum(GRADES, "Выберите грейд"),
  experience_years: requiredYears,
  industries: z.array(z.string()).max(5, "Не больше 5 отраслей"),
  roles: z.array(z.string()).max(5, "Не больше 5 ролей"),
  skills: z.array(z.string()).min(1, "Выберите хотя бы один навык").max(30, "Не больше 30 навыков"),
});

export type SurveyFormInput = z.input<typeof surveySchema>;
export type SurveyFormOutput = z.output<typeof surveySchema> & SurveyInput;

/** Опрос ещё не пройден — подставляем заявленное в профиле (в т. ч. перенесённое из резюме). */
export function surveyToForm(state: AssessmentState | undefined, profile?: Profile): SurveyFormInput {
  const survey = state?.survey;
  return {
    specialization: (survey?.specialization ?? profile?.specialization ?? "") as Specialization,
    grade: survey?.grade ?? profile?.grade ?? "middle",
    experience_years: survey?.experience_years ?? profile?.experience_years ?? "",
    industries: survey?.industries ?? [],
    roles: survey?.roles ?? profile?.roles ?? [],
    skills: survey?.skills.map((s) => s.slug) ?? profile?.skills.map((s) => s.slug) ?? [],
  };
}
