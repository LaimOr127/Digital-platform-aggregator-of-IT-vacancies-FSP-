// Вакансии для самостоятельного отклика: дополнение к приглашениям, по соответствию профилю.
import { Briefcase, Building2, Send } from "lucide-react";
import { useState } from "react";
import type { BoardFilters, BoardVacancy, Grade, Specialization } from "../../../api/types";
import { formatSalaryRange, labels, options } from "../../../lib/format";
import { applicationTone } from "../../../lib/tones";
import { useDebounced } from "../../../lib/useDebounced";
import { PageHeader } from "../../../ui/AppShell";
import { Badge } from "../../../ui/Badge";
import { Button } from "../../../ui/Button";
import { CursorListView } from "../../../ui/CursorListView";
import { Dialog } from "../../../ui/Dialog";
import { Field, Input, Select, Textarea } from "../../../ui/form";
import { useAction } from "../../../ui/useAction";
import { MatchPanel } from "../../employer/catalog/MatchPanel";
import { useRespond, useVacancyBoard } from "./hooks";

export function VacancyBoard() {
  const [filters, setFilters] = useState<BoardFilters>({});
  const [query, setQuery] = useState("");
  const q = useDebounced(query.trim(), 300) || undefined;
  const board = useVacancyBoard({ ...filters, q });
  const [responding, setResponding] = useState<BoardVacancy | null>(null);
  const pick = <T extends string>(value: string) => (value || undefined) as T | undefined;

  return (
    <>
      <PageHeader
        title="Вакансии"
        text="Пока приглашений нет, можно откликнуться самостоятельно: компания сразу получит ваше имя и контакты. Вакансии отсортированы по соответствию вашему профилю."
      />
      <div className="mb-6 grid gap-4 sm:grid-cols-3">
        <Field label="Поиск по названию">
          <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Python, аналитик…" />
        </Field>
        <Field label="Специализация">
          <Select
            placeholder="Любая"
            options={options(labels.specialization)}
            value={filters.specialization ?? ""}
            onChange={(e) => setFilters((f) => ({ ...f, specialization: pick<Specialization>(e.target.value) }))}
          />
        </Field>
        <Field label="Грейд">
          <Select
            placeholder="Любой"
            options={options(labels.grade)}
            value={filters.grade ?? ""}
            onChange={(e) => setFilters((f) => ({ ...f, grade: pick<Grade>(e.target.value) }))}
          />
        </Field>
      </div>
      <CursorListView
        query={board}
        className="grid gap-4 md:grid-cols-2"
        empty={{ icon: <Briefcase className="size-5" />, title: "Вакансий не найдено", text: "Измените фильтры." }}
      >
        {(v) => <VacancyRow key={v.id} vacancy={v} onRespond={() => setResponding(v)} />}
      </CursorListView>
      <RespondDialog key={responding?.id ?? "none"} vacancy={responding} onClose={() => setResponding(null)} />
    </>
  );
}

function VacancyRow({ vacancy: v, onRespond }: { vacancy: BoardVacancy; onRespond: () => void }) {
  return (
    <article className="flex flex-col gap-3 rounded-2xl border border-line bg-surface p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-semibold">{v.title}</h3>
          <p className="mt-1 flex items-center gap-1.5 text-sm text-muted">
            <Building2 className="size-3.5" aria-hidden />
            {v.company.name}
          </p>
        </div>
        {v.application_status && (
          <Badge tone={applicationTone[v.application_status]}>{labels.applicationStatus[v.application_status]}</Badge>
        )}
      </div>
      <p className="text-lg font-semibold tabular">{formatSalaryRange(v.salary_min, v.salary_max)}</p>
      <p className="text-sm text-muted">
        {v.specialization && `${labels.specialization[v.specialization]} · `}
        {labels.grade[v.grade]} · {labels.workFormat[v.work_format]}
        {v.city && ` · ${v.city}`}
      </p>
      <MatchPanel match={v.match} />
      {v.skills.length > 0 && <p className="text-xs text-muted">{v.skills.join(" · ")}</p>}
      {!v.application_status && (
        <div className="border-t border-line pt-3">
          <Button size="sm" onClick={onRespond}>
            <Send className="size-3.5" aria-hidden />
            Откликнуться
          </Button>
        </div>
      )}
    </article>
  );
}

function RespondDialog({ vacancy, onClose }: { vacancy: BoardVacancy | null; onClose: () => void }) {
  const respond = useRespond();
  const run = useAction();
  const [message, setMessage] = useState("");
  return (
    <Dialog open={vacancy !== null} title="Отклик на вакансию" onClose={onClose} busy={respond.isPending}>
      <p className="text-sm text-muted">
        «{vacancy?.title}» в компании «{vacancy?.company.name}». Компания сразу получит ваше имя и контакты из профиля.
      </p>
      <Field label="Сопроводительное письмо (необязательно)" className="mt-4">
        <Textarea rows={4} maxLength={2000} value={message} onChange={(e) => setMessage(e.target.value)} />
      </Field>
      <div className="mt-6 flex justify-end gap-3">
        <Button variant="ghost" onClick={onClose} disabled={respond.isPending}>
          Отмена
        </Button>
        <Button
          loading={respond.isPending}
          onClick={() => vacancy && run(respond, { id: vacancy.id, message: message.trim() }, "Отклик отправлен", onClose)}
        >
          Откликнуться
        </Button>
      </div>
    </Dialog>
  );
}
