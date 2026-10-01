import { zodResolver } from "@hookform/resolvers/zod";
import { KeyRound, Link2, MailCheck, RefreshCw, Sparkles, Unlink } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link } from "react-router";
import type { FspLinkStart, FspStatus } from "../../../api/types";
import { formatDate } from "../../../lib/format";
import { applyServerErrors } from "../../../lib/forms";
import { Alert } from "../../../ui/Alert";
import { Badge } from "../../../ui/Badge";
import { Button, buttonClasses } from "../../../ui/Button";
import { Card, CardTitle } from "../../../ui/Card";
import { ConfirmDialog } from "../../../ui/ConfirmDialog";
import { Field, Input } from "../../../ui/form";
import { useToast } from "../../../ui/Toast";
import { useAction } from "../../../ui/useAction";
import { useConfirmLink, useStartLink, useSyncFsp, useUnlinkFsp } from "./hooks";
import { athleteIdSchema, codeSchema, type AthleteIdForm, type CodeForm } from "./schemas";

const DEMO_IDS = ["FSP-24001", "FSP-24002", "FSP-24003", "FSP-24004", "FSP-24006"];

/** Привязка аккаунта ФСП: ID -> код на почту владельца -> подтверждение. */
export function FspLinkCard({ status }: { status: FspStatus }) {
  if (status.linked) return <LinkedAccount status={status} />;
  return (
    <Card>
      <div className="flex items-center gap-3">
        <span className="grid size-10 place-items-center rounded-xl bg-accent/10 text-accent" aria-hidden>
          <Link2 className="size-5" />
        </span>
        <div>
          <CardTitle>Привязка аккаунта ФСП</CardTitle>
          <p className="text-sm text-muted">Код подтверждения придёт на почту, указанную в аккаунте ФСП.</p>
        </div>
      </div>
      <LinkSteps status={status} />
    </Card>
  );
}

function LinkSteps({ status }: { status: FspStatus }) {
  const [started, setStarted] = useState<(FspLinkStart & { athleteId: string }) | null>(null);
  const [editing, setEditing] = useState(false);
  const pendingId = started?.athleteId ?? status.pending_athlete_id;
  if (pendingId && !editing) {
    return <CodeStep athleteId={pendingId} started={started} onChangeId={() => setEditing(true)} />;
  }
  return (
    <IdStep
      demo={status.demo_mode}
      onStarted={(result) => {
        setStarted(result);
        setEditing(false);
      }}
    />
  );
}

function IdStep({ demo, onStarted }: { demo: boolean; onStarted: (r: FspLinkStart & { athleteId: string }) => void }) {
  const start = useStartLink();
  const [formError, setFormError] = useState<string | null>(null);
  const form = useForm<AthleteIdForm>({ resolver: zodResolver(athleteIdSchema), defaultValues: { athlete_id: "" } });
  const onSubmit = form.handleSubmit(async ({ athlete_id }) => {
    setFormError(null);
    try {
      onStarted({ ...(await start.mutateAsync(athlete_id)), athleteId: athlete_id });
    } catch (err) {
      setFormError(applyServerErrors(err, form.setError, ["athlete_id"]));
    }
  });
  return (
    <form onSubmit={onSubmit} noValidate className="mt-6 flex flex-col gap-4">
      {formError && <Alert>{formError}</Alert>}
      <Field label="ID спортсмена в ФСП" error={form.formState.errors.athlete_id?.message} hint="Указан в личном кабинете ФСП">
        <Input placeholder="FSP-24001" autoComplete="off" className="uppercase" {...form.register("athlete_id")} />
      </Field>
      {demo && (
        <Alert tone="info">
          Демо-стенд с моком ФСП. Попробуйте ID:{" "}
          {DEMO_IDS.map((id, i) => (
            <span key={id}>
              <button type="button" className="font-medium underline" onClick={() => form.setValue("athlete_id", id)}>
                {id}
              </button>
              {i < DEMO_IDS.length - 1 ? ", " : ""}
            </span>
          ))}
        </Alert>
      )}
      <Button type="submit" loading={form.formState.isSubmitting} className="self-start">
        <MailCheck className="size-4" aria-hidden />
        Получить код
      </Button>
    </form>
  );
}

