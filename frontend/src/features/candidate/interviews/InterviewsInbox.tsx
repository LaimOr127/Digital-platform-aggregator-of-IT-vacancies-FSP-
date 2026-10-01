import { CalendarCheck, CalendarClock } from "lucide-react";
import { useState } from "react";
import type { Interview, InterviewStatus } from "../../../api/types";
import { formatDateTime, labels } from "../../../lib/format";
import { interviewTone } from "../../../lib/tones";
import { PageHeader } from "../../../ui/AppShell";
import { Badge } from "../../../ui/Badge";
import { Button } from "../../../ui/Button";
import { ConfirmDialog } from "../../../ui/ConfirmDialog";
import { CursorListView } from "../../../ui/CursorListView";
import { Field, Textarea } from "../../../ui/form";
import { Segmented } from "../../../ui/Segmented";
import { useAction } from "../../../ui/useAction";
import { InterviewDetails } from "../../interviews/InterviewDetails";
import { useAcceptSlot, useDeclineInterview, useMyInterviews } from "./hooks";

type Filter = InterviewStatus | "all";
const FILTERS: { value: Filter; label: string }[] = [
  { value: "invited", label: "Новые" },
  { value: "scheduled", label: "Назначены" },
  { value: "all", label: "Все" },
];

export function InterviewsInbox() {
  const [filter, setFilter] = useState<Filter>("invited");
  const [declining, setDeclining] = useState<Interview | null>(null);
  const [reason, setReason] = useState("");
  const interviews = useMyInterviews(filter === "all" ? undefined : filter);
  const decline = useDeclineInterview();
  const run = useAction();
  const closeDecline = () => {
    setDeclining(null);
    setReason("");
  };

  return (
    <>
      <PageHeader
        title="Собеседования"
        text="Компании приглашают вас на встречу с руководителем. Выберите удобное время — после успешного собеседования придёт оффер."
      />
      <div className="mb-6">
        <Segmented label="Фильтр собеседований" value={filter} options={FILTERS} onChange={setFilter} />
      </div>
      <CursorListView
        query={interviews}
        empty={{
          icon: <CalendarClock className="size-5" />,
          title: filter === "invited" ? "Новых приглашений нет" : "Собеседований пока нет",
          text: "Заполните профиль и укажите статус «Активно ищу работу» — так компании быстрее вас найдут.",
        }}
      >
        {(interview) => <InterviewCard key={interview.id} interview={interview} onDecline={() => setDeclining(interview)} />}
      </CursorListView>
      <ConfirmDialog
        open={declining !== null}
        title="Отказаться от собеседования?"
        confirmLabel="Отказаться"
        pending={decline.isPending}
        onClose={closeDecline}
        onConfirm={() => declining && run(decline, { id: declining.id, reason: reason.trim() }, "Вы отказались от собеседования", closeDecline)}
      >
        <p className="mb-3">Компания получит уведомление. Повторно пригласить вас она сможет через 30 дней.</p>
        <Field label="Причина (необязательно)">
          <Textarea rows={2} value={reason} maxLength={500} onChange={(e) => setReason(e.target.value)} />
        </Field>
      </ConfirmDialog>
    </>
  );
}

function InterviewCard({ interview, onDecline }: { interview: Interview; onDecline: () => void }) {
  const canAnswer = interview.status === "invited" || interview.status === "scheduled";
  return (
    <article className="flex flex-col gap-4 rounded-2xl border border-line bg-surface p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold">{interview.company_name}</h3>
          <p className="mt-0.5 text-sm text-muted">{interview.vacancy_title}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge tone={interviewTone[interview.status]}>{labels.interviewStatus[interview.status]}</Badge>
          {interview.result && (
            <Badge tone={interview.result === "passed" ? "accent" : "neutral"}>{labels.interviewResult[interview.result]}</Badge>
          )}
          {interview.offer_id && <Badge tone="accent">Есть оффер</Badge>}
        </div>
      </div>
      <InterviewDetails interview={interview} />
      {interview.status === "invited" && <SlotPicker interview={interview} />}
      {canAnswer && (
        <div className="flex justify-end">
          <Button variant="ghost" size="sm" onClick={onDecline}>
            Отказаться
          </Button>
        </div>
      )}
    </article>
  );
}

function SlotPicker({ interview }: { interview: Interview }) {
  const run = useAction();
  const accept = useAcceptSlot();
  const future = interview.slots.filter((s) => new Date(s) > new Date());
  const [slot, setSlot] = useState(future[0] ?? "");
  if (future.length === 0) return <p className="text-sm text-muted">Все предложенные варианты времени уже прошли.</p>;
  return (
    <fieldset className="rounded-xl border border-line p-4">
      <legend className="px-1 text-sm font-medium">Выберите время</legend>
      <div className="flex flex-col gap-2">
        {future.map((s) => (
          <label key={s} className="flex cursor-pointer items-center gap-2 text-sm">
            <input type="radio" name={`slot-${interview.id}`} className="accent-accent" checked={slot === s} onChange={() => setSlot(s)} />
            {formatDateTime(s)} · {interview.duration_minutes} мин
          </label>
        ))}
      </div>
      <Button
        size="sm"
        className="mt-4"
        loading={accept.isPending}
        onClick={() => run(accept, { id: interview.id, slot }, "Время подтверждено — компания получила уведомление")}
      >
        <CalendarCheck className="size-3.5" aria-hidden />
        Подтвердить время
      </Button>
    </fieldset>
  );
}
