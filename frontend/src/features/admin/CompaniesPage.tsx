import { Ban, Building2, Check } from "lucide-react";
import { useState } from "react";
import type { Company, CompanyStatus } from "../../api/types";
import { formatDate, labels } from "../../lib/format";
import { companyTone } from "../../lib/tones";
import { PageHeader } from "../../ui/AppShell";
import { Badge } from "../../ui/Badge";
import { Button } from "../../ui/Button";
import { CursorListView } from "../../ui/CursorListView";
import { Segmented } from "../../ui/Segmented";
import { useAction } from "../../ui/useAction";
import { useCompanies, useSetCompanyStatus } from "./hooks";
import { ReasonDialog } from "./ReasonDialog";

const FILTERS: { value: CompanyStatus; label: string }[] = [
  { value: "pending", label: "На модерации" },
  { value: "approved", label: "Одобрены" },
  { value: "blocked", label: "Заблокированы" },
];

export function CompaniesPage() {
  const [status, setStatus] = useState<CompanyStatus>("pending");
  const [blocking, setBlocking] = useState<Company | null>(null);
  const query = useCompanies(status);

  return (
    <>
      <PageHeader
        title="Компании"
        text="Публиковать вакансии и видеть каталог кандидатов могут только одобренные компании. Блокировка скрывает все вакансии компании."
      />
      <div className="mb-6">
        <Segmented label="Статус компаний" value={status} options={FILTERS} onChange={setStatus} />
      </div>
      <CursorListView
        query={query}
        empty={{ icon: <Building2 className="size-5" />, title: "Список пуст", text: "Компаний с таким статусом нет." }}
      >
        {(company) => <CompanyRow key={company.id} company={company} onBlock={() => setBlocking(company)} />}
      </CursorListView>
      <BlockCompanyDialog key={blocking?.id ?? "none"} company={blocking} onClose={() => setBlocking(null)} />
    </>
  );
}

function CompanyRow({ company, onBlock }: { company: Company; onBlock: () => void }) {
  const run = useAction();
  const setStatus = useSetCompanyStatus();
  const approve = () => run(setStatus, { id: company.id, status: "approved", reason: "" }, `«${company.name}» одобрена`);
  return (
    <article className="flex flex-wrap items-center gap-4 rounded-2xl border border-line bg-surface p-5">
      <div className="min-w-0 flex-1 basis-64">
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

function BlockCompanyDialog({ company, onClose }: { company: Company | null; onClose: () => void }) {
  const run = useAction();
  const setStatus = useSetCompanyStatus();
  return (
    <ReasonDialog
      open={company !== null}
      title={`Заблокировать «${company?.name ?? ""}»?`}
      confirmLabel="Заблокировать"
      pending={setStatus.isPending}
      onClose={onClose}
      onConfirm={(reason) =>
        company &&
        run(setStatus, { id: company.id, status: "blocked", reason }, `«${company.name}» заблокирована`, onClose)
      }
    >
      Все черновики и опубликованные вакансии компании будут заблокированы.
    </ReasonDialog>
  );
}
