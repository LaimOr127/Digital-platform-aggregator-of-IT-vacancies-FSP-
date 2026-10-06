// Категории кандидатов: специализация x подтверждённый грейд, в ячейке — число кандидатов.
import type { CatalogCategory, Grade, Specialization } from "../../../api/types";
import { cn } from "../../../lib/cn";
import { GRADES } from "../../../lib/fields";
import { labels } from "../../../lib/format";

type Props = {
  categories: CatalogCategory[];
  selected?: string;
  /** категории, рекомендованные под выбранную потребность */
  recommended?: string[];
  onSelect: (slug: string | undefined) => void;
};

/** Рекомендованные категории под потребность — как в подборе: тот же грейд и соседние. */
export function recommendedCategories(specialization: Specialization, grade: Grade): string[] {
  const index = GRADES.indexOf(grade);
  return GRADES.filter((_, i) => Math.abs(i - index) <= 1).map((g) => `${specialization}:${g}`);
}

export function CategoryGrid({ categories, selected, recommended = [], onSelect }: Props) {
  const bySlug = new Map(categories.map((c) => [c.slug, c]));
  const specializations = [...new Set(categories.map((c) => c.specialization))];
  return (
    <section aria-label="Категории кандидатов" className="mb-6 overflow-x-auto rounded-2xl border border-line bg-surface">
      <table className="w-full min-w-[640px] text-sm">
        <caption className="sr-only">Число кандидатов по специализации и подтверждённому грейду</caption>
        <thead>
          <tr className="text-xs text-muted">
            <th scope="col" className="px-4 py-3 text-left font-medium">
              Специализация
            </th>
            {GRADES.map((g) => (
              <th key={g} scope="col" className="px-2 py-3 font-medium">
                {labels.grade[g]}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {specializations.map((spec) => (
            <tr key={spec} className="border-t border-line">
              <th scope="row" className="px-4 py-2 text-left font-normal">
                {labels.specialization[spec]}
              </th>
              {GRADES.map((grade) => (
                <td key={grade} className="px-2 py-2 text-center">
                  <Cell
                    category={bySlug.get(`${spec}:${grade}`)}
                    spec={spec}
                    grade={grade}
                    selected={selected}
                    recommended={recommended.includes(`${spec}:${grade}`)}
                    onSelect={onSelect}
                  />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

type CellProps = {
  category: CatalogCategory | undefined;
  spec: Specialization;
  grade: Grade;
  selected?: string;
  recommended: boolean;
  onSelect: (slug: string | undefined) => void;
};

function Cell({ category, spec, grade, selected, recommended, onSelect }: CellProps) {
  const count = category?.candidates ?? 0;
  const slug = `${spec}:${grade}`;
  const active = selected === slug;
  return (
    <button
      type="button"
      aria-pressed={active}
      aria-label={`${labels.specialization[spec]}, ${labels.grade[grade]}: кандидатов ${count}${recommended ? ", рекомендуется" : ""}`}
      disabled={count === 0 && !active}
      onClick={() => onSelect(active ? undefined : slug)}
      className={cn(
        "min-w-12 rounded-lg px-2 py-1.5 tabular transition-colors disabled:cursor-default disabled:opacity-35",
        active ? "bg-accent text-on-accent" : "bg-surface-2 hover:bg-line",
        recommended && "ring-2 ring-accent",
      )}
    >
      {count}
    </button>
  );
}
