// Регулярные короткие задачи: кандидаты специализации получают одну задачу в неделю,
// ответы приходят анонимно — их можно оценить и пригласить автора сильного решения.
import { ClipboardList, MessageSquareText, Plus, Square } from "lucide-react";
import { useState } from "react";
import type { CandidateCard, Company, EmployerTask } from "../../../api/types";
import { formatDate, labels } from "../../../lib/format";
import { PageHeader } from "../../../ui/AppShell";
import { Badge } from "../../../ui/Badge";
import { Button } from "../../../ui/Button";
import { CursorListView } from "../../../ui/CursorListView";
import { useAction } from "../../../ui/useAction";
import { InvitationDialog } from "../applications/InvitationDialog";
import { useNeedVacancies } from "../catalog/hooks";
import { AnswersDialog } from "./AnswersDialog";
import { useCloseTask, useEmployerTasks } from "./hooks";
import { TaskDialog } from "./TaskDialog";

export function TasksPage({ company }: { company: Company | undefined }) {
  const tasks = useEmployerTasks();
  const close = useCloseTask();
  const vacancies = useNeedVacancies();
  const run = useAction();
  const [creating, setCreating] = useState(false);
  const [viewing, setViewing] = useState<EmployerTask | null>(null);
  const [inviting, setInviting] = useState<CandidateCard | null>(null);

  return (
    <>
      <PageHeader
        title="Задачи для кандидатов"
        text="Раз в неделю кандидат вашей специализации получает короткую задачу: решает её или предлагает подход. Это держит профили актуальными, а вам даёт свежий сигнал — ответы приходят анонимно, автора сильного ответа можно пригласить."
      >
        <Button onClick={() => setCreating(true)} disabled={company?.status !== "approved"}>
          <Plus className="size-4" aria-hidden />
          Новая задача
        </Button>
      </PageHeader>
      <CursorListView
        query={tasks}
        empty={{
          icon: <ClipboardList className="size-5" />,
          title: "Задач пока нет",
          text: "Опубликуйте задачу на 15–30 минут из реальной работы команды.",
        }}
      >
        {(task) => (
          <TaskRow
            key={task.id}
            task={task}
            onAnswers={() => setViewing(task)}
            onClose={() => run(close, task.id, "Задача снята — новым кандидатам она не попадёт")}
          />
        )}
      </CursorListView>
      <TaskDialog open={creating} onClose={() => setCreating(false)} />
      <AnswersDialog
        key={viewing?.id ?? "none"}
        task={viewing}
        onClose={() => setViewing(null)}
        onInvite={(card) => {
          setViewing(null);
          setInviting(card);
        }}
      />
      <InvitationDialog
        key={inviting?.anon_id ?? "none"}
        candidate={inviting}
        vacancies={vacancies.data ?? []}
        company={company}
        onClose={() => setInviting(null)}
      />
    </>
  );
}

function TaskRow({ task, onAnswers, onClose }: { task: EmployerTask; onAnswers: () => void; onClose: () => void }) {
  return (
    <article className="rounded-2xl border border-line bg-surface p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-semibold">{task.title}</h3>
          <p className="mt-1 text-sm text-muted">
            {labels.specialization[task.specialization]} · {task.grade ? labels.grade[task.grade] : "любой грейд"} ·{" "}
            {formatDate(task.created_at)}
          </p>
        </div>
        <Badge tone={task.is_active ? "success" : "neutral"}>{task.is_active ? "Активна" : "Снята"}</Badge>
      </div>
      <p className="mt-3 line-clamp-3 whitespace-pre-line text-sm leading-relaxed">{task.body}</p>
      <div className="mt-4 flex flex-wrap gap-2 border-t border-line pt-4">
        <Button variant="secondary" size="sm" onClick={onAnswers} disabled={task.answers_count === 0}>
          <MessageSquareText className="size-3.5" aria-hidden />
          Ответы: {task.answers_count}
        </Button>
        {task.is_active && (
          <Button variant="ghost" size="sm" onClick={onClose}>
            <Square className="size-3.5" aria-hidden />
            Снять
          </Button>
        )}
      </div>
    </article>
  );
}
