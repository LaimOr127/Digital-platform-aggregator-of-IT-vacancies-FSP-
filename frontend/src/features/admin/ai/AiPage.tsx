import { Bot, Pencil, PlugZap, Plus, Power, Trash2 } from "lucide-react";
import { useState } from "react";
import { errorMessage } from "../../../api/errors";
import type { AiProvider, AiTest } from "../../../api/types";
import { Alert } from "../../../ui/Alert";
import { PageHeader } from "../../../ui/AppShell";
import { Badge } from "../../../ui/Badge";
import { Button } from "../../../ui/Button";
import { ConfirmDialog } from "../../../ui/ConfirmDialog";
import { EmptyState } from "../../../ui/EmptyState";
import { LoadingBlock } from "../../../ui/Spinner";
import { useAction } from "../../../ui/useAction";
import { useActivateProvider, useAiProviders, useDeleteProvider, useTestProvider } from "./hooks";
import { ProviderDialog } from "./ProviderDialog";

const KIND_LABELS = { openai: "OpenAI-совместимый", anthropic: "Anthropic" } as const;

/** Языковые модели: подключение любой OpenAI-совместимой или Anthropic, выбор активной. */
export function AiPage() {
  const providers = useAiProviders();
  const [editing, setEditing] = useState<AiProvider | "new" | null>(null);
  const [deleting, setDeleting] = useState<AiProvider | null>(null);
  const remove = useDeleteProvider();
  const run = useAction();
  const items = providers.data ?? [];

  return (
    <>
      <PageHeader
        title="Искусственный интеллект"
        text="Модель разбирает резюме кандидатов (с их согласия, без контактов). Подключите любую модель с OpenAI-совместимым API или Anthropic — активна одна."
      >
        <Button onClick={() => setEditing("new")}>
          <Plus className="size-4" aria-hidden />
          Подключить модель
        </Button>
      </PageHeader>
      {providers.error && <Alert>{errorMessage(providers.error)}</Alert>}
      {providers.isPending && <LoadingBlock />}
      {providers.data && items.length === 0 && (
        <EmptyState
          icon={<Bot className="size-5" />}
          title="Модели не подключены"
          text="Без модели резюме разбирает встроенный алгоритм. Подключите облачную модель или локальную (Ollama), чтобы разбор был точнее."
        />
      )}
      <div className="flex flex-col gap-3">
        {items.map((p) => (
          <ProviderRow key={p.id} provider={p} onEdit={() => setEditing(p)} onDelete={() => setDeleting(p)} />
        ))}
      </div>
      {editing && (
        <ProviderDialog
          key={editing === "new" ? "new" : editing.id}
          open
          provider={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
        />
      )}
      <ConfirmDialog
        open={deleting !== null}
        title={`Удалить «${deleting?.name ?? ""}»?`}
        confirmLabel="Удалить"
        pending={remove.isPending}
        onClose={() => setDeleting(null)}
        onConfirm={() => deleting && run(remove, deleting.id, "Модель удалена", () => setDeleting(null))}
      >
        Ключ будет удалён. Если модель активна, разбор резюме перейдёт на встроенный алгоритм.
      </ConfirmDialog>
    </>
  );
}

function ProviderRow({ provider, onEdit, onDelete }: { provider: AiProvider; onEdit: () => void; onDelete: () => void }) {
  const run = useAction();
  const activate = useActivateProvider();
  const test = useTestProvider();
  const [result, setResult] = useState<AiTest | null>(null);
  const check = () => test.mutate(provider.id, { onSuccess: setResult });

  return (
    <article className="flex flex-col gap-4 rounded-2xl border border-line bg-surface p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-semibold">{provider.name}</h3>
            <Badge tone="neutral">{KIND_LABELS[provider.kind]}</Badge>
            {provider.is_active && <Badge tone="accent">Активна</Badge>}
          </div>
          <p className="mt-1 break-all font-mono text-xs text-muted">
            {provider.model} · {provider.base_url}
          </p>
          <p className="mt-1 text-xs text-muted">{provider.has_key ? `Ключ ${provider.key_hint ?? "сохранён"}` : "Без ключа"}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" size="sm" onClick={check} loading={test.isPending}>
            <PlugZap className="size-3.5" aria-hidden />
            Проверить
          </Button>
          <Button
            variant={provider.is_active ? "ghost" : "primary"}
            size="sm"
            loading={activate.isPending}
            onClick={() =>
              run(activate, provider.is_active ? null : provider.id, provider.is_active ? "ИИ выключен" : `Активна: ${provider.name}`)
            }
          >
            <Power className="size-3.5" aria-hidden />
            {provider.is_active ? "Выключить" : "Сделать активной"}
          </Button>
          <Button variant="ghost" size="sm" onClick={onEdit} aria-label={`Изменить ${provider.name}`}>
            <Pencil className="size-3.5" aria-hidden />
          </Button>
          <Button variant="ghost" size="sm" onClick={onDelete} aria-label={`Удалить ${provider.name}`}>
            <Trash2 className="size-3.5" aria-hidden />
          </Button>
        </div>
      </div>
      {result && <Alert tone={result.ok ? "info" : "danger"}>{result.message}</Alert>}
      {test.error && <Alert>{errorMessage(test.error)}</Alert>}
    </article>
  );
}
