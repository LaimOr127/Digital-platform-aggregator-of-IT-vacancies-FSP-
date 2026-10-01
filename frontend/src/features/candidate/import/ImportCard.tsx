import { useMutation, useQuery } from "@tanstack/react-query";
import { FileText, Link2, Sparkles } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import { importApi } from "../../../api/endpoints";
import { errorMessage } from "../../../api/errors";
import type { ProfileDraft } from "../../../api/types";
import { Alert } from "../../../ui/Alert";
import { Button } from "../../../ui/Button";
import { Card, CardTitle } from "../../../ui/Card";

const ACCEPT = ".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document";

type Props = {
  fspLinked: boolean;
  /** открыть импорт из ФСП сразу (переход со страницы ФСП) */
  autoFsp?: boolean;
  onDraft: (draft: ProfileDraft) => void;
};

/** Автозаполнение: из анкеты ФСП или из файла резюме (алгоритм, по согласию — ИИ). */
export function ImportCard({ fspLinked, autoFsp = false, onDraft }: Props) {
  const fileId = useId();
  const input = useRef<HTMLInputElement>(null);
  const [useAi, setUseAi] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const capabilities = useQuery({ queryKey: ["import-capabilities"], queryFn: importApi.capabilities, staleTime: Infinity });
  const maxMb = capabilities.data?.max_file_mb ?? 5;
  const handlers = { onSuccess: onDraft, onError: (err: Error) => setError(errorMessage(err)) };
  const fsp = useMutation({ mutationFn: importApi.fromFsp, ...handlers });
  const resume = useMutation({ mutationFn: (file: File) => importApi.fromResume(file, useAi), ...handlers });

  const started = useRef(false);
  useEffect(() => {
    if (autoFsp && fspLinked && !started.current) {
      started.current = true;
      fsp.mutate();
    }
  }, [autoFsp, fspLinked, fsp]);

  const pickFile = (file: File | undefined) => {
    setError(null);
    if (input.current) input.current.value = ""; // тот же файл можно выбрать повторно
    if (!file) return;
    if (file.size > maxMb * 1024 * 1024) return setError(`Файл больше ${maxMb} МБ`);
    resume.mutate(file);
  };

  return (
    <Card className="border-accent/30 bg-accent/5">
      <div className="flex items-center gap-2">
        <Sparkles className="size-5 text-accent" aria-hidden />
        <CardTitle>Заполнить автоматически</CardTitle>
      </div>
      <p className="mt-1 text-sm text-muted">
        Подставим данные из анкеты ФСП или из вашего резюме — вы проверите их перед сохранением.
      </p>
      {error && (
        <div className="mt-4">
          <Alert>{error}</Alert>
        </div>
      )}
      <div className="mt-4 flex flex-wrap gap-3">
        <Button
          variant="secondary"
          onClick={() => {
            setError(null);
            fsp.mutate();
          }}
          loading={fsp.isPending}
          disabled={!fspLinked}
        >
          <Link2 className="size-4" aria-hidden />
          Из анкеты ФСП
        </Button>
        <Button variant="secondary" onClick={() => input.current?.click()} loading={resume.isPending}>
          <FileText className="size-4" aria-hidden />
          Из резюме (PDF, DOCX)
        </Button>
        <input
          ref={input}
          id={fileId}
          type="file"
          accept={ACCEPT}
          className="sr-only"
          aria-label="Файл резюме"
          onChange={(e) => pickFile(e.target.files?.[0])}
        />
      </div>
      {!fspLinked && <p className="mt-3 text-xs text-muted">Анкета ФСП доступна после привязки аккаунта.</p>}
      {capabilities.data?.ai_available && (
        <label className="mt-4 flex items-start gap-2 text-sm">
          <input type="checkbox" className="mt-0.5 accent-accent" checked={useAi} onChange={(e) => setUseAi(e.target.checked)} />
          <span>
            Разобрать резюме с помощью ИИ ({capabilities.data.ai_provider})
            <span className="block text-xs text-muted">
              Текст резюме без контактов будет передан этой модели. Без согласия работает наш алгоритм.
            </span>
          </span>
        </label>
      )}
    </Card>
  );
}
