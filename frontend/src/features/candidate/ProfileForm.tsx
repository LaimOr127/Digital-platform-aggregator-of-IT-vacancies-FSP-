import { zodResolver } from "@hookform/resolvers/zod";
import { Save } from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";
import { Controller, useForm } from "react-hook-form";
import type { Profile, ProfileDraft, Skill } from "../../api/types";
import { labels, options } from "../../lib/format";
import { applyServerErrors } from "../../lib/forms";
import { Button } from "../../ui/Button";
import { Card, CardTitle } from "../../ui/Card";
import { Field, FieldGroup, Input, Select, Switch, Textarea } from "../../ui/form";
import { Segmented } from "../../ui/Segmented";
import { SkillPicker } from "../../ui/SkillPicker";
import { useToast } from "../../ui/Toast";
import { useUpdateProfile } from "./hooks";
import type { FieldChange } from "./import/draft";
import { DraftDialog } from "./import/DraftDialog";
import { ImportCard } from "./import/ImportCard";
import { formToUpdate, profileSchema, profileToForm, type ProfileFormInput, type ProfileFormOutput } from "./schemas";

const FIELDS = [
  "full_name", "title", "about", "grade", "work_format", "city", "salary_min", "salary_max",
  "skills", "is_hidden", "search_status", "phone", "telegram", "contact_email",
];
const SEARCH_OPTIONS = options(labels.searchStatus);
const ALIASES = { "contacts.phone": "phone", "contacts.telegram": "telegram", "contacts.email": "contact_email" };

function Section({ title, text, children }: { title: string; text?: string; children: ReactNode }) {
  return (
    <Card>
      <CardTitle>{title}</CardTitle>
      {text && <p className="mt-1 text-sm text-muted">{text}</p>}
      <div className="mt-5 grid gap-5 sm:grid-cols-2">{children}</div>
    </Card>
  );
}

type Props = { profile: Profile; skills: Skill[]; fspLinked: boolean; autoFsp?: boolean };

