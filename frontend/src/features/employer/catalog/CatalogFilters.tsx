// Уточнение выдачи: фильтры сужают её, не меняя порядка кандидатов внутри.
import { useSkills } from "../../../api/queries";
import type { CatalogFilters, FspCategory, Grade, SearchStatus, Specialization, WorkFormat } from "../../../api/types";
import { labels, options } from "../../../lib/format";
import { Button } from "../../../ui/Button";
import { CitySelect } from "../../../ui/CitySelect";
import { Field, FieldGroup, Select, Switch } from "../../../ui/form";
import { SkillPicker } from "../../../ui/SkillPicker";

type Props = {
  filters: CatalogFilters;
  fspCategories: FspCategory[];
  onChange: (patch: Partial<CatalogFilters>) => void;
  onReset: () => void;
};

export function FiltersPanel({ filters, fspCategories, onChange, onReset }: Props) {
  const skills = useSkills();
  const pick = <T extends string>(value: string) => (value || undefined) as T | undefined;
  return (
    <section aria-label="Фильтры" className="mb-6 flex flex-col gap-4 rounded-2xl border border-line bg-surface p-4">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <Field label="Специализация">
          <Select
            placeholder="Любая"
            options={options(labels.specialization)}
            value={filters.specialization ?? ""}
            onChange={(e) => onChange({ specialization: pick<Specialization>(e.target.value) })}
          />
        </Field>
        <Field label="Грейд" hint="Подтверждённый тестом">
          <Select
            placeholder="Любой"
            options={options(labels.grade)}
            value={filters.grade ?? ""}
            onChange={(e) => onChange({ grade: pick<Grade>(e.target.value) })}
          />
        </Field>
        <Field label="Формат работы">
          <Select
            placeholder="Любой"
            options={options(labels.workFormat)}
            value={filters.work_format ?? ""}
            onChange={(e) => onChange({ work_format: pick<WorkFormat>(e.target.value) })}
          />
        </Field>
        <Field label="Город" hint="Живёт в нём или готов к переезду">
          <CitySelect
            placeholder="Любой"
            value={filters.city}
            onChange={(e) => onChange({ city: e.target.value || undefined })}
          />
        </Field>
        <Field label="Статус поиска">
          <Select
            placeholder="Любой"
            options={options({ active: labels.searchStatus.active, open: labels.searchStatus.open })}
            value={filters.search_status ?? ""}
            onChange={(e) => onChange({ search_status: pick<SearchStatus>(e.target.value) })}
          />
        </Field>
      </div>
      <FieldGroup label="Стек" hint="Кандидаты со всеми выбранными навыками">
        <SkillPicker
          skills={skills.data ?? []}
          value={filters.skill ?? []}
          onChange={(skill) => onChange({ skill })}
          max={10}
        />
      </FieldGroup>
      <div className="grid items-end gap-4 lg:grid-cols-[1fr_1fr_minmax(0,1.2fr)_auto]">
        <Switch
          label="Только с категорией"
          description="Грейд подтверждён тестом"
          checked={filters.confirmed_only ?? false}
          onChange={(e) => onChange({ confirmed_only: e.target.checked })}
        />
        <Switch
          label="С достижениями ФСП"
          description="Аккаунт ФСП подтверждён"
          checked={filters.fsp_only ?? false}
          onChange={(e) => onChange({ fsp_only: e.target.checked })}
        />
        <Field label="Достижения ФСП">
          <Select
            placeholder="Любые"
            options={fspCategories.map((c) => ({ value: c.slug, label: `${c.title} (${c.candidates})` }))}
            value={filters.fsp_category ?? ""}
            onChange={(e) => onChange({ fsp_category: e.target.value || undefined })}
          />
        </Field>
        <Button variant="ghost" onClick={onReset}>
          Сбросить
        </Button>
      </div>
    </section>
  );
}
