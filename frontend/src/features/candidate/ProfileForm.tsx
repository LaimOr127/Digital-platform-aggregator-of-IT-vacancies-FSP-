import { zodResolver } from "@hookform/resolvers/zod";
import { Save } from "lucide-react";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Controller, useForm } from "react-hook-form";
import { useDictionaries } from "../../api/queries";
import type { Profile, ProfileDraft, Skill } from "../../api/types";
import { labels, options } from "../../lib/format";
import { applyServerErrors } from "../../lib/forms";
import { Button } from "../../ui/Button";
import { Card, CardTitle } from "../../ui/Card";
import { Field, FieldGroup, Input, MoneyInput, Select, Switch, Textarea } from "../../ui/form";
import { Segmented } from "../../ui/Segmented";
import { ChipGroup } from "../../ui/ChipGroup";
import { CitySelect } from "../../ui/CitySelect";
import { SkillPicker } from "../../ui/SkillPicker";
import { useToast } from "../../ui/Toast";
import { useUpdateProfile } from "./hooks";
import type { DraftLists, FieldChange } from "./import/draft";
import { DraftDialog } from "./import/DraftDialog";
import { ImportCard } from "./import/ImportCard";
import { formToUpdate, profileSchema, profileToForm, type ProfileFormInput, type ProfileFormOutput } from "./schemas";

