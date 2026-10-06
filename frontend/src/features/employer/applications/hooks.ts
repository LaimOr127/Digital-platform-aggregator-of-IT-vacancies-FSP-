import { useMutation, useQueryClient } from "@tanstack/react-query";
import { applicationsApi } from "../../../api/endpoints";
import { useCursorList } from "../../../api/queries";
import type { ApplicationDirection, InvitationInput } from "../../../api/types";

const APPLICATIONS = ["employer-applications"] as const;

export const useEmployerApplications = (direction: ApplicationDirection) =>
  useCursorList([...APPLICATIONS, direction], (cursor) => applicationsApi.list({ direction }, cursor));

function useApplicationMutation<A>(fn: (arg: A) => Promise<unknown>) {
  const client = useQueryClient();
  return useMutation({ mutationFn: fn, onSuccess: () => client.invalidateQueries({ queryKey: APPLICATIONS }) });
}

export const useSendInvitation = () => useApplicationMutation((body: InvitationInput) => applicationsApi.invite(body));
export const useAcceptResponse = () =>
  useApplicationMutation(({ id, contact }: { id: string; contact: string }) => applicationsApi.accept(id, contact));
export const useDeclineResponse = () =>
  useApplicationMutation(({ id, reason }: { id: string; reason: string }) => applicationsApi.decline(id, reason));
export const useWithdrawInvitation = () => useApplicationMutation(applicationsApi.withdraw);
export const useApplicationContacts = () => useMutation({ mutationFn: applicationsApi.contacts });
