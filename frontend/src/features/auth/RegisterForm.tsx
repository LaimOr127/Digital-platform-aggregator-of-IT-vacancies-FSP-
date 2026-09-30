import { zodResolver } from "@hookform/resolvers/zod";
import { useState, type ReactNode } from "react";
import { useForm, type FieldValues, type UseFormSetError } from "react-hook-form";
import { useNavigate } from "react-router";
import { authApi } from "../../api/endpoints";
import type { TokenOut } from "../../api/types";
import { useAuth } from "../../auth/AuthProvider";
import { portalPath } from "../../auth/portal";
import { applyServerErrors } from "../../lib/forms";
import { Alert } from "../../ui/Alert";
import { Button } from "../../ui/Button";
import { Field, Input } from "../../ui/form";
import { Segmented } from "../../ui/Segmented";
import {
  candidateRegisterSchema,
  employerRegisterSchema,
  type CandidateRegisterForm,
  type EmployerRegisterForm,
} from "./schemas";

type Role = "candidate" | "employer";

const PASSWORD_HINT = "Не короче 10 символов, буквы и цифры или символы";

/** Общий сценарий отправки: запрос -> вход -> кабинет; ошибки сервера -> поля формы. */
function useRegister<T extends FieldValues>(fields: readonly string[], request: (v: T) => Promise<TokenOut>) {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [formError, setFormError] = useState<string | null>(null);
  const submit = (setError: UseFormSetError<T>) => async (values: T) => {
    setFormError(null);
    try {
      const user = await signIn(await request(values));
      navigate(portalPath(user.role), { replace: true });
    } catch (err) {
      setFormError(applyServerErrors(err, setError, fields));
    }
  };
  return { formError, submit };
}

export function RegisterForm({ initialRole }: { initialRole: Role }) {
  const [role, setRole] = useState<Role>(initialRole);
  return (
    <div className="flex flex-col gap-6">
      <Segmented<Role>
        label="Тип аккаунта"
        value={role}
        onChange={setRole}
        options={[
          { value: "candidate", label: "Я ищу работу" },
          { value: "employer", label: "Я нанимаю" },
        ]}
      />
      {role === "candidate" ? <CandidateForm /> : <EmployerForm />}
    </div>
  );
}

function CandidateForm() {
  const form = useForm<CandidateRegisterForm>({ resolver: zodResolver(candidateRegisterSchema) });
  const { formError, submit } = useRegister<CandidateRegisterForm>(
    ["email", "password", "full_name"],
    authApi.registerCandidate,
  );
  const { errors, isSubmitting } = form.formState;
  return (
    <FormLayout onSubmit={form.handleSubmit(submit(form.setError))} error={formError} loading={isSubmitting}>
      <Field label="Имя и фамилия" error={errors.full_name?.message} hint="Работодатель увидит их только после вашего согласия">
        <Input autoComplete="name" {...form.register("full_name")} />
      </Field>
      <Field label="Email" error={errors.email?.message}>
        <Input type="email" autoComplete="email" {...form.register("email")} />
      </Field>
      <Field label="Пароль" error={errors.password?.message} hint={PASSWORD_HINT}>
        <Input type="password" autoComplete="new-password" {...form.register("password")} />
      </Field>
    </FormLayout>
  );
}

function EmployerForm() {
  const form = useForm<EmployerRegisterForm>({ resolver: zodResolver(employerRegisterSchema) });
  const { formError, submit } = useRegister<EmployerRegisterForm>(
    ["email", "password", "company_name", "inn"],
    authApi.registerEmployer,
  );
  const { errors, isSubmitting } = form.formState;
  return (
    <FormLayout onSubmit={form.handleSubmit(submit(form.setError))} error={formError} loading={isSubmitting}>
      <Field label="Название компании" error={errors.company_name?.message} hint="После регистрации компания уйдёт на модерацию">
        <Input autoComplete="organization" {...form.register("company_name")} />
      </Field>
      <Field label="ИНН (необязательно)" error={errors.inn?.message} hint="Ускоряет проверку компании">
        <Input inputMode="numeric" {...form.register("inn")} />
      </Field>
      <Field label="Рабочий email" error={errors.email?.message}>
        <Input type="email" autoComplete="email" {...form.register("email")} />
      </Field>
      <Field label="Пароль" error={errors.password?.message} hint={PASSWORD_HINT}>
        <Input type="password" autoComplete="new-password" {...form.register("password")} />
      </Field>
    </FormLayout>
  );
}

function FormLayout({
  onSubmit,
  error,
  loading,
  children,
}: {
  onSubmit: () => void;
  error: string | null;
  loading: boolean;
  children: ReactNode;
}) {
  return (
    <form onSubmit={onSubmit} noValidate className="flex flex-col gap-5">
      {error && <Alert>{error}</Alert>}
      {children}
      <Button type="submit" size="lg" loading={loading}>
        Создать аккаунт
      </Button>
      <p className="text-xs leading-relaxed text-muted">
        Регистрируясь, вы соглашаетесь на обработку персональных данных по 152-ФЗ.
      </p>
    </form>
  );
}
