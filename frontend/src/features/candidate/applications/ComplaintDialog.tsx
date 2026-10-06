// Жалоба на вакансию: фиктивная компания, неверная вилка, дискриминация, спам. Видит модератор.
import { useState } from "react";
import type { BoardVacancy, ComplaintReason } from "../../../api/types";
import { Button } from "../../../ui/Button";
import { Dialog } from "../../../ui/Dialog";
import { Field, Select, Textarea } from "../../../ui/form";
import { useAction } from "../../../ui/useAction";
import { useComplain } from "./hooks";

const REASONS: { value: ComplaintReason; label: string }[] = [
  { value: "fake", label: "Фиктивная вакансия или компания" },
  { value: "salary", label: "Вилка не соответствует действительности" },
  { value: "discrimination", label: "Дискриминация" },
  { value: "spam", label: "Спам, сбор данных, платное «обучение»" },
  { value: "other", label: "Другое" },
];

export function ComplaintDialog({ vacancy, onClose }: { vacancy: BoardVacancy | null; onClose: () => void }) {
  const complain = useComplain();
  const run = useAction();
  const [reason, setReason] = useState<ComplaintReason>("fake");
  const [comment, setComment] = useState("");
  return (
    <Dialog open={vacancy !== null} title="Пожаловаться на вакансию" onClose={onClose} busy={complain.isPending}>
      <p className="text-sm text-muted">
        «{vacancy?.title}» в компании «{vacancy?.company.name}». Жалобу проверит модератор; компания не узнает, кто её
        отправил.
      </p>
      <Field label="Причина" className="mt-4">
        <Select options={REASONS} value={reason} onChange={(e) => setReason(e.target.value as ComplaintReason)} />
      </Field>
      <Field label="Подробности (необязательно)" className="mt-4">
        <Textarea rows={3} maxLength={500} value={comment} onChange={(e) => setComment(e.target.value)} />
      </Field>
      <div className="mt-6 flex justify-end gap-3">
        <Button variant="ghost" onClick={onClose} disabled={complain.isPending}>
          Отмена
        </Button>
        <Button
          variant="danger"
          loading={complain.isPending}
          onClick={() =>
            vacancy &&
            run(complain, { id: vacancy.id, body: { reason, comment: comment.trim() } }, "Жалоба отправлена модератору", onClose)
          }
        >
          Отправить жалобу
        </Button>
      </div>
    </Dialog>
  );
}
