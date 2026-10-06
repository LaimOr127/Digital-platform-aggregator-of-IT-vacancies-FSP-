// Индикаторы нового: точка на разделе, если там что-то произошло после последнего просмотра.
// Сервер отдаёт время последнего события раздела, браузер помнит, когда раздел открывали.
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useLocation } from "react-router";
import { useAuth } from "../auth/AuthProvider";

const REFRESH_MS = 60_000;

type Seen = Record<string, number>;

function load(key: string): Seen {
  try {
    return JSON.parse(localStorage.getItem(key) ?? "{}") as Seen;
  } catch {
    return {};
  }
}

function save(key: string, value: Seen) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // хранилище недоступно (приватный режим): точки просто не запоминаются между визитами
  }
}

/**
 * paths: раздел -> путь страницы, где видны его события. Возвращает путь -> есть ли новое.
 * Открытый раздел считается просмотренным: и при входе, и при уходе — свои действия на странице
 * точку не зажигают.
 */
export function useNews<K extends string>(
  name: string,
  fetchUpdates: () => Promise<object>,
  paths: Record<K, string>,
): Record<string, boolean> {
  const auth = useAuth();
  const storageKey = `news:${name}:${auth.status === "authenticated" ? auth.user.id : "anon"}`;
  const { pathname } = useLocation();
  const updates = useQuery({ queryKey: ["news", name], queryFn: fetchUpdates, refetchInterval: REFRESH_MS });
  const [seen, setSeen] = useState<Seen>(() => load(storageKey));
  const sections = Object.keys(paths) as K[];
  const latest = (section: K) => {
    const value = (updates.data as Record<string, unknown> | undefined)?.[section];
    return typeof value === "string" ? Date.parse(value) : 0;
  };
  const current = sections.find((section) => paths[section] === pathname);
  const currentLatest = current ? latest(current) : 0;

  useEffect(() => {
    if (!current) return;
    const mark = () =>
      setSeen((prev) => {
        const next = { ...prev, [current]: Math.max(Date.now(), currentLatest) };
        save(storageKey, next);
        return next;
      });
    mark();
    return mark;
  }, [current, currentLatest, storageKey]);

  return Object.fromEntries(sections.map((section) => [paths[section], latest(section) > (seen[section] ?? 0)]));
}
