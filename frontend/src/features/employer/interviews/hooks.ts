import { useMutation, useQueryClient } from "@tanstack/react-query";
import { interviewsApi } from "../../../api/endpoints";
import { useCursorList } from "../../../api/queries";
import type { InterviewInvite, InterviewResult, InterviewStatus } from "../../../api/types";

export const INTERVIEWS = ["employer-interviews"] as const;

export const useInterviews = (status: InterviewStatus | undefined) =>
  useCursorList([...INTERVIEWS, status ?? "all"], (cursor) => interviewsApi.list(status, cursor));

function useInterviewMutation<A>(fn: (arg: A) => Promise<unknown>) {
  const client = useQueryClient();
  return useMutation({ mutationFn: fn, onSuccess: () => client.invalidateQueries({ queryKey: INTERVIEWS }) });
}

export const useInvite = () => useInterviewMutation((body: InterviewInvite) => interviewsApi.invite(body));
export const useCancelInterview = () =>
  useInterviewMutation(({ id, reason }: { id: string; reason: string }) => interviewsApi.cancel(id, reason));
export const useCompleteInterview = () =>
  useInterviewMutation(({ id, result, feedback }: { id: string; result: InterviewResult; feedback: string }) =>
    interviewsApi.complete(id, result, feedback),
  );
