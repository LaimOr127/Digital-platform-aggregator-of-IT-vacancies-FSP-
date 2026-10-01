import { Copy, ExternalLink, FileBadge, RotateCw, ShieldOff } from "lucide-react";
import { useState } from "react";
import type { Passport, PassportPayload, VerificationTier } from "../../../api/types";
import { formatDate, labels } from "../../../lib/format";
import { Alert } from "../../../ui/Alert";
import { Button } from "../../../ui/Button";
import { Card, CardTitle } from "../../../ui/Card";
import { ConfirmDialog } from "../../../ui/ConfirmDialog";
import { Switch } from "../../../ui/form";
import { QrCode } from "../../../ui/QrCode";
import { useToast } from "../../../ui/Toast";
import { useAction } from "../../../ui/useAction";
import { useIssuePassport, useRevokePassport } from "./hooks";

export const passportUrl = (id: string) => `${window.location.origin}/passport/${id}`;

type Props = { passport: Passport | null; tier: VerificationTier };

/** Паспорт навыков: проверяемая ссылка для работодателей на любой площадке. */
export function PassportCard({ passport, tier }: Props) {
  const run = useAction();
  const issue = useIssuePassport();
  const [showName, setShowName] = useState(false);
  const issueNow = () =>
    run(issue, showName, passport ? "Паспорт перевыпущен, старая ссылка отозвана" : "Паспорт навыков выпущен");

  return (
    <Card className="border-accent/30">
      <div className="flex items-center gap-3">
        <span className="grid size-10 place-items-center rounded-xl bg-accent/10 text-accent" aria-hidden>
          <FileBadge className="size-5" />
        </span>
        <div>
          <CardTitle>Паспорт навыков</CardTitle>
          <p className="text-sm text-muted">Ссылка с электронной подписью — подлинность проверит любой работодатель.</p>
        </div>
      </div>

      {passport ? (
        <ActivePassport passport={passport} />
      ) : (
        <p className="mt-5 text-sm leading-relaxed text-muted">
          В паспорт попадут должность, грейд, навыки, результаты ФСП и категории. Изменить выпущенный паспорт нельзя — только
          перевыпустить: так работодатель уверен, что видит подписанные данные.
        </p>
      )}

      {tier !== "verified_fsp" && (
        <div className="mt-5">
          <Alert tone="warn">
            Профиль не подтверждён ФСП — паспорт будет с отметкой «{labels.tier[tier]}». Привяжите аккаунт ФСП выше.
          </Alert>
        </div>
      )}

      <div className="mt-5 flex flex-col gap-4 border-t border-line pt-5">
        <Switch
          label="Показывать имя и ID ФСП"
          description="Имя берётся из ФСП (подтверждённое). Анонимный паспорт обобщает достижения, чтобы вас нельзя было найти по протоколам"
          checked={showName}
          onChange={(e) => setShowName(e.target.checked)}
        />
        <Button onClick={issueNow} loading={issue.isPending} className="self-start">
          {passport ? <RotateCw className="size-4" aria-hidden /> : <FileBadge className="size-4" aria-hidden />}
          {passport ? "Перевыпустить" : "Выпустить паспорт"}
        </Button>
      </div>
    </Card>
  );
}

function ActivePassport({ passport }: { passport: Passport }) {
  const notify = useToast();
  const run = useAction();
  const revoke = useRevokePassport();
  const [confirming, setConfirming] = useState(false);
  const url = passportUrl(passport.id);
  const payload = passport.payload as PassportPayload;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(url);
      notify("Ссылка скопирована");
    } catch {
      notify("Не удалось скопировать — выделите ссылку вручную", "error");
    }
  };

  return (
    <div className="mt-5 flex flex-col gap-5 sm:flex-row">
      <QrCode value={url} size={140} label="QR-код ссылки на паспорт навыков" />
      <div className="flex min-w-0 flex-1 flex-col gap-3">
        <p className="text-sm text-muted">
          Выпущен {formatDate(passport.issued_at)} · {payload.holder.name ? `с именем «${payload.holder.name}»` : "анонимный"}
        </p>
        <label className="sr-only" htmlFor="passport-url">
          Ссылка на паспорт
        </label>
        <input
          id="passport-url"
          readOnly
          value={url}
          onFocus={(e) => e.currentTarget.select()}
          className="h-10 w-full rounded-lg border border-line bg-surface-2 px-3 font-mono text-xs"
        />
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" size="sm" onClick={copy}>
            <Copy className="size-3.5" aria-hidden />
            Скопировать
          </Button>
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex h-8 items-center gap-2 rounded-lg border border-line bg-surface-2 px-3 text-sm font-medium hover:border-muted/60"
          >
            <ExternalLink className="size-3.5" aria-hidden />
            Открыть
          </a>
          <Button variant="ghost" size="sm" onClick={() => setConfirming(true)}>
            <ShieldOff className="size-3.5" aria-hidden />
            Отозвать
          </Button>
        </div>
      </div>
      <ConfirmDialog
        open={confirming}
        title="Отозвать паспорт?"
        confirmLabel="Отозвать"
        pending={revoke.isPending}
        onClose={() => setConfirming(false)}
        onConfirm={() => run(revoke, undefined, "Паспорт отозван", () => setConfirming(false))}
      >
        По ссылке и QR-коду работодатели увидят только то, что паспорт отозван, — без ваших данных. Новый паспорт можно
        выпустить в любой момент.
      </ConfirmDialog>
    </div>
  );
}