type CodeStepProps = { athleteId: string; started: FspLinkStart | null; onChangeId: () => void };

function CodeStep({ athleteId, started, onChangeId }: CodeStepProps) {
  const notify = useToast();
  const confirm = useConfirmLink();
  const [formError, setFormError] = useState<string | null>(null);
  const form = useForm<CodeForm>({ resolver: zodResolver(codeSchema), defaultValues: { code: "" } });
  const onSubmit = form.handleSubmit(async ({ code }) => {
    setFormError(null);
    try {
      const status = await confirm.mutateAsync(code);
      notify(
        status?.last_synced_at
          ? "Аккаунт ФСП привязан — достижения загружены"
          : "Аккаунт ФСП привязан. ФСП сейчас не отвечает — достижения подгрузятся автоматически",
      );
    } catch (err) {
      setFormError(applyServerErrors(err, form.setError, ["code"]));
    }
  });
  return (
    <form onSubmit={onSubmit} noValidate className="mt-6 flex flex-col gap-4">
      <p className="text-sm" role="status">
        Код для <span className="font-medium">{athleteId}</span> отправлен
        {started ? ` на ${started.email_masked}` : " на почту аккаунта ФСП"}. Он действует 10 минут.
      </p>
      {started?.demo_code && (
        <Alert tone="info">
          Демо-режим: письма не отправляются, код — <span className="font-mono font-semibold">{started.demo_code}</span>.{" "}
          <button type="button" className="font-medium underline" onClick={() => form.setValue("code", started.demo_code ?? "")}>
            Подставить
          </button>
        </Alert>
      )}
      {formError && <Alert>{formError}</Alert>}
      <Field label="Код из письма" error={form.formState.errors.code?.message}>
        {/* фокус сразу на поле кода: шаг ввода ID (и кнопка в фокусе) исчезает */}
        <Input
          autoFocus
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={6}
          className="max-w-40 font-mono tracking-widest"
          {...form.register("code")}
        />
      </Field>
      <div className="flex flex-wrap gap-3">
        <Button type="submit" loading={confirm.isPending}>
          <KeyRound className="size-4" aria-hidden />
          Подтвердить
        </Button>
        <Button variant="ghost" onClick={onChangeId}>
          Другой ID или новый код
        </Button>
      </div>
    </form>
  );
}

function LinkedAccount({ status }: { status: FspStatus }) {
  const run = useAction();
  const sync = useSyncFsp();
  const unlink = useUnlinkFsp();
  const [confirming, setConfirming] = useState(false);
  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <CardTitle>Аккаунт ФСП {status.athlete_id}</CardTitle>
            <Badge tone="accent">Привязан</Badge>
          </div>
          <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
            <dt className="text-muted">Разряд</dt>
            <dd>{status.rank ?? "нет"}</dd>
            <dt className="text-muted">Регион</dt>
            <dd>{status.region ?? "не указан"}</dd>
            <dt className="text-muted">Обновлено</dt>
            <dd>{status.last_synced_at ? formatDate(status.last_synced_at) : "—"}</dd>
          </dl>
          <Link to="/app?import=fsp" className={buttonClasses("primary", "sm", "mt-4")}>
            <Sparkles className="size-3.5" aria-hidden />
            Заполнить профиль из анкеты ФСП
          </Link>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={() => run(sync, undefined, "Данные ФСП обновлены")} loading={sync.isPending}>
            <RefreshCw className="size-3.5" aria-hidden />
            Обновить
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setConfirming(true)}>
            <Unlink className="size-3.5" aria-hidden />
            Отвязать
          </Button>
        </div>
      </div>
      <ConfirmDialog
        open={confirming}
        title="Отвязать аккаунт ФСП?"
        confirmLabel="Отвязать"
        pending={unlink.isPending}
        onClose={() => setConfirming(false)}
        onConfirm={() => run(unlink, undefined, "Аккаунт ФСП отвязан", () => setConfirming(false))}
      >
        Достижения и категории удалятся из профиля, уровень подтверждения станет «Заявлено кандидатом», а действующий
        паспорт навыков будет отозван — он больше не подтверждён данными ФСП.
      </ConfirmDialog>
    </Card>
  );
}
