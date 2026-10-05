// Профиль компании: его видит кандидат в приглашении и в вакансии.
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { employerApi } from "../../api/endpoints";
import type { Company, CompanyUpdate } from "../../api/types";
import { optionalText } from "../../lib/fields";
import { applyServerErrors } from "../../lib/forms";
import { PageHeader } from "../../ui/AppShell";
import { Button } from "../../ui/Button";
import { Card } from "../../ui/Card";
import { Field, Input, Textarea } from "../../ui/form";
import { LoadingBlock } from "../../ui/Spinner";
import { useToast } from "../../ui/Toast";
import { useCompany } from "./hooks";

const schema = z.object({
  name: z.string().trim().min(2, "Минимум 2 символа").max(200),
  industry: optionalText(120),
  website: optionalText(255).refine((v) => v === null || z.url().safeParse(v).success, "Ссылка вида https://…"),
  description: z.string().trim().max(4000),
  contact_email: optionalText(254).refine((v) => v === null || z.email().safeParse(v).success, "Некорректный email"),
  contact_phone: optionalText(32),
  contact_telegram: optionalText(64),
});
type FormInput = z.input<typeof schema>;
type Output = z.output<typeof schema>;
const FIELDS = Object.keys(schema.shape);

export function CompanyPage() {
  const company = useCompany();
  return (
    <>
      <PageHeader
        title="Профиль компании"
        text="Кандидат видит его в приглашении и в вакансии: чем занимается компания и как с вами связаться."
      />
      {company.data ? <CompanyForm company={company.data} /> : <LoadingBlock />}
    </>
  );
}

function CompanyForm({ company }: { company: Company }) {
  const notify = useToast();
  const client = useQueryClient();
  const save = useMutation({
    mutationFn: (body: CompanyUpdate) => employerApi.updateCompany(body),
    onSuccess: (updated) => client.setQueryData(["company"], updated),
  });
  const form = useForm<FormInput, unknown, Output>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: company.name,
      industry: company.industry ?? "",
      website: company.website ?? "",
      description: company.description ?? "",
      contact_email: company.contact_email ?? "",
      contact_phone: company.contact_phone ?? "",
      contact_telegram: company.contact_telegram ?? "",
    },
  });
  const { errors, isSubmitting } = form.formState;
  const onSubmit = form.handleSubmit(async (values) => {
    try {
      await save.mutateAsync(values);
      notify("Профиль компании сохранён");
    } catch (err) {
      const message = applyServerErrors(err, form.setError, FIELDS);
      if (message) notify(message, "error");
    }
  });

  return (
    <Card className="max-w-3xl">
      <form onSubmit={onSubmit} noValidate className="grid gap-5 sm:grid-cols-2">
        <Field label="Название" error={errors.name?.message}>
          <Input {...form.register("name")} />
        </Field>
        <Field label="Направление деятельности" error={errors.industry?.message}>
          <Input placeholder="Финтех, e-commerce, госсектор…" {...form.register("industry")} />
        </Field>
        <Field label="Сайт" error={errors.website?.message} className="sm:col-span-2">
          <Input type="url" placeholder="https://company.ru" {...form.register("website")} />
        </Field>
        <Field label="О компании" error={errors.description?.message} className="sm:col-span-2">
          <Textarea rows={5} placeholder="Продукт, команда, стек, как устроена работа" {...form.register("description")} />
        </Field>
        <Field label="Email для кандидатов" error={errors.contact_email?.message}>
          <Input type="email" {...form.register("contact_email")} />
        </Field>
        <Field label="Телефон" error={errors.contact_phone?.message}>
          <Input type="tel" {...form.register("contact_phone")} />
        </Field>
        <Field label="Telegram" error={errors.contact_telegram?.message} hint="Подставится в приглашения как способ связи">
          <Input placeholder="@hr_company" {...form.register("contact_telegram")} />
        </Field>
        <div className="flex items-end justify-end">
          <Button type="submit" loading={isSubmitting}>
            Сохранить
          </Button>
        </div>
      </form>
    </Card>
  );
}
