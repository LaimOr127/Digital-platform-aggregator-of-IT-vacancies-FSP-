import { Inbox, Undo2 } from "lucide-react";
import { useState } from "react";
import type { EmployerOffer, OfferStatus } from "../../../api/types";
import { daysLeft, formatDate, labels } from "../../../lib/format";
import { offerTone } from "../../../lib/tones";
import { PageHeader } from "../../../ui/AppShell";
import { Badge } from "../../../ui/Badge";
import { Button } from "../../../ui/Button";
import { CursorListView } from "../../../ui/CursorListView";
import { ConfirmDialog } from "../../../ui/ConfirmDialog";
import { Segmented } from "../../../ui/Segmented";
import { useAction } from "../../../ui/useAction";
import { useEmployerOffers, useOfferContacts, useWithdrawOffer } from "../catalog/hooks";
import { ContactsReveal } from "../ContactsReveal";
import { Salary } from "../../../ui/Salary";

type Filter = OfferStatus | "all";

const FILTERS: { value: Filter; label: string }[] = [
  { value: "all", label: "Все" },
  { value: "sent", label: "Ждут ответа" },
  { value: "accepted", label: "Приняты" },
  { value: "declined", label: "Отклонены" },
  { value: "withdrawn", label: "Отозваны" },
  { value: "expired", label: "Истекли" },
];

export function EmployerOffersPage() {
  const [filter, setFilter] = useState<Filter>("all");
  const [withdrawing, setWithdrawing] = useState<EmployerOffer | null>(null);
  const offers = useEmployerOffers(filter === "all" ? undefined : filter);
  const withdraw = useWithdrawOffer();
  const run = useAction();

  return (
    <>
      <PageHeader
        title="Офферы"
        text="Оффер — итог успешного собеседования. Кандидат отвечает в течение 7 дней."
      />
      <div className="mb-6">
        <Segmented label="Статус офферов" value={filter} options={FILTERS} onChange={setFilter} />
      </div>
      <CursorListView
        query={offers}
        empty={{
          icon: <Inbox className="size-5" />,
          title: "Офферов пока нет",
          text: "Найдите кандидата в каталоге и предложите ему вакансию с зарплатной вилкой.",
        }}
      >
        {(offer) => <OfferRow key={offer.id} offer={offer} onWithdraw={() => setWithdrawing(offer)} />}
      </CursorListView>
      <ConfirmDialog
        open={withdrawing !== null}
        title="Отозвать оффер?"
        confirmLabel="Отозвать"
        pending={withdraw.isPending}
        onClose={() => setWithdrawing(null)}
        onConfirm={() => withdrawing && run(withdraw, withdrawing.id, "Оффер отозван", () => setWithdrawing(null))}
      >
        Кандидат увидит, что оффер отозван, и не сможет его принять.
      </ConfirmDialog>
    </>
  );
}

function OfferRow({ offer, onWithdraw }: { offer: EmployerOffer; onWithdraw: () => void }) {
  const contacts = useOfferContacts();
  const left = offer.status === "sent" ? daysLeft(offer.expires_at) : null;
  const who = offer.candidate
    ? `Кандидат #${offer.candidate.anon_id.slice(0, 6).toUpperCase()} · ${offer.candidate.title ?? "должность не указана"}`
    : "Кандидат скрыл профиль из каталога";
  return (
    <article className="rounded-2xl border border-line bg-surface p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold">{offer.vacancy_title}</h3>
          <p className="mt-1 text-sm text-muted">{who}</p>
        </div>
        <Badge tone={offerTone[offer.status]}>{labels.offerStatus[offer.status]}</Badge>
      </div>
      <p className="mt-3 text-sm">
        <span className="font-medium tabular"><Salary min={offer.salary_min} max={offer.salary_max} /></span>
        <span className="text-muted"> · отправлен {formatDate(offer.created_at)}</span>
        {left !== null && <span className="text-muted"> · на ответ осталось дней: {left}</span>}
      </p>
      {offer.decline_reason && <p className="mt-2 text-sm text-muted">Причина отказа: {offer.decline_reason}</p>}
      {offer.status === "accepted" && (
        <ContactsReveal reveal={contacts} id={offer.id} note="кандидат передал их, приняв оффер" />
      )}
      {offer.status === "sent" && (
        <div className="mt-4 border-t border-line pt-4">
          <Button variant="ghost" size="sm" onClick={onWithdraw}>
            <Undo2 className="size-3.5" aria-hidden />
            Отозвать
          </Button>
        </div>
      )}
    </article>
  );
}
