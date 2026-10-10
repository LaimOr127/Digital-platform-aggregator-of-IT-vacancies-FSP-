import { zodResolver } from "@hookform/resolvers/zod";
import { Send } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import type { EmployerInterview } from "../../../api/types";
import { labels, options } from "../../../lib/format";
import { applyServerErrors } from "../../../lib/forms";
import { randomKey } from "../../../lib/ids";
import { Alert } from "../../../ui/Alert";
import { Button } from "../../../ui/Button";
import { Dialog } from "../../../ui/Dialog";
import { Field, MoneyInput, Select, Textarea } from "../../../ui/form";
import { useToast } from "../../../ui/Toast";
import { useActiveVacancies, useSendOffer } from "../catalog/hooks";
import { useCompleteInterview } from "./hooks";
import { completeSchema, offerSchema, type CompleteForm, type OfferFormInput, type OfferFormOutput } from "./schemas";

type Props = { interview: EmployerInterview | null; onClose: () => void };

/** Итог собеседования: «успешно» открывает оффер, отзыв увидит кандидат. */
export function CompleteDialog({ interview, onClose }: Props) {
  const notify = useToast();
  const complete = useCompleteInterview();
  const [error, setError] = useState<string | null>(null);
  const form = useForm<CompleteForm>({ resolver: zodResolver(completeSchema), defaultValues: { result: "passed", feedback: "" } });
  const onSubmit = form.handleSubmit(async (values) => {
    if (!interview) return;
    setError(null);
    try {
      await complete.mutateAsync({ id: interview.id, ...values });
      notify(values.result === "passed" ? "Отмечено: успешно — можно отправить оффер" : "Результат сохранён");
      onClose();
    } catch (err) {
      setError(applyServerErrors(err, form.setError, ["result", "feedback"]));
    }
  });
  return (
    <Dialog open={interview !== null} title="Итог собеседования" onClose={onClose} busy={complete.isPending}>
      <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
        {error && <Alert>{error}</Alert>}
        <Field label="Результат" error={form.formState.errors.result?.message}>
          <Select options={options(labels.interviewResult)} {...form.register("result")} />
        </Field>
        <Field label="Отзыв для кандидата" hint="Кандидат увидит его в кабинете" error={form.formState.errors.feedback?.message}>
          <Textarea rows={4} placeholder="Что понравилось, что стоит подтянуть" {...form.register("feedback")} />
        </Field>
        <div className="flex justify-end gap-3">
          <Button variant="ghost" onClick={onClose}>
            Отмена
          </Button>
          <Button type="submit" loading={form.formState.isSubmitting}>
            Сохранить
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

/** Оффер по итогам успешного собеседования; вилка по умолчанию — из вакансии. */
export function OfferDialog({ interview, onClose }: Props) {
  return (
    <Dialog open={interview !== null} title="Оффер по итогам собеседования" onClose={onClose} wide>
      {interview && <OfferForm interview={interview} onDone={onClose} />}
    </Dialog>
  );
}

function OfferForm({ interview, onDone }: { interview: EmployerInterview; onDone: () => void }) {
  const notify = useToast();
  const send = useSendOffer();
  const vacancy = useActiveVacancies().data?.items.find((v) => v.id === interview.vacancy_id);
  const [idempotencyKey] = useState(randomKey);
  const [error, setError] = useState<string | null>(null);
  const form = useForm<OfferFormInput, unknown, OfferFormOutput>({
    resolver: zodResolver(offerSchema),
    values: { salary_min: vacancy?.salary_min ?? "", salary_max: vacancy?.salary_max ?? "", message: "" },
    resetOptions: { keepDirtyValues: true },
  });
  const { errors, isSubmitting } = form.formState;
  const onSubmit = form.handleSubmit(async (values) => {
    setError(null);
    try {
      await send.mutateAsync({ body: { ...values, interview_id: interview.id }, key: idempotencyKey });
      notify("Оффер отправлен — после принятия вы увидите имя и контакты кандидата");
      onDone();
    } catch (err) {
      setError(applyServerErrors(err, form.setError, ["salary_min", "salary_max", "message"]));
    }
  });
  return (
    <form onSubmit={onSubmit} noValidate className="grid gap-5 sm:grid-cols-2">
      <p className="text-sm text-muted sm:col-span-2">Вакансия «{interview.vacancy_title}» · вилка обязательна.</p>
      {error && (
        <div className="sm:col-span-2">
          <Alert>{error}</Alert>
        </div>
      )}
      <Field label="Зарплата от, ₽" error={errors.salary_min?.message} hint="До вычета налогов">
        <MoneyInput {...form.register("salary_min")} />
      </Field>
      <Field label="Зарплата до, ₽" error={errors.salary_max?.message}>
        <MoneyInput {...form.register("salary_max")} />
      </Field>
      <Field label="Сообщение кандидату" error={errors.message?.message} className="sm:col-span-2">
        <Textarea rows={4} placeholder="Условия, команда, следующий шаг" {...form.register("message")} />
      </Field>
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
