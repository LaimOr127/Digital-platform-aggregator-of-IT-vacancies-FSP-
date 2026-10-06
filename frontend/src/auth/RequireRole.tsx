import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router";
import type { UserRole } from "../api/types";
import { FullScreenSpinner } from "../ui/Spinner";
import { useAuth } from "./AuthProvider";
import { portalPath } from "./portal";

/** Маршрут только для роли role: гость -> вход, чужая роль -> свой кабинет. */
export function RequireRole({ role, children }: { role: UserRole; children: ReactNode }) {
  const auth = useAuth();
  const location = useLocation();
  if (auth.status === "loading") return <FullScreenSpinner />;
  if (auth.status === "anonymous" && auth.signedOut) return <Navigate to="/" replace />;
  if (auth.status === "anonymous") {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?next=${next}`} replace />;
  }
  if (auth.user.role !== role) return <Navigate to={portalPath(auth.user.role)} replace />;
  return <>{children}</>;
}
