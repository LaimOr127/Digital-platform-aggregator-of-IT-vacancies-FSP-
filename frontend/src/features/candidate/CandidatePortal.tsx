import { Route, Routes } from "react-router";
import { AppShell } from "../../ui/AppShell";
import { FspPage } from "./fsp/FspPage";
import { ProfilePage } from "./ProfilePage";

const NAV = [
  { to: "/app", label: "Профиль", end: true },
  { to: "/app/fsp", label: "ФСП и паспорт навыков" },
];

export default function CandidatePortal() {
  return (
    <AppShell nav={NAV}>
      <Routes>
        <Route index element={<ProfilePage />} />
        <Route path="fsp" element={<FspPage />} />
        <Route path="*" element={<ProfilePage />} />
      </Routes>
    </AppShell>
  );
}
