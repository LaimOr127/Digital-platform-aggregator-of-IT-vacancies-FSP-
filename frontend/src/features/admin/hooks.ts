// Запросы и действия модератора. После любого действия обновляется и журнал аудита.
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { adminApi } from "../../api/endpoints";
import { useCursorList } from "../../api/queries";
import type { CompanyStatus, ModerationAction, UserRole, VacancyStatus } from "../../api/types";

const ADMIN = ["admin"] as const;
const KEYS = {
  companies: [...ADMIN, "companies"],
  vacancies: [...ADMIN, "vacancies"],
  users: [...ADMIN, "users"],
  audit: [...ADMIN, "audit"],
} as const;

export const useCompanies = (status: CompanyStatus) =>
  useCursorList([...KEYS.companies, status], (cursor) => adminApi.companies(status, cursor));

export const useAdminVacancies = (status: VacancyStatus | undefined, withComplaints = false) =>
  useCursorList([...KEYS.vacancies, status ?? "all", withComplaints], (cursor) =>
    adminApi.vacancies(status, withComplaints, cursor),
  );

export const useAdminUsers = (filters: { role?: UserRole; q?: string }) =>
  useCursorList([...KEYS.users, filters], (cursor) => adminApi.users(filters, cursor), { keepPrevious: true });

export const useAudit = (action: string | undefined) =>
  useCursorList([...KEYS.audit, action ?? "all"], (cursor) => adminApi.audit(action, cursor));

/** Мутация модератора: обновляет свой список и журнал аудита. */
function useModeration<A>(mutationFn: (arg: A) => Promise<unknown>, keys: readonly (readonly string[])[]) {
  const client = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: () =>
      Promise.all([...keys, KEYS.audit].map((queryKey) => client.invalidateQueries({ queryKey }))),
  });
}

type Moderation = { id: string; action: ModerationAction; reason: string };

export const useSetCompanyStatus = () =>
  // блокировка компании блокирует её вакансии — обновляем и их
  useModeration(
    (arg: { id: string; status: CompanyStatus; reason: string }) =>
      adminApi.setCompanyStatus(arg.id, arg.status, arg.reason),
    [KEYS.companies, KEYS.vacancies],
  );

export const useModerateVacancy = () =>
  useModeration((arg: Moderation) => adminApi.moderateVacancy(arg.id, arg.action, arg.reason), [KEYS.vacancies]);

export const useModerateUser = () =>
  useModeration((arg: Moderation) => adminApi.moderateUser(arg.id, arg.action, arg.reason), [KEYS.users]);
