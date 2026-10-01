import type { ReactNode } from "react";
import { Button } from "./Button";
import { Dialog } from "./Dialog";

type Props = {
  open: boolean;
  title: string;
  confirmLabel: string;
  pending: boolean;
  onConfirm: () => void;
  onClose: () => void;
  children: ReactNode;
};

/** Подтверждение необратимого действия: закрыть нельзя, пока запрос выполняется. */
export function ConfirmDialog({ open, title, confirmLabel, pending, onConfirm, onClose, children }: Props) {
  return (
    <Dialog open={open} title={title} onClose={onClose} busy={pending}>
      <div className="text-sm text-muted">{children}</div>
      <div className="mt-6 flex justify-end gap-3">
        <Button variant="ghost" onClick={onClose} disabled={pending}>
          Отмена
        </Button>
        <Button variant="danger" onClick={onConfirm} loading={pending}>
          {confirmLabel}
        </Button>
      </div>
    </Dialog>
  );
}
