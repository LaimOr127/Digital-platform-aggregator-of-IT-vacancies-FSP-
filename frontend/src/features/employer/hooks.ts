import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { employerApi } from "../../api/endpoints";
import { useCursorList } from "../../api/queries";
import type { VacancyCreate, VacancyStatus, VacancyUpdate } from "../../api/types";

const VACANCIES = ["vacancies"] as const;

export const useCompany = () => useQuery({ queryKey: ["company"], queryFn: employerApi.company });

export const useVacancies = (status: VacancyStatus | undefined) =>
  useCursorList([...VACANCIES, status ?? "all"], (cursor) => employerApi.vacancies(status, cursor));

/** Любое изменение вакансии обновляет все списки (фильтры по статусу). */
function useVacancyMutation<A>(fn: (arg: A) => Promise<unknown>) {
  const client = useQueryClient();
  return useMutation({ mutationFn: fn, onSuccess: () => client.invalidateQueries({ queryKey: VACANCIES }) });
}

export const useCreateVacancy = () => useVacancyMutation((body: VacancyCreate) => employerApi.createVacancy(body));
export const useUpdateVacancy = () =>
  useVacancyMutation(({ id, body }: { id: string; body: VacancyUpdate }) => employerApi.updateVacancy(id, body));
export const usePublishVacancy = () => useVacancyMutation(employerApi.publishVacancy);
export const useCloseVacancy = () => useVacancyMutation(employerApi.closeVacancy);
export const useDeleteVacancy = () => useVacancyMutation(employerApi.deleteVacancy);
