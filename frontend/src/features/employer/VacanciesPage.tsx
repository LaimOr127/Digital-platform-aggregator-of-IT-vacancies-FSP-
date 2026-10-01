import { Briefcase, Plus } from "lucide-react";
import { AnimatePresence } from "motion/react";
import { useState } from "react";
import { errorMessage } from "../../api/errors";
import { useSkills } from "../../api/queries";
import type { Vacancy, VacancyStatus } from "../../api/types";
import { Alert } from "../../ui/Alert";
import { PageHeader } from "../../ui/AppShell";
import { Button } from "../../ui/Button";
import { Dialog } from "../../ui/Dialog";
import { EmptyState } from "../../ui/EmptyState";
import { Segmented } from "../../ui/Segmented";
import { LoadingBlock } from "../../ui/Spinner";
import { useAction } from "../../ui/useAction";
import { useCompany, useDeleteVacancy, useVacancies } from "./hooks";
import { VacancyCard } from "./VacancyCard";
import { VacancyForm } from "./VacancyForm";

type Filter = VacancyStatus | "all";

const FILTERS: { value: Filter; label: string }[] = [
  { value: "all", label: "Все" },
  { value: "draft", label: "Черновики" },
  { value: "active", label: "Опубликованы" },
  { value: "closed", label: "Закрыты" },
  { value: "blocked", label: "Заблокированы" },
];

type Editing = { vacancy: Vacancy | null } | null;

export function VacanciesPage() {
  const company = useCompany();
  const skills = useSkills();
  const [filter, setFilter] = useState<Filter>("all");
  const [editing, setEditing] = useState<Editing>(null);
  const [deleting, setDeleting] = useState<Vacancy | null>(null);
  const blocked = company.data?.status === "blocked";
  const loadError = company.error ?? skills.error;

  return (
    <>
      {loadError && (
        <div className="mb-6">
          <Alert>Не удалось загрузить данные компании: {errorMessage(loadError)}</Alert>
        </div>
      )}
      <PageHeader title="Вакансии" text="Вакансия живёт 14 дней после публикации — затем продлите её или закройте.">
        <Button onClick={() => setEditing({ vacancy: null })} disabled={blocked || !skills.data || !company.data}>
          <Plus className="size-4" aria-hidden />
          Новая вакансия
        </Button>
      </PageHeader>
      <div className="mb-6">
        <Segmented label="Статус вакансий" value={filter} options={FILTERS} onChange={setFilter} />
      </div>
      <VacancyList
        status={filter === "all" ? undefined : filter}
        canPublish={company.data?.status === "approved"}
        onCreate={blocked ? undefined : () => setEditing({ vacancy: null })}
        onEdit={(vacancy) => setEditing({ vacancy })}
        onDelete={setDeleting}
      />

      <Dialog
        open={editing !== null}
        title={editing?.vacancy ? "Редактирование вакансии" : "Новая вакансия"}
        onClose={() => setEditing(null)}
        wide
      >
        {editing && skills.data && (
          <VacancyForm vacancy={editing.vacancy} skills={skills.data} onDone={() => setEditing(null)} />
        )}
      </Dialog>
      <DeleteDialog key={deleting?.id ?? "none"} vacancy={deleting} onClose={() => setDeleting(null)} />
    </>
  );
}

type ListProps = {
  status: VacancyStatus | undefined;
  canPublish: boolean;
  onCreate?: () => void;
  onEdit: (v: Vacancy) => void;
  onDelete: (v: Vacancy) => void;
};

function VacancyList({ status, canPublish, onCreate, onEdit, onDelete }: ListProps) {
  const query = useVacancies(status);
  // ошибка без данных — вместо списка; ошибка догрузки — рядом с уже загруженным списком
  if (query.error && !query.data) return <Alert>{errorMessage(query.error)}</Alert>;
  if (!query.data) return <LoadingBlock />;
  if (query.items.length === 0) {
    return (
      <EmptyState
        icon={<Briefcase className="size-5" />}
        title={status ? "Здесь пока пусто" : "Вакансий пока нет"}
        text="Создайте черновик: название, грейд, стек и обязательная зарплатная вилка."
        action={onCreate && <Button onClick={onCreate}>Создать вакансию</Button>}
      />
    );
  }
  return (
    <div className="flex flex-col gap-4">
      <AnimatePresence initial={false}>
        {query.items.map((v) => (
          <VacancyCard key={v.id} vacancy={v} canPublish={canPublish} onEdit={onEdit} onDelete={onDelete} />
        ))}
      </AnimatePresence>
      {query.error && <Alert>{errorMessage(query.error)}</Alert>}
      {query.hasNextPage && (
        <Button variant="secondary" className="self-center" onClick={() => query.fetchNextPage()} loading={query.isFetchingNextPage}>
          Показать ещё
        </Button>
      )}
    </div>
  );
}

function DeleteDialog({ vacancy, onClose }: { vacancy: Vacancy | null; onClose: () => void }) {
  const run = useAction();
  const remove = useDeleteVacancy();
  return (
    <Dialog open={vacancy !== null} title="Удалить вакансию?" onClose={onClose} busy={remove.isPending}>
      <p className="text-sm text-muted">
        «{vacancy?.title}» будет удалена без возможности восстановления. Если вакансия просто неактуальна — лучше закройте её.
      </p>
      <div className="mt-6 flex justify-end gap-3">
        <Button variant="ghost" onClick={onClose} disabled={remove.isPending}>
          Отмена
        </Button>
        <Button
          variant="danger"
          onClick={() => vacancy && run(remove, vacancy.id, "Вакансия удалена", onClose)}
          loading={remove.isPending}
        >
          Удалить
        </Button>
      </div>
    </Dialog>
  );
}
