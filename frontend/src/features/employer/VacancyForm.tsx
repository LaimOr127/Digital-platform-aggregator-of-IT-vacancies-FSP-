import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";
import type { Skill, Vacancy } from "../../api/types";
import { labels, options } from "../../lib/format";
import { applyServerErrors } from "../../lib/forms";
import { Button } from "../../ui/Button";
import { Field, FieldGroup, Input, MoneyInput, Select, Textarea } from "../../ui/form";
import { SkillPicker } from "../../ui/SkillPicker";
import { useToast } from "../../ui/Toast";
import { useCreateVacancy, useUpdateVacancy } from "./hooks";
import { MarketHint } from "./MarketHint";
import { emptyVacancy, vacancySchema, vacancyToForm, type VacancyFormInput, type VacancyFormOutput } from "./schemas";

const FIELDS = ["title", "description", "specialization", "grade", "work_format", "city", "salary_min", "salary_max", "skills"];

type Props = { vacancy: Vacancy | null; skills: Skill[]; onDone: () => void };

export function VacancyForm({ vacancy, skills, onDone }: Props) {
  const notify = useToast();
  const create = useCreateVacancy();
  const update = useUpdateVacancy();
  const form = useForm<VacancyFormInput, unknown, VacancyFormOutput>({
    resolver: zodResolver(vacancySchema),
    defaultValues: vacancy ? vacancyToForm(vacancy) : emptyVacancy,
  });
  const { register, control, formState } = form;
  const { errors, isSubmitting } = formState;

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      if (vacancy) await update.mutateAsync({ id: vacancy.id, body: values });
      else await create.mutateAsync(values);
      notify(vacancy ? "Вакансия сохранена" : "Черновик вакансии создан");
      onDone();
    } catch (err) {
      const message = applyServerErrors(err, form.setError, FIELDS);
      if (message) notify(message, "error");
    }
  });

  return (
    <form onSubmit={onSubmit} noValidate className="grid gap-5 sm:grid-cols-2">
      <Field label="Название" error={errors.title?.message} className="sm:col-span-2">
        <Input placeholder="Backend-разработчик (Python)" {...register("title")} />
      </Field>
      <Field label="Специализация" error={errors.specialization?.message} hint="По ней и грейду строится подборка кандидатов">
        <Select options={options(labels.specialization)} {...register("specialization")} />
      </Field>
      <Field label="Грейд" error={errors.grade?.message}>
        <Select options={options(labels.grade)} {...register("grade")} />
      </Field>
      <Field label="Формат работы" error={errors.work_format?.message} className="sm:col-span-2">
        <Select options={options(labels.workFormat)} {...register("work_format")} />
      </Field>
      <Field label="Зарплата от, ₽" error={errors.salary_min?.message} hint="Вилка обязательна">
        <MoneyInput {...register("salary_min")} />
      </Field>
      <Field label="Зарплата до, ₽" error={errors.salary_max?.message}>
        <MoneyInput {...register("salary_max")} />
      </Field>
      <MarketHint control={control} />
      <Field label="Город" error={errors.city?.message} className="sm:col-span-2">
        <Input placeholder="Можно оставить пустым для удалёнки" {...register("city")} />
      </Field>
      <FieldGroup label="Навыки" error={errors.skills?.message} className="sm:col-span-2">
        <Controller
          control={control}
          name="skills"
          render={({ field }) => <SkillPicker skills={skills} value={field.value} onChange={field.onChange} max={30} />}
        />
      </FieldGroup>
      <Field label="Описание" error={errors.description?.message} className="sm:col-span-2">
        <Textarea rows={6} placeholder="Задачи, команда, условия" {...register("description")} />
      </Field>
      <div className="flex justify-end gap-3 sm:col-span-2">
        <Button variant="ghost" onClick={onDone}>
          Отмена
        </Button>
        <Button type="submit" loading={isSubmitting}>
          {vacancy ? "Сохранить" : "Создать черновик"}
        </Button>
      </div>
    </form>
  );
}
