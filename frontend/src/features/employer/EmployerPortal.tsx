import { Briefcase, Plus } from "lucide-react";
import { AnimatePresence } from "motion/react";
import { useState } from "react";
import { errorMessage } from "../../api/errors";
import { useSkills } from "../../api/queries";
import type { Company, Vacancy, VacancyStatus } from "../../api/types";
import { labels } from "../../lib/format";
import { companyTone } from "../../lib/tones";
import { Alert } from "../../ui/Alert";
import { AppShell, PageHeader } from "../../ui/AppShell";
import { Badge } from "../../ui/Badge";
import { Button } from "../../ui/Button";
import { Dialog } from "../../ui/Dialog";
import { EmptyState } from "../../ui/EmptyState";
import { Segmented } from "../../ui/Segmented";
import { Spinner } from "../../ui/Spinner";
import { useToast } from "../../ui/Toast";
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

export default function EmployerPortal() {
  const company = useCompany();
  const skills = useSkills();
  const [filter, setFilter] = useState<Filter>("all");
  const [editing, setEditing] = useState<Editing>(null);
  const [deleting, setDeleting] = useState<Vacancy | null>(null);
  const blocked = company.data?.status === "blocked";

  return (
    <AppShell>
      {company.data && <CompanyBanner company={company.data} />}
      <PageHeader title="Вакансии" text="Вакансия живёт 14 дней после публикации — затем продлите её или закройте.">
        <Button onClick={() => setEditing({ vacancy: null })} disabled={blocked || !skills.data}>
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
      <DeleteDialog vacancy={deleting} onClose={() => setDeleting(null)} />
    </AppShell>
  );
}

function CompanyBanner({ company }: { company: Company }) {
  return (
    <div className="mb-8 flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-lg font-semibold">{company.name}</span>
        <Badge tone={companyTone[company.status]}>{labels.companyStatus[company.status]}</Badge>
      </div>
      {company.status === "pending" && (
        <Alert tone="warn">
          Компания на модерации. Готовьте черновики вакансий — опубликовать их можно будет сразу после проверки.
        </Alert>
      )}
      {company.status === "blocked" && (
        <Alert>Компания заблокирована модератором: вакансии скрыты, создавать и менять их нельзя.</Alert>
      )}
    </div>
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
  if (query.error) return <Alert>{errorMessage(query.error)}</Alert>;
  if (!query.data) {
    return (
      <div className="flex justify-center py-16 text-muted">
        <Spinner className="size-6" />
      </div>
    );
  }
  const items = query.data.pages.flatMap((page) => page.items);
  if (items.length === 0) {
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
        {items.map((v) => (
          <VacancyCard key={v.id} vacancy={v} canPublish={canPublish} onEdit={onEdit} onDelete={onDelete} />
        ))}
      </AnimatePresence>
      {query.hasNextPage && (
        <Button variant="secondary" className="self-center" onClick={() => query.fetchNextPage()} loading={query.isFetchingNextPage}>
          Показать ещё
        </Button>
      )}
    </div>
  );
}

function DeleteDialog({ vacancy, onClose }: { vacancy: Vacancy | null; onClose: () => void }) {
  const notify = useToast();
  const remove = useDeleteVacancy();
  const confirm = () =>
    vacancy &&
    remove.mutate(vacancy.id, {
      onSuccess: () => {
        notify("Вакансия удалена");
        onClose();
      },
      onError: (err) => notify(errorMessage(err), "error"),
    });
  return (
    <Dialog open={vacancy !== null} title="Удалить вакансию?" onClose={onClose}>
      <p className="text-sm text-muted">
        «{vacancy?.title}» будет удалена без возможности восстановления. Если вакансия просто неактуальна — лучше закройте её.
      </p>
      <div className="mt-6 flex justify-end gap-3">
        <Button variant="ghost" onClick={onClose}>
          Отмена
        </Button>
        <Button variant="danger" onClick={confirm} loading={remove.isPending}>
          Удалить
        </Button>
      </div>
    </Dialog>
  );
}
