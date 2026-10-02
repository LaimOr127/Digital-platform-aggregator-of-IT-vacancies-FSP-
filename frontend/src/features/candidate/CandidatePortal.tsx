import { Route, Routes } from "react-router";
import { AppShell } from "../../ui/AppShell";
import { FspPage } from "./fsp/FspPage";
import { InsightsPage } from "./insights/InsightsPage";
import { InterviewsInbox } from "./interviews/InterviewsInbox";
import { OffersInbox } from "./offers/OffersInbox";
import { ProfilePage } from "./ProfilePage";

const NAV = [
  { to: "/app", label: "Профиль", end: true },
  { to: "/app/fsp", label: "ФСП и паспорт навыков" },
  { to: "/app/insights", label: "Рост и зарплаты" },
  { to: "/app/interviews", label: "Собеседования" },
  { to: "/app/offers", label: "Офферы" },
];

export default function CandidatePortal() {
  return (
    <AppShell nav={NAV}>
      <Routes>
        <Route index element={<ProfilePage />} />
        <Route path="fsp" element={<FspPage />} />
        <Route path="insights" element={<InsightsPage />} />
        <Route path="interviews" element={<InterviewsInbox />} />
        <Route path="offers" element={<OffersInbox />} />
        <Route path="*" element={<ProfilePage />} />
      </Routes>
    </AppShell>
  );
}
