// Прохождение теста: все задания на одной странице, таймер, отправка до истечения времени.
// Правильные ответы в браузер не приходят: проверка — только на сервере.
import { Clock, Send } from "lucide-react";
import { useCallback, useEffect, useId, useRef, useState } from "react";
import type { Attempt, AttemptResult, Question } from "../../../api/types";
import { errorMessage } from "../../../api/errors";
import { labels } from "../../../lib/format";
import { Badge } from "../../../ui/Badge";
import { Button } from "../../../ui/Button";
import { Card } from "../../../ui/Card";
import { ConfirmDialog } from "../../../ui/ConfirmDialog";
import { Input } from "../../../ui/form";
import { useToast } from "../../../ui/Toast";
import { useSubmitAttempt } from "./hooks";

type Props = { attempt: Attempt; onFinished: (result: AttemptResult) => void };

export function TestRunner({ attempt, onFinished }: Props) {
  const [answers, setAnswers] = useState<(string | null)[]>(() => attempt.questions.map(() => null));
  const [confirming, setConfirming] = useState(false);
  const submit = useSubmitAttempt();
  const notify = useToast();
  const answered = answers.filter((a) => a !== null && a !== "").length;
  const total = attempt.questions.length;

  const send = useCallback(async () => {
    setConfirming(false);
    try {
      onFinished(await submit.mutateAsync({ id: attempt.id, responses: answers.map((a) => (a === "" ? null : a)) }));
    } catch (err) {
      notify(errorMessage(err), "error");
    }
  }, [answers, attempt.id, notify, onFinished, submit]);

  const seconds = useCountdown(attempt.deadline_at);
  // время вышло — отправляем то, что успели ответить (сервер примет в течение минуты)
  const sentOnTimeout = useRef(false);
  useEffect(() => {
    if (seconds === 0 && !sentOnTimeout.current && !submit.isPending) {
      sentOnTimeout.current = true;
      void send();
    }
  }, [seconds, send, submit.isPending]);

  const setAnswer = (index: number, value: string) =>
    setAnswers((prev) => prev.map((a, i) => (i === index ? value : a)));

  return (
    <div className="flex flex-col gap-5">
      <div className="sticky top-28 z-20 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-line bg-surface/95 px-5 py-3 backdrop-blur">
        <div>
          <p className="font-semibold">
            Тест: {labels.specialization[attempt.specialization]} · {labels.grade[attempt.grade]}
          </p>
          <p className="text-sm text-muted tabular">
            Отвечено {answered} из {total}
          </p>
        </div>
        <Badge tone={seconds < 120 ? "warn" : "neutral"}>
          <Clock className="size-3.5" aria-hidden />
          <span className="tabular" aria-live={seconds < 60 ? "polite" : "off"}>
            {formatClock(seconds)}
          </span>
        </Badge>
      </div>
      <ol className="flex flex-col gap-4">
        {attempt.questions.map((q) => (
          <li key={q.index}>
            <QuestionCard question={q} value={answers[q.index]} onChange={(v) => setAnswer(q.index, v)} />
          </li>
        ))}
      </ol>
      <div className="flex justify-end">
        <Button size="lg" loading={submit.isPending} onClick={() => (answered < total ? setConfirming(true) : void send())}>
          <Send className="size-4" aria-hidden />
          Завершить тест
        </Button>
      </div>
      <ConfirmDialog
        open={confirming}
        title="Завершить тест?"
        confirmLabel="Завершить"
        tone="primary"
        pending={submit.isPending}
        onConfirm={() => void send()}
        onClose={() => setConfirming(false)}
      >
        Без ответа осталось заданий: {total - answered}. Они будут засчитаны как неверные.
      </ConfirmDialog>
    </div>
  );
}

function QuestionCard({ question: q, value, onChange }: { question: Question; value: string | null; onChange: (v: string) => void }) {
  const titleId = useId();
  return (
    <Card>
      <fieldset aria-labelledby={titleId}>
        <p className="text-xs text-muted">
          Задание {q.index + 1} · {q.topic}
        </p>
        <legend className="sr-only">Задание {q.index + 1}</legend>
        <p id={titleId} className="mt-1 font-medium leading-relaxed">
          {q.prompt}
        </p>
        {q.code && (
          <pre className="mt-3 overflow-x-auto rounded-xl border border-line bg-bg p-4 text-sm leading-relaxed">
            <code>{q.code}</code>
          </pre>
        )}
        {q.kind === "choice" ? (
          <div className="mt-4 flex flex-col gap-2">
            {q.options.map((option, i) => (
              <label
                key={i}
                className="flex cursor-pointer items-start gap-3 rounded-xl border border-line px-4 py-3 text-sm transition-colors hover:border-muted/60 has-[:checked]:border-accent has-[:checked]:bg-accent/10"
              >
                <input
                  type="radio"
                  name={`q-${q.index}`}
                  value={i}
                  checked={value === String(i)}
                  onChange={() => onChange(String(i))}
                  className="mt-0.5 accent-[var(--accent)]"
                />
                <span className="leading-relaxed">{option}</span>
              </label>
            ))}
          </div>
        ) : (
          <Input
            aria-label={`Ответ на задание ${q.index + 1}`}
            inputMode="numeric"
            placeholder="Число"
            className="mt-4 max-w-48 tabular"
            value={value ?? ""}
            onChange={(e) => onChange(e.target.value.slice(0, 32))}
          />
        )}
      </fieldset>
    </Card>
  );
}

/** Секунды до дедлайна по часам браузера; 0 — время вышло. */
function useCountdown(deadline: string): number {
  const [seconds, setSeconds] = useState(() => secondsUntil(deadline));
  useEffect(() => {
    setSeconds(secondsUntil(deadline));
    const timer = setInterval(() => setSeconds(secondsUntil(deadline)), 1000);
    return () => clearInterval(timer);
  }, [deadline]);
  return seconds;
}

function secondsUntil(deadline: string): number {
  return Math.max(0, Math.floor((new Date(deadline).getTime() - Date.now()) / 1000));
}

function formatClock(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}
