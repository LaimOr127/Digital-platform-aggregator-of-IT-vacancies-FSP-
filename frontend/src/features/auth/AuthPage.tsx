import { BadgeCheck, EyeOff, Scale } from "lucide-react";
import { motion } from "motion/react";
import { Link, Navigate, useSearchParams } from "react-router";
import { useAuth } from "../../auth/AuthProvider";
import { portalPath } from "../../auth/portal";
import { Logo } from "../../ui/Logo";
import { FullScreenSpinner } from "../../ui/Spinner";
import { LoginForm } from "./LoginForm";
import { RegisterForm } from "./RegisterForm";

const points = [
  { icon: BadgeCheck, text: "Навыки подтверждаются результатами соревнований ФСП" },
  { icon: Scale, text: "Каждое предложение — с зарплатной вилкой" },
  { icon: EyeOff, text: "Контакты открываются только с вашего согласия" },
];

export default function AuthPage({ mode }: { mode: "login" | "register" }) {
  const auth = useAuth();
  const [params] = useSearchParams();
  if (auth.status === "loading") return <FullScreenSpinner />;
  if (auth.status === "authenticated") return <Navigate to={portalPath(auth.user.role)} replace />;

  return (
    <div className="grid min-h-dvh lg:grid-cols-2">
      <aside className="relative hidden flex-col justify-between overflow-hidden border-r border-line bg-surface p-10 lg:flex">
        <div aria-hidden className="absolute -bottom-40 -left-20 size-[32rem] rounded-full bg-accent/10 blur-3xl" />
        <Logo />
        <div className="relative">
          <h2 className="text-3xl font-semibold leading-tight tracking-tight">
            Работодатель приходит к вам
            <br />с вакансией и зарплатой
          </h2>
          <ul className="mt-8 flex flex-col gap-4">
            {points.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-center gap-3 text-muted">
                <Icon className="size-5 shrink-0 text-accent" aria-hidden />
                {text}
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-xs text-muted">Трек Федерации спортивного программирования</p>
      </aside>

      <main className="flex flex-col px-4 py-8 sm:px-10">
        <div className="lg:hidden">
          <Logo />
        </div>
        <motion.div
          key={mode}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="m-auto w-full max-w-md py-10"
        >
          <h1 className="text-2xl font-semibold tracking-tight">{mode === "login" ? "Вход" : "Регистрация"}</h1>
          <p className="mt-2 text-sm text-muted">
            {mode === "login" ? "Нет аккаунта? " : "Уже есть аккаунт? "}
            <Link to={mode === "login" ? "/register" : "/login"} className="font-medium text-accent hover:underline">
              {mode === "login" ? "Зарегистрироваться" : "Войти"}
            </Link>
          </p>
          <div className="mt-8">
            {mode === "login" ? (
              <LoginForm next={params.get("next")} />
            ) : (
              <RegisterForm initialRole={params.get("role") === "employer" ? "employer" : "candidate"} />
            )}
          </div>
        </motion.div>
      </main>
    </div>
  );
}
