import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import { RequireRole } from "./auth/RequireRole";
import { Landing } from "./features/landing/Landing";
import { FullScreenSpinner } from "./ui/Spinner";

// Порталы и формы грузятся лениво: лендинг открывается быстро, кандидат не скачивает код админки
const AuthPage = lazy(() => import("./features/auth/AuthPage"));
const CandidatePortal = lazy(() => import("./features/candidate/CandidatePortal"));
const EmployerPortal = lazy(() => import("./features/employer/EmployerPortal"));
const AdminPortal = lazy(() => import("./features/admin/AdminPortal"));
const PublicPassport = lazy(() => import("./features/passport/PublicPassport"));

export function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<FullScreenSpinner />}>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<AuthPage mode="login" />} />
          <Route path="/register" element={<AuthPage mode="register" />} />
          <Route path="/passport/:id" element={<PublicPassport />} />
          <Route path="/app/*" element={<RequireRole role="candidate"><CandidatePortal /></RequireRole>} />
          <Route path="/company/*" element={<RequireRole role="employer"><EmployerPortal /></RequireRole>} />
          <Route path="/admin/*" element={<RequireRole role="admin"><AdminPortal /></RequireRole>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
