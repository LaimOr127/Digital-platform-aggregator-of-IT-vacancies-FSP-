import { zodResolver } from "@hookform/resolvers/zod";
import { KeyRound, ShieldCheck } from "lucide-react";
import { useState, type FormEventHandler, type ReactNode } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { authApi } from "../../api/endpoints";
import { ApiError, errorMessage } from "../../api/errors";
import type { MfaChallenge, MfaSetup } from "../../api/types";
import { useAuth } from "../../auth/AuthProvider";
import { Alert } from "../../ui/Alert";
import { Button } from "../../ui/Button";
import { Field, Input } from "../../ui/form";
import { QrCode } from "../../ui/QrCode";

const codeSchema = z.object({ code: z.string().trim().regex(/^\d{6}$/, "Код из 6 цифр") });
const enrollSchema = z.object({ enrollment: z.string().trim().min(8, "Код подключения — не короче 8 символов") });

type Props = { challenge: MfaChallenge; onRestart: () => void };
type Failure = { text: string; expired: boolean };

const failure = (err: unknown): Failure => ({
  text: errorMessage(err),
  expired: err instanceof ApiError && err.code === "mfa_expired",
});

/** Второй шаг входа администратора: при первом входе — подключение аутентификатора
 * по коду из CLI (секрет показывается один раз), затем — код из приложения. */
export function MfaStep({ challenge, onRestart }: Props) {
  // секрет живёт только в состоянии компонента: не кэшируется и исчезает после входа
  const [setup, setSetup] = useState<MfaSetup | null>(null);
  const needsSetup = !challenge.enrolled && setup === null;
  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-start gap-3 rounded-xl border border-accent/30 bg-accent/5 p-4 text-sm">
        <ShieldCheck className="mt-0.5 size-5 shrink-0 text-accent" aria-hidden />
        <p>
          Для администраторов вход защищён вторым фактором.{" "}
          {needsSetup
            ? "Введите код подключения, который выдала команда make create-admin или make reset-admin-2fa."
            : challenge.enrolled
              ? "Введите код из приложения-аутентификатора."
              : "Отсканируйте QR-код в Google Authenticator, Яндекс Ключе или аналоге и введите код."}
        </p>
      </div>
      {setup && <SetupInfo setup={setup} />}
      {needsSetup ? (
        <EnrollForm mfaToken={challenge.mfa_token} onReady={setSetup} onRestart={onRestart} />
      ) : (
        <CodeForm mfaToken={challenge.mfa_token} onRestart={onRestart} />
      )}
    </div>
  );
}

type EnrollProps = { mfaToken: string; onReady: (setup: MfaSetup) => void; onRestart: () => void };

function EnrollForm({ mfaToken, onReady, onRestart }: EnrollProps) {
  const [error, setError] = useState<Failure | null>(null);
  const form = useForm({ resolver: zodResolver(enrollSchema), defaultValues: { enrollment: "" } });
  const onSubmit = form.handleSubmit(async ({ enrollment }) => {
    setError(null);
    try {
      onReady(await authApi.mfaSetup(mfaToken, enrollment));
    } catch (err) {
      setError(failure(err));
    }
  });
  return (
    <StepForm onSubmit={onSubmit} error={error} onRestart={onRestart} submitting={form.formState.isSubmitting} label="Продолжить">
      <Field label="Код подключения" error={form.formState.errors.enrollment?.message}>
        <Input autoFocus autoComplete="off" spellCheck={false} className="font-mono" {...form.register("enrollment")} />
      </Field>
    </StepForm>
  );
}

function CodeForm({ mfaToken, onRestart }: { mfaToken: string; onRestart: () => void }) {
  const { signIn } = useAuth();
  const [error, setError] = useState<Failure | null>(null);
  const form = useForm({ resolver: zodResolver(codeSchema), defaultValues: { code: "" } });
  const onSubmit = form.handleSubmit(async ({ code }) => {
    setError(null);
    try {
      await signIn(await authApi.mfaVerify(mfaToken, code));
    } catch (err) {
      setError(failure(err));
      form.setValue("code", "");
    }
  });
  return (
    <StepForm onSubmit={onSubmit} error={error} onRestart={onRestart} submitting={form.formState.isSubmitting} label="Войти">
      <Field label="Код из приложения" error={form.formState.errors.code?.message}>
        <Input
          autoFocus
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={6}
          className="font-mono tracking-widest"
          {...form.register("code")}
        />
      </Field>
    </StepForm>
  );
}

type StepFormProps = {
  onSubmit: FormEventHandler<HTMLFormElement>;
  error: Failure | null;
  onRestart: () => void;
  submitting: boolean;
  label: string;
  children: ReactNode;
};

/** Общая разметка шага: ошибка (с предложением начать заново, если шаг истёк), поле, кнопки. */
function StepForm({ onSubmit, error, onRestart, submitting, label, children }: StepFormProps) {
  return (
    <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
      {error && (
        <Alert>
          {error.text}
          {error.expired && (
            <button type="button" onClick={onRestart} className="ml-2 font-medium underline">
              Войти заново
            </button>
          )}
        </Alert>
      )}
      {children}
      <Button type="submit" size="lg" loading={submitting}>
        <KeyRound className="size-4" aria-hidden />
        {label}
      </Button>
      <Button variant="ghost" onClick={onRestart}>
        Другой аккаунт
      </Button>
    </form>
  );
}

function SetupInfo({ setup }: { setup: MfaSetup }) {
  const grouped = setup.secret.match(/.{1,4}/g)?.join(" ") ?? setup.secret;
  return (
    <div className="flex flex-col items-center gap-3 sm:flex-row sm:items-start">
      <QrCode value={setup.otpauth_uri} size={150} label="QR-код для приложения-аутентификатора" />
      <div className="text-sm">
        <p className="text-muted">Не получается отсканировать? Введите ключ вручную:</p>
        <p className="mt-2 select-all break-all font-mono text-sm">{grouped}</p>
        <p className="mt-2 text-xs text-muted">Ключ показывается один раз. Сохраните доступ к приложению.</p>
      </div>
    </div>
  );
}
