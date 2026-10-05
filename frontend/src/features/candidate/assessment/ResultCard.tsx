// Итог теста: подтверждён ли грейд, оценка уровня на шкале грейдов, результаты по темам.
import { CheckCircle2, CircleAlert } from "lucide-react";
import type { AttemptResult, Grade } from "../../../api/types";
import { labels } from "../../../lib/format";
import { GRADES } from "../../../lib/fields";
import { Card, CardTitle } from "../../../ui/Card";

export function ResultCard({ result }: { result: AttemptResult }) {
  const passed = result.result === "passed";
  const Icon = passed ? CheckCircle2 : CircleAlert;
  return (
    <Card className={passed ? "border-accent/40" : "border-warn/40"}>
      <div className="flex items-start gap-3">
        <Icon className={`mt-0.5 size-6 shrink-0 ${passed ? "text-accent" : "text-warn"}`} aria-hidden />
        <div>
          <CardTitle>{passed ? `Грейд ${labels.grade[result.grade]} подтверждён` : `Грейд ${labels.grade[result.grade]} пока не подтверждён`}</CardTitle>
          <p className="mt-1 text-sm text-muted">{verdict(result)}</p>
        </div>
      </div>
      <dl className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-3">
        <Stat label="Верных ответов" value={`${result.correct ?? 0} из ${result.total}`} />
        <Stat label="Оценка уровня" value={result.theta !== null ? `${result.theta.toFixed(1)} из 5` : "—"} />
        {passed && <Stat label="Место в категории" value={`${result.score ?? 0} из 100`} />}
      </dl>
      {result.theta !== null && <LevelScale theta={result.theta} target={result.grade} />}
      {result.topics.length > 0 && (
        <section className="mt-6">
          <h3 className="text-sm font-semibold">Результаты по темам</h3>
          <ul className="mt-3 grid gap-2 sm:grid-cols-2">
            {result.topics.map((t) => (
              <li key={t.topic} className="flex items-center justify-between gap-3 rounded-lg bg-surface-2 px-3 py-2 text-sm">
                <span className="truncate">{t.topic}</span>
                <span className="shrink-0 tabular text-muted">
                  {t.correct} из {t.total}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </Card>
  );
}

function verdict(result: AttemptResult): string {
  if (result.result === "failed") {
    return "Грейд не понижается: можно сразу пройти тест на грейд ниже, а этот — повторить через 14 дней.";
  }
  if (result.confident) return "Уверенный результат: в течение 14 дней можно сразу подтвердить грейд выше.";
  return "Вы в категории — работодатели видят её и результат теста. Сменить грейд можно через три месяца.";
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-surface-2 p-3">
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="mt-1 font-semibold tabular">{value}</dd>
    </div>
  );
}

/** Шкала грейдов 1–5 с отметкой оценки уровня и проходным порогом заявленного грейда. */
function LevelScale({ theta, target }: { theta: number; target: Grade }) {
  const position = (value: number) => `${Math.min(100, Math.max(0, ((value - 0.5) / 5) * 100))}%`;
  const threshold = GRADES.indexOf(target) + 1 - 0.5;
  return (
    <figure className="mt-6" aria-label={`Оценка уровня ${theta.toFixed(1)}, порог грейда ${threshold.toFixed(1)}`}>
      <div className="relative h-8">
        <div className="absolute inset-x-0 top-1/2 h-1.5 -translate-y-1/2 rounded-full bg-surface-2" aria-hidden />
        <span
          aria-hidden
          className="absolute top-1/2 h-5 -translate-y-1/2 border-l-2 border-dashed border-muted"
          style={{ left: position(threshold) }}
        />
        <span
          aria-hidden
          className="absolute top-1/2 size-4 -translate-x-1/2 -translate-y-1/2 rounded-full bg-accent ring-4 ring-surface"
          style={{ left: position(theta) }}
        />
      </div>
      <div className="relative h-4 text-[11px] text-muted" aria-hidden>
        {GRADES.map((g, i) => (
          <span key={g} className="absolute -translate-x-1/2" style={{ left: position(i + 1) }}>
            {labels.grade[g]}
          </span>
        ))}
      </div>
      <figcaption className="mt-2 text-xs text-muted">Пунктир — порог заявленного грейда, точка — ваша оценка уровня.</figcaption>
    </figure>
  );
}
