// Путь кандидата к категории: опрос -> тест на грейд -> категория (специализация x грейд).
import { Pencil } from "lucide-react";
import { useState } from "react";
import type { AttemptResult, Grade } from "../../../api/types";
import { errorMessage } from "../../../api/errors";
import { cn } from "../../../lib/cn";
import { labels } from "../../../lib/format";
import { Alert } from "../../../ui/Alert";
import { PageHeader } from "../../../ui/AppShell";
import { Button } from "../../../ui/Button";
import { Card, CardTitle } from "../../../ui/Card";
import { LoadingBlock } from "../../../ui/Spinner";
import { useToast } from "../../../ui/Toast";
import { useAssessment, useStartAttempt } from "./hooks";
import { CategoryCard, GradeOptions, History } from "./Overview";
import { ResultCard } from "./ResultCard";
import { SurveyForm } from "./SurveyForm";
import { TestRunner } from "./TestRunner";
import { WeeklyTask } from "../tasks/WeeklyTask";

export function AssessmentPage() {
  const state = useAssessment();
  const start = useStartAttempt();
  const notify = useToast();
  const [result, setResult] = useState<AttemptResult | null>(null);
  const [editing, setEditing] = useState(false);
  const [starting, setStarting] = useState<Grade | null>(null);

  const onStart = async (grade: Grade) => {
    setStarting(grade);
    setResult(null);
    try {
      await start.mutateAsync(grade);
      window.scrollTo({ top: 0 });
    } catch (err) {
      notify(errorMessage(err), "error");
    } finally {
      setStarting(null);
    }
  };
  const onFinished = (finished: AttemptResult) => {
    setResult(finished);
    window.scrollTo({ top: 0 });
  };

  const data = state.data;
  const step = !data?.survey ? 1 : data.category ? 3 : 2;
  return (
    <>
      <PageHeader
        title="Категория и тест"
        text="Работодатели ищут кандидатов по категориям: специализация и грейд, подтверждённый тестом. Внутри категории выше те, у кого лучше результат теста и есть достижения ФСП."
      />
      {state.error && <Alert>{errorMessage(state.error)}</Alert>}
      {!state.error && !data && <LoadingBlock />}
      {data && !data.active && <Steps current={step} />}
      {data?.active && <TestRunner key={data.active.id} attempt={data.active} onFinished={onFinished} />}
      {data && !data.active && (
        <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
          <div className="flex flex-col gap-6">
            {result && <ResultCard result={result} />}
            {(!data.survey || editing) && (
              <Card>
                <CardTitle className="mb-5">{data.survey ? "Изменить ответы опроса" : "Шаг 1. Расскажите о себе"}</CardTitle>
                <SurveyForm state={data} onDone={() => setEditing(false)} />
              </Card>
            )}
            {data.survey && !editing && <GradeOptions state={data} starting={starting} onStart={onStart} />}
            {data.survey && !editing && <WeeklyTask />}
            <History history={data.history} />
          </div>
          <aside className="flex flex-col gap-4 lg:sticky lg:top-32">
            <CategoryCard state={data} />
            {data.survey && !editing && (
              <Card>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-xs text-muted">Опрос</p>
                    <p className="mt-0.5 font-medium">{labels.specialization[data.survey.specialization]}</p>
                    <p className="text-sm text-muted">
                      Заявлен грейд {data.survey.grade ? labels.grade[data.survey.grade] : "—"} · стаж{" "}
                      {data.survey.experience_years ?? 0} лет
                    </p>
                  </div>
                  <Button variant="ghost" size="sm" onClick={() => setEditing(true)} aria-label="Изменить ответы опроса">
                    <Pencil className="size-3.5" aria-hidden />
                  </Button>
                </div>
              </Card>
            )}
          </aside>
        </div>
      )}
    </>
  );
}

const STEPS = ["Опрос", "Тест", "Категория"];

function Steps({ current }: { current: number }) {
  return (
    <ol className="mb-6 flex flex-wrap gap-2" aria-label="Шаги">
      {STEPS.map((label, i) => {
        const done = i + 1 < current || current === 3;
        const active = i + 1 === current;
        return (
          <li
            key={label}
            aria-current={active ? "step" : undefined}
            className={cn(
              "flex items-center gap-2 rounded-full border px-3 py-1 text-sm",
              done ? "border-accent/40 text-accent" : active ? "border-fg/40 text-fg" : "border-line text-muted",
            )}
          >
            <span className="tabular">{i + 1}</span>
            {label}
          </li>
        );
      })}
    </ol>
  );
}
