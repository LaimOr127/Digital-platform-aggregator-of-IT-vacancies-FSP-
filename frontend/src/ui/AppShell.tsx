// Оболочка кабинетов: шапка с разделом, пользователем и выходом; контент с плавным появлением.
import { LogOut } from "lucide-react";
import { motion } from "motion/react";
import { useState, type ReactNode } from "react";
import { useNavigate } from "react-router";
import { errorMessage } from "../api/errors";
import { useAuth } from "../auth/AuthProvider";
import { PORTALS } from "../auth/portal";
import { Button } from "./Button";
import { Logo } from "./Logo";
import { useToast } from "./Toast";

export function AppShell({ children, actions }: { children: ReactNode; actions?: ReactNode }) {
  const auth = useAuth();
  const navigate = useNavigate();
  const notify = useToast();
  const user = auth.status === "authenticated" ? auth.user : null;

  const [leaving, setLeaving] = useState(false);
  // выход подтверждает сервер; уходим со страницы кабинета до очистки сессии,
  // иначе защита маршрута отправит «гостя» на вход с ?next= текущего кабинета
  const signOut = async () => {
    setLeaving(true);
    try {
      await auth.signOut(() => navigate("/", { replace: true }));
    } catch (err) {
      notify(`Не удалось выйти: ${errorMessage(err)}`, "error");
      setLeaving(false);
    }
  };

  return (
    <div className="min-h-dvh">
      <header className="sticky top-0 z-30 border-b border-line bg-bg/85 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center gap-4 px-4 sm:px-6">
          <Logo to={user ? PORTALS[user.role].path : "/"} />
          {user && <span className="hidden text-sm text-muted sm:inline">/ {PORTALS[user.role].title}</span>}
          <div className="ml-auto flex items-center gap-2">
            {actions}
            {user && <span className="hidden max-w-48 truncate text-sm text-muted md:inline">{user.email}</span>}
            <Button variant="ghost" size="sm" onClick={signOut} loading={leaving} aria-label="Выйти">
              <LogOut className="size-4" aria-hidden />
              <span className="hidden sm:inline">Выйти</span>
            </Button>
          </div>
        </div>
      </header>
      <motion.main
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25, ease: "easeOut" }}
        className="mx-auto max-w-6xl px-4 py-8 sm:px-6"
      >
        {children}
      </motion.main>
    </div>
  );
}

export function PageHeader({ title, text, children }: { title: string; text?: string; children?: ReactNode }) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h1>
        {text && <p className="mt-1.5 max-w-2xl text-sm text-muted">{text}</p>}
      </div>
      {children}
    </div>
  );
}
