// Подсказка для опроса: языковая модель (или правила по стеку и стажу) предлагает специализацию
// и грейд. Кандидат применяет её одним нажатием; категорию всё равно подтверждает тест.
import { useMutation } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";
import { assessmentApi } from "../../../api/endpoints";
import { errorMessage } from "../../../api/errors";
import type { Grade, Specialization } from "../../../api/types";
import { labels } from "../../../lib/format";
import { Button } from "../../../ui/Button";

type Props = { onApply: (specialization: Specialization, grade: Grade | null) => void };

export function SuggestionHint({ onApply }: Props) {
  const suggest = useMutation({ mutationFn: assessmentApi.suggest });
  const s = suggest.data;
  return (
    <div className="rounded-xl border border-line bg-surface-2 p-4 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-muted">Не уверены, что выбрать? Подскажем по вашему профилю: стек, стаж, роли.</p>
        <Button variant="secondary" size="sm" loading={suggest.isPending} onClick={() => suggest.mutate()}>
          <Sparkles className="size-3.5" aria-hidden />
          Подсказать
        </Button>
      </div>
      {suggest.error && <p className="mt-3 text-danger">{errorMessage(suggest.error)}</p>}
      {s && (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-3" aria-live="polite">
          <div className="min-w-0">
            <p className="font-medium">
              {s.specialization ? labels.specialization[s.specialization] : "Специализация не определена"}
              {s.grade && ` · ${labels.grade[s.grade]}`}
            </p>
            <p className="mt-0.5 text-muted">
              {s.reason}{" "}
              <span className="text-xs">({s.source === "ai" ? `модель: ${s.provider}` : "по правилам"})</span>
            </p>
          </div>
          {s.specialization && (
            <Button size="sm" onClick={() => s.specialization && onApply(s.specialization, s.grade ?? null)}>
              Применить
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
