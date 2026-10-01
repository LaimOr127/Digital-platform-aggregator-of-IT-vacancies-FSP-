import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fspApi, passportApi } from "../../../api/endpoints";
import type { FspStatus } from "../../../api/types";

const FSP = ["fsp"] as const;
const PASSPORT = ["passport"] as const;

export const useFspStatus = () => useQuery({ queryKey: FSP, queryFn: fspApi.status });
export const usePassport = () => useQuery({ queryKey: PASSPORT, queryFn: passportApi.active });

/** Ответ со статусом ФСП сразу кладём в кэш; уровень подтверждения меняет и профиль. */
function useFspMutation<A>(fn: (arg: A) => Promise<FspStatus | void>) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: (status) => {
      if (status) client.setQueryData(FSP, status);
      else void client.invalidateQueries({ queryKey: FSP });
      void client.invalidateQueries({ queryKey: ["profile"] });
      void client.invalidateQueries({ queryKey: PASSPORT }); // отвязка отзывает паспорт
    },
  });
}

export function useStartLink() {
  const client = useQueryClient();
  // статус с ожидающей заявкой: при возврате на страницу сразу шаг ввода кода
  return useMutation({ mutationFn: fspApi.link, onSuccess: () => client.invalidateQueries({ queryKey: FSP }) });
}
export const useConfirmLink = () => useFspMutation(fspApi.confirm);
export const useSyncFsp = () => useFspMutation(() => fspApi.sync());
export const useUnlinkFsp = () => useFspMutation(() => fspApi.unlink());

function usePassportMutation<A>(fn: (arg: A) => Promise<unknown>) {
  const client = useQueryClient();
  return useMutation({ mutationFn: fn, onSuccess: () => client.invalidateQueries({ queryKey: PASSPORT }) });
}

export const useIssuePassport = () => usePassportMutation(passportApi.issue);
export const useRevokePassport = () => usePassportMutation(() => passportApi.revoke());
