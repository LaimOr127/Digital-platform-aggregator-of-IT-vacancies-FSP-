import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { employerApi } from "../../api/endpoints";
import { useCursorList } from "../../api/queries";
import type { VacancyCreate, VacancyStatus, VacancyUpdate } from "../../api/types";

const VACANCIES = ["vacancies"] as const;
/** тот же запрос, что у индикаторов нового в кабинете (lib/news) */
const NEWS = ["news", "employer"] as const;
/** вакансию пора продлить, если до снятия осталось столько дней или меньше (как на сервере) */
export const RENEW_SOON_DAYS = 3;

export const useCompany = () => useQuery({ queryKey: ["company"], queryFn: employerApi.company });

/** Сколько опубликованных вакансий пора продлить. */
export const useRenewDue = () =>
  useQuery({ queryKey: NEWS, queryFn: employerApi.updates }).data?.renew_due ?? 0;

export const useVacancies = (status: VacancyStatus | undefined) =>
  useCursorList([...VACANCIES, status ?? "all"], (cursor) => employerApi.vacancies(status, cursor));

/** Любое изменение вакансии обновляет все списки (фильтры по статусу). */
function useVacancyMutation<A>(fn: (arg: A) => Promise<unknown>) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => Promise.all([VACANCIES, NEWS].map((queryKey) => client.invalidateQueries({ queryKey }))),
  });
}

export const useCreateVacancy = () => useVacancyMutation((body: VacancyCreate) => employerApi.createVacancy(body));
export const useUpdateVacancy = () =>
  useVacancyMutation(({ id, body }: { id: string; body: VacancyUpdate }) => employerApi.updateVacancy(id, body));
export const usePublishVacancy = () => useVacancyMutation(employerApi.publishVacancy);
export const useCloseVacancy = () => useVacancyMutation(employerApi.closeVacancy);
export const useDeleteVacancy = () => useVacancyMutation(employerApi.deleteVacancy);
