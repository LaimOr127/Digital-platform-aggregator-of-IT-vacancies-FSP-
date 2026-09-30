// Выбор навыков из справочника: выбранные — чипы, поиск — по названию.
import { Plus, X } from "lucide-react";
import { useId, useMemo, useState } from "react";
import type { Skill } from "../api/types";

type Props = { skills: Skill[]; value: string[]; onChange: (slugs: string[]) => void; max: number };

const SUGGESTIONS = 12;

export function SkillPicker({ skills, value, onChange, max }: Props) {
  const [query, setQuery] = useState("");
  const searchId = useId();
  const bySlug = useMemo(() => new Map(skills.map((s) => [s.slug, s])), [skills]);
  const available = useMemo(() => {
    const q = query.trim().toLowerCase();
    return skills
      .filter((s) => !value.includes(s.slug) && (!q || s.name.toLowerCase().includes(q)))
      .slice(0, SUGGESTIONS);
  }, [skills, value, query]);

  const add = (slug: string) => {
    if (value.length >= max) return;
    onChange([...value, slug]);
    setQuery("");
  };
  const remove = (slug: string) => onChange(value.filter((s) => s !== slug));

  return (
    <div className="flex flex-col gap-3">
      <ul aria-label="Выбранные навыки" className="flex min-h-9 flex-wrap gap-2">
        {value.length === 0 && <li className="text-sm text-muted">Навыки не выбраны</li>}
        {value.map((slug) => (
          <li key={slug}>
            <button
              type="button"
              onClick={() => remove(slug)}
              className="inline-flex items-center gap-1.5 rounded-full border border-accent/40 bg-accent/10 py-1 pl-3 pr-2 text-sm text-accent hover:bg-accent/20"
              aria-label={`Убрать ${bySlug.get(slug)?.name ?? slug}`}
            >
              {bySlug.get(slug)?.name ?? slug}
              <X className="size-3.5" aria-hidden />
            </button>
          </li>
        ))}
      </ul>
      <label htmlFor={searchId} className="sr-only">
        Найти навык
      </label>
      <input
        id={searchId}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={(e) => {
          // Enter добавляет первую подсказку и не отправляет форму, внутри которой стоит поиск
          if (e.key !== "Enter") return;
          e.preventDefault();
          if (query.trim() && available[0]) add(available[0].slug);
        }}
        placeholder="Найти навык: Python, Kubernetes, алгоритмы…"
        className="h-10 w-full rounded-lg border border-line bg-surface-2 px-3 text-sm placeholder:text-muted/70 focus:border-accent focus:outline-none"
      />
      <div className="flex flex-wrap gap-2">
        {available.map((s) => (
          <button
            key={s.slug}
            type="button"
            onClick={() => add(s.slug)}
            disabled={value.length >= max}
            className="inline-flex items-center gap-1 rounded-full border border-line px-3 py-1 text-sm text-muted transition-colors hover:border-muted/60 hover:text-fg disabled:opacity-40"
          >
            <Plus className="size-3.5" aria-hidden />
            {s.name}
          </button>
        ))}
        {available.length === 0 && query && <span className="text-sm text-muted">Ничего не найдено</span>}
      </div>
    </div>
  );
}
