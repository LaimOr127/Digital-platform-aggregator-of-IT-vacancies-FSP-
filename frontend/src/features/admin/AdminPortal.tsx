import { Route, Routes } from "react-router";
import { useAuth } from "../../auth/AuthProvider";
import { AppShell } from "../../ui/AppShell";
import { AiPage } from "./ai/AiPage";
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
// модели ИИ (ключи API) настраивает только суперадмин
const SUPER_NAV = [...NAV, { to: "/admin/ai", label: "ИИ" }];

export default function AdminPortal() {
  const auth = useAuth();
  const superadmin = auth.status === "authenticated" && auth.user.is_superadmin;
  return (
    <AppShell nav={superadmin ? SUPER_NAV : NAV}>
      <Routes>
        <Route index element={<CompaniesPage />} />
        <Route path="vacancies" element={<VacanciesPage />} />
        <Route path="users" element={<UsersPage />} />
        <Route path="audit" element={<AuditPage />} />
        {superadmin && <Route path="ai" element={<AiPage />} />}
        <Route path="*" element={<CompaniesPage />} />
      </Routes>
    </AppShell>
  );
}
