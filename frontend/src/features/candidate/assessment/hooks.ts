import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { assessmentApi } from "../../../api/endpoints";
import type { AssessmentState, Grade, SurveyInput } from "../../../api/types";

export const ASSESSMENT = ["assessment"] as const;

export const useAssessment = () => useQuery({ queryKey: ASSESSMENT, queryFn: assessmentApi.state });

/** Опрос и тест меняют категорию и профиль: обновляются и они, и радар зарплат. */
function useInvalidateCandidate() {
  const client = useQueryClient();
  return () =>
    Promise.all(
      [ASSESSMENT, ["profile"], ["insights"]].map((queryKey) => client.invalidateQueries({ queryKey })),
    );
}

export function useSaveSurvey() {
  const client = useQueryClient();
  const invalidate = useInvalidateCandidate();
  return useMutation({
    mutationFn: (body: SurveyInput) => assessmentApi.saveSurvey(body),
    onSuccess: (state: AssessmentState) => {
      client.setQueryData(ASSESSMENT, state);
      return invalidate();
    },
  });
}

export function useStartAttempt() {
  const invalidate = useInvalidateCandidate();
  return useMutation({ mutationFn: (grade: Grade) => assessmentApi.start(grade), onSuccess: invalidate });
}

export function useSubmitAttempt() {
  const invalidate = useInvalidateCandidate();
  return useMutation({
    mutationFn: ({ id, responses }: { id: string; responses: (string | null)[] }) =>
      assessmentApi.submit(id, responses),
    onSuccess: invalidate,
  });
}