const FIELDS = [
  "full_name", "title", "about", "grade", "work_formats", "city", "relocation", "education", "salary_min",
  "salary_max", "skills", "custom_skills", "is_hidden", "search_status", "phone", "telegram", "contact_email",
  "experience_years", "roles", "soft_skills", "specialization",
];
const FORMAT_OPTIONS = options(labels.workFormat);
const EDUCATION_OPTIONS = options(labels.education);
const SEARCH_OPTIONS = options(labels.searchStatus);
const ALIASES = { "contacts.phone": "phone", "contacts.telegram": "telegram", "contacts.email": "contact_email" };
/** сколько держится «Все изменения сохранены» после сохранения */
const SAVED_NOTICE_MS = 3000;

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
  const dictionaries = useDictionaries().data;
  const form = useForm<ProfileFormInput, unknown, ProfileFormOutput>({
    resolver: zodResolver(profileSchema),
    values: profileToForm(profile),
    // фоновое обновление профиля не стирает несохранённые правки пользователя
    resetOptions: { keepDirtyValues: true },
  });
  const { register, control, formState } = form;
  const { errors, isDirty } = formState;
  // панель сохранения видна, пока есть правки, и ещё несколько секунд после сохранения
  const [justSaved, setJustSaved] = useState(false);
  useEffect(() => {
    if (!justSaved) return;
    const timer = setTimeout(() => setJustSaved(false), SAVED_NOTICE_MS);
    return () => clearTimeout(timer);
  }, [justSaved]);

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      const saved = await update.mutateAsync(formToUpdate(values));
      // сохранённое — новая точка отсчёта: иначе поля, изменённые до сохранения, остаются «грязными»
      form.reset(profileToForm(saved));
      setJustSaved(true);
    } catch (err) {
      const message = applyServerErrors(err, form.setError, FIELDS, ALIASES);
      if (message) notify(message, "error");
    }
  });

  const applyDraft = (changes: FieldChange[], added: DraftLists) => {
    const options = { shouldDirty: true, shouldValidate: true } as const;
    for (const change of changes) form.setValue(change.field, change.value as never, options);
    for (const name of ["skills", "custom_skills", "roles", "soft_skills"] as const) {
      if (added[name].length) form.setValue(name, [...form.getValues(name), ...added[name]], options);
    }
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
          profile={profile}
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
        <Field label="Имя и фамилия" error={errors.full_name?.message} hint="Компания увидит его, только когда вы примете её приглашение или откликнетесь">
          <Input autoComplete="name" {...register("full_name")} />
        </Field>
        <Field label="Должность" error={errors.title?.message}>
          <Input placeholder="Backend-разработчик" {...register("title")} />
        </Field>
        <Field label="Грейд" error={errors.grade?.message}>
          <Select placeholder="Не выбран" options={options(labels.grade)} {...register("grade")} />
        </Field>
        <Field
          label="Специализация"
          error={errors.specialization?.message}
          hint={
            profile.confirmed_grade
              ? "Подтверждена тестом — сменить можно через опрос"
              : "Заявленная: подсказка для опроса, категорию подтверждает тест"
          }
        >
          <Select
            placeholder="Не выбрана"
            options={options(labels.specialization)}
            disabled={Boolean(profile.confirmed_grade)}
            {...register("specialization")}
          />
        </Field>
        <Field label="Образование" error={errors.education?.message}>
          <Select placeholder="Не указано" options={EDUCATION_OPTIONS} {...register("education")} />
        </Field>
        <FieldGroup label="Формат работы" hint="Можно выбрать несколько" error={errors.work_formats?.message}>
          <Controller
            control={control}
            name="work_formats"
            render={({ field }) => <ChipGroup options={FORMAT_OPTIONS} value={field.value} onChange={field.onChange} />}
          />
        </FieldGroup>
        <Controller
          control={control}
          name="city"
          render={({ field }) => (
            <Field label="Город" error={errors.city?.message}>
              <CitySelect value={field.value} onChange={field.onChange} onBlur={field.onBlur} name={field.name} />
            </Field>
          )}
        />
        <div className="flex items-end sm:col-span-2">
          <Switch
            label="Готов к переезду"
            description="Работодатели из других городов увидят вас в фильтре по своему городу"
            {...register("relocation")}
          />
        </div>
      </Section>

      <Section title="Опыт, роли и софт-скиллы" text="Заполняются из резюме автоматически — проверьте и поправьте.">
        <Field label="Опыт в профессии, лет" hint="Можно с десятыми: 3 года 5 месяцев — 3,4" error={errors.experience_years?.message}>
          <Input type="number" inputMode="decimal" min={0} max={50} step={0.1} {...register("experience_years")} />
        </Field>
        {dictionaries && (
          <>
            <FieldGroup label="Роли" hint="До 5" error={errors.roles?.message} className="sm:col-span-2">
              <Controller
                control={control}
                name="roles"
                render={({ field }) => <ChipGroup options={dictionaries.roles} value={field.value} onChange={field.onChange} max={5} />}
              />
            </FieldGroup>
            <FieldGroup label="Софт-скиллы" hint="До 10: выберите или впишите своё" error={errors.soft_skills?.message} className="sm:col-span-2">
              <Controller
                control={control}
                name="soft_skills"
                render={({ field }) => (
                  <ChipGroup options={dictionaries.soft_skills} value={field.value} onChange={field.onChange} max={10} allowCustom />
                )}
              />
            </FieldGroup>
          </>
        )}
      </Section>

      <Section title="Ожидания по зарплате" text="Рубли в месяц до вычета налогов. Компании предлагают оффер с вилкой.">
        <Field label="От, ₽" error={errors.salary_min?.message}>
          <MoneyInput {...register("salary_min")} />
        </Field>
        <Field label="До, ₽" error={errors.salary_max?.message}>
          <MoneyInput {...register("salary_max")} />
        </Field>
      </Section>

      <Card>
        <FieldGroup
          label="Навыки"
          hint="Из справочника — так работодатели находят вас по стеку. Нет нужного — добавьте свой."
          error={errors.skills?.message ?? errors.custom_skills?.message}
        >
          <Controller
            control={control}
            name="skills"
            render={({ field }) => (
              <Controller
                control={control}
                name="custom_skills"
                render={({ field: own }) => (
                  <SkillPicker
                    skills={skills}
                    value={field.value}
                    onChange={field.onChange}
                    max={50}
                    custom={own.value}
                    onCustomChange={own.onChange}
                  />
                )}
              />
            )}
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

      <Section title="Контакты" text="Компания получит их, только когда вы примете её приглашение или откликнетесь сами.">
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

      {(isDirty || justSaved) && (
        <div className="fixed inset-x-0 bottom-0 z-20 border-t border-line bg-bg/90 backdrop-blur">
          <div className="mx-auto flex max-w-6xl items-center justify-end gap-3 px-4 py-3 sm:px-6">
            <span className="text-sm text-muted" aria-live="polite">
              {isDirty ? "Есть несохранённые изменения" : "Все изменения сохранены"}
            </span>
            {isDirty && (
              <Button type="submit" loading={update.isPending}>
                <Save className="size-4" aria-hidden />
                Сохранить
              </Button>
            )}
          </div>
        </div>
      )}
    </form>
  );
}
