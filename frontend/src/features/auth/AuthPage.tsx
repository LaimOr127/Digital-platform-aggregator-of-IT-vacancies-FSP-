import { useState } from "react";
import { Link, Navigate, useSearchParams } from "react-router";
import { useAuth } from "../../auth/AuthProvider";
import { safeNext } from "../../auth/portal";
import { FullScreenSpinner } from "../../ui/Spinner";
import { AuthLayout } from "./AuthLayout";
import { LoginForm } from "./LoginForm";
import { RegisterForm, type Role } from "./RegisterForm";

export default function AuthPage({ mode }: { mode: "login" | "register" }) {
  const auth = useAuth();
  const [params] = useSearchParams();
  const [role, setRole] = useState<Role>(params.get("role") === "employer" ? "employer" : "candidate");
  if (auth.status === "loading") return <FullScreenSpinner />;
  // единственная точка редиректа после входа: учитывает ?next= своего портала
  if (auth.status === "authenticated") return <Navigate to={safeNext(params.get("next"), auth.user.role)} replace />;

  const login = mode === "login";
  return (
    <AuthLayout
      audience={role}
      title={login ? "Вход" : "Регистрация"}
      subtitle={
        <>
          {login ? "Нет аккаунта? " : "Уже есть аккаунт? "}
          <Link to={login ? "/register" : "/login"} className="font-medium text-accent hover:underline">
            {login ? "Зарегистрироваться" : "Войти"}
          </Link>
        </>
      }
    >
      {login ? (
        <LoginForm />
      ) : (
        <RegisterForm role={role} onRoleChange={setRole} />
      )}
    </AuthLayout>
  );
}
