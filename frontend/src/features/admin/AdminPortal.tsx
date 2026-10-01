import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Building2, Check, Ban } from "lucide-react";
import { useState } from "react";
import { adminApi } from "../../api/endpoints";
import { useCursorList } from "../../api/queries";
import { errorMessage } from "../../api/errors";
import type { Company, CompanyStatus } from "../../api/types";
import { formatDate, labels } from "../../lib/format";
import { companyTone } from "../../lib/tones";
import { Alert } from "../../ui/Alert";
import { AppShell, PageHeader } from "../../ui/AppShell";
import { Badge } from "../../ui/Badge";
import { Button } from "../../ui/Button";
import { Dialog } from "../../ui/Dialog";
import { EmptyState } from "../../ui/EmptyState";
import { Field, Textarea } from "../../ui/form";
import { Segmented } from "../../ui/Segmented";
import { LoadingBlock } from "../../ui/Spinner";
import { useAction } from "../../ui/useAction";

const FILTERS: { value: CompanyStatus; label: string }[] = [
  { value: "pending", label: "На модерации" },
  { value: "approved", label: "Одобрены" },
  { value: "blocked", label: "Заблокированы" },
];

const COMPANIES = ["admin", "companies"] as const;

const useCompanies = (status: CompanyStatus) =>
  useCursorList([...COMPANIES, status], (cursor) => adminApi.companies(status, cursor));

function useSetStatus() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (arg: { id: string; status: CompanyStatus; reason: string }) =>
      adminApi.setCompanyStatus(arg.id, arg.status, arg.reason),
    onSuccess: () => client.invalidateQueries({ queryKey: COMPANIES }),
  });
}

export default function AdminPortal() {
  const [status, setStatus] = useState<CompanyStatus>("pending");
  const [blocking, setBlocking] = useState<Company | null>(null);
  const query = useCompanies(status);
  const items = query.items;

  return (
    <AppShell>
      <PageHeader
        title="Модерация компаний"
        text="Публиковать вакансии могут только одобренные компании. Блокировка скрывает все вакансии компании."
      />
      <div className="mb-6">
        <Segmented label="Статус компаний" value={status} options={FILTERS} onChange={setStatus} />
      </div>
      {query.error && <Alert>{errorMessage(query.error)}</Alert>}
      {!query.data && !query.error && <LoadingBlock />}
      {query.data && items.length === 0 && (
        <EmptyState icon={<Building2 className="size-5" />} title="Список пуст" text="Компаний с таким статусом нет." />
      )}
      <div className="flex flex-col gap-3">
        {items.map((company) => (
          <CompanyRow key={company.id} company={company} onBlock={() => setBlocking(company)} />
        ))}
        {query.hasNextPage && (
          <Button variant="secondary" className="self-center" onClick={() => query.fetchNextPage()} loading={query.isFetchingNextPage}>
            Показать ещё
          </Button>
        )}
      </div>
      {/* key: причина не переносится с одной компании на другую */}
      <BlockDialog key={blocking?.id ?? "none"} company={blocking} onClose={() => setBlocking(null)} />
    </AppShell>
  );
}

function CompanyRow({ company, onBlock }: { company: Company; onBlock: () => void }) {
  const run = useAction();
  const setStatus = useSetStatus();
  const approve = () => run(setStatus, { id: company.id, status: "approved", reason: "" }, `«${company.name}» одобрена`);
  return (
    <article className="flex flex-wrap items-center gap-4 rounded-2xl border border-line bg-surface p-5">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="font-semibold">{company.name}</h3>
          <Badge tone={companyTone[company.status]}>{labels.companyStatus[company.status]}</Badge>
        </div>
        <p className="mt-1 text-sm text-muted">
          ИНН: {company.inn ?? "не указан"} · зарегистрирована {formatDate(company.created_at)}
        </p>
      </div>
      <div className="flex gap-2">
        {company.status !== "approved" && (
          <Button size="sm" onClick={approve} loading={setStatus.isPending}>
            <Check className="size-3.5" aria-hidden />
            Одобрить
          </Button>
        )}
        {company.status !== "blocked" && (
          <Button variant="danger" size="sm" onClick={onBlock}>
            <Ban className="size-3.5" aria-hidden />
            Заблокировать
          </Button>
        )}
      </div>
    </article>
  );
}

function BlockDialog({ company, onClose }: { company: Company | null; onClose: () => void }) {
  const run = useAction();
  const setStatus = useSetStatus();
  const [reason, setReason] = useState("");
  const tooShort = reason.trim().length < 5;

  const submit = () =>
    company &&
    run(setStatus, { id: company.id, status: "blocked", reason: reason.trim() }, `«${company.name}» заблокирована`, onClose);

  return (
    <Dialog
      open={company !== null}
      title={`Заблокировать «${company?.name ?? ""}»?`}
      onClose={onClose}
      busy={setStatus.isPending}
    >
      <p className="mb-4 text-sm text-muted">
        Все черновики и опубликованные вакансии компании будут заблокированы. Причина попадёт в журнал аудита.
      </p>
      <Field label="Причина" hint="Не короче 5 символов">
        <Textarea rows={3} value={reason} onChange={(e) => setReason(e.target.value)} maxLength={500} />
      </Field>
      <div className="mt-6 flex justify-end gap-3">
        <Button variant="ghost" onClick={onClose}>
          Отмена
        </Button>
        <Button variant="danger" onClick={submit} disabled={tooShort} loading={setStatus.isPending}>
          Заблокировать
        </Button>
      </div>
    </Dialog>
  );
}
