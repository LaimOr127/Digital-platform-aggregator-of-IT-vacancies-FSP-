import { useMutation, useQueryClient } from "@tanstack/react-query";
import { myApplicationsApi } from "../../../api/endpoints";
import { useCursorList } from "../../../api/queries";
import type { ApplicationDirection, BoardFilters } from "../../../api/types";

const MINE = ["my-applications"] as const;
const BOARD = ["vacancy-board"] as const;

export const useMyApplications = (direction: ApplicationDirection) =>
  useCursorList([...MINE, direction], (cursor) => myApplicationsApi.list({ direction }, cursor));

export const useVacancyBoard = (filters: BoardFilters) =>
  useCursorList([...BOARD, filters], (cursor) => myApplicationsApi.vacancies(filters, cursor), { keepPrevious: true });

/** Ответ или отклик меняет и список обращений, и отметки в ленте вакансий. */
function useMineMutation<A>(fn: (arg: A) => Promise<unknown>) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => Promise.all([MINE, BOARD].map((queryKey) => client.invalidateQueries({ queryKey }))),
  });
}

export const useAcceptInvitation = () => useMineMutation(myApplicationsApi.accept);
export const useDeclineInvitation = () =>
  useMineMutation(({ id, reason }: { id: string; reason: string }) => myApplicationsApi.decline(id, reason));
export const useWithdrawResponse = () => useMineMutation(myApplicationsApi.withdraw);
export const useRespond = () =>
  useMineMutation(({ id, message }: { id: string; message: string }) => myApplicationsApi.respond(id, message));
