// Запуск мутации с уведомлением об успехе или ошибке — один шаблон для всех порталов.
import type { UseMutationResult } from "@tanstack/react-query";
import { useCallback } from "react";
import { errorMessage } from "../api/errors";
import { useToast } from "./Toast";

export function useAction() {
  const notify = useToast();
  return useCallback(
    <D, A>(mutation: UseMutationResult<D, Error, A>, arg: NoInfer<A>, success: string, after?: () => void) =>
      mutation.mutate(arg, {
        onSuccess: () => {
          notify(success);
          after?.();
        },
        onError: (err) => notify(errorMessage(err), "error"),
      }),
    [notify],
  );
}
