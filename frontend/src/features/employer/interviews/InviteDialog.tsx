import { zodResolver } from "@hookform/resolvers/zod";
import { CalendarPlus } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link } from "react-router";
import type { CandidateCard } from "../../../api/types";
import { formatSalaryRange, labels, options } from "../../../lib/format";
import { applyServerErrors } from "../../../lib/forms";
import { Alert } from "../../../ui/Alert";
import { Button } from "../../../ui/Button";
import { Dialog } from "../../../ui/Dialog";
import { Field, Input, Select, Textarea } from "../../../ui/form";
import { Spinner } from "../../../ui/Spinner";
import { useToast } from "../../../ui/Toast";
import { useActiveVacancies } from "../catalog/hooks";
import { useInvite } from "./hooks";
import { inviteSchema, type InviteFormInput, type InviteFormOutput } from "./schemas";

const FIELDS = ["vacancy_id", "slots", "location", "interviewer", "message", "duration_minutes", "format"];
const DURATIONS = [30, 45, 60, 90].map((m) => ({ value: String(m), label: `${m} минут` }));

type Props = { candidate: CandidateCard | null; vacancyId?: string; onClose: () => void };

/** Монтируется заново для каждого кандидата (key): форма не переносится между кандидатами. */
export function InviteDialog({ candidate, vacancyId, onClose }: Props) {
  return (
    <Dialog open={candidate !== null} title="Приглашение на собеседование" onClose={onClose} wide>
      {candidate && <InviteForm candidate={candidate} vacancyId={vacancyId} onDone={onClose} />}
    </Dialog>
  );
}

function InviteForm({ candidate, vacancyId, onDone }: { candidate: CandidateCard; vacancyId?: string; onDone: () => void }) {
  const notify = useToast();
  const vacancies = useActiveVacancies();
  const invite = useInvite();
  const [formError, setFormError] = useState<string | null>(null);
  const form = useForm<InviteFormInput, unknown, InviteFormOutput>({
    resolver: zodResolver(inviteSchema),
    defaultValues: {
      vacancy_id: vacancyId ?? "",
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
  const items = vacancies.data?.items ?? [];

  const onSubmit = form.handleSubmit(async (values) => {
    setFormError(null);
    try {
      await invite.mutateAsync({ ...values, anon_id: candidate.anon_id });
      notify("Приглашение отправлено — кандидат выберет удобное время");
      onDone();
    } catch (err) {
      setFormError(applyServerErrors(err, form.setError, FIELDS));
    }
  });

  if (vacancies.isPending) return <Spinner />;
  if (items.length === 0) {
    return (
      <Alert tone="warn">
        Пригласить можно по опубликованной вакансии. <Link to="/company" className="underline">Опубликуйте вакансию</Link>.
      </Alert>
    );
  }
  const online = form.watch("format") === "online";

  return (
    <form onSubmit={onSubmit} noValidate className="grid gap-5 sm:grid-cols-2">
      <p className="text-sm text-muted sm:col-span-2">
        Кандидат #{candidate.anon_id.slice(0, 6).toUpperCase()} · {candidate.title ?? "должность не указана"}. Он выберет
        одно из предложенных времён; имя и контакты откроются после принятого оффера.
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
          {...form.register("vacancy_id")}
        />
      </Field>
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
          Пригласить
        </Button>
      </div>
    </form>
  );
}
