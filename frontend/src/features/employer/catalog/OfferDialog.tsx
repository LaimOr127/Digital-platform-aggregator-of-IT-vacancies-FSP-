import { zodResolver } from "@hookform/resolvers/zod";
import { Send } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link } from "react-router";
import type { CandidateCard } from "../../../api/types";
import { formatSalaryRange } from "../../../lib/format";
import { applyServerErrors } from "../../../lib/forms";
import { randomKey } from "../../../lib/ids";
import { Alert } from "../../../ui/Alert";
import { Button } from "../../../ui/Button";
import { Dialog } from "../../../ui/Dialog";
import { Field, Input, Select, Textarea } from "../../../ui/form";
import { Spinner } from "../../../ui/Spinner";
import { useToast } from "../../../ui/Toast";
import { useActiveVacancies, useSendOffer } from "./hooks";
import { offerSchema, type OfferFormInput, type OfferFormOutput } from "./schemas";

const FIELDS = ["vacancy_id", "salary_min", "salary_max", "message"];

type Props = { candidate: CandidateCard | null; onClose: () => void };

/** Монтируется заново для каждого кандидата (key): ключ идемпотентности — один на попытку. */
export function OfferDialog({ candidate, onClose }: Props) {
  return (
    <Dialog open={candidate !== null} title="Оффер кандидату" onClose={onClose} wide>
      {candidate && <OfferForm candidate={candidate} onDone={onClose} />}
    </Dialog>
  );
}

function OfferForm({ candidate, onDone }: { candidate: CandidateCard; onDone: () => void }) {
  const notify = useToast();
  const vacancies = useActiveVacancies();
  const send = useSendOffer();
  const [idempotencyKey] = useState(randomKey);
  const [formError, setFormError] = useState<string | null>(null);
  const form = useForm<OfferFormInput, unknown, OfferFormOutput>({
    resolver: zodResolver(offerSchema),
    defaultValues: { vacancy_id: "", salary_min: "", salary_max: "", message: "" },
  });
  const { errors, isSubmitting } = form.formState;
  const items = vacancies.data?.items ?? [];

  const pickVacancy = (id: string) => {
    const vacancy = items.find((v) => v.id === id);
    form.setValue("vacancy_id", id, { shouldValidate: true });
    if (vacancy) {
      form.setValue("salary_min", vacancy.salary_min);
      form.setValue("salary_max", vacancy.salary_max);
    }
  };

  const onSubmit = form.handleSubmit(async (values) => {
    setFormError(null);
    try {
      await send.mutateAsync({ body: { ...values, anon_id: candidate.anon_id }, key: idempotencyKey });
      notify("Оффер отправлен — кандидат ответит в течение 7 дней");
      onDone();
    } catch (err) {
      setFormError(applyServerErrors(err, form.setError, FIELDS));
    }
  });

  if (vacancies.isPending) return <Spinner />;
  if (items.length === 0) {
    return (
      <Alert tone="warn">
        Оффер отправляется по опубликованной вакансии. <Link to="/company" className="underline">Опубликуйте вакансию</Link>,
        и возвращайтесь в каталог.
      </Alert>
    );
  }

  return (
    <form onSubmit={onSubmit} noValidate className="grid gap-5 sm:grid-cols-2">
      <p className="text-sm text-muted sm:col-span-2">
        Кандидат #{candidate.anon_id.slice(0, 6).toUpperCase()} · {candidate.title ?? "должность не указана"} · ожидания{" "}
        {formatSalaryRange(candidate.salary_min, candidate.salary_max)}
      </p>
      {formError && (
        <div className="sm:col-span-2">
          <Alert>{formError}</Alert>
        </div>
      )}
      <Field label="Вакансия" error={errors.vacancy_id?.message} className="sm:col-span-2">
        <Select
          placeholder="Выберите опубликованную вакансию"
          options={items.map((v) => ({ value: v.id, label: `${v.title} · ${formatSalaryRange(v.salary_min, v.salary_max)}` }))}
          value={form.watch("vacancy_id")}
          onChange={(e) => pickVacancy(e.target.value)}
        />
      </Field>
      <Field label="Зарплата от, ₽" error={errors.salary_min?.message} hint="Вилка обязательна">
        <Input type="number" inputMode="numeric" min={0} step={5000} className="tabular" {...form.register("salary_min")} />
      </Field>
      <Field label="Зарплата до, ₽" error={errors.salary_max?.message}>
        <Input type="number" inputMode="numeric" min={0} step={5000} className="tabular" {...form.register("salary_max")} />
      </Field>
      <Field label="Сообщение кандидату" error={errors.message?.message} className="sm:col-span-2">
        <Textarea rows={4} placeholder="Чем заинтересовал профиль, задачи, команда" {...form.register("message")} />
      </Field>
      <p className="text-xs text-muted sm:col-span-2">
        Имя и контакты кандидата откроются только после того, как он примет оффер.
      </p>
      <div className="flex justify-end gap-3 sm:col-span-2">
        <Button variant="ghost" onClick={onDone}>
          Отмена
        </Button>
        <Button type="submit" loading={isSubmitting}>
          <Send className="size-4" aria-hidden />
          Отправить оффер
        </Button>
      </div>
    </form>
  );
}
