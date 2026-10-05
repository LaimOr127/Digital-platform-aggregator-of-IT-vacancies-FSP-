// Состояние кандидата: категория, на какие грейды можно пройти тест, история попыток.
import { Award, Lock, PlayCircle } from "lucide-react";
import type { AssessmentState, AttemptResult, Grade } from "../../../api/types";
import { formatDate, formatDateTime, labels } from "../../../lib/format";
import { Badge } from "../../../ui/Badge";
import { Button } from "../../../ui/Button";
import { Card, CardTitle } from "../../../ui/Card";

export function CategoryCard({ state }: { state: AssessmentState }) {
  const category = state.category;
  if (!category) {
    return (
      <Card>
        <CardTitle>Категория не присвоена</CardTitle>
        <p className="mt-2 text-sm text-muted">
          Пройдите тест на свой грейд — после него вы попадёте в категорию, и работодатели увидят вас в выдаче.
        </p>
      </Card>
    );
  }
  return (
    <Card className="border-accent/40 bg-accent/5">
      <div className="flex items-start gap-3">
        <Award className="mt-0.5 size-6 shrink-0 text-accent" aria-hidden />
        <div>
          <p className="text-xs text-muted">Ваша категория</p>
          <CardTitle className="mt-0.5 text-lg">{category.title}</CardTitle>
          <p className="mt-1 text-sm text-muted">
            Результат теста: {category.score ?? 0} из 100
            {category.confirmed_at && ` · подтверждено ${formatDate(category.confirmed_at)}`}
          </p>
          {category.next_change_at && (
            <p className="mt-1 text-xs text-muted">Сменить грейд можно с {formatDate(category.next_change_at)}</p>
          )}
        </div>
      </div>
    </Card>
  );
}

type OptionsProps = { state: AssessmentState; starting: Grade | null; onStart: (grade: Grade) => void };

export function GradeOptions({ state, starting, onStart }: OptionsProps) {
  return (
    <Card>
      <CardTitle>Пройти тест</CardTitle>
      <p className="mt-1 text-sm text-muted">
        15 заданий на 25 минут: уровни ниже, на уровне и выше заявленного. Задания составляются заново для каждой
        попытки.
      </p>
      <ul className="mt-4 flex flex-col gap-2">
        {state.options.map((o) => (
          <li key={o.grade} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-line px-4 py-3">
            <div className="min-w-0">
              <p className="font-medium">{labels.grade[o.grade]}</p>
              {!o.allowed && (
                <p className="flex items-center gap-1.5 text-xs text-muted">
                  <Lock className="size-3" aria-hidden />
                  {o.reason}
                  {o.retry_at && ` — с ${formatDate(o.retry_at)}`}
                </p>
              )}
              {o.allowed && o.reason && <p className="text-xs text-accent">{o.reason}</p>}
            </div>
            <Button
              size="sm"
              variant={o.grade === state.survey?.grade ? "primary" : "secondary"}
              disabled={!o.allowed || starting !== null}
              loading={starting === o.grade}
              onClick={() => onStart(o.grade)}
              aria-label={`Начать тест на грейд ${labels.grade[o.grade]}`}
            >
              <PlayCircle className="size-3.5" aria-hidden />
              Начать
            </Button>
          </li>
        ))}
      </ul>
    </Card>
  );
}

export function History({ history }: { history: AttemptResult[] }) {
  if (history.length === 0) return null;
  return (
    <Card>
      <CardTitle>История тестов</CardTitle>
      <ul className="mt-4 flex flex-col divide-y divide-line">
        {history.map((h) => (
          <li key={h.id} className="flex flex-wrap items-center justify-between gap-3 py-3 text-sm">
            <div>
              <p className="font-medium">
                {labels.specialization[h.specialization]} · {labels.grade[h.grade]}
              </p>
              <p className="text-xs text-muted">{formatDateTime(h.finished_at ?? h.started_at)}</p>
            </div>
            <div className="flex items-center gap-3">
              {h.correct !== null && (
                <span className="tabular text-muted">
                  {h.correct} из {h.total}
                </span>
              )}
              <Badge tone={h.result === "passed" ? "accent" : h.status === "expired" ? "neutral" : "warn"}>
                {h.status === "expired" ? "Время вышло" : h.result === "passed" ? "Подтверждён" : "Не подтверждён"}
              </Badge>
            </div>
          </li>
        ))}
      </ul>
    </Card>
  );
}
