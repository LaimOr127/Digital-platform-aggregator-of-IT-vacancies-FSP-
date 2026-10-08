// Выход на контакт со стороны компании: отправленные приглашения и входящие отклики со статусами.
// После контакта — собеседование (по желанию) и оффер.
import { CalendarPlus, Check, Inbox, Undo2, X } from "lucide-react";
import { useState } from "react";
import type { ApplicationDirection, EmployerApplication } from "../../../api/types";
import { daysLeft, formatDate, labels } from "../../../lib/format";
import { applicationTone } from "../../../lib/tones";
import { PageHeader } from "../../../ui/AppShell";
import { Badge } from "../../../ui/Badge";
import { Button } from "../../../ui/Button";
import { ConfirmDialog } from "../../../ui/ConfirmDialog";
import { CursorListView } from "../../../ui/CursorListView";
import { Dialog } from "../../../ui/Dialog";
import { Field, Input } from "../../../ui/form";
import { Segmented } from "../../../ui/Segmented";
import { useAction } from "../../../ui/useAction";
import { ContactsReveal } from "../ContactsReveal";
import { InviteDialog } from "../interviews/InviteDialog";
import {
  useAcceptResponse,
  useApplicationContacts,
  useDeclineResponse,
  useEmployerApplications,
  useWithdrawInvitation,
} from "./hooks";
import { Salary } from "../../../ui/Salary";

const TABS: { value: ApplicationDirection; label: string }[] = [
  { value: "invitation", label: "Приглашения" },
  { value: "response", label: "Отклики" },
];

export function ApplicationsPage() {
  const [tab, setTab] = useState<ApplicationDirection>("invitation");
  const [withdrawing, setWithdrawing] = useState<EmployerApplication | null>(null);
  const [answering, setAnswering] = useState<EmployerApplication | null>(null);
  const [scheduling, setScheduling] = useState<EmployerApplication | null>(null);
  const list = useEmployerApplications(tab);
  const withdraw = useWithdrawInvitation();
  const decline = useDeclineResponse();
  const run = useAction();

  return (
    <>
      <PageHeader
        title="Приглашения и отклики"
        text="Статусы: отправлено → просмотрено → принято или отклонено. Контакты кандидата откроются, когда он примет приглашение или откликнется сам."
      />
      <div className="mb-6">
        <Segmented label="Вид обращений" value={tab} options={TABS} onChange={setTab} />
      </div>
      <CursorListView
        query={list}
        empty={{
          icon: <Inbox className="size-5" />,
          title: tab === "invitation" ? "Приглашений пока нет" : "Откликов пока нет",
          text:
            tab === "invitation"
              ? "Найдите кандидата в каталоге и пригласите его с описанием предложения и вилкой."
              : "Опубликуйте вакансию — кандидаты без приглашений смогут откликнуться сами.",
        }}
      >
        {(item) => (
          <Row
            key={item.id}
            item={item}
            onWithdraw={() => setWithdrawing(item)}
            onAccept={() => setAnswering(item)}
            onDecline={() => run(decline, { id: item.id, reason: "" }, "Отклик отклонён")}
            onSchedule={() => setScheduling(item)}
          />
        )}
      </CursorListView>
      <ConfirmDialog
        open={withdrawing !== null}
        title="Отозвать приглашение?"
        confirmLabel="Отозвать"
        pending={withdraw.isPending}
        onClose={() => setWithdrawing(null)}
        onConfirm={() => withdrawing && run(withdraw, withdrawing.id, "Приглашение отозвано", () => setWithdrawing(null))}
      >
        Кандидат увидит, что приглашение отозвано, и не сможет его принять.
      </ConfirmDialog>
      <AcceptDialog key={answering?.id ?? "none"} item={answering} onClose={() => setAnswering(null)} />
      <InviteDialog key={scheduling?.id ?? "none"} application={scheduling} onClose={() => setScheduling(null)} />
    </>
  );
}

type RowProps = {
  item: EmployerApplication;
  onWithdraw: () => void;
  onAccept: () => void;
  onDecline: () => void;
  onSchedule: () => void;
};

function Row({ item, onWithdraw, onAccept, onDecline, onSchedule }: RowProps) {
  const contacts = useApplicationContacts();
  const open = item.status === "sent" || item.status === "viewed";
  const left = open ? daysLeft(item.expires_at) : null;
  const who = item.candidate
    ? `Кандидат #${item.candidate.anon_id.slice(0, 6).toUpperCase()}${item.candidate.category ? ` · ${item.candidate.category.title}` : ""}`
    : "Кандидат скрыл профиль из каталога";
  return (
    <article className="rounded-2xl border border-line bg-surface p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h3 className="font-semibold">{item.title}</h3>
          <p className="mt-1 text-sm text-muted">{who}</p>
        </div>
        <Badge tone={applicationTone[item.status]}>{labels.applicationStatus[item.status]}</Badge>
      </div>
      <p className="mt-3 text-sm">
        <span className="font-medium tabular"><Salary min={item.salary_min} max={item.salary_max} /></span>
        <span className="text-muted"> · {formatDate(item.created_at)}</span>
        {left !== null && <span className="text-muted"> · на ответ осталось дней: {left}</span>}
      </p>
      {item.message && <p className="mt-2 text-sm text-muted">Письмо кандидата: {item.message}</p>}
      {item.decline_reason && <p className="mt-2 text-sm text-muted">Причина отказа: {item.decline_reason}</p>}
      {item.contacts_available && <ContactsReveal reveal={contacts} id={item.id} note="кандидат согласился их передать" />}
      <div className="mt-4 flex flex-wrap gap-2 border-t border-line pt-4 empty:hidden">
        {item.direction === "invitation" && open && (
          <Button variant="ghost" size="sm" onClick={onWithdraw}>
            <Undo2 className="size-3.5" aria-hidden />
            Отозвать
          </Button>
        )}
        {item.direction === "response" && open && (
          <>
            <Button size="sm" onClick={onAccept}>
              <Check className="size-3.5" aria-hidden />
              Ответить и дать контакт
            </Button>
            <Button variant="ghost" size="sm" onClick={onDecline}>
              <X className="size-3.5" aria-hidden />
              Отклонить
            </Button>
          </>
        )}
        {item.status === "accepted" && (
          <Button variant="secondary" size="sm" onClick={onSchedule}>
            <CalendarPlus className="size-3.5" aria-hidden />
            Назначить собеседование
          </Button>
        )}
      </div>
    </article>
  );
}

/** Ответ на отклик: кандидат получит способ связи с компанией. */
function AcceptDialog({ item, onClose }: { item: EmployerApplication | null; onClose: () => void }) {
  const accept = useAcceptResponse();
  const run = useAction();
  const [contact, setContact] = useState("");
  return (
    <Dialog open={item !== null} title="Ответить на отклик" onClose={onClose} busy={accept.isPending}>
      <Field label="Как кандидату связаться с вами" hint="Telegram, почта или телефон">
        <Input value={contact} onChange={(e) => setContact(e.target.value)} placeholder="Telegram @hr" />
      </Field>
      <div className="mt-6 flex justify-end gap-3">
        <Button variant="ghost" onClick={onClose} disabled={accept.isPending}>
          Отмена
        </Button>
        <Button
          loading={accept.isPending}
          disabled={contact.trim().length < 3}
          onClick={() => item && run(accept, { id: item.id, contact: contact.trim() }, "Кандидат получит ваш контакт", onClose)}
        >
          Отправить
        </Button>
      </div>
    </Dialog>
  );
}