export function ProfileForm({ profile, skills, fspLinked, autoFsp }: Props) {
  const notify = useToast();
  const [draft, setDraft] = useState<ProfileDraft | null>(null);
  const skillNames = useMemo(() => new Map(skills.map((s) => [s.slug, s.name])), [skills]);
  const update = useUpdateProfile();
  const form = useForm<ProfileFormInput, unknown, ProfileFormOutput>({
    resolver: zodResolver(profileSchema),
    values: profileToForm(profile),
    // фоновое обновление профиля не стирает несохранённые правки пользователя
    resetOptions: { keepDirtyValues: true },
  });
  const { register, control, formState } = form;
  const { errors, isDirty } = formState;

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      const saved = await update.mutateAsync(formToUpdate(values));
      // сохранённое — новая точка отсчёта: иначе поля, изменённые до сохранения, остаются «грязными»
      form.reset(profileToForm(saved));
      notify("Профиль сохранён");
    } catch (err) {
      const message = applyServerErrors(err, form.setError, FIELDS, ALIASES);
      if (message) notify(message, "error");
    }
  });

  const applyDraft = (changes: FieldChange[], newSkills: string[]) => {
    const options = { shouldDirty: true, shouldValidate: true } as const;
    for (const change of changes) form.setValue(change.field, change.value as never, options);
    if (newSkills.length) form.setValue("skills", [...form.getValues("skills"), ...newSkills], options);
    setDraft(null);
    notify("Данные перенесены в форму — проверьте и сохраните профиль");
  };

  return (
    <form onSubmit={onSubmit} noValidate className="flex flex-col gap-6 pb-24">
      <ImportCard fspLinked={fspLinked} autoFsp={autoFsp} onDraft={setDraft} />
      {draft && (
        <DraftDialog
          draft={draft}
          form={form.getValues()}
          skillNames={skillNames}
          onApply={applyDraft}
          onClose={() => setDraft(null)}
        />
      )}
      <Card>
        <CardTitle>Статус поиска</CardTitle>
        <p className="mt-1 text-sm text-muted">
          Работодатели видят его в каталоге. «Не ищу» убирает профиль из каталога — новые офферы не придут.
        </p>
        <div className="mt-4 overflow-x-auto">
          <Controller
            control={control}
            name="search_status"
            render={({ field }) => (
              <Segmented label="Статус поиска" value={field.value} options={SEARCH_OPTIONS} onChange={field.onChange} />
            )}
          />
        </div>
      </Card>
      <Section title="Основное" text="По этим данным вы попадаете в категории, которые видят работодатели.">
        <Field label="Имя и фамилия" error={errors.full_name?.message} hint="Видно только после принятого оффера">
          <Input autoComplete="name" {...register("full_name")} />
        </Field>
        <Field label="Должность" error={errors.title?.message}>
          <Input placeholder="Backend-разработчик" {...register("title")} />
        </Field>
        <Field label="Грейд" error={errors.grade?.message}>
          <Select placeholder="Не выбран" options={options(labels.grade)} {...register("grade")} />
        </Field>
        <Field label="Формат работы" error={errors.work_format?.message}>
          <Select placeholder="Не выбран" options={options(labels.workFormat)} {...register("work_format")} />
        </Field>
        <Field label="Город" error={errors.city?.message}>
          <Input autoComplete="address-level2" {...register("city")} />
        </Field>
      </Section>

      <Section title="Ожидания по зарплате" text="Рубли в месяц до вычета налогов. Компании предлагают оффер с вилкой.">
        <Field label="От" error={errors.salary_min?.message}>
          <Input type="number" inputMode="numeric" min={0} step={5000} className="tabular" {...register("salary_min")} />
        </Field>
        <Field label="До" error={errors.salary_max?.message}>
          <Input type="number" inputMode="numeric" min={0} step={5000} className="tabular" {...register("salary_max")} />
        </Field>
      </Section>

      <Card>
        <FieldGroup
          label="Навыки"
          hint="Из общего справочника — так работодатели находят вас по стеку."
          error={errors.skills?.message}
        >
          <Controller
            control={control}
            name="skills"
            render={({ field }) => <SkillPicker skills={skills} value={field.value} onChange={field.onChange} max={50} />}
          />
        </FieldGroup>
      </Card>

      <Section title="О себе">
        <Field
          label="Опыт и проекты"
          error={errors.about?.message}
          hint="Работодатели видят этот текст в анонимной карточке — не указывайте здесь имя и контакты"
          className="sm:col-span-2"
        >
          <Textarea rows={5} placeholder="Чем занимались, какие задачи решали, чем гордитесь" {...register("about")} />
        </Field>
      </Section>

      <Section title="Контакты" text="Работодатель получит их только после того, как вы примете его оффер.">
        <Field label="Telegram" error={errors.telegram?.message}>
          <Input placeholder="@username" {...register("telegram")} />
        </Field>
        <Field label="Телефон" error={errors.phone?.message}>
          <Input type="tel" autoComplete="tel" {...register("phone")} />
        </Field>
        <Field label="Email для связи" error={errors.contact_email?.message}>
          <Input type="email" {...register("contact_email")} />
        </Field>
      </Section>

      <Card>
        <Switch
          label="Скрыть профиль от работодателей"
          description="Вы пропадёте из каталога, новые офферы приходить не будут"
          {...register("is_hidden")}
        />
      </Card>

      <div className="fixed inset-x-0 bottom-0 z-20 border-t border-line bg-bg/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-end gap-3 px-4 py-3 sm:px-6">
          <span className="text-sm text-muted" aria-live="polite">
            {isDirty ? "Есть несохранённые изменения" : "Все изменения сохранены"}
          </span>
          <Button type="submit" loading={update.isPending} disabled={!isDirty}>
            <Save className="size-4" aria-hidden />
            Сохранить
          </Button>
        </div>
      </div>
    </form>
  );
}
