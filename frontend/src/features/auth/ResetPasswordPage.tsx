import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { authApi } from "../../api/endpoints";
import { ApiError } from "../../api/errors";
import { applyServerErrors } from "../../lib/forms";
import { forgetLinkToken, readLinkToken } from "../../lib/linkToken";
import { Alert } from "../../ui/Alert";
import { Button } from "../../ui/Button";
import { Field, Input } from "../../ui/form";
import { AuthLayout } from "./AuthLayout";
import { resetPasswordSchema, type ResetPasswordForm } from "./schemas";
import { StatusPanel } from "./StatusPanel";

type Outcome = "done" | "invalid" | null;
const NEW_LINK = { to: "/forgot-password", label: "Запросить новую ссылку" };

/** Новый пароль по ссылке из письма: все прежние сессии завершаются. */
export default function ResetPasswordPage() {
  const [token] = useState(() => readLinkToken());
  useEffect(forgetLinkToken, []);
  const [outcome, setOutcome] = useState<Outcome>(token ? null : "invalid");
  const [formError, setFormError] = useState<string | null>(null);
  const form = useForm<ResetPasswordForm>({ resolver: zodResolver(resetPasswordSchema) });
  const { errors, isSubmitting } = form.formState;

  const onSubmit = form.handleSubmit(async ({ password }) => {
    setFormError(null);
    try {
      await authApi.resetPassword(token ?? "", password);
      setOutcome("done");
    } catch (err) {
      if (err instanceof ApiError && err.code === "invalid_link") setOutcome("invalid");
      else setFormError(applyServerErrors(err, form.setError, ["password"]));
    }
  });

  return (
    <AuthLayout title="Новый пароль">
      {outcome === "done" && (
        <StatusPanel ok title="Пароль изменён" action={{ to: "/login", label: "Войти" }}>
          Все прежние сессии завершены — войдите с новым паролем.
        </StatusPanel>
      )}
      {outcome === "invalid" && (
        <StatusPanel ok={false} title="Ссылка недействительна" action={NEW_LINK}>
          Ссылка устарела, уже использована или открыта не полностью. Запросите новую — она действует 1 час.
        </StatusPanel>
      )}
      {outcome === null && (
        <form onSubmit={onSubmit} noValidate className="flex flex-col gap-5">
          {formError && <Alert>{formError}</Alert>}
          <Field label="Новый пароль" error={errors.password?.message} hint="Не короче 10 символов, буквы и цифры или символы">
            <Input type="password" autoComplete="new-password" autoFocus {...form.register("password")} />
          </Field>
          <Field label="Повторите пароль" error={errors.confirm?.message}>
            <Input type="password" autoComplete="new-password" {...form.register("confirm")} />
          </Field>
          <Button type="submit" size="lg" loading={isSubmitting}>
            Сохранить пароль
          </Button>
        </form>
      )}
    </AuthLayout>
  );
}
