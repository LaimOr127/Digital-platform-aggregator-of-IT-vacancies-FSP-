// Приглашения от компаний и мои отклики: условия, компания, способ связи, статусы.
import { Building2, Check, Inbox, Undo2, X } from "lucide-react";
import { useState } from "react";
import type { Application, ApplicationDirection } from "../../../api/types";
import { daysLeft, formatDate, formatSalaryRange, labels } from "../../../lib/format";
import { applicationTone } from "../../../lib/tones";
import { PageHeader } from "../../../ui/AppShell";
import { Badge } from "../../../ui/Badge";
import { Button } from "../../../ui/Button";
import { ConfirmDialog } from "../../../ui/ConfirmDialog";
import { CursorListView } from "../../../ui/CursorListView";
import { Segmented } from "../../../ui/Segmented";
import { useAction } from "../../../ui/useAction";
import { useAcceptInvitation, useDeclineInvitation, useMyApplications, useWithdrawResponse } from "./hooks";
import { ExpandableText } from "../../../ui/ExpandableText";

const TABS: { value: ApplicationDirection; label: string }[] = [
  { value: "invitation", label: "Приглашения" },
  { value: "response", label: "Мои отклики" },
];

export function ApplicationsInbox() {
  const [tab, setTab] = useState<ApplicationDirection>("invitation");
  const [accepting, setAccepting] = useState<Application | null>(null);
  const list = useMyApplications(tab);
  const accept = useAcceptInvitation();
  const decline = useDeclineInvitation();
  const withdraw = useWithdrawResponse();
  const run = useAction();

  return (
    <>
      <PageHeader
        title="Приглашения и отклики"
        text="Компании приходят к вам сами — с описанием предложения и зарплатной вилкой. Имя и контакты они увидят, только если вы примете приглашение."
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
              ? "Пройдите тест в разделе «Тест» — так работодатели найдут вас в своей категории."
              : "Откликнитесь на вакансию в разделе «Вакансии», если не хотите ждать приглашения.",
        }}
      >
        {(item) => (
          <Row
            key={item.id}
            item={item}
            onAccept={() => setAccepting(item)}
            onDecline={() => run(decline, { id: item.id, reason: "" }, "Приглашение отклонено")}
            onWithdraw={() => run(withdraw, item.id, "Отклик отозван")}
          />
        )}
      </CursorListView>
      <ConfirmDialog
        open={accepting !== null}
        title="Принять приглашение?"
        confirmLabel="Принять и передать контакты"
        tone="primary"
        pending={accept.isPending}
        onClose={() => setAccepting(null)}
        onConfirm={() => accepting && run(accept, accepting.id, "Приглашение принято — компания свяжется с вами", () => setAccepting(null))}
      >
        Компания «{accepting?.company.name}» получит ваше имя и контакты из профиля.
      </ConfirmDialog>
    </>
  );
}

type RowProps = { item: Application; onAccept: () => void; onDecline: () => void; onWithdraw: () => void };

function Row({ item, onAccept, onDecline, onWithdraw }: RowProps) {
  const open = item.status === "sent" || item.status === "viewed";
  const left = open ? daysLeft(item.expires_at) : null;
  return (
    <article className="rounded-2xl border border-line bg-surface p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold">{item.title}</h3>
          <p className="mt-1 flex items-center gap-1.5 text-sm text-muted">
            <Building2 className="size-3.5" aria-hidden />
            {item.company.name}
            {item.company.industry && ` · ${item.company.industry}`}
          </p>
        </div>
        <Badge tone={applicationTone[item.status]}>{labels.applicationStatus[item.status]}</Badge>
      </div>
      <p className="mt-3 text-lg font-semibold tabular">{formatSalaryRange(item.salary_min, item.salary_max)}</p>
      <p className="mt-1 text-sm text-muted">
        {labels.grade[item.grade]} · {labels.workFormat[item.work_format]}
        {item.city && ` · ${item.city}`} · {formatDate(item.created_at)}
        {left !== null && ` · на ответ осталось дней: ${left}`}
      </p>
      {item.description && <p className="mt-3 whitespace-pre-line text-sm leading-relaxed">{item.description}</p>}
      {item.company.description && (
        <ExpandableText className="mt-2 text-sm" label="О компании" text={item.company.description} />
      )}
      {item.contact_method && (
        <p className="mt-3 rounded-xl border border-accent/30 bg-accent/5 px-4 py-3 text-sm">
          <span className="text-muted">Как связаться: </span>
          <span className="font-medium">{item.contact_method}</span>
        </p>
      )}
      {item.direction === "response" && item.message && (
        <p className="mt-2 text-sm text-muted">Ваше письмо: {item.message}</p>
      )}
      {item.decline_reason && <p className="mt-2 text-sm text-muted">Причина отказа: {item.decline_reason}</p>}
      {open && (
        <div className="mt-4 flex flex-wrap gap-2 border-t border-line pt-4">
          {item.direction === "invitation" ? (
            <>
              <Button size="sm" onClick={onAccept}>
                <Check className="size-3.5" aria-hidden />
                Принять
              </Button>
              <Button variant="ghost" size="sm" onClick={onDecline}>
                <X className="size-3.5" aria-hidden />
                Отклонить
              </Button>
            </>
          ) : (
            <Button variant="ghost" size="sm" onClick={onWithdraw}>
              <Undo2 className="size-3.5" aria-hidden />
              Отозвать отклик
            </Button>
          )}
        </div>
      )}
    </article>
  );
}
