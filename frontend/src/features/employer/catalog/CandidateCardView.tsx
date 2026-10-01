import { Award, MapPin } from "lucide-react";
import type { ReactNode } from "react";
import type { CandidateCard } from "../../../api/types";
import { formatSalaryRange, labels, tierLabels } from "../../../lib/format";
import { tierTone } from "../../../lib/tones";
import { Badge } from "../../../ui/Badge";

const MAX_ACHIEVEMENTS = 3;

/** Анонимная карточка кандидата: без имени и контактов — их видно только после принятого оффера. */
export function CandidateCardView({ card, action }: { card: CandidateCard; action?: ReactNode }) {
  const meta = [
    card.grade ? labels.grade[card.grade] : null,
    card.work_format ? labels.workFormat[card.work_format] : null,
  ].filter(Boolean);
  const extra = card.achievements.length - MAX_ACHIEVEMENTS;

  return (
    <article className="flex flex-col gap-4 rounded-2xl border border-line bg-surface p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs text-muted">Кандидат #{card.anon_id.slice(0, 6).toUpperCase()}</p>
          <h3 className="mt-0.5 text-lg font-semibold">{card.title ?? "Должность не указана"}</h3>
          <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted">
            {meta.map((m) => (
              <span key={m}>{m}</span>
            ))}
            {card.city && (
              <span className="inline-flex items-center gap-1">
                <MapPin className="size-3.5" aria-hidden />
                {card.city}
              </span>
            )}
          </p>
        </div>
        <Badge tone={card.verification_tier === "verified_fsp" ? "accent" : "neutral"}>
          {labels.tier[card.verification_tier]}
        </Badge>
      </div>

      <p className="text-sm">
        <span className="text-muted">Ожидания: </span>
        <span className="font-medium tabular">{formatSalaryRange(card.salary_min, card.salary_max)}</span>
      </p>

      {card.categories.length > 0 && (
        <ul className="flex flex-col gap-1.5" aria-label="Категории">
          {card.categories.map((c) => (
            <li key={c.slug} className="flex flex-wrap items-center gap-2 text-sm">
              <Badge tone={tierTone[c.tier] ?? "neutral"}>{tierLabels[c.tier] ?? c.tier}</Badge>
              <span>{c.title.split(":")[0]}</span>
            </li>
          ))}
        </ul>
      )}

      {card.achievements.length > 0 && (
        <ul className="flex flex-col gap-1 text-sm text-muted" aria-label="Подтверждённые результаты ФСП">
          {card.achievements.slice(0, MAX_ACHIEVEMENTS).map((a, i) => (
            <li key={i} className="flex items-center gap-2">
              <Award className="size-3.5 shrink-0 text-accent" aria-hidden />
              {a}
            </li>
          ))}
          {extra > 0 && <li className="pl-5">и ещё {extra}</li>}
        </ul>
      )}

      {card.skills.length > 0 && (
        <ul className="flex flex-wrap gap-2" aria-label="Навыки">
          {card.skills.map((s) => (
            <li key={s} className="rounded-full border border-line px-2.5 py-0.5 text-xs text-muted">
              {s}
            </li>
          ))}
        </ul>
      )}

      {card.about && <p className="line-clamp-3 text-sm leading-relaxed text-muted">{card.about}</p>}
      {action && <div className="border-t border-line pt-4">{action}</div>}
    </article>
  );
}
