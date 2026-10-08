import { Award, BadgeCheck, MapPin } from "lucide-react";
import type { ReactNode } from "react";
import type { AiReview, CandidateCard } from "../../../api/types";
import { formatYears, labels, tierLabels } from "../../../lib/format";
import { cn } from "../../../lib/cn";
import { searchTone, tierTone } from "../../../lib/tones";
import { Badge } from "../../../ui/Badge";
import { AiReviewNote } from "./AiReviewBar";
import { MatchPanel } from "./MatchPanel";
import { ExpandableText } from "../../../ui/ExpandableText";
import { Salary } from "../../../ui/Salary";

const MAX_ACHIEVEMENTS = 3;

/** Анонимная карточка кандидата: категория и тест — главное, самоописание — дополнительно.
 * Имени и контактов нет: их видно после того, как кандидат примет приглашение. */
type Props = { card: CandidateCard; action?: ReactNode; className?: string; aiReview?: AiReview };

export function CandidateCardView({ card, action, className, aiReview }: Props) {
  const meta = [
    card.specialization ? labels.specialization[card.specialization] : null,
    card.experience_years !== null ? `стаж ${formatYears(card.experience_years)}` : null,
    card.work_formats.length ? card.work_formats.map((f) => labels.workFormat[f]).join(" / ") : null,
    card.education ? labels.education[card.education] : null,
    card.relocation ? "готов к переезду" : null,
  ].filter(Boolean);
  const extra = card.achievements.length - MAX_ACHIEVEMENTS;
  const declared = card.skills.filter((s) => !card.confirmed_skills.includes(s));

  return (
    <article className={cn("flex flex-col gap-4 rounded-2xl border border-line bg-surface p-5", className)}>
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
        <Badge tone={searchTone[card.search_status]}>{labels.searchStatus[card.search_status]}</Badge>
      </div>

      <CategoryLine card={card} />
      {card.match && <MatchPanel match={card.match} kind="match" />}
      {!card.match && card.strength && <MatchPanel match={card.strength} kind="strength" />}
      {aiReview && <AiReviewNote review={aiReview} />}

      <p className="text-sm">
        <span className="text-muted">Ожидания: </span>
        <span className="font-medium tabular"><Salary min={card.salary_min} max={card.salary_max} /></span>
      </p>

      {(card.fsp_categories.length > 0 || card.achievements.length > 0) && (
        <section aria-label="Достижения ФСП" className="flex flex-col gap-1.5 text-sm">
          {card.fsp_categories.map((c) => (
            <p key={c.slug} className="flex flex-wrap items-center gap-2">
              <Badge tone={tierTone[c.tier] ?? "neutral"}>{tierLabels[c.tier] ?? c.tier}</Badge>
              <span>{c.title.split(":")[0]}</span>
            </p>
          ))}
          <ul className="flex flex-col gap-1 text-muted">
            {card.achievements.slice(0, MAX_ACHIEVEMENTS).map((a, i) => (
              <li key={i} className="flex items-center gap-2">
                <Award className="size-3.5 shrink-0 text-accent" aria-hidden />
                {a}
              </li>
            ))}
            {extra > 0 && <li className="pl-5">и ещё {extra}</li>}
          </ul>
        </section>
      )}

      {(card.confirmed_skills.length > 0 || declared.length > 0) && (
        <ul className="flex flex-wrap gap-2" aria-label="Навыки">
          {card.confirmed_skills.map((s) => (
            <li key={s} className="inline-flex items-center gap-1 rounded-full border border-accent/40 bg-accent/10 px-2.5 py-0.5 text-xs">
              <BadgeCheck className="size-3 text-accent" aria-label="подтверждён тестом" />
              {s}
            </li>
          ))}
          {declared.map((s) => (
            <li key={s} className="rounded-full border border-line px-2.5 py-0.5 text-xs text-muted">
              {s}
            </li>
          ))}
        </ul>
      )}

      {card.about && <ExpandableText className="text-sm leading-relaxed text-muted" text={card.about} />}
      {action && <div className="border-t border-line pt-4">{action}</div>}
    </article>
  );
}

/** Категория по итогам теста или пометка, что грейд только заявлен. */
function CategoryLine({ card }: { card: CandidateCard }) {
  if (card.category) {
    return (
      <p className="flex flex-wrap items-center gap-2 text-sm">
        <Badge tone="accent">
          <BadgeCheck className="size-3.5" aria-hidden />
          {card.category.title}
        </Badge>
        <span className="text-muted tabular">тест: {card.assessment_score ?? 0} из 100</span>
        {card.verification_tier === "verified_fsp" && <Badge tone="info">Подтверждено ФСП</Badge>}
      </p>
    );
  }
  return (
    <p className="flex flex-wrap items-center gap-2 text-sm text-muted">
      <Badge tone="warn">Грейд не подтверждён тестом</Badge>
      {card.grade && <span>заявлен: {labels.grade[card.grade]}</span>}
    </p>
  );
}
