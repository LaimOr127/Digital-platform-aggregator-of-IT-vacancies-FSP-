import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { catalogApi, employerApi, employerOffersApi } from "../../../api/endpoints";
import { useCursorList } from "../../../api/queries";
import type { CatalogFilters, OfferCreate, OfferStatus } from "../../../api/types";
import { INTERVIEWS } from "../interviews/hooks";

const OFFERS = ["employer-offers"] as const;

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
