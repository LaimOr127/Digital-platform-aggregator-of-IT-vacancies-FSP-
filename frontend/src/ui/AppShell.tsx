// Оболочка кабинетов: шапка с разделом, пользователем и выходом; контент с плавным появлением.
import { LogOut } from "lucide-react";
import { motion } from "motion/react";
import { useState, type ReactNode } from "react";
import { Link, useLocation } from "react-router";
import { errorMessage } from "../api/errors";
import { useAuth } from "../auth/AuthProvider";
import { PORTALS } from "../auth/portal";
import { Button } from "./Button";
import { Logo } from "./Logo";
import { useToast } from "./Toast";

export type NavItem = {
  to: string;
  label: string;
  end?: boolean;
  /** что-то новое в разделе (как непрочитанное сообщение) */
  dot?: boolean;
  /** подразделы: показываются второй строкой, пока раздел открыт */
  children?: NavItem[];
};

const isActive = (item: NavItem, pathname: string): boolean =>
  item.children
    ? item.children.some((child) => isActive(child, pathname))
    : item.end
      ? pathname === item.to
      : pathname === item.to || pathname.startsWith(`${item.to}/`);

const hasDot = (item: NavItem): boolean => Boolean(item.dot || item.children?.some(hasDot));

export function AppShell({ children, actions, nav }: { children: ReactNode; actions?: ReactNode; nav?: NavItem[] }) {
  const auth = useAuth();
  const notify = useToast();
  const user = auth.status === "authenticated" ? auth.user : null;
  const { pathname } = useLocation();
  const group = nav?.find((item) => item.children && isActive(item, pathname));

  const [leaving, setLeaving] = useState(false);
  // выход подтверждает сервер; после выхода защита маршрута сама уведёт на главную
  const signOut = async () => {
    setLeaving(true);
    try {
      await auth.signOut();
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
        {nav && (
          <nav aria-label="Разделы кабинета" className="mx-auto flex max-w-6xl gap-1 overflow-x-auto px-4 sm:px-6">
            {nav.map((item) => (
              <TabLink key={item.to} item={item} active={isActive(item, pathname)} />
            ))}
          </nav>
        )}
        {group?.children && (
          <nav
            aria-label={`Подразделы: ${group.label}`}
            className="mx-auto flex max-w-6xl gap-2 overflow-x-auto px-4 py-2.5 sm:px-6"
          >
            {group.children.map((item) => (
              <SubTabLink key={item.to} item={item} active={isActive(item, pathname)} />
            ))}
          </nav>
        )}
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

function Dot({ show }: { show: boolean }) {
  if (!show) return null;
  return (
    <>
      <span className="ml-1.5 inline-block size-2 rounded-full bg-accent align-middle" aria-hidden />
      <span className="sr-only">, есть новое</span>
    </>
  );
}

function TabLink({ item, active }: { item: NavItem; active: boolean }) {
  return (
    <Link
      to={item.to}
      aria-current={active ? "page" : undefined}
      className={`-mb-px whitespace-nowrap border-b-2 px-3 py-2.5 text-sm transition-colors ${
        active ? "border-accent text-fg" : "border-transparent text-muted hover:text-fg"
      }`}
    >
      {item.label}
      <Dot show={hasDot(item)} />
    </Link>
  );
}

function SubTabLink({ item, active }: { item: NavItem; active: boolean }) {
  return (
    <Link
      to={item.to}
      aria-current={active ? "page" : undefined}
      className={`whitespace-nowrap rounded-full px-3 py-1 text-sm transition-colors ${
        active ? "bg-surface-2 text-fg" : "text-muted hover:text-fg"
      }`}
    >
      {item.label}
      <Dot show={hasDot(item)} />
    </Link>
  );
}

export function PageHeader({ title, text, children }: { title: string; text?: string; children?: ReactNode }) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-bold uppercase tracking-tight sm:text-3xl">{title}</h1>
        {text && <p className="mt-1.5 max-w-2xl text-sm text-muted">{text}</p>}
      </div>
      {children}
    </div>
  );
}
