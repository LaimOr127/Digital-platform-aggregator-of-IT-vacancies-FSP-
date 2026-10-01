import { Send, Users } from "lucide-react";
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
import { useCatalogCandidates, useCatalogCategories } from "./hooks";
import { OfferDialog } from "./OfferDialog";

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
  const [offerTo, setOfferTo] = useState<CandidateCard | null>(null);
  const categories = useCatalogCategories(true);
  const candidates = useCatalogCandidates(filters, true);
  const update = (patch: Partial<CatalogFilters>) => setFilters((f) => ({ ...f, ...patch }));

  return (
    <>
      <PageHeader
        title="Каталог кандидатов"
        text="Выберите категорию — дисциплину ФСП и уровень достижений. Профили анонимны; имя и контакты откроются, когда кандидат примет ваш оффер."
      />
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
              <Button size="sm" onClick={() => setOfferTo(card)}>
                <Send className="size-3.5" aria-hidden />
                Предложить оффер
              </Button>
            }
          />
        )}
      </CursorListView>
      <OfferDialog key={offerTo?.anon_id ?? "none"} candidate={offerTo} onClose={() => setOfferTo(null)} />
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
