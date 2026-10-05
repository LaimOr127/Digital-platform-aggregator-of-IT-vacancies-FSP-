// Запросы, общие для нескольких порталов.
import { keepPreviousData, useInfiniteQuery, useQuery, type QueryKey } from "@tanstack/react-query";
import { publicApi } from "./endpoints";
import type { Page } from "./types";

export const useSkills = () => useQuery({ queryKey: ["skills"], queryFn: publicApi.skills, staleTime: Infinity });

type ListOptions = {
  enabled?: boolean;
  /** поиск и фильтры: пока грузится новый запрос, показываем прежний список без мигания */
  keepPrevious?: boolean;
};

/** Список с курсорной пагинацией API ({items, next_cursor}) и кнопкой «Показать ещё». */
export function useCursorList<T>(
  queryKey: QueryKey,
  fetchPage: (cursor: string | undefined) => Promise<Page<T>>,
  { enabled = true, keepPrevious = false }: ListOptions = {},
) {
  const query = useInfiniteQuery({
    queryKey,
    enabled,
    placeholderData: keepPrevious ? keepPreviousData : undefined,
    queryFn: ({ pageParam }) => fetchPage(pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (page) => page.next_cursor ?? undefined,
  });
  return { ...query, items: query.data?.pages.flatMap((page) => page.items) ?? [] };
}

/** Справочники для опроса и фильтров: специализации, отрасли, роли (не меняются в сеансе). */
export const useDictionaries = () =>
  useQuery({ queryKey: ["dictionaries"], queryFn: publicApi.dictionaries, staleTime: Infinity });
