import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { aiAdminApi } from "../../../api/endpoints";
import type { AiProviderInput, AiProviderUpdate } from "../../../api/types";

const AI = ["admin", "ai-providers"] as const;

export const useAiProviders = () => useQuery({ queryKey: AI, queryFn: aiAdminApi.list });

function useAiMutation<A>(fn: (arg: A) => Promise<unknown>) {
  const client = useQueryClient();
  return useMutation({ mutationFn: fn, onSuccess: () => client.invalidateQueries({ queryKey: AI }) });
}

export const useCreateProvider = () => useAiMutation((body: AiProviderInput) => aiAdminApi.create(body));
export const useUpdateProvider = () =>
  useAiMutation(({ id, body }: { id: string; body: AiProviderUpdate }) => aiAdminApi.update(id, body));
export const useDeleteProvider = () => useAiMutation(aiAdminApi.remove);
export const useActivateProvider = () =>
  useAiMutation((id: string | null) => (id ? aiAdminApi.activate(id) : aiAdminApi.deactivate()));
export const useTestProvider = () => useMutation({ mutationFn: aiAdminApi.test });
