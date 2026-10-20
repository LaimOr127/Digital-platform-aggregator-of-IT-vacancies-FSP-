// Выход на контакт: приглашение конкретному кандидату с описанием, вилкой и способом связи.
import { zodResolver } from "@hookform/resolvers/zod";
import { Send } from "lucide-react";
import { Controller, useForm } from "react-hook-form";
import type { CandidateCard, Company, Vacancy } from "../../../api/types";
import { labels, options } from "../../../lib/format";
import { applyServerErrors } from "../../../lib/forms";
import { Button } from "../../../ui/Button";
import { CitySelect } from "../../../ui/CitySelect";
import { Dialog } from "../../../ui/Dialog";
import { Field, Input, MoneyInput, Select, Textarea } from "../../../ui/form";
import { useToast } from "../../../ui/Toast";
import { useSendInvitation } from "./hooks";
import { invitationDefaults, invitationSchema, type InvitationFormInput, type InvitationFormOutput } from "./schemas";

const FIELDS = ["vacancy_id", "title", "description", "grade", "work_format", "city", "salary_min", "salary_max", "contact_method"];

type Props = {
  candidate: CandidateCard | null;
  vacancies: Vacancy[];
  vacancyId?: string;
  company: Company | undefined;
  onClose: () => void;
};

/** Монтируется заново для каждого кандидата (key): форма не переносится между кандидатами. */
export function InvitationDialog({ candidate, onClose, ...rest }: Props) {
  return (
    <Dialog open={candidate !== null} title="Пригласить кандидата" onClose={onClose} wide>
      {candidate && <InvitationForm candidate={candidate} onDone={onClose} {...rest} />}
    </Dialog>
  );
}

type FormProps = Omit<Props, "candidate" | "onClose"> & { candidate: CandidateCard; onDone: () => void };

function InvitationForm({ candidate, vacancies, vacancyId, company, onDone }: FormProps) {
  const notify = useToast();
  const send = useSendInvitation();
  const form = useForm<InvitationFormInput, unknown, InvitationFormOutput>({
    resolver: zodResolver(invitationSchema),
    defaultValues: invitationDefaults(vacancies.find((v) => v.id === vacancyId), company),
  });
  const { errors, isSubmitting } = form.formState;

  // выбор вакансии заполняет предложение её условиями — их можно поправить
  const pickVacancy = (id: string) => form.reset(invitationDefaults(vacancies.find((v) => v.id === id), company));

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      await send.mutateAsync({ ...values, anon_id: candidate.anon_id });
      notify("Приглашение отправлено — статус виден в «Приглашениях и откликах»");
      onDone();
    } catch (err) {
      const message = applyServerErrors(err, form.setError, FIELDS);
      if (message) notify(message, "error");
    }
  });

  return (
    <form onSubmit={onSubmit} noValidate className="grid gap-5 sm:grid-cols-2">
      <p className="text-sm text-muted sm:col-span-2">
        Кандидат #{candidate.anon_id.slice(0, 6).toUpperCase()}
        {candidate.category ? ` · ${candidate.category.title}` : ""}. Он увидит предложение, вилку, название компании и
        способ связи; его имя и контакты откроются, когда он примет приглашение.
      </p>
      <Field label="Вакансия (необязательно)" className="sm:col-span-2" hint="Заполнит предложение условиями вакансии">
        <Select
          placeholder="Без вакансии"
          options={vacancies.map((v) => ({ value: v.id, label: v.title }))}
          {...form.register("vacancy_id", { onChange: (e) => pickVacancy(e.target.value) })}
        />
      </Field>
      <Field label="Должность" error={errors.title?.message} className="sm:col-span-2">
        <Input placeholder="Backend-разработчик (Python)" {...form.register("title")} />
      </Field>
      <Field label="Описание предложения" error={errors.description?.message} className="sm:col-span-2">
        <Textarea rows={4} placeholder="Задачи, команда, условия" {...form.register("description")} />
      </Field>
      <Field label="Грейд" error={errors.grade?.message}>
        <Select options={options(labels.grade)} {...form.register("grade")} />
      </Field>
      <Field label="Формат работы" error={errors.work_format?.message}>
        <Select options={options(labels.workFormat)} {...form.register("work_format")} />
      </Field>
      <Field label="Зарплата от, ₽" error={errors.salary_min?.message} hint="Вилка обязательна, до вычета налогов">
        <MoneyInput {...form.register("salary_min")} />
      </Field>
      <Field label="Зарплата до, ₽" error={errors.salary_max?.message}>
        <MoneyInput {...form.register("salary_max")} />
      </Field>
      <Controller
        control={form.control}
        name="city"
        render={({ field }) => (
          <Field label="Город" error={errors.city?.message} hint="Для удалёнки можно не указывать">
            <CitySelect value={field.value} onChange={field.onChange} onBlur={field.onBlur} name={field.name} placeholder="Не указан" />
          </Field>
        )}
      />
      <Field label="Как связаться с вами" error={errors.contact_method?.message}>
        <Input placeholder="Telegram @hr, hr@company.ru" {...form.register("contact_method")} />
      </Field>
      <div className="flex justify-end gap-3 sm:col-span-2">
        <Button variant="ghost" onClick={onDone}>
          Отмена
        </Button>
        <Button type="submit" loading={isSubmitting}>
          <Send className="size-4" aria-hidden />
          Отправить приглашение
        </Button>
      </div>
    </form>
  );
}
