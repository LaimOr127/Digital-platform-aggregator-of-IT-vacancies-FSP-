import { z } from "zod";
import type { AssessmentState, Specialization, SurveyInput } from "../../../api/types";
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

export function surveyToForm(state: AssessmentState | undefined): SurveyFormInput {
  const survey = state?.survey;
  return {
    specialization: (survey?.specialization ?? "") as Specialization,
    grade: survey?.grade ?? "middle",
    experience_years: survey?.experience_years ?? "",
    industries: survey?.industries ?? [],
    roles: survey?.roles ?? [],
    skills: survey?.skills.map((s) => s.slug) ?? [],
  };
}
