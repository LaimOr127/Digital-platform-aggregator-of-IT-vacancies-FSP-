import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router";
import { catalogApi, employerApi, employerOffersApi } from "../../../api/endpoints";
import { useCursorList } from "../../../api/queries";
import type { CatalogFilters, OfferCreate, OfferStatus } from "../../../api/types";
import { INTERVIEWS } from "../interviews/hooks";

const OFFERS = ["employer-offers"] as const;

export const DEFAULT_FILTERS: CatalogFilters = { confirmed_only: true };
const FILTER_KEYS = [
  "category", "specialization", "grade", "work_format", "skill", "search_status", "confirmed_only", "fsp_only", "fsp_category",
] as const;
const FLAGS: readonly string[] = ["confirmed_only", "fsp_only"];
/** выбранная потребность: id вакансии, "" — явно без вакансии, нет параметра — первая вакансия */
const NEED = "need";

/** Фильтры и потребность живут в адресе: подборка переживает переход по кабинету и «Назад». */
export function useCatalogUrlState() {
  const [params, setParams] = useSearchParams();
  const parsed = Object.fromEntries(
    FILTER_KEYS.filter((key) => params.has(key)).map((key) => [
      key,
      key === "skill" ? params.getAll(key) : FLAGS.includes(key) ? params.get(key) === "true" : params.get(key),
    ]),
  );
  const filters: CatalogFilters = { ...DEFAULT_FILTERS, ...parsed };
  const need = params.get(NEED);

  const write = (next: CatalogFilters, nextNeed: string | null) => {
    const out = new URLSearchParams();
    for (const [key, value] of Object.entries(next)) {
      for (const item of [value].flat()) if (item !== undefined && item !== "") out.append(key, String(item));
    }
    if (nextNeed !== null) out.set(NEED, nextNeed);
    setParams(out, { replace: true });
  };

  return {
    filters,
    need,
    update: (patch: Partial<CatalogFilters>) => write({ ...filters, ...patch }, need),
    reset: () => write(DEFAULT_FILTERS, need),
    choose: (vacancyId: string) => write(filters, vacancyId),
  };
}

export const useCatalogCategories = (enabled: boolean) =>
  useQuery({ queryKey: ["catalog", "categories"], queryFn: catalogApi.categories, enabled });

export const useFspCategories = () =>
  useQuery({ queryKey: ["catalog", "fsp-categories"], queryFn: catalogApi.fspCategories });

export const useCatalogCandidates = (filters: CatalogFilters, enabled: boolean) =>
  useCursorList(["catalog", "candidates", filters], (cursor) => catalogApi.candidates(filters, cursor), {
    enabled,
    keepPrevious: true,
  });

/** Приглашения и офферы — по опубликованным вакансиям. */
export const useActiveVacancies = () =>
  useQuery({ queryKey: ["vacancies", "active-for-offers"], queryFn: () => employerApi.vacancies("active", undefined) });

/** Описание потребности для подбора: опубликованные вакансии и черновики. */
export const useNeedVacancies = () =>
  useQuery({
    queryKey: ["vacancies", "needs"],
    queryFn: async () =>
      (await employerApi.vacancies(undefined, undefined)).items.filter((v) => v.status === "active" || v.status === "draft"),
  });

export const useEmployerOffers = (status: OfferStatus | undefined) =>
  useCursorList([...OFFERS, status ?? "all"], (cursor) => employerOffersApi.list(status, cursor));

/** Оффер меняет и список офферов, и собеседование, по итогам которого он отправлен. */
function useOfferMutation<A>(fn: (arg: A) => Promise<unknown>) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () =>
      Promise.all([OFFERS, INTERVIEWS].map((queryKey) => client.invalidateQueries({ queryKey }))),
  });
}

export const useSendOffer = () =>
  useOfferMutation(({ body, key }: { body: OfferCreate; key: string }) => employerOffersApi.send(body, key));
export const useWithdrawOffer = () => useOfferMutation(employerOffersApi.withdraw);
export const useOfferContacts = () => useMutation({ mutationFn: employerOffersApi.contacts });
