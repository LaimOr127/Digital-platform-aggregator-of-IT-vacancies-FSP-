// Путь роста: каких навыков не хватает до следующего грейда, сколько там платят и что дальше в ФСП.
import { ArrowRight, BadgeCheck } from "lucide-react";
import type { Growth, SkillShare } from "../../../api/types";
import { labels } from "../../../lib/format";
import { Card, CardTitle } from "../../../ui/Card";
import { compactMoney } from "../../insights/scale";

export function GrowthCard({ growth }: { growth: Growth }) {
  const current = growth.current_grade ? labels.grade[growth.current_grade] : "—";
  const target = growth.target_grade ? labels.grade[growth.target_grade] : null;
  return (
    <Card className="flex flex-col gap-6">
      <div>
        <CardTitle>Путь роста</CardTitle>
        <p className="mt-2 flex items-center gap-2 text-lg font-semibold">
          {current}
          {target && <ArrowRight className="size-4 text-muted" aria-label="следующий грейд" />}
          {target}
        </p>
        <p className="mt-1 text-sm text-muted">{scopeText(growth, target)}</p>
      </div>
      <SalaryStep now={growth.salary_now} later={growth.salary_target} target={target} />
      {growth.missing_skills.length > 0 && (
        <SkillList title="Чего не хватает" hint="доля вакансий, где нужен навык" skills={growth.missing_skills} />
      )}
      {growth.strengths.length > 0 && (
        <SkillList title="Что уже есть" hint="ваши навыки, востребованные на этом уровне" skills={growth.strengths} />
      )}
      <div className="flex gap-3 rounded-xl border border-accent/30 bg-accent/5 p-4 text-sm">
        <BadgeCheck className="mt-0.5 size-5 shrink-0 text-accent" aria-hidden />
        <p>{growth.fsp_next}</p>
      </div>
    </Card>
  );
}

function scopeText(growth: Growth, target: string | null): string {
  if (!target) return "Вы на верхнем грейде — ниже навыки, которые чаще всего просят на этом уровне.";
  if (growth.vacancies_considered === 0) {
    return `Вакансий уровня ${target} с вашим стеком пока нет — подсказки появятся с ростом рынка.`;
  }
  return `По ${growth.vacancies_considered} вакансиям уровня ${target} с похожим стеком.`;
}

function SalaryStep({ now, later, target }: { now: number | null; later: number | null; target: string | null }) {
  const increasePercent = now && later ? Math.round(((later - now) / now) * 100) : null;
  return (
    <dl className="grid grid-cols-2 gap-3">
      <div className="rounded-xl bg-surface-2 p-3">
        <dt className="text-xs text-muted">Медиана сейчас</dt>
        <dd className="mt-1 text-lg font-semibold tabular">{now ? `${compactMoney(now)} ₽` : "мало данных"}</dd>
      </div>
      <div className="rounded-xl bg-surface-2 p-3">
        <dt className="text-xs text-muted">{target ? `Медиана на ${target}` : "Следующий шаг"}</dt>
        <dd className="mt-1 text-lg font-semibold tabular">
          {later ? `${compactMoney(later)} ₽` : "мало данных"}
          {increasePercent !== null && increasePercent > 0 && (
            <span className="ml-2 text-sm font-medium text-accent">+{increasePercent}%</span>
          )}
        </dd>
      </div>
    </dl>
  );
}

function SkillList({ title, hint, skills }: { title: string; hint: string; skills: SkillShare[] }) {
  return (
    <section>
      <h3 className="text-sm font-semibold">{title}</h3>
      <p className="text-xs text-muted">{hint}</p>
      <ul className="mt-3 flex flex-col gap-2.5">
        {skills.map((skill) => {
          const percent = Math.round(skill.share * 100);
          return (
            <li key={skill.slug}>
              <div className="flex items-baseline justify-between gap-3 text-sm">
                <span className="truncate">{skill.name}</span>
                <span className="shrink-0 text-xs tabular text-muted">в {percent}% вакансий</span>
              </div>
              <div aria-hidden className="mt-1 h-1.5 overflow-hidden rounded-full bg-surface-2">
                <div className="h-full rounded-full bg-accent" style={{ width: `${percent}%` }} />
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
