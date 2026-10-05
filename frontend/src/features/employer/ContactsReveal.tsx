// Контакты кандидата запрашиваются явно: каждое раскрытие фиксируется в журнале аудита.
import type { UseMutationResult } from "@tanstack/react-query";
import { Contact } from "lucide-react";
import { useState } from "react";
import { errorMessage } from "../../api/errors";
import type { OfferContacts } from "../../api/types";
import { Button } from "../../ui/Button";
import { useToast } from "../../ui/Toast";

type Props = { reveal: UseMutationResult<OfferContacts, Error, string>; id: string; note: string };

export function ContactsReveal({ reveal, id, note }: Props) {
  const notify = useToast();
  const [contacts, setContacts] = useState<OfferContacts | null>(null);
  const open = () => reveal.mutate(id, { onSuccess: setContacts, onError: (err) => notify(errorMessage(err), "error") });

  if (!contacts) {
    return (
      <div className="mt-4 border-t border-line pt-4">
        <Button size="sm" onClick={open} loading={reveal.isPending}>
          <Contact className="size-3.5" aria-hidden />
          Показать контакты
        </Button>
      </div>
    );
  }
  const rows = [
    ["Имя", contacts.full_name],
    ["Telegram", contacts.telegram],
    ["Телефон", contacts.phone],
    ["Email", contacts.email],
  ].filter(([, value]) => value);
  return (
    <div className="mt-4 rounded-xl border border-accent/30 bg-accent/5 p-4">
      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
        {rows.map(([label, value]) => (
          <div key={label} className="contents">
            <dt className="text-muted">{label}</dt>
            <dd className="font-medium">{value}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-3 text-xs text-muted">Просмотр контактов записан в журнал — {note}.</p>
    </div>
  );
}
