// Как система формирует задания под вакансию: пример теста по её специализации, грейду и стеку.
// Каждый показ — новый вариант (параметры заданий меняются), поэтому ответы видны.
import { useQuery } from "@tanstack/react-query";
import { Check, RefreshCw } from "lucide-react";
import { employerApi } from "../../api/endpoints";
import { errorMessage } from "../../api/errors";
import type { Vacancy } from "../../api/types";
import { labels } from "../../lib/format";
import { Alert } from "../../ui/Alert";
import { Button } from "../../ui/Button";
import { Dialog } from "../../ui/Dialog";
import { LoadingBlock } from "../../ui/Spinner";

export function TestPreviewDialog({ vacancy, onClose }: { vacancy: Vacancy | null; onClose: () => void }) {
  const preview = useQuery({
    queryKey: ["assessment-preview", vacancy?.id],
    queryFn: () => employerApi.assessmentPreview(vacancy!.id),
    enabled: vacancy !== null,
    staleTime: Infinity,
  });
  return (
    <Dialog open={vacancy !== null} title="Пример теста для кандидатов" onClose={onClose} wide>
      <p className="text-sm text-muted">
        Задания подобраны по специализации, грейду и навыкам вакансии: уровни ниже, на уровне и выше{" "}
        {vacancy ? labels.grade[vacancy.grade] : ""}. Каждый кандидат получает свой вариант — числа, данные и
        утверждения меняются, поэтому ответы чужой попытки бесполезны.
      </p>
      {preview.error && <Alert>{errorMessage(preview.error)}</Alert>}
      {preview.isPending && <LoadingBlock />}
      {preview.data && (
        <>
          <ol className="mt-5 flex flex-col gap-4">
            {preview.data.map((q) => (
              <li key={q.index} className="rounded-xl border border-line p-4 text-sm">
                <p className="text-xs text-muted">
                  {q.index + 1}. {q.topic} · уровень {q.level}
                  {q.skills.length > 0 && ` · ${q.skills.join(", ")}`}
                </p>
                <p className="mt-1 font-medium">{q.prompt}</p>
                {q.code && (
                  <pre className="mt-2 overflow-x-auto rounded-lg bg-bg p-3 text-xs">
                    <code>{q.code}</code>
                  </pre>
                )}
                {q.options.length > 0 && (
                  <ul className="mt-2 flex flex-col gap-1">
                    {q.options.map((o) => (
                      <li key={o} className={o === q.answer ? "flex gap-1.5 text-accent" : "pl-5 text-muted"}>
                        {o === q.answer && <Check className="mt-0.5 size-3.5 shrink-0" aria-label="верный ответ" />}
                        {o}
                      </li>
                    ))}
                  </ul>
                )}
                {q.kind === "number" && <p className="mt-2 text-accent">Ответ: {q.answer}</p>}
              </li>
            ))}
          </ol>
          <div className="mt-5 flex justify-end">
            <Button variant="secondary" onClick={() => void preview.refetch()} loading={preview.isFetching}>
              <RefreshCw className="size-3.5" aria-hidden />
              Другой вариант
            </Button>
          </div>
        </>
      )}
    </Dialog>
  );
}
