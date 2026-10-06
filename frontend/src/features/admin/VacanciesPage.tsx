import { Ban, Briefcase, RotateCcw } from "lucide-react";
import { useState } from "react";
import type { AdminVacancy, ModerationAction, VacancyStatus } from "../../api/types";
import { formatDate, formatSalaryRange, labels } from "../../lib/format";
import { vacancyTone } from "../../lib/tones";
import { PageHeader } from "../../ui/AppShell";
import { Badge } from "../../ui/Badge";
import { Button } from "../../ui/Button";
import { CursorListView } from "../../ui/CursorListView";
import { Segmented } from "../../ui/Segmented";
import { useAction } from "../../ui/useAction";
import { useAdminVacancies, useModerateVacancy } from "./hooks";
import { ReasonDialog } from "./ReasonDialog";

type Filter = VacancyStatus | "all" | "complaints";
type Pending = { vacancy: AdminVacancy; action: ModerationAction };

const FILTERS: { value: Filter; label: string }[] = [
  { value: "active", label: "Опубликованы" },
  { value: "blocked", label: "Заблокированы" },
  { value: "draft", label: "Черновики" },
  { value: "closed", label: "Закрыты" },
  { value: "complaints", label: "С жалобами" },
  { value: "all", label: "Все" },
];

const COPY: Record<ModerationAction, { title: string; confirm: string; text: string; done: string }> = {
  block: {
    title: "Заблокировать вакансию?",
    confirm: "Заблокировать",
    text: "Вакансия исчезнет из выдачи кандидатов. Работодатель увидит статус «Заблокирована».",
    done: "Вакансия заблокирована",
  },
  unblock: {
    title: "Разблокировать вакансию?",
    confirm: "Разблокировать",
    text: "Вакансия вернётся работодателю черновиком: он проверит её и опубликует заново.",
    done: "Вакансия разблокирована и возвращена в черновики",
  },
};

export function VacanciesPage() {
  const [filter, setFilter] = useState<Filter>("active");
  const [pending, setPending] = useState<Pending | null>(null);
  const status = filter === "all" || filter === "complaints" ? undefined : filter;
  const query = useAdminVacancies(status, filter === "complaints");

  return (
    <>
      <PageHeader
        title="Вакансии"
        text="Блокируйте вакансии с нарушениями: скрытая зарплата в тексте, дискриминация, сбор персональных данных."
      />
      <div className="mb-6 overflow-x-auto">
        <Segmented label="Статус вакансий" value={filter} options={FILTERS} onChange={setFilter} />
      </div>
      <CursorListView
        query={query}
        empty={{ icon: <Briefcase className="size-5" />, title: "Список пуст", text: "Вакансий с таким статусом нет." }}
      >
        {(vacancy) => (
          <VacancyRow key={vacancy.id} vacancy={vacancy} onModerate={(action) => setPending({ vacancy, action })} />
        )}
      </CursorListView>
      <ModerateDialog key={pending ? `${pending.vacancy.id}:${pending.action}` : "none"} pending={pending} onClose={() => setPending(null)} />
    </>
  );
}

function VacancyRow({ vacancy, onModerate }: { vacancy: AdminVacancy; onModerate: (action: ModerationAction) => void }) {
  return (
    <article className="flex flex-wrap items-center gap-4 rounded-2xl border border-line bg-surface p-5">
      <div className="min-w-0 flex-1 basis-64">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="font-semibold">{vacancy.title}</h3>
          <Badge tone={vacancyTone[vacancy.status]}>{labels.vacancyStatus[vacancy.status]}</Badge>
          {vacancy.complaints > 0 && <Badge tone="danger">Жалоб: {vacancy.complaints}</Badge>}
        </div>
        <p className="mt-1 text-sm text-muted">
          {vacancy.company_name} · {labels.grade[vacancy.grade]} · {formatSalaryRange(vacancy.salary_min, vacancy.salary_max)} ·
          создана {formatDate(vacancy.created_at)}
        </p>
        {vacancy.complaint_notes.length > 0 && (
          <ul className="mt-2 flex flex-col gap-1 text-sm" aria-label="Жалобы кандидатов">
            {vacancy.complaint_notes.map((note, i) => (
              <li key={i}>— {note}</li>
            ))}
          </ul>
        )}
      </div>
      {vacancy.status === "blocked" ? (
        <Button variant="secondary" size="sm" onClick={() => onModerate("unblock")}>
          <RotateCcw className="size-3.5" aria-hidden />
          Разблокировать
        </Button>
      ) : (
        <Button variant="danger" size="sm" onClick={() => onModerate("block")}>
          <Ban className="size-3.5" aria-hidden />
          Заблокировать
        </Button>
      )}
    </article>
  );
}

function ModerateDialog({ pending, onClose }: { pending: Pending | null; onClose: () => void }) {
  const run = useAction();
  const moderate = useModerateVacancy();
  const copy = COPY[pending?.action ?? "block"];
  return (
    <ReasonDialog
      open={pending !== null}
      title={copy.title}
      confirmLabel={copy.confirm}
      tone={pending?.action === "unblock" ? "primary" : "danger"}
      pending={moderate.isPending}
      onClose={onClose}
      onConfirm={(reason) =>
        pending && run(moderate, { id: pending.vacancy.id, action: pending.action, reason }, copy.done, onClose)
      }
    >
      <p className="mb-2 font-medium text-fg">«{pending?.vacancy.title}»</p>
      {copy.text}
    </ReasonDialog>
  );
}
