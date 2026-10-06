import { Route, Routes } from "react-router";
import { candidateApi } from "../../api/endpoints";
import { useNews } from "../../lib/news";
import { AppShell, type NavItem } from "../../ui/AppShell";
import { ApplicationsInbox } from "./applications/ApplicationsInbox";
import { VacancyBoard } from "./applications/VacancyBoard";
import { AssessmentPage } from "./assessment/AssessmentPage";
import { FspPage } from "./fsp/FspPage";
import { InsightsPage } from "./insights/InsightsPage";
import { InterviewsInbox } from "./interviews/InterviewsInbox";
import { OffersInbox } from "./offers/OffersInbox";
import { ProfilePage } from "./ProfilePage";

/** Разделы с индикатором нового: где видны их события. */
const NEWS_PATHS = {
  vacancies: "/app/vacancies",
  invitations: "/app/applications",
  responses: "/app/responses",
  interviews: "/app/interviews",
  offers: "/app/offers",
};

function nav(news: Record<string, boolean>): NavItem[] {
  const item = (to: string, label: string, end?: boolean): NavItem => ({ to, label, end, dot: news[to] });
  return [
    {
      to: "/app",
      label: "Профиль",
      children: [item("/app", "Основная информация", true), item("/app/assessment", "Грейд"), item("/app/fsp", "ФСП")],
    },
    {
      to: "/app/vacancies",
      label: "Поиск работы",
      children: [
        item("/app/vacancies", "Вакансии"),
        item("/app/applications", "Приглашения"),
        item("/app/responses", "Мои отклики"),
        item("/app/interviews", "Собеседования"),
        item("/app/offers", "Офферы"),
        item("/app/insights", "Рост и зарплаты"),
      ],
    },
  ];
}

export default function CandidatePortal() {
  const news = useNews("candidate", candidateApi.updates, NEWS_PATHS);
  return (
    <AppShell nav={nav(news)}>
      <Routes>
        <Route index element={<ProfilePage />} />
        <Route path="assessment" element={<AssessmentPage />} />
        <Route path="applications" element={<ApplicationsInbox direction="invitation" />} />
        <Route path="responses" element={<ApplicationsInbox direction="response" />} />
        <Route path="vacancies" element={<VacancyBoard />} />
        <Route path="fsp" element={<FspPage />} />
        <Route path="insights" element={<InsightsPage />} />
        <Route path="interviews" element={<InterviewsInbox />} />
        <Route path="offers" element={<OffersInbox />} />
        <Route path="*" element={<ProfilePage />} />
      </Routes>
    </AppShell>
  );
}
