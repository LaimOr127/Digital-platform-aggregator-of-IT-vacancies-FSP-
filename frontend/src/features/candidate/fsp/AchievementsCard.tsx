import { Award, ChevronDown, Trophy } from "lucide-react";
import type { Achievement, Category } from "../../../api/types";
import { levelLabels, outcomeLabel, tierLabels } from "../../../lib/format";
import { tierTone } from "../../../lib/tones";
import { Badge } from "../../../ui/Badge";
import { Card, CardTitle } from "../../../ui/Card";
import { EmptyState } from "../../../ui/EmptyState";

/** Категории, в которые кандидат попал автоматически, с обоснованием. */
export function CategoriesCard({ categories }: { categories: Category[] }) {
  return (
    <Card>
      <CardTitle>Ваши категории</CardTitle>
      <p className="mt-1 text-sm text-muted">
        Работодатель выбирает категорию и видит в ней ваш анонимный профиль. Считаются автоматически по данным ФСП.
      </p>
      {categories.length === 0 ? (
        <p className="mt-5 text-sm text-muted">Категорий пока нет — они появятся после привязки ФСП с результатами.</p>
      ) : (
        <ul className="mt-5 flex flex-col gap-3">
          {categories.map((c) => (
            <li key={c.slug}>
              <details className="group rounded-xl border border-line bg-surface-2 px-4 py-3">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-3">
                  <span className="flex flex-col items-start gap-1.5">
                    <Badge tone={tierTone[c.tier] ?? "neutral"}>{tierLabels[c.tier] ?? c.tier}</Badge>
                    <span className="font-medium">{c.title}</span>
                  </span>
                  <ChevronDown className="size-4 shrink-0 text-muted transition-transform group-open:rotate-180" aria-hidden />
                </summary>
                <div className="mt-3 border-t border-line pt-3 text-sm text-muted">
                  <p className="mb-1 text-fg">Почему эта категория:</p>
                  <ul className="list-disc pl-5">
                    {c.reasons.map((r) => (
                      <li key={r}>{r}</li>
                    ))}
                  </ul>
                </div>
              </details>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export function AchievementsCard({ achievements }: { achievements: Achievement[] }) {
  if (achievements.length === 0) {
    return (
      <EmptyState
        icon={<Trophy className="size-5" />}
        title="Результатов пока нет"
        text="Как только в ФСП появятся ваши результаты соревнований, они подтянутся сюда автоматически."
      />
    );
  }
  return (
    <Card>
      <CardTitle>Результаты соревнований</CardTitle>
      <ol className="mt-5 flex flex-col">
        {achievements.map((a) => (
          <li key={a.external_id} className="flex gap-4 border-b border-line py-4 last:border-0 last:pb-0 first:pt-0">
            <span
              className={`grid size-10 shrink-0 place-items-center rounded-xl ${a.place && a.place <= 3 ? "bg-accent/15 text-accent" : "bg-surface-2 text-muted"}`}
              aria-hidden
            >
              <Award className="size-5" />
            </span>
            <div className="min-w-0">
              <p className="font-medium">{a.competition_title}</p>
              <p className="mt-0.5 text-sm text-muted">
                {a.discipline_title} · {levelLabels[a.level] ?? a.level} уровень · {a.date.slice(0, 4)}
                {a.team ? ` · команда «${a.team}»` : ""}
              </p>
            </div>
            <span className="ml-auto shrink-0 self-center">
              <Badge tone={a.place && a.place <= 3 ? "accent" : "neutral"}>{outcomeLabel(a.place, a.stage)}</Badge>
            </span>
          </li>
        ))}
      </ol>
    </Card>
  );
}
