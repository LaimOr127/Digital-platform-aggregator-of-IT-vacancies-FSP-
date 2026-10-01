import { Route, Routes } from "react-router";
import { AppShell } from "../../ui/AppShell";
import { AuditPage } from "./AuditPage";
import { CompaniesPage } from "./CompaniesPage";
import { UsersPage } from "./UsersPage";
import { VacanciesPage } from "./VacanciesPage";

const NAV = [
  { to: "/admin", label: "Компании", end: true },
  { to: "/admin/vacancies", label: "Вакансии" },
  { to: "/admin/users", label: "Пользователи" },
  { to: "/admin/audit", label: "Аудит" },
];

export default function AdminPortal() {
  return (
    <AppShell nav={NAV}>
      <Routes>
        <Route index element={<CompaniesPage />} />
        <Route path="vacancies" element={<VacanciesPage />} />
        <Route path="users" element={<UsersPage />} />
        <Route path="audit" element={<AuditPage />} />
        <Route path="*" element={<CompaniesPage />} />
      </Routes>
    </AppShell>
  );
}
