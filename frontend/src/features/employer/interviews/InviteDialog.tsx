import { zodResolver } from "@hookform/resolvers/zod";
import { CalendarPlus } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import type { EmployerApplication } from "../../../api/types";
import { SALARY_NOTE, formatSalaryRange, labels, options } from "../../../lib/format";
import { applyServerErrors } from "../../../lib/forms";
import { Alert } from "../../../ui/Alert";
import { Button } from "../../../ui/Button";
import { Dialog } from "../../../ui/Dialog";
import { Field, Input, Select, Textarea } from "../../../ui/form";
import { useToast } from "../../../ui/Toast";
import { useInvite } from "./hooks";
import { inviteSchema, type InviteFormInput, type InviteFormOutput } from "./schemas";

const FIELDS = ["slots", "location", "interviewer", "message", "duration_minutes", "format"];
const DURATIONS = [30, 45, 60, 90].map((m) => ({ value: String(m), label: `${m} минут` }));

type Props = { application: EmployerApplication | null; onClose: () => void };

/** Собеседование по состоявшемуся контакту. Монтируется заново для каждого контакта (key). */
export function InviteDialog({ application, onClose }: Props) {
  return (
    <Dialog open={application !== null} title="Назначить собеседование" onClose={onClose} wide>
      {application && <InviteForm application={application} onDone={onClose} />}
    </Dialog>
  );
}

function InviteForm({ application, onDone }: { application: EmployerApplication; onDone: () => void }) {
  const notify = useToast();
  const invite = useInvite();
  const [formError, setFormError] = useState<string | null>(null);
  const form = useForm<InviteFormInput, unknown, InviteFormOutput>({
    resolver: zodResolver(inviteSchema),
    defaultValues: {
      slot1: "",
      slot2: "",
      slot3: "",
      duration_minutes: "60",
      format: "online",
      location: "",
      interviewer: "",
      message: "",
    },
  });
  const { errors, isSubmitting } = form.formState;

  const onSubmit = form.handleSubmit(async (values) => {
    setFormError(null);
    try {
      await invite.mutateAsync({ ...values, application_id: application.id });
      notify("Приглашение отправлено — кандидат выберет удобное время");
      onDone();
    } catch (err) {
      setFormError(applyServerErrors(err, form.setError, FIELDS));
    }
  });

  const online = form.watch("format") === "online";

  return (
    <form onSubmit={onSubmit} noValidate className="grid gap-5 sm:grid-cols-2">
      <p className="text-sm text-muted sm:col-span-2">
        «{application.title}» · {formatSalaryRange(application.salary_min, application.salary_max)} {SALARY_NOTE}. Кандидат выберет
        одно из предложенных времён.
      </p>
      {formError && (
        <div className="sm:col-span-2">
          <Alert>{formError}</Alert>
        </div>
      )}
      <Field label="Вариант времени 1" error={errors.slot1?.message}>
        <Input type="datetime-local" {...form.register("slot1")} />
      </Field>
      <Field label="Вариант времени 2 (необязательно)" error={errors.slot2?.message}>
        <Input type="datetime-local" {...form.register("slot2")} />
      </Field>
      <Field label="Вариант времени 3 (необязательно)" error={errors.slot3?.message}>
        <Input type="datetime-local" {...form.register("slot3")} />
      </Field>
      <Field label="Длительность">
        <Select options={DURATIONS} {...form.register("duration_minutes")} />
      </Field>
      <Field label="Формат">
        <Select options={options(labels.interviewFormat)} {...form.register("format")} />
      </Field>
      <Field label={online ? "Ссылка на встречу" : "Адрес"} error={errors.location?.message}>
        <Input placeholder={online ? "https://telemost.yandex.ru/j/..." : "Город, улица, офис"} {...form.register("location")} />
      </Field>
      <Field label="Кто проводит" error={errors.interviewer?.message} hint="Руководитель, к которому идёт кандидат" className="sm:col-span-2">
        <Input placeholder="Иван Петров, руководитель разработки" {...form.register("interviewer")} />
      </Field>
      <Field label="Сообщение кандидату" error={errors.message?.message} className="sm:col-span-2">
        <Textarea rows={3} placeholder="О чём поговорим, что подготовить" {...form.register("message")} />
      </Field>
      <div className="flex justify-end gap-3 sm:col-span-2">
        <Button variant="ghost" onClick={onDone}>
          Отмена
        </Button>
        <Button type="submit" loading={isSubmitting}>
          <CalendarPlus className="size-4" aria-hidden />
          Назначить
        </Button>
      </div>
    </form>
  );
}
