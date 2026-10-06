// Индикаторы нового: точка на разделе, если там что-то произошло после последнего просмотра.
// И время событий, и отметки «просмотрено» хранит сервер — точки одинаковы на всех устройствах
// аккаунта: открыл раздел на телефоне — на ноутбуке точка погаснет при ближайшем опросе
// (раз в 15 секунд) или сразу при возврате на вкладку.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { useLocation } from "react-router";

const REFRESH_MS = 15_000;

type Updates = { seen?: Record<string, string> } & object;

/**
 * paths: раздел -> путь страницы, где видны его события. Возвращает путь -> есть ли новое.
 * Открытый раздел отмечается просмотренным при входе, при новых событиях, пока он открыт,
 * и при уходе — свои действия на странице точку не зажигают.
 */
export function useNews<K extends string>(
  name: string,
  fetchUpdates: () => Promise<Updates>,
  markSeen: (section: K) => Promise<unknown>,
  paths: Record<K, string>,
): Record<string, boolean> {
  const client = useQueryClient();
  const queryKey = ["news", name];
  const { pathname } = useLocation();
  const updates = useQuery({ queryKey, queryFn: fetchUpdates, refetchInterval: REFRESH_MS });
  const mark = useMutation({
    mutationFn: markSeen,
    // точка гаснет сразу, не дожидаясь ответа и следующего опроса
    onMutate: (section: K) =>
      client.setQueryData<Updates>(queryKey, (data) =>
        data ? { ...data, seen: { ...data.seen, [section]: new Date().toISOString() } } : data,
      ),
    // точное время отметки — серверное (часы устройства могут спешить или отставать)
    onSettled: () => client.invalidateQueries({ queryKey }),
  });
  const sections = Object.keys(paths) as K[];
  const time = (value: unknown) => (typeof value === "string" ? Date.parse(value) : 0);
  const latest = (section: K) => time((updates.data as Record<string, unknown> | undefined)?.[section]);
  const seenAt = (section: K) => time(updates.data?.seen?.[section]);
  const current = sections.find((section) => paths[section] === pathname);
  const currentLatest = current ? latest(current) : 0;

  useEffect(() => {
    if (!current || !updates.data) return;
    // mutate у TanStack Query стабилен между рендерами — в зависимости его не добавляем
    mark.mutate(current);
    return () => mark.mutate(current);
  }, [current, currentLatest, Boolean(updates.data)]);

  return Object.fromEntries(sections.map((section) => [paths[section], latest(section) > seenAt(section)]));
}
