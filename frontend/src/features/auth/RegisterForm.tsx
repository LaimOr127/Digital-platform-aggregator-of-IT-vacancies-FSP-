import { zodResolver } from "@hookform/resolvers/zod";
import { useState, type InputHTMLAttributes, type ReactNode } from "react";
import { useForm, type FieldValues, type UseFormRegisterReturn, type UseFormSetError } from "react-hook-form";
import { authApi } from "../../api/endpoints";
import { applyServerErrors } from "../../lib/forms";
import { Alert } from "../../ui/Alert";
import { Button } from "../../ui/Button";
import { Field, Input } from "../../ui/form";
import { Segmented } from "../../ui/Segmented";
import { CheckEmail } from "./CheckEmail";
import {
  candidateRegisterSchema,
  employerRegisterSchema,
  type CandidateRegisterForm,
  type EmployerRegisterForm,
} from "./schemas";

export type Role = "candidate" | "employer";

const PASSWORD_HINT = "Не короче 10 символов, буквы и цифры или символы";

type Registered = (email: string) => void;

/** Общий сценарий отправки: запрос -> экран «проверьте почту»; ошибки -> поля формы. */
function useRegister<T extends FieldValues & { email: string }>(
  fields: readonly string[],
  request: (v: T) => Promise<unknown>,
  onDone: Registered,
) {
  const [formError, setFormError] = useState<string | null>(null);
  const submit = (setError: UseFormSetError<T>) => async (values: T) => {
    setFormError(null);
    try {
      await request(values);
      onDone(values.email);
    } catch (err) {
      setFormError(applyServerErrors(err, setError, fields));
    }
  };
  return { formError, submit };
}

/** Тип аккаунта хранит страница: от него зависит и текст рядом с формой. */
export function RegisterForm({ role, onRoleChange }: { role: Role; onRoleChange: (role: Role) => void }) {
  const [sentTo, setSentTo] = useState<string | null>(null);
  if (sentTo) return <CheckEmail email={sentTo} />;
  return (
    <div className="flex flex-col gap-6">
      <Segmented<Role>
        label="Тип аккаунта"
        value={role}
        onChange={onRoleChange}
        options={[
          { value: "candidate", label: "Я ищу работу" },
          { value: "employer", label: "Я нанимаю" },
        ]}
      />
      {role === "candidate" ? <CandidateForm onDone={setSentTo} /> : <EmployerForm onDone={setSentTo} />}
    </div>
  );
}

function CandidateForm({ onDone }: { onDone: Registered }) {
  const form = useForm<CandidateRegisterForm>({ resolver: zodResolver(candidateRegisterSchema) });
  const { formError, submit } = useRegister<CandidateRegisterForm>(
    ["email", "password", "full_name", "consent"],
    authApi.registerCandidate,
    onDone,
  );
  const { errors, isSubmitting } = form.formState;
  return (
    <FormLayout onSubmit={form.handleSubmit(submit(form.setError))} error={formError} loading={isSubmitting}>
      <Field label="Имя и фамилия" error={errors.full_name?.message} hint="Работодатель увидит их только после вашего согласия">
        <Input autoComplete="name" {...form.register("full_name")} />
      </Field>
      <CredentialFields
        emailLabel="Email"
        email={form.register("email")}
        password={form.register("password")}
        consent={form.register("consent")}
        errors={errors}
      />
    </FormLayout>
  );
}

function EmployerForm({ onDone }: { onDone: Registered }) {
  const form = useForm<EmployerRegisterForm>({ resolver: zodResolver(employerRegisterSchema) });
  const { formError, submit } = useRegister<EmployerRegisterForm>(
    ["email", "password", "company_name", "inn", "consent"],
    authApi.registerEmployer,
    onDone,
  );
  const { errors, isSubmitting } = form.formState;
  return (
    <FormLayout onSubmit={form.handleSubmit(submit(form.setError))} error={formError} loading={isSubmitting}>
      <Field label="Название компании" error={errors.company_name?.message} hint="Модератор может проверить компанию позже">
        <Input autoComplete="organization" {...form.register("company_name")} />
      </Field>
      <Field label="ИНН (необязательно)" error={errors.inn?.message} hint="Ускоряет проверку компании">
        <Input inputMode="numeric" {...form.register("inn")} />
      </Field>
      <CredentialFields
        emailLabel="Рабочий email"
        email={form.register("email")}
        password={form.register("password")}
        consent={form.register("consent")}
        errors={errors}
      />
    </FormLayout>
  );
}

type CredentialProps = {
  emailLabel: string;
  email: UseFormRegisterReturn;
  password: UseFormRegisterReturn;
  consent: UseFormRegisterReturn;
  errors: Partial<Record<"email" | "password" | "consent", { message?: string }>>;
};

/** Почта, пароль и согласие — общие для обеих форм регистрации. */
function CredentialFields({ emailLabel, email, password, consent, errors }: CredentialProps) {
  return (
    <>
      <Field label={emailLabel} error={errors.email?.message}>
        <Input type="email" autoComplete="email" {...email} />
      </Field>
      <Field label="Пароль" error={errors.password?.message} hint={PASSWORD_HINT}>
        <Input type="password" autoComplete="new-password" {...password} />
      </Field>
      <Consent error={errors.consent?.message} {...consent} />
    </>
  );
}

/** Согласие на обработку ПДн (152-ФЗ): без отметки аккаунт не создаётся. */
function Consent({ error, ...input }: InputHTMLAttributes<HTMLInputElement> & { error?: string }) {
  return (
    <div className="flex flex-col gap-1">
      <label className="flex cursor-pointer items-start gap-3 text-sm">
        <input type="checkbox" className="mt-0.5 size-4 accent-[var(--accent)]" aria-invalid={Boolean(error)} {...input} />
        <span className="leading-relaxed text-muted">
          Согласен на обработку персональных данных и публикацию анонимного профиля (152-ФЗ). Имя и контакты
          компании увидят только с моего согласия.
        </span>
      </label>
      {error && <p className="text-xs text-danger">{error}</p>}
    </div>
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
    </form>
  );
}
