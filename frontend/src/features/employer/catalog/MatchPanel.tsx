import { ChevronDown } from "lucide-react";
import { useId, useState } from "react";
import type { Match } from "../../../api/types";
import { cn } from "../../../lib/cn";
import { matchTone } from "../../../lib/tones";
import { Badge } from "../../../ui/Badge";

type Kind = "match" | "strength" | "need";

function ScoreText({ kind, score }: { kind: Kind; score: number }) {
  if (kind === "match") return <><span className="tabular">{score}%</span>&nbsp;соответствия</>;
  const value = <span className="tabular">{score}</span>;
  if (kind === "need") return <>под вакансию:&nbsp;{value}&nbsp;из&nbsp;100</>;
  return <>сила профиля:&nbsp;{value}</>;
}

/** Оценка с объяснением: соответствие вакансии (лента кандидата), сила профиля в категории или
 * место под вакансию (каталог). Под оценкой — строка «почему», по кнопке — вклад факторов.
 * Под вакансию категория задаёт группу в выдаче, а остальные факторы с нулевым весом (стек,
 * формат, зарплата) только поясняют выбор. */
export function MatchPanel({ match, kind = "match" }: { match: Match; kind?: Kind }) {
  const [open, setOpen] = useState(false);
  const listId = useId();
  const category = match.factors.find((f) => f.key === "category" && f.weight === 0);
  const ranked = match.factors.filter((f) => f.weight > 0);
  const notes = match.factors.filter((f) => f.weight === 0 && f !== category);
  return (
    <div className="rounded-xl border border-line bg-surface-2/40 p-3">
      <div className="flex items-center justify-between gap-3">
        <Badge tone={matchTone(match.score)}>
          <ScoreText kind={kind} score={match.score} />
        </Badge>
        <button
          type="button"
          aria-expanded={open}
          aria-controls={listId}
          onClick={() => setOpen((v) => !v)}
          className="inline-flex items-center gap-1 text-sm text-muted hover:text-fg"
        >
          Почему
          <ChevronDown className={cn("size-4 transition-transform", open && "rotate-180")} aria-hidden />
        </button>
      </div>
      {match.summary && <p className="mt-2 text-xs leading-relaxed text-muted">{match.summary}</p>}
      {open && (
        <div id={listId} className="mt-3 flex flex-col gap-3 text-sm">
          {category && (
            <p>
              Категория — группа в выдаче: <span className="text-muted">{category.detail}</span>
            </p>
          )}
          <ul className="flex flex-col gap-2.5">
            {ranked.map((f) => (
              <li key={f.key}>
                <div className="flex items-baseline justify-between gap-3">
                  <span>{f.label}</span>
                  <span className="tabular text-xs text-muted">
                    {Math.round(f.share * f.weight)} из {f.weight}
                  </span>
                </div>
                <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-surface-2" aria-hidden>
                  <div className="h-full rounded-full bg-accent" style={{ width: `${Math.round(f.share * 100)}%` }} />
                </div>
                <p className="mt-1 text-xs text-muted">{f.detail}</p>
              </li>
            ))}
          </ul>
          {notes.length > 0 && (
            <div className="border-t border-line pt-3">
              <p className="text-xs font-medium text-muted">Для сведения — на место в выдаче не влияет:</p>
              <ul className="mt-1.5 flex flex-col gap-1 text-xs">
                {notes.map((f) => (
                  <li key={f.key}>
                    <span className="text-fg">{f.label}:</span> <span className="text-muted">{f.detail}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
