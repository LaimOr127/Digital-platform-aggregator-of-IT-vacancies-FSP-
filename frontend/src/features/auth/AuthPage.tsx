import { Link, Navigate, useSearchParams } from "react-router";
import { useAuth } from "../../auth/AuthProvider";
import { safeNext } from "../../auth/portal";
import { FullScreenSpinner } from "../../ui/Spinner";
import { AuthLayout } from "./AuthLayout";
import { LoginForm } from "./LoginForm";
import { RegisterForm } from "./RegisterForm";

export default function AuthPage({ mode }: { mode: "login" | "register" }) {
  const auth = useAuth();
  const [params] = useSearchParams();
  if (auth.status === "loading") return <FullScreenSpinner />;
  // единственная точка редиректа после входа: учитывает ?next= своего портала
  if (auth.status === "authenticated") return <Navigate to={safeNext(params.get("next"), auth.user.role)} replace />;

  const login = mode === "login";
  return (
    <AuthLayout
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
        <RegisterForm initialRole={params.get("role") === "employer" ? "employer" : "candidate"} />
      )}
    </AuthLayout>
  );
}
