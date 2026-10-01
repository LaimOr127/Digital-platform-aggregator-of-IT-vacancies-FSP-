import { useMutation, useQueryClient } from "@tanstack/react-query";
import { myInterviewsApi } from "../../../api/endpoints";
import { useCursorList } from "../../../api/queries";
import type { InterviewStatus } from "../../../api/types";

const MY_INTERVIEWS = ["my-interviews"] as const;

export const useMyInterviews = (status: InterviewStatus | undefined) =>
  useCursorList([...MY_INTERVIEWS, status ?? "all"], (cursor) => myInterviewsApi.list(status, cursor));

function useAnswer<A>(fn: (arg: A) => Promise<unknown>) {
  const client = useQueryClient();
  return useMutation({ mutationFn: fn, onSuccess: () => client.invalidateQueries({ queryKey: MY_INTERVIEWS }) });
}

export const useAcceptSlot = () =>
  useAnswer(({ id, slot }: { id: string; slot: string }) => myInterviewsApi.accept(id, slot));
export const useDeclineInterview = () =>
  useAnswer(({ id, reason }: { id: string; reason: string }) => myInterviewsApi.decline(id, reason));
