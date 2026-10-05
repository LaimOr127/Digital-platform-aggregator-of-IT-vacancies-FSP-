import { Building2, Check, Inbox, X } from "lucide-react";
import { useState } from "react";
import type { Offer, OfferStatus } from "../../../api/types";
import { daysLeft, formatDate, formatSalaryRange, labels } from "../../../lib/format";
import { offerTone } from "../../../lib/tones";
import { PageHeader } from "../../../ui/AppShell";
import { Badge } from "../../../ui/Badge";
import { Button } from "../../../ui/Button";
import { CursorListView } from "../../../ui/CursorListView";
import { ConfirmDialog } from "../../../ui/ConfirmDialog";
import { Dialog } from "../../../ui/Dialog";
import { Field, Textarea } from "../../../ui/form";
import { Segmented } from "../../../ui/Segmented";
import { useAction } from "../../../ui/useAction";
import { useAcceptOffer, useDeclineOffer, useInbox } from "./hooks";

type Filter = OfferStatus | "all";

const FILTERS: { value: Filter; label: string }[] = [
  { value: "sent", label: "Новые" },
  { value: "accepted", label: "Принятые" },
  { value: "all", label: "Все" },
];

export function OffersInbox() {
  const [filter, setFilter] = useState<Filter>("sent");
  const [accepting, setAccepting] = useState<Offer | null>(null);
  const [declining, setDeclining] = useState<Offer | null>(null);
  const inbox = useInbox(filter === "all" ? undefined : filter);
  const accept = useAcceptOffer();
  const run = useAction();

  return (
    <>
      <PageHeader
        title="Офферы"
        text="Оффер — итог успешного собеседования: окончательные условия от компании, с которой вы уже на связи."
      />
      <div className="mb-6">
        <Segmented label="Фильтр офферов" value={filter} options={FILTERS} onChange={setFilter} />
      </div>
      <CursorListView
        query={inbox}
        empty={{
          icon: <Inbox className="size-5" />,
          title: filter === "sent" ? "Новых офферов нет" : "Офферов пока нет",
          text: "Заполните профиль и привяжите ФСП — так вы попадёте в категории, где вас ищут работодатели.",
        }}
      >
        {(offer) => (
          <OfferCard key={offer.id} offer={offer} onAccept={() => setAccepting(offer)} onDecline={() => setDeclining(offer)} />
        )}
      </CursorListView>
      <ConfirmDialog
        open={accepting !== null}
        title={`Принять оффер «${accepting?.company_name ?? ""}»?`}
        confirmLabel="Принять и передать контакты"
        tone="primary"
        pending={accept.isPending}
        onClose={() => setAccepting(null)}
        onConfirm={() =>
          accepting && run(accept, accepting.id, "Оффер принят — компания свяжется с вами", () => setAccepting(null))
        }
      >
        Компания получит ваше имя и контакты из профиля (телефон, Telegram, email) в том виде, в каком они указаны сейчас.
        Другие компании их не увидят.
      </ConfirmDialog>
      <DeclineDialog key={declining?.id ?? "none"} offer={declining} onClose={() => setDeclining(null)} />
    </>
  );
}

function OfferCard({ offer, onAccept, onDecline }: { offer: Offer; onAccept: () => void; onDecline: () => void }) {
  const left = offer.status === "sent" ? daysLeft(offer.expires_at) : null;
  const meta = [labels.grade[offer.grade], labels.workFormat[offer.work_format], offer.city].filter(Boolean).join(" · ");
  return (
    <article className="rounded-2xl border border-line bg-surface p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="flex items-center gap-2 text-sm text-muted">
            <Building2 className="size-4" aria-hidden />
            {offer.company_name}
          </p>
          <h3 className="mt-1 text-lg font-semibold">{offer.vacancy_title}</h3>
          <p className="mt-1 text-sm text-muted">{meta}</p>
        </div>
        <Badge tone={offerTone[offer.status]}>{labels.offerStatus[offer.status]}</Badge>
      </div>
      <p className="mt-4 text-xl font-semibold tabular">{formatSalaryRange(offer.salary_min, offer.salary_max)}</p>
      {offer.message && <p className="mt-3 whitespace-pre-line text-sm leading-relaxed">{offer.message}</p>}
      <p className="mt-3 text-xs text-muted">
        Получен {formatDate(offer.created_at)}
        {left !== null && ` · ответить нужно в течение ${left} дн.`}
      </p>
      {offer.status === "sent" && (
        <div className="mt-4 flex flex-wrap gap-2 border-t border-line pt-4">
          <Button size="sm" onClick={onAccept}>
            <Check className="size-3.5" aria-hidden />
            Принять
          </Button>
          <Button variant="ghost" size="sm" onClick={onDecline}>
            <X className="size-3.5" aria-hidden />
            Отклонить
          </Button>
        </div>
      )}
      {offer.status === "accepted" && (
        <p className="mt-4 border-t border-line pt-4 text-sm text-accent">Контакты переданы компании — ждите связи.</p>
      )}
    </article>
  );
}

function DeclineDialog({ offer, onClose }: { offer: Offer | null; onClose: () => void }) {
  const run = useAction();
  const decline = useDeclineOffer();
  const [reason, setReason] = useState("");
  return (
    <Dialog open={offer !== null} title="Отклонить оффер?" onClose={onClose} busy={decline.isPending}>
      <Field label="Причина (необязательно)" hint="Компания увидит её — это помогает делать офферы точнее">
        <Textarea rows={3} value={reason} onChange={(e) => setReason(e.target.value)} maxLength={500} />
      </Field>
      <div className="mt-6 flex justify-end gap-3">
        <Button variant="ghost" onClick={onClose} disabled={decline.isPending}>
          Отмена
        </Button>
        <Button
          variant="danger"
          loading={decline.isPending}
          onClick={() => offer && run(decline, { id: offer.id, reason }, "Оффер отклонён", onClose)}
        >
          Отклонить
        </Button>
      </div>
    </Dialog>
  );
}
