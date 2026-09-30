import type { UserRole } from "../api/types";

export const PORTALS: Record<UserRole, { path: string; title: string }> = {
  candidate: { path: "/app", title: "Кабинет кандидата" },
  employer: { path: "/company", title: "Кабинет компании" },
  admin: { path: "/admin", title: "Модерация" },
};

export const portalPath = (role: UserRole) => PORTALS[role].path;

/** Куда вернуть после входа: только внутренний путь своего портала (без open redirect). */
export function safeNext(next: string | null, role: UserRole): string {
  const home = portalPath(role);
  if (!next || !next.startsWith("/") || next.startsWith("//")) return home;
  return next === home || next.startsWith(`${home}/`) ? next : home;
}
