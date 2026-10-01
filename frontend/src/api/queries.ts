// Запросы, общие для нескольких порталов.
import { useInfiniteQuery, useQuery, type QueryKey } from "@tanstack/react-query";
import { publicApi } from "./endpoints";
import type { Page } from "./types";

export const useSkills = () => useQuery({ queryKey: ["skills"], queryFn: publicApi.skills, staleTime: Infinity });

/** Список с курсорной пагинацией API ({items, next_cursor}) и кнопкой «Показать ещё». */
export function useCursorList<T>(
  queryKey: QueryKey,
  fetchPage: (cursor: string | undefined) => Promise<Page<T>>,
  enabled = true,
) {
  const query = useInfiniteQuery({
    queryKey,
    enabled,
    queryFn: ({ pageParam }) => fetchPage(pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (page) => page.next_cursor ?? undefined,
  });
  return { ...query, items: query.data?.pages.flatMap((page) => page.items) ?? [] };
}
