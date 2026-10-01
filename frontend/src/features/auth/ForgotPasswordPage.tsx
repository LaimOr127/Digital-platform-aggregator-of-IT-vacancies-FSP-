import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link } from "react-router";
import { authApi } from "../../api/endpoints";
import { applyServerErrors } from "../../lib/forms";
import { Alert } from "../../ui/Alert";
import { Button } from "../../ui/Button";
import { Field, Input } from "../../ui/form";
import { AuthLayout } from "./AuthLayout";
import { forgotPasswordSchema, type ForgotPasswordForm } from "./schemas";
import { StatusPanel } from "./StatusPanel";

/** Запрос ссылки для сброса пароля. Ответ одинаковый для любого адреса. */
export default function ForgotPasswordPage() {
  const [sent, setSent] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const form = useForm<ForgotPasswordForm>({ resolver: zodResolver(forgotPasswordSchema) });

  const onSubmit = form.handleSubmit(async ({ email }) => {
    setFormError(null);
    try {
      await authApi.forgotPassword(email);
      setSent(true);
    } catch (err) {
      setFormError(applyServerErrors(err, form.setError, ["email"]));
    }
  });

  return (
    <AuthLayout
      title="Восстановление пароля"
      subtitle={
        <>
          Вспомнили?{" "}
          <Link to="/login" className="font-medium text-accent hover:underline">
            Войти
          </Link>
        </>
      }
    >
      {sent ? (
        <StatusPanel ok title="Проверьте почту" action={{ to: "/login", label: "Ко входу" }}>
          Если адрес зарегистрирован, мы отправили письмо со ссылкой для нового пароля. Ссылка действует 1 час.
        </StatusPanel>
      ) : (
        <form onSubmit={onSubmit} noValidate className="flex flex-col gap-5">
          {formError && <Alert>{formError}</Alert>}
          <Field label="Email" error={form.formState.errors.email?.message}>
            <Input type="email" autoComplete="email" autoFocus {...form.register("email")} />
          </Field>
          <Button type="submit" size="lg" loading={form.formState.isSubmitting}>
            Отправить ссылку
          </Button>
        </form>
      )}
    </AuthLayout>
  );
}
