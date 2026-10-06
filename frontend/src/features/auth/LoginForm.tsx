import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link } from "react-router";
import { authApi } from "../../api/endpoints";
import { ApiError } from "../../api/errors";
import type { MfaChallenge } from "../../api/types";
import { useAuth } from "../../auth/AuthProvider";
import { applyServerErrors } from "../../lib/forms";
import { Alert } from "../../ui/Alert";
import { Button } from "../../ui/Button";
import { Field, Input } from "../../ui/form";
import { ResendButton } from "./CheckEmail";
import { MfaStep } from "./MfaStep";
import { loginSchema, type LoginForm as Values } from "./schemas";

/** После входа AuthPage сам перенаправит в кабинет (с учётом ?next=).
 * Администратору сервер вместо токенов возвращает вызов второго фактора. */
export function LoginForm() {
  const [challenge, setChallenge] = useState<MfaChallenge | null>(null);
  if (challenge) return <MfaStep challenge={challenge} onRestart={() => setChallenge(null)} />;
  return <PasswordStep onChallenge={setChallenge} />;
}

function PasswordStep({ onChallenge }: { onChallenge: (challenge: MfaChallenge) => void }) {
  const { signIn } = useAuth();
  const [formError, setFormError] = useState<string | null>(null);
  // пароль верный, но почта не подтверждена: предлагаем отправить письмо ещё раз
  const [unverified, setUnverified] = useState<string | null>(null);
  const { register, handleSubmit, setError, formState } = useForm<Values>({ resolver: zodResolver(loginSchema) });
  const { errors, isSubmitting } = formState;

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    setUnverified(null);
    try {
      const result = await authApi.login(values);
      if ("mfa_token" in result) onChallenge(result);
      else await signIn(result);
    } catch (err) {
      if (err instanceof ApiError && err.code === "email_not_verified") setUnverified(values.email);
      else setFormError(applyServerErrors(err, setError, ["email", "password"]));
    }
  });

  return (
    <form onSubmit={onSubmit} noValidate className="flex flex-col gap-5">
      {formError && <Alert>{formError}</Alert>}
      {unverified && (
        <div className="flex flex-col gap-3">
          <Alert tone="warn">Подтвердите почту: откройте ссылку из письма, которое пришло после регистрации.</Alert>
          <ResendButton email={unverified} />
        </div>
      )}
      <Field label="Email" error={errors.email?.message}>
        <Input type="email" autoComplete="email" {...register("email")} />
      </Field>
      <Field label="Пароль" error={errors.password?.message}>
        <Input type="password" autoComplete="current-password" {...register("password")} />
      </Field>
      <Link to="/forgot-password" className="-mt-2 self-end text-sm text-accent hover:underline">
        Забыли пароль?
      </Link>
      <Button type="submit" size="lg" loading={isSubmitting}>
        Войти
      </Button>
    </form>
  );
}
