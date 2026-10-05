import { CalendarClock, CheckCircle2, Send, X } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router";
import type { EmployerInterview, InterviewStatus } from "../../../api/types";
import { formatDateTime, labels } from "../../../lib/format";
import { interviewTone } from "../../../lib/tones";
import { PageHeader } from "../../../ui/AppShell";
import { Badge } from "../../../ui/Badge";
import { Button, buttonClasses } from "../../../ui/Button";
import { ConfirmDialog } from "../../../ui/ConfirmDialog";
import { CursorListView } from "../../../ui/CursorListView";
import { Segmented } from "../../../ui/Segmented";
import { useAction } from "../../../ui/useAction";
import { InterviewDetails } from "../../interviews/InterviewDetails";
import { useCancelInterview, useInterviews } from "./hooks";
import { CompleteDialog, OfferDialog } from "./ResultDialogs";

type Filter = InterviewStatus | "all";
const FILTERS: { value: Filter; label: string }[] = [
  { value: "all", label: "Все" },
  { value: "invited", label: "Ждут ответа" },
  { value: "scheduled", label: "Назначены" },
  { value: "completed", label: "Состоялись" },
];

export function InterviewsPage() {
  const [filter, setFilter] = useState<Filter>("all");
  const [cancelling, setCancelling] = useState<EmployerInterview | null>(null);
  const [completing, setCompleting] = useState<EmployerInterview | null>(null);
  const [offering, setOffering] = useState<EmployerInterview | null>(null);
  const interviews = useInterviews(filter === "all" ? undefined : filter);
  const cancel = useCancelInterview();
  const run = useAction();

  return (
    <>
      <PageHeader
        title="Собеседования"
        text="Назначьте собеседование по принятому приглашению или отклику (раздел «Приглашения и отклики»), отметьте итог — после успешного собеседования отправьте оффер."
      />
      <div className="mb-6 overflow-x-auto">
        <Segmented label="Статус собеседований" value={filter} options={FILTERS} onChange={setFilter} />
      </div>
      <CursorListView
        query={interviews}
        empty={{
          icon: <CalendarClock className="size-5" />,
          title: "Собеседований пока нет",
          text: "Откройте каталог, выберите подходящего кандидата и пригласите его на собеседование.",
        }}
      >
        {(interview) => (
          <InterviewRow
            key={interview.id}
            interview={interview}
            onCancel={() => setCancelling(interview)}
            onComplete={() => setCompleting(interview)}
            onOffer={() => setOffering(interview)}
          />
        )}
      </CursorListView>
      <ConfirmDialog
        open={cancelling !== null}
        title="Отменить собеседование?"
        confirmLabel="Отменить"
        pending={cancel.isPending}
        onClose={() => setCancelling(null)}
        onConfirm={() =>
          cancelling && run(cancel, { id: cancelling.id, reason: "" }, "Собеседование отменено", () => setCancelling(null))
        }
      >
        Кандидат получит письмо об отмене.
      </ConfirmDialog>
      <CompleteDialog key={`c-${completing?.id}`} interview={completing} onClose={() => setCompleting(null)} />
      <OfferDialog key={`o-${offering?.id}`} interview={offering} onClose={() => setOffering(null)} />
    </>
  );
}

type RowProps = { interview: EmployerInterview; onCancel: () => void; onComplete: () => void; onOffer: () => void };

function InterviewRow({ interview, onCancel, onComplete, onOffer }: RowProps) {
  const active = interview.status === "invited" || interview.status === "scheduled";
  const held = interview.status === "scheduled" && interview.scheduled_at && new Date(interview.scheduled_at) <= new Date();
  const passed = interview.status === "completed" && interview.result === "passed";
  return (
    <article className="flex flex-col gap-4 rounded-2xl border border-line bg-surface p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs text-muted">
            Кандидат #{interview.candidate?.anon_id.slice(0, 6).toUpperCase() ?? "скрыт"} · {interview.vacancy_title}
          </p>
          <h3 className="mt-0.5 font-semibold">{interview.candidate?.title ?? "Должность не указана"}</h3>
          <p className="mt-1 text-xs text-muted">Приглашение от {formatDateTime(interview.created_at)}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge tone={interviewTone[interview.status]}>{labels.interviewStatus[interview.status]}</Badge>
          {interview.result && (
            <Badge tone={interview.result === "passed" ? "accent" : "danger"}>{labels.interviewResult[interview.result]}</Badge>
          )}
        </div>
      </div>
      <InterviewDetails interview={interview} />
      <div className="flex flex-wrap justify-end gap-2">
        {active && (
          <Button variant="ghost" size="sm" onClick={onCancel}>
            <X className="size-3.5" aria-hidden />
            Отменить
          </Button>
        )}
        {held && (
          <Button size="sm" onClick={onComplete}>
            <CheckCircle2 className="size-3.5" aria-hidden />
            Отметить итог
          </Button>
        )}
        {passed && !interview.offer_id && (
          <Button size="sm" onClick={onOffer}>
            <Send className="size-3.5" aria-hidden />
            Отправить оффер
          </Button>
        )}
        {interview.offer_id && (
          <Link to="/company/offers" className={buttonClasses("secondary", "sm")}>
            Оффер отправлен — к офферам
          </Link>
        )}
      </div>
    </article>
  );
}
