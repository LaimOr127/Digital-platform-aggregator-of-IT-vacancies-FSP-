import { ChevronDown } from "lucide-react";
import { useId, useState } from "react";
import type { Match } from "../../../api/types";
import { cn } from "../../../lib/cn";
import { matchTone } from "../../../lib/tones";
import { Badge } from "../../../ui/Badge";

/** Процент соответствия вакансии и вклад каждого фактора (по кнопке «Почему»). */
export function MatchPanel({ match }: { match: Match }) {
  const [open, setOpen] = useState(false);
  const listId = useId();
  return (
    <div className="rounded-xl border border-line bg-surface-2/40 p-3">
      <div className="flex items-center justify-between gap-3">
        <Badge tone={matchTone(match.score)}>
          <span className="tabular">{match.score}%</span>&nbsp;соответствия
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
      {open && (
        <ul id={listId} className="mt-3 flex flex-col gap-2.5 text-sm">
          {match.factors.map((f) => (
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
      )}
    </div>
  );
}
