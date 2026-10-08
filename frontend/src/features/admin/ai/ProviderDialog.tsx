import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import type { AiProvider } from "../../../api/types";
import { applyServerErrors } from "../../../lib/forms";
import { Alert } from "../../../ui/Alert";
import { Button } from "../../../ui/Button";
import { Dialog } from "../../../ui/Dialog";
import { Field, Input, Select } from "../../../ui/form";
import { useToast } from "../../../ui/Toast";
import { useCreateProvider, useUpdateProvider } from "./hooks";
import { PRESETS } from "./presets";

const schema = z.object({
  name: z.string().trim().min(2, "Минимум 2 символа").max(80),
  kind: z.enum(["openai", "anthropic"]),
  base_url: z.string().trim().min(8, "Укажите адрес API").max(300),
  model: z
    .string()
    .trim()
    .min(1, "Укажите модель")
    .max(120)
    // шаблон YandexGPT подставляет gpt://<folder_id>/... — заглушку легко оставить, а сервис ответит 400
    .refine((v) => !/[<>]/.test(v), "Замените <folder_id> на ID каталога Yandex Cloud (консоль → каталог → ID)"),
  api_key: z.string().trim().max(512),
});
type Form = z.infer<typeof schema>;
const KINDS = [
  { value: "openai", label: "OpenAI-совместимый (/chat/completions)" },
  { value: "anthropic", label: "Anthropic (/v1/messages)" },
];

type Props = { open: boolean; provider: AiProvider | null; onClose: () => void };

/** Подключение или изменение модели. Ключ не показывается: пустое поле — оставить прежний. */
export function ProviderDialog({ open, provider, onClose }: Props) {
  const notify = useToast();
  const create = useCreateProvider();
  const update = useUpdateProvider();
  const [error, setError] = useState<string | null>(null);
  const [hint, setHint] = useState<string | undefined>();
  const form = useForm<Form>({
    resolver: zodResolver(schema),
    defaultValues: provider
      ? { name: provider.name, kind: provider.kind, base_url: provider.base_url, model: provider.model, api_key: "" }
      : { name: "", kind: "openai", base_url: "https://", model: "", api_key: "" },
  });
  const { errors, isSubmitting } = form.formState;

  const applyPreset = (id: string) => {
    const preset = PRESETS.find((p) => p.id === id);
    if (!preset) return;
    form.reset({ ...form.getValues(), name: preset.id === "custom" ? "" : preset.label, kind: preset.kind, base_url: preset.base_url, model: preset.model });
    setHint(preset.hint);
  };

  const onSubmit = form.handleSubmit(async ({ api_key, ...values }) => {
    setError(null);
    try {
      if (provider) {
        await update.mutateAsync({ id: provider.id, body: { ...values, api_key: api_key || null, clear_key: false } });
      }
      else await create.mutateAsync({ ...values, api_key: api_key || null });
      notify(provider ? "Модель обновлена" : "Модель подключена — проверьте связь и сделайте активной");
      onClose();
    } catch (err) {
      setError(applyServerErrors(err, form.setError, ["name", "kind", "base_url", "model", "api_key"]));
    }
  });

  return (
    <Dialog open={open} title={provider ? "Изменить модель" : "Подключить модель"} onClose={onClose} wide>
      <form onSubmit={onSubmit} noValidate className="grid gap-5 sm:grid-cols-2">
        {error && (
          <div className="sm:col-span-2">
            <Alert>{error}</Alert>
          </div>
        )}
        {!provider && (
          <Field label="Шаблон" className="sm:col-span-2" hint={hint}>
            <Select placeholder="Выберите провайдера" options={PRESETS.map((p) => ({ value: p.id, label: p.label }))} onChange={(e) => applyPreset(e.target.value)} />
          </Field>
        )}
        <Field label="Название" error={errors.name?.message}>
          <Input placeholder="Например: YandexGPT Pro" {...form.register("name")} />
        </Field>
        <Field label="Вид API" error={errors.kind?.message}>
          <Select options={KINDS} {...form.register("kind")} />
        </Field>
        <Field label="Адрес API" error={errors.base_url?.message} className="sm:col-span-2" hint="https:// — для облачных моделей; http:// — только для локальной">
          <Input spellCheck={false} {...form.register("base_url")} />
        </Field>
        <Field label="Модель" error={errors.model?.message}>
          <Input spellCheck={false} {...form.register("model")} />
        </Field>
        <Field
          label="Ключ API"
          error={errors.api_key?.message}
          hint={provider?.has_key ? `Сохранён ключ ${provider.key_hint ?? ""} — оставьте пустым, чтобы не менять` : "Хранится зашифрованным"}
        >
          <Input type="password" autoComplete="off" spellCheck={false} {...form.register("api_key")} />
        </Field>
        <div className="flex justify-end gap-3 sm:col-span-2">
          <Button variant="ghost" onClick={onClose}>
            Отмена
          </Button>
          <Button type="submit" loading={isSubmitting}>
            {provider ? "Сохранить" : "Подключить"}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
