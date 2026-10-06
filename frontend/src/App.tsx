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
const CvPage = lazy(() => import("./features/candidate/cv/CvPage"));
const VerifyEmailPage = lazy(() => import("./features/auth/VerifyEmailPage"));
const ForgotPasswordPage = lazy(() => import("./features/auth/ForgotPasswordPage"));
const ResetPasswordPage = lazy(() => import("./features/auth/ResetPasswordPage"));

export function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<FullScreenSpinner />}>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<AuthPage mode="login" />} />
          <Route path="/register" element={<AuthPage mode="register" />} />
          <Route path="/verify-email" element={<VerifyEmailPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route path="/passport/:id" element={<PublicPassport />} />
          <Route path="/cv" element={<RequireRole role="candidate"><CvPage /></RequireRole>} />
          <Route path="/app/*" element={<RequireRole role="candidate"><CandidatePortal /></RequireRole>} />
          <Route path="/company/*" element={<RequireRole role="employer"><EmployerPortal /></RequireRole>} />
          <Route path="/admin/*" element={<RequireRole role="admin"><AdminPortal /></RequireRole>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
