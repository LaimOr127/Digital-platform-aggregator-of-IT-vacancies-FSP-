import { CalendarPlus, Users } from "lucide-react";
import { useMemo, useState } from "react";
import { errorMessage } from "../../../api/errors";
import { useSkills } from "../../../api/queries";
import type {
  CandidateCard,
  CatalogCategory,
  CatalogFilters,
  Company,
  Grade,
  SearchStatus,
  WorkFormat,
} from "../../../api/types";
import { cn } from "../../../lib/cn";
import { labels, options, tierLabels } from "../../../lib/format";
import { Alert } from "../../../ui/Alert";
import { PageHeader } from "../../../ui/AppShell";
import { Button } from "../../../ui/Button";
import { CursorListView } from "../../../ui/CursorListView";
import { EmptyState } from "../../../ui/EmptyState";
import { Field, Select } from "../../../ui/form";
import { LoadingBlock } from "../../../ui/Spinner";
import { CandidateCardView } from "./CandidateCardView";
import { useActiveVacancies, useCatalogCandidates, useCatalogCategories } from "./hooks";
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

function Catalog() {
  const [filters, setFilters] = useState<CatalogFilters>({});
  const [inviteTo, setInviteTo] = useState<CandidateCard | null>(null);
  // подбор «из коробки»: по первой опубликованной вакансии, пока работодатель не выберет другую
  const vacancies = useActiveVacancies();
  const [chosen, setChosen] = useState<string | null>(null);
  const matchVacancy = chosen ?? vacancies.data?.items[0]?.id ?? "";
  const categories = useCatalogCategories(true);
  const candidates = useCatalogCandidates({ ...filters, vacancy_id: matchVacancy || undefined }, !vacancies.isPending);
  const update = (patch: Partial<CatalogFilters>) => setFilters((f) => ({ ...f, ...patch }));

  return (
    <>
      <PageHeader
        title="Каталог кандидатов"
        text="Кандидаты отсортированы по соответствию вашей вакансии. Пригласите на собеседование — после него можно отправить оффер; имя и контакты откроются, когда кандидат примет оффер."
      />
      <Field label="Подбор под вакансию" className="mb-6 max-w-xl" hint="Кандидаты отсортированы по проценту соответствия">
        <Select
          placeholder="Без подбора — новые профили сверху"
          options={(vacancies.data?.items ?? []).map((v) => ({ value: v.id, label: v.title }))}
          value={matchVacancy}
          onChange={(e) => setChosen(e.target.value)}
        />
      </Field>
      {categories.error && <Alert>{errorMessage(categories.error)}</Alert>}
      {categories.data && (
        <CategoryGrid categories={categories.data} selected={filters.category} onSelect={(category) => update({ category })} />
      )}
      <Filters filters={filters} onChange={update} />
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

type GridProps = { categories: CatalogCategory[]; selected?: string; onSelect: (slug: string | undefined) => void };

/** Категории по дисциплинам: три уровня в каждой, счётчик видимых кандидатов. */
function CategoryGrid({ categories, selected, onSelect }: GridProps) {
  const groups = useMemo(() => {
    const map = new Map<string, CatalogCategory[]>();
    for (const c of categories) map.set(c.discipline, [...(map.get(c.discipline) ?? []), c]);
    return [...map.values()];
  }, [categories]);

  return (
    <section aria-label="Категории" className="mb-8 grid gap-3 lg:grid-cols-2">
      {groups.map((group) => (
        <div key={group[0].discipline} className="rounded-2xl border border-line bg-surface p-4">
          <p className="text-sm font-medium">{group[0].title.split(":")[0]}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {group.map((c) => (
              <button
                key={c.slug}
                type="button"
                aria-pressed={selected === c.slug}
                aria-label={`${c.title.split(":")[0]}: ${tierLabels[c.tier] ?? c.tier}, кандидатов: ${c.candidates}`}
                onClick={() => onSelect(selected === c.slug ? undefined : c.slug)}
                className={cn(
                  "inline-flex items-center gap-2 rounded-full border px-3 py-1 text-sm transition-colors",
                  selected === c.slug ? "border-accent bg-accent/15 text-accent" : "border-line text-muted hover:text-fg",
                )}
              >
                {tierLabels[c.tier] ?? c.tier}
                <span className="tabular rounded-full bg-surface-2 px-1.5 text-xs">{c.candidates}</span>
              </button>
            ))}
          </div>
        </div>
      ))}
    </section>
  );
}

function Filters({ filters, onChange }: { filters: CatalogFilters; onChange: (patch: Partial<CatalogFilters>) => void }) {
  const skills = useSkills();
  return (
    <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <Field label="Грейд">
        <Select
          placeholder="Любой"
          options={options(labels.grade)}
          value={filters.grade ?? ""}
          onChange={(e) => onChange({ grade: (e.target.value || undefined) as Grade | undefined })}
        />
      </Field>
      <Field label="Формат работы">
        <Select
          placeholder="Любой"
          options={options(labels.workFormat)}
          value={filters.work_format ?? ""}
          onChange={(e) => onChange({ work_format: (e.target.value || undefined) as WorkFormat | undefined })}
        />
      </Field>
      <Field label="Статус поиска">
        <Select
          placeholder="Любой"
          options={options({ active: labels.searchStatus.active, open: labels.searchStatus.open })}
          value={filters.search_status ?? ""}
          onChange={(e) => onChange({ search_status: (e.target.value || undefined) as SearchStatus | undefined })}
        />
      </Field>
      <Field label="Навык">
        <Select
          placeholder="Любой"
          options={(skills.data ?? []).map((s) => ({ value: s.slug, label: s.name }))}
          value={filters.skill ?? ""}
          onChange={(e) => onChange({ skill: e.target.value || undefined })}
        />
      </Field>
    </div>
  );
}
