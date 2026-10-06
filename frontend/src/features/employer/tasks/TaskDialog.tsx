// Новая короткая задача: условие, специализация и (по желанию) грейд кандидатов.
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { labels, options } from "../../../lib/format";
import { applyServerErrors } from "../../../lib/forms";
import { Button } from "../../../ui/Button";
import { Dialog } from "../../../ui/Dialog";
import { Field, Input, Select, Textarea } from "../../../ui/form";
import { useToast } from "../../../ui/Toast";
import { useCreateTask } from "./hooks";

const schema = z.object({
  title: z.string().trim().min(3, "Минимум 3 символа").max(160),
  specialization: z.enum(Object.keys(labels.specialization) as [keyof typeof labels.specialization], "Выберите специализацию"),
  grade: z
    .enum(["", ...Object.keys(labels.grade)] as ["", ...(keyof typeof labels.grade)[]])
    .transform((v) => (v === "" ? null : v)),
  body: z.string().trim().min(10, "Опишите задачу: минимум 10 символов").max(4000),
});
type FormInput = z.input<typeof schema>;
type Output = z.output<typeof schema>;
const FIELDS = Object.keys(schema.shape);

export function TaskDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const notify = useToast();
  const create = useCreateTask();
  const form = useForm<FormInput, unknown, Output>({
    resolver: zodResolver(schema),
    defaultValues: { title: "", specialization: undefined, grade: "", body: "" },
  });
  const { errors, isSubmitting } = form.formState;
  const onSubmit = form.handleSubmit(async (values) => {
    try {
      await create.mutateAsync(values);
      notify("Задача опубликована — кандидаты увидят её в ближайшую неделю");
      form.reset();
      onClose();
    } catch (err) {
      const message = applyServerErrors(err, form.setError, FIELDS);
      if (message) notify(message, "error");
    }
  });

  return (
    <Dialog open={open} title="Новая задача" onClose={onClose} busy={isSubmitting} wide>
      <form onSubmit={onSubmit} noValidate className="grid gap-5 sm:grid-cols-2">
        <Field label="Название" error={errors.title?.message} className="sm:col-span-2">
          <Input placeholder="Медленный запрос ленты" {...form.register("title")} />
        </Field>
        <Field label="Специализация" error={errors.specialization?.message}>
          <Select placeholder="Выберите" options={options(labels.specialization)} {...form.register("specialization")} />
        </Field>
        <Field label="Грейд" hint="Пусто — задача для всех грейдов" error={errors.grade?.message}>
          <Select placeholder="Любой" options={options(labels.grade)} {...form.register("grade")} />
        </Field>
        <Field
          label="Условие"
          hint="Задача на 15–30 минут: кандидат решает её или предлагает подход"
          error={errors.body?.message}
          className="sm:col-span-2"
        >
          <Textarea rows={6} {...form.register("body")} />
        </Field>
        <div className="flex justify-end gap-3 sm:col-span-2">
          <Button type="button" variant="ghost" onClick={onClose} disabled={isSubmitting}>
            Отмена
          </Button>
          <Button type="submit" loading={isSubmitting}>
            Опубликовать
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
