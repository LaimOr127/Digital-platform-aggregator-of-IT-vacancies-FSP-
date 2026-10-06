// Опрос по отрасли и специализации: с него начинается путь кандидата к категории.
import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm, useWatch } from "react-hook-form";
import { useDictionaries, useSkills } from "../../../api/queries";
import type { AssessmentState, Grade, SurveyInput } from "../../../api/types";
import { labels, options } from "../../../lib/format";
import { applyServerErrors } from "../../../lib/forms";
import { Alert } from "../../../ui/Alert";
import { Button } from "../../../ui/Button";
import { ChipGroup } from "../../../ui/ChipGroup";
import { Field, FieldGroup, Input } from "../../../ui/form";
import { Segmented } from "../../../ui/Segmented";
import { SkillPicker } from "../../../ui/SkillPicker";
import { LoadingBlock } from "../../../ui/Spinner";
import { useToast } from "../../../ui/Toast";
import { useSaveSurvey } from "./hooks";
import { surveySchema, surveyToForm, type SurveyFormInput, type SurveyFormOutput } from "./schemas";

const FIELDS = ["specialization", "grade", "experience_years", "industries", "roles", "skills"];

export function SurveyForm({ state, onDone }: { state: AssessmentState | undefined; onDone?: () => void }) {
  const dictionaries = useDictionaries();
  const skills = useSkills();
  if (dictionaries.error || skills.error) return <Alert>Не удалось загрузить справочники</Alert>;
  if (!dictionaries.data || !skills.data) return <LoadingBlock />;
  return <Form state={state} onDone={onDone} />;
}

function Form({ state, onDone }: { state: AssessmentState | undefined; onDone?: () => void }) {
  const dictionaries = useDictionaries().data!;
  const skills = useSkills().data!;
  const notify = useToast();
  const save = useSaveSurvey();
  const form = useForm<SurveyFormInput, unknown, SurveyFormOutput>({
    resolver: zodResolver(surveySchema),
    defaultValues: surveyToForm(state),
  });
  const { control, formState, register } = form;
  const { errors, isSubmitting } = formState;
  const specialization = useWatch({ control, name: "specialization" });
  const typical = dictionaries.specializations.find((s) => s.slug === specialization)?.skills ?? [];

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      await save.mutateAsync(values as SurveyInput);
      notify("Ответы сохранены — можно проходить тест");
      onDone?.();
    } catch (err) {
      const message = applyServerErrors(err, form.setError, FIELDS);
      if (message) notify(message, "error");
    }
  });

  return (
    <form onSubmit={onSubmit} noValidate className="flex flex-col gap-7">
      <FieldGroup
        label="Специализация"
        hint="Категория, в которой вас увидят работодатели, — специализация и подтверждённый тестом грейд."
        error={errors.specialization?.message}
      >
        <Controller
          control={control}
          name="specialization"
          render={({ field }) => (
            <ChipGroup
              single
              options={dictionaries.specializations.map((s) => ({ value: s.slug, label: s.title }))}
              value={field.value ? [field.value] : []}
              onChange={(v) => field.onChange(v[0])}
            />
          )}
        />
      </FieldGroup>
      <FieldGroup
        label="Ваш грейд"
        hint="Тест проверит именно его. Не прошли — сможете сразу пройти тест на грейд ниже."
        error={errors.grade?.message}
      >
        <Controller
          control={control}
          name="grade"
          render={({ field }) => (
            <Segmented<Grade> label="Грейд" value={field.value} options={options(labels.grade)} onChange={field.onChange} />
          )}
        />
      </FieldGroup>
      <Field label="Опыт в профессии, лет" error={errors.experience_years?.message} className="max-w-48">
        <Input type="number" inputMode="numeric" min={0} max={50} {...register("experience_years")} />
      </Field>
      <FieldGroup label="Стек" hint={typicalHint(typical, skills)} error={errors.skills?.message}>
        <Controller
          control={control}
          name="skills"
          render={({ field }) => <SkillPicker skills={skills} value={field.value} onChange={field.onChange} max={30} />}
        />
      </FieldGroup>
      <FieldGroup label="Отрасли, в которых хотите работать" hint="До пяти, необязательно" error={errors.industries?.message}>
        <Controller
          control={control}
          name="industries"
          render={({ field }) => (
            <ChipGroup options={dictionaries.industries} value={field.value} onChange={field.onChange} max={5} />
          )}
        />
      </FieldGroup>
      <FieldGroup label="Роли, которые вам близки" hint="Необязательно" error={errors.roles?.message}>
        <Controller
          control={control}
          name="roles"
          render={({ field }) => <ChipGroup options={dictionaries.roles} value={field.value} onChange={field.onChange} max={5} />}
        />
      </FieldGroup>
      <div className="flex justify-end gap-3 border-t border-line pt-5">
        {onDone && state?.survey && (
          <Button variant="ghost" onClick={onDone}>
            Отмена
          </Button>
        )}
        <Button type="submit" loading={isSubmitting}>
          Сохранить ответы
        </Button>
      </div>
    </form>
  );
}

function typicalHint(typical: string[], skills: { slug: string; name: string }[]): string {
  const names = typical.map((slug) => skills.find((s) => s.slug === slug)?.name).filter(Boolean);
  const base = "Задания теста подбираются и под ваш стек.";
  return names.length ? `${base} Обычно для этой специализации: ${names.join(", ")}.` : base;
}
