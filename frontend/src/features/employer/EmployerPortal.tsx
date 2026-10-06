import { Route, Routes } from "react-router";
import { employerApi } from "../../api/endpoints";
import type { Company } from "../../api/types";
import { labels } from "../../lib/format";
import { companyTone } from "../../lib/tones";
import { Alert } from "../../ui/Alert";
import { useNews } from "../../lib/news";
import { AppShell, type NavItem } from "../../ui/AppShell";
import { Badge } from "../../ui/Badge";
import { ApplicationsPage } from "./applications/ApplicationsPage";
import { CatalogPage } from "./catalog/CatalogPage";
import { CompanyPage } from "./CompanyPage";
import { useCompany, useRenewDue } from "./hooks";
import { InterviewsPage } from "./interviews/InterviewsPage";
import { EmployerOffersPage } from "./offers/EmployerOffersPage";
import { TasksPage } from "./tasks/TasksPage";
import { VacanciesPage } from "./VacanciesPage";

const NAV: NavItem[] = [
  { to: "/company", label: "Вакансии", end: true },
  { to: "/company/catalog", label: "Каталог кандидатов" },
  { to: "/company/applications", label: "Приглашения и отклики" },
  { to: "/company/tasks", label: "Задачи" },
  { to: "/company/interviews", label: "Собеседования" },
  { to: "/company/offers", label: "Офферы" },
  { to: "/company/profile", label: "Компания" },
];

/** Разделы с индикатором нового: где видны их события. */
const NEWS_PATHS = {
  applications: "/company/applications",
  tasks: "/company/tasks",
  interviews: "/company/interviews",
  offers: "/company/offers",
};

export default function EmployerPortal() {
  const company = useCompany();
  const news = useNews("employer", employerApi.updates, NEWS_PATHS);
  const renewDue = useRenewDue();
  // вакансии к продлению держат точку, пока их не продлят
  const nav = NAV.map((item) => ({ ...item, dot: item.to === "/company" ? renewDue > 0 : news[item.to] }));
  return (
    <AppShell nav={nav}>
      {company.data && <CompanyBanner company={company.data} />}
      <Routes>
        <Route index element={<VacanciesPage />} />
        <Route path="catalog" element={<CatalogPage company={company.data} />} />
        <Route path="applications" element={<ApplicationsPage />} />
        <Route path="tasks" element={<TasksPage company={company.data} />} />
        <Route path="interviews" element={<InterviewsPage />} />
        <Route path="profile" element={<CompanyPage />} />
        <Route path="offers" element={<EmployerOffersPage />} />
        <Route path="*" element={<VacanciesPage />} />
      </Routes>
    </AppShell>
  );
}

function CompanyBanner({ company }: { company: Company }) {
  return (
    <div className="mb-8 flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-lg font-semibold">{company.name}</span>
        <Badge tone={companyTone[company.status]}>{labels.companyStatus[company.status]}</Badge>
      </div>
      {company.status === "pending" && (
        <Alert tone="warn">
          Компания на проверке у модератора. Готовьте черновики вакансий — публикация, каталог и приглашения откроются
          сразу после проверки.
        </Alert>
      )}
      {company.status === "blocked" && (
        <Alert>Компания заблокирована модератором: вакансии скрыты, каталог и офферы недоступны.</Alert>
      )}
    </div>
  );
}
