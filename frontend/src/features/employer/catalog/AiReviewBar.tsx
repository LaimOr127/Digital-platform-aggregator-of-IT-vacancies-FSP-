// Второе мнение языковой модели о первых кандидатах выдачи под выбранную вакансию.
// Модели уходят только анонимные карточки; оценка дополняет процент соответствия, а не заменяет его.
import { useMutation, useQuery } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";
import { catalogApi } from "../../../api/endpoints";
import type { AiReview } from "../../../api/types";
import { Button } from "../../../ui/Button";
import { useAction } from "../../../ui/useAction";

const REVIEWED = 10;

type Props = { vacancyId: string; anonIds: string[]; onReviews: (reviews: AiReview[]) => void };

export function AiReviewBar({ vacancyId, anonIds, onReviews }: Props) {
  const status = useQuery({ queryKey: ["catalog", "ai-status"], queryFn: catalogApi.aiStatus, staleTime: 60_000 });
  const review = useMutation({
    mutationFn: () => catalogApi.aiReview(vacancyId, anonIds.slice(0, REVIEWED)),
    onSuccess: onReviews,
  });
  const run = useAction();
  if (!status.data?.available || anonIds.length === 0) return null;
  return (
    <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-line bg-surface p-4 text-sm">
      <p className="max-w-2xl text-muted">
        Второе мнение ИИ ({status.data.provider}): оценит первых {Math.min(REVIEWED, anonIds.length)} кандидатов под
        вакансию и объяснит оценку. Модели уходят только анонимные карточки — без имени, контактов и «о себе».
      </p>
      <Button variant="secondary" size="sm" loading={review.isPending} onClick={() => run(review, undefined, "Оценки ИИ добавлены в карточки")}>
        <Sparkles className="size-3.5" aria-hidden />
        Оценить с ИИ
      </Button>
    </div>
  );
}

export function AiReviewNote({ review }: { review: AiReview }) {
  return (
    <p className="flex items-start gap-2 rounded-xl bg-surface-2 px-3 py-2 text-sm">
      <Sparkles className="mt-0.5 size-3.5 shrink-0 text-accent" aria-hidden />
      <span>
        <span className="font-semibold tabular">ИИ: {review.fit}%</span> — {review.reason}
      </span>
    </p>
  );
}
