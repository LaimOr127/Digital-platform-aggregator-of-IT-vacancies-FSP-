// Ответы на задачу: анонимная карточка автора, текст, оценка 1–5 и приглашение.
import { UserRound, MessageSquareText, Send } from "lucide-react";
import { useState } from "react";
import type { CandidateCard, EmployerTask, TaskAnswer } from "../../../api/types";
import { formatDate } from "../../../lib/format";
import { Button } from "../../../ui/Button";
import { CursorListView } from "../../../ui/CursorListView";
import { Dialog } from "../../../ui/Dialog";
import { Segmented } from "../../../ui/Segmented";
import { useAction } from "../../../ui/useAction";
import { CandidateCardView } from "../catalog/CandidateCardView";
import { useRateAnswer, useTaskAnswers } from "./hooks";

type Props = { task: EmployerTask | null; onClose: () => void; onInvite: (card: CandidateCard) => void };

export function AnswersDialog({ task, onClose, onInvite }: Props) {
  return (
    <Dialog open={task !== null} title={task ? `Ответы на задачу «${task.title}»` : "Ответы"} onClose={onClose} wide>
      {task && <AnswersList taskId={task.id} onInvite={onInvite} />}
    </Dialog>
  );
}

function AnswersList({ taskId, onInvite }: { taskId: string; onInvite: (card: CandidateCard) => void }) {
  const answers = useTaskAnswers(taskId);
  return (
    <CursorListView query={answers} empty={{ icon: <MessageSquareText className="size-5" />, title: "Ответов пока нет", text: "Кандидаты получают задачу раз в неделю." }}>
      {(answer) => <AnswerRow key={answer.id} taskId={taskId} answer={answer} onInvite={onInvite} />}
    </CursorListView>
  );
}

const RATINGS = ["1", "2", "3", "4", "5"].map((value) => ({ value, label: value }));

function AnswerRow({ taskId, answer, onInvite }: { taskId: string; answer: TaskAnswer; onInvite: (card: CandidateCard) => void }) {
  const rate = useRateAnswer();
  const run = useAction();
  const [showCard, setShowCard] = useState(false);
  const card = answer.candidate;
  return (
    <article className="rounded-xl border border-line bg-surface-2 p-4">
      <p className="text-sm text-muted">
        {card
          ? `Кандидат #${card.anon_id.slice(0, 6).toUpperCase()}${card.category ? ` · ${card.category.title}` : ""}`
          : "Кандидат скрыл профиль из каталога"}{" "}
        · {formatDate(answer.created_at)}
      </p>
      <p className="mt-2 whitespace-pre-line text-sm leading-relaxed">{answer.answer}</p>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <span className="text-sm text-muted">Оценка</span>
        <Segmented
          label="Оценка ответа"
          value={answer.rating ? String(answer.rating) : ""}
          options={RATINGS}
          onChange={(value) => run(rate, { taskId, answerId: answer.id, rating: Number(value) }, "Оценка сохранена")}
        />
        {card && (
          <Button variant="secondary" size="sm" aria-expanded={showCard} onClick={() => setShowCard((v) => !v)}>
            <UserRound className="size-3.5" aria-hidden />
            {showCard ? "Скрыть карточку" : "Карточка кандидата"}
          </Button>
        )}
        {card && (
          <Button size="sm" onClick={() => onInvite(card)}>
            <Send className="size-3.5" aria-hidden />
            Пригласить
          </Button>
        )}
      </div>
      {card && showCard && <CandidateCardView card={card} className="mt-3" />}
    </article>
  );
}
