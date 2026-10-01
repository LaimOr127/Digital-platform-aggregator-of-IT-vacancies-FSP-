import { Ban, Search, ShieldCheck, Unlock, UserRound } from "lucide-react";
import { useState } from "react";
import type { AdminUser, ModerationAction, UserRole } from "../../api/types";
import { useAuth } from "../../auth/AuthProvider";
import { formatDate, labels } from "../../lib/format";
import { useDebounced } from "../../lib/useDebounced";
import { PageHeader } from "../../ui/AppShell";
import { Badge } from "../../ui/Badge";
import { Button } from "../../ui/Button";
import { CursorListView } from "../../ui/CursorListView";
import { Input } from "../../ui/form";
import { Segmented } from "../../ui/Segmented";
import { useAction } from "../../ui/useAction";
import { useAdminUsers, useModerateUser } from "./hooks";
import { ReasonDialog } from "./ReasonDialog";

type RoleFilter = UserRole | "all";
type Pending = { user: AdminUser; action: ModerationAction };

const ROLES: { value: RoleFilter; label: string }[] = [
  { value: "all", label: "Все" },
  { value: "candidate", label: "Кандидаты" },
  { value: "employer", label: "Работодатели" },
  { value: "admin", label: "Администраторы" },
];

export function UsersPage() {
  const [role, setRole] = useState<RoleFilter>("all");
  const [search, setSearch] = useState("");
  const [pending, setPending] = useState<Pending | null>(null);
  const q = useDebounced(search.trim()) || undefined;
  const query = useAdminUsers({ role: role === "all" ? undefined : role, q });

  return (
    <>
      <PageHeader
        title="Пользователи"
        text="Блокировка закрывает вход и завершает все сессии пользователя. Администраторов блокирует только суперадмин."
      />
      <div className="mb-6 flex flex-col gap-3 lg:flex-row lg:items-center">
        <div className="overflow-x-auto">
          <Segmented label="Роль" value={role} options={ROLES} onChange={setRole} />
        </div>
        <label className="relative lg:ml-auto lg:w-72">
          <span className="sr-only">Поиск по email</span>
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted" aria-hidden />
          <Input
            type="search"
            placeholder="Поиск по email"
            value={search}
            maxLength={100}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </label>
      </div>
      <CursorListView
        query={query}
        empty={{ icon: <UserRound className="size-5" />, title: "Никого не нашли", text: "Измените роль или запрос." }}
      >
        {(user) => <UserRow key={user.id} user={user} onModerate={(action) => setPending({ user, action })} />}
      </CursorListView>
      <ModerateDialog key={pending ? `${pending.user.id}:${pending.action}` : "none"} pending={pending} onClose={() => setPending(null)} />
    </>
  );
}

function UserRow({ user, onModerate }: { user: AdminUser; onModerate: (action: ModerationAction) => void }) {
  const auth = useAuth();
  const me = auth.status === "authenticated" ? auth.user : null;
  // сервер всё равно проверит права; здесь только не показываем заведомо запрещённое
  const canModerate = me !== null && me.id !== user.id && (user.role !== "admin" || me.is_superadmin);
  return (
    <article className="flex flex-wrap items-center gap-4 rounded-2xl border border-line bg-surface p-5">
      <div className="min-w-0 flex-1 basis-64">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="break-all font-semibold">{user.email}</h3>
          <Badge tone="neutral">{labels.role[user.role]}</Badge>
          {user.is_superadmin && <Badge tone="info">Суперадмин</Badge>}
          {!user.is_active && <Badge tone="danger">Заблокирован</Badge>}
        </div>
        <p className="mt-1 flex flex-wrap items-center gap-x-3 text-sm text-muted">
          <span>Зарегистрирован {formatDate(user.created_at)}</span>
          {user.role === "admin" && (
            <span className="inline-flex items-center gap-1">
              <ShieldCheck className="size-3.5" aria-hidden />
              {user.totp_enabled ? "2FA включена" : "2FA не настроена"}
            </span>
          )}
          {me?.id === user.id && <span>Это вы</span>}
        </p>
      </div>
      {canModerate &&
        (user.is_active ? (
          <Button variant="danger" size="sm" onClick={() => onModerate("block")}>
            <Ban className="size-3.5" aria-hidden />
            Заблокировать
          </Button>
        ) : (
          <Button variant="secondary" size="sm" onClick={() => onModerate("unblock")}>
            <Unlock className="size-3.5" aria-hidden />
            Разблокировать
          </Button>
        ))}
    </article>
  );
}

function ModerateDialog({ pending, onClose }: { pending: Pending | null; onClose: () => void }) {
  const run = useAction();
  const moderate = useModerateUser();
  const blocking = pending?.action !== "unblock";
  const email = pending?.user.email ?? "";
  return (
    <ReasonDialog
      open={pending !== null}
      title={blocking ? "Заблокировать пользователя?" : "Разблокировать пользователя?"}
      confirmLabel={blocking ? "Заблокировать" : "Разблокировать"}
      tone={blocking ? "danger" : "primary"}
      pending={moderate.isPending}
      onClose={onClose}
      onConfirm={(reason) =>
        pending &&
        run(
          moderate,
          { id: pending.user.id, action: pending.action, reason },
          blocking ? `${email} заблокирован` : `${email} разблокирован`,
          onClose,
        )
      }
    >
      <p className="mb-2 font-medium text-fg">{email}</p>
      {blocking
        ? "Пользователь не сможет войти, все его активные сессии завершатся."
        : "Пользователь снова сможет войти в систему."}
    </ReasonDialog>
  );
}
