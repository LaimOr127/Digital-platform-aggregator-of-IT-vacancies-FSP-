// Задача недели от работодателя: решить или предложить подход. Ответ поднимает
// актуальность профиля в подборе; компания видит его анонимно и может оценить.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ClipboardList, Send } from "lucide-react";
import { useState } from "react";
import { myTasksApi } from "../../../api/endpoints";
import { useCursorList } from "../../../api/queries";
import type { MyTaskAnswer, OfferedTask } from "../../../api/types";
import { formatDate } from "../../../lib/format";
import { Button } from "../../../ui/Button";
import { Card, CardTitle } from "../../../ui/Card";
import { Field, Textarea } from "../../../ui/form";
import { useAction } from "../../../ui/useAction";

const TASKS = ["candidate-tasks"] as const;
const MIN_ANSWER = 20;

export function WeeklyTask() {
  const current = useQuery({ queryKey: [...TASKS, "current"], queryFn: myTasksApi.current });
  const history = useCursorList([...TASKS, "answers"], (cursor) => myTasksApi.answers(cursor));
  const data = current.data;
  return (
    <Card>
      <CardTitle className="mb-1 flex items-center gap-2">
        <ClipboardList className="size-4 text-accent" aria-hidden />
        Задача недели
      </CardTitle>
      <p className="mb-4 text-sm text-muted">
        Короткая задача от работодателя: решите её или опишите подход. Свежий ответ поднимает профиль в подборке.
      </p>
      {data?.task && <TaskForm key={data.task.id} task={data.task} />}
      {data?.next_at && <p className="text-sm">Ответ отправлен. Следующая задача — с {formatDate(data.next_at)}</p>}
      {data?.reason && <p className="text-sm text-muted">{data.reason}</p>}
      {history.items.length > 0 && (
        <ul className="mt-5 flex flex-col gap-2 border-t border-line pt-4" aria-label="Мои ответы">
          {history.items.map((item) => (
            <AnswerItem key={item.id} item={item} />
          ))}
        </ul>
      )}
    </Card>
  );
}

function TaskForm({ task }: { task: OfferedTask }) {
  const client = useQueryClient();
  const run = useAction();
  const [answer, setAnswer] = useState("");
  const send = useMutation({
    mutationFn: (text: string) => myTasksApi.answer(task.id, text),
    onSuccess: () => Promise.all([TASKS, ["assessment"]].map((queryKey) => client.invalidateQueries({ queryKey }))),
  });
  const short = answer.trim().length < MIN_ANSWER;
  return (
    <div>
      <p className="text-xs text-muted">{task.company_name}</p>
      <h3 className="mt-0.5 font-medium">{task.title}</h3>
      <p className="mt-2 whitespace-pre-line text-sm leading-relaxed">{task.body}</p>
      <Field label="Ваш ответ" hint={`Решение или подход, от ${MIN_ANSWER} символов`} className="mt-4">
        <Textarea rows={5} maxLength={4000} value={answer} onChange={(e) => setAnswer(e.target.value)} />
      </Field>
      <div className="mt-3 flex justify-end">
        <Button
          size="sm"
          loading={send.isPending}
          disabled={short}
          onClick={() => run(send, answer.trim(), "Ответ отправлен компании")}
        >
          <Send className="size-3.5" aria-hidden />
          Отправить ответ
        </Button>
      </div>
    </div>
  );
}

function AnswerItem({ item }: { item: MyTaskAnswer }) {
  return (
    <li className="flex flex-wrap items-baseline justify-between gap-2 text-sm">
      <span className="min-w-0">
        {item.task_title} <span className="text-muted">· {item.company_name} · {formatDate(item.created_at)}</span>
      </span>
      <span className={item.rating ? "font-medium" : "text-muted"}>
        {item.rating ? `оценка ${item.rating} из 5` : "ещё не оценён"}
      </span>
    </li>
  );
}
