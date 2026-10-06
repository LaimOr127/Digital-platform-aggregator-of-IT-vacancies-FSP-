import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { candidateApi } from "../../api/endpoints";
import type { ProfileUpdate } from "../../api/types";

export const useProfile = () => useQuery({ queryKey: ["profile"], queryFn: candidateApi.profile });

export function useUpdateProfile() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: ProfileUpdate) => candidateApi.updateProfile(body),
    onSuccess: (profile) => {
      client.setQueryData(["profile"], profile);
      // радар и путь роста считаются от грейда, навыков и ожиданий профиля
      void client.invalidateQueries({ queryKey: ["insights"] });
    },
  });
}
