import { CalendarPlus, Users } from "lucide-react";
import { useState } from "react";
import { errorMessage } from "../../../api/errors";
import type { CandidateCard, CatalogFilters, Company } from "../../../api/types";
import { Alert } from "../../../ui/Alert";
import { PageHeader } from "../../../ui/AppShell";
import { Button } from "../../../ui/Button";
import { CursorListView } from "../../../ui/CursorListView";
import { EmptyState } from "../../../ui/EmptyState";
import { Field, Select } from "../../../ui/form";
import { LoadingBlock } from "../../../ui/Spinner";
import { CandidateCardView } from "./CandidateCardView";
import { FiltersPanel } from "./CatalogFilters";
import { CategoryGrid } from "./CategoryGrid";
import { useCatalogCandidates, useCatalogCategories, useFspCategories, useNeedVacancies } from "./hooks";
import { InviteDialog } from "../interviews/InviteDialog";

export function CatalogPage({ company }: { company: Company | undefined }) {
  if (!company) return <LoadingBlock />;
  if (company.status !== "approved") {
    return (
      <EmptyState
        icon={<Users className="size-5" />}
        title="Каталог откроется после модерации"
        text="Кандидатов видят только проверенные компании — так мы защищаем их от спама и фейковых работодателей."
      />
    );
  }
  return <Catalog />;
}

const DEFAULT_FILTERS: CatalogFilters = { confirmed_only: true };

function Catalog() {
  const [filters, setFilters] = useState<CatalogFilters>(DEFAULT_FILTERS);
  const [inviteTo, setInviteTo] = useState<CandidateCard | null>(null);
  // подбор «из коробки»: по первой вакансии (описанию потребности), пока работодатель не выберет другую
  const vacancies = useNeedVacancies();
  const [chosen, setChosen] = useState<string | null>(null);
  const matchVacancy = chosen ?? vacancies.data?.[0]?.id ?? "";
  const categories = useCatalogCategories(true);
  const fspCategories = useFspCategories();
  const candidates = useCatalogCandidates({ ...filters, vacancy_id: matchVacancy || undefined }, !vacancies.isPending);
  const update = (patch: Partial<CatalogFilters>) => setFilters((f) => ({ ...f, ...patch }));

  return (
    <>
      <PageHeader
        title="Каталог кандидатов"
        text="Выдача строится от категорий — специализация и грейд, подтверждённый тестом. С вакансией кандидаты отсортированы по соответствию ей, без вакансии — по силе подтверждённого профиля. У каждого — объяснение «Почему»."
      />
      <Field
        label="Подбор под потребность"
        className="mb-6 max-w-xl"
        hint="Вакансия или черновик с описанием, кого вы ищете: специализация, грейд, стек"
      >
        <Select
          placeholder="Без вакансии — по силе профиля"
          options={(vacancies.data ?? []).map((v) => ({ value: v.id, label: v.title }))}
          value={matchVacancy}
          onChange={(e) => setChosen(e.target.value)}
        />
      </Field>
      {categories.error && <Alert>{errorMessage(categories.error)}</Alert>}
      {categories.data && (
        <CategoryGrid categories={categories.data} selected={filters.category} onSelect={(category) => update({ category })} />
      )}
      <FiltersPanel
        filters={filters}
        fspCategories={fspCategories.data ?? []}
        onChange={update}
        onReset={() => setFilters(DEFAULT_FILTERS)}
      />
      <CursorListView
        query={candidates}
        className="grid gap-4 md:grid-cols-2"
        empty={{
          icon: <Users className="size-5" />,
          title: "Подходящих кандидатов пока нет",
          text: "Снимите часть фильтров или выберите соседнюю категорию.",
        }}
      >
        {(card) => (
          <CandidateCardView
            key={card.anon_id}
            card={card}
            action={
              <Button size="sm" onClick={() => setInviteTo(card)}>
                <CalendarPlus className="size-3.5" aria-hidden />
                Пригласить на собеседование
              </Button>
            }
          />
        )}
      </CursorListView>
      <InviteDialog
        key={inviteTo?.anon_id ?? "none"}
        candidate={inviteTo}
        vacancyId={matchVacancy || undefined}
        onClose={() => setInviteTo(null)}
      />
    </>
  );
}
