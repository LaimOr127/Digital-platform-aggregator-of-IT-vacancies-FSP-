import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { authApi } from "../../api/endpoints";
import { useAuth } from "../../auth/AuthProvider";
import { applyServerErrors } from "../../lib/forms";
import { Alert } from "../../ui/Alert";
import { Button } from "../../ui/Button";
import { Field, Input } from "../../ui/form";
import { loginSchema, type LoginForm as Values } from "./schemas";

/** После входа AuthPage сам перенаправит в кабинет (с учётом ?next=). */
export function LoginForm() {
  const { signIn } = useAuth();
  const [formError, setFormError] = useState<string | null>(null);
  const { register, handleSubmit, setError, formState } = useForm<Values>({ resolver: zodResolver(loginSchema) });
  const { errors, isSubmitting } = formState;

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      await signIn(await authApi.login(values));
    } catch (err) {
      setFormError(applyServerErrors(err, setError, ["email", "password"]));
    }
  });

  return (
    <form onSubmit={onSubmit} noValidate className="flex flex-col gap-5">
      {formError && <Alert>{formError}</Alert>}
      <Field label="Email" error={errors.email?.message}>
        <Input type="email" autoComplete="email" {...register("email")} />
      </Field>
      <Field label="Пароль" error={errors.password?.message}>
        <Input type="password" autoComplete="current-password" {...register("password")} />
      </Field>
      <Button type="submit" size="lg" loading={isSubmitting}>
        Войти
      </Button>
    </form>
  );
}
