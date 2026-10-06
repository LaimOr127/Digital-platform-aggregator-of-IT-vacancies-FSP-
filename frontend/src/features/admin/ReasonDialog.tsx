import { useState, type ReactNode } from "react";
import { Button } from "../../ui/Button";
import { Dialog } from "../../ui/Dialog";
import { Field, Textarea } from "../../ui/form";

const MIN_REASON = 5;

type Props = {
  open: boolean;
  title: string;
  confirmLabel: string;
  pending: boolean;
  onConfirm: (reason: string) => void;
  onClose: () => void;
  children: ReactNode;
  /** danger — блокировка; primary — снятие блокировки */
  tone?: "danger" | "primary";
};

/** Действие модератора с обязательной причиной — она попадает в журнал аудита.
 * Монтируйте с key объекта, чтобы причина не переносилась между объектами. */
export function ReasonDialog({ open, title, confirmLabel, pending, onConfirm, onClose, children, tone = "danger" }: Props) {
  const [reason, setReason] = useState("");
  const trimmed = reason.trim();
  return (
    <Dialog open={open} title={title} onClose={onClose} busy={pending}>
      <div className="mb-4 text-sm text-muted">{children}</div>
      <Field label="Причина" hint={`Не короче ${MIN_REASON} символов, попадёт в журнал аудита`}>
        <Textarea rows={3} value={reason} onChange={(e) => setReason(e.target.value)} maxLength={500} />
      </Field>
      <div className="mt-6 flex justify-end gap-3">
        <Button variant="ghost" onClick={onClose} disabled={pending}>
          Отмена
        </Button>
        <Button variant={tone} onClick={() => onConfirm(trimmed)} disabled={trimmed.length < MIN_REASON} loading={pending}>
          {confirmLabel}
        </Button>
      </div>
    </Dialog>
  );
}
