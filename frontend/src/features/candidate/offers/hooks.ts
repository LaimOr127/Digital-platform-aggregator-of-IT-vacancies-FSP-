import { useMutation, useQueryClient } from "@tanstack/react-query";
import { candidateOffersApi } from "../../../api/endpoints";
import { useCursorList } from "../../../api/queries";
import type { OfferStatus } from "../../../api/types";

const INBOX = ["inbox"] as const;

export const useInbox = (status: OfferStatus | undefined) =>
  useCursorList([...INBOX, status ?? "all"], (cursor) => candidateOffersApi.list(status, cursor));

function useInboxMutation<A>(fn: (arg: A) => Promise<unknown>) {
  const client = useQueryClient();
  return useMutation({ mutationFn: fn, onSuccess: () => client.invalidateQueries({ queryKey: INBOX }) });
}

export const useAcceptOffer = () => useInboxMutation(candidateOffersApi.accept);
export const useDeclineOffer = () =>
  useInboxMutation(({ id, reason }: { id: string; reason: string }) => candidateOffersApi.decline(id, reason));
