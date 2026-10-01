// Детали собеседования — одинаково для компании и кандидата: время, формат, место, кто проводит.
import { Clock, MapPin, User, Video } from "lucide-react";
import type { Interview } from "../../api/types";
import { formatDateTime, labels } from "../../lib/format";

export function InterviewDetails({ interview }: { interview: Interview }) {
  const online = interview.format === "online";
  const showLink = online && interview.status === "scheduled";
  return (
    <dl className="grid gap-2 text-sm sm:grid-cols-2">
      <div className="flex items-start gap-2">
        <Clock className="mt-0.5 size-4 shrink-0 text-muted" aria-hidden />
        <div>
          <dt className="sr-only">Время</dt>
          <dd>
            {interview.scheduled_at
              ? `${formatDateTime(interview.scheduled_at)} · ${interview.duration_minutes} мин`
              : `Варианты: ${interview.slots.map(formatDateTime).join("; ")}`}
          </dd>
        </div>
      </div>
      <div className="flex items-start gap-2">
        {online ? <Video className="mt-0.5 size-4 shrink-0 text-muted" aria-hidden /> : <MapPin className="mt-0.5 size-4 shrink-0 text-muted" aria-hidden />}
        <div className="min-w-0">
          <dt className="sr-only">Формат</dt>
          <dd className="break-words">
            {labels.interviewFormat[interview.format]}
            {showLink ? (
              <>
                {" · "}
                <a href={interview.location} target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">
                  ссылка на встречу
                </a>
              </>
            ) : (
              !online && ` · ${interview.location}`
            )}
          </dd>
        </div>
      </div>
      <div className="flex items-start gap-2 sm:col-span-2">
        <User className="mt-0.5 size-4 shrink-0 text-muted" aria-hidden />
        <div>
          <dt className="sr-only">Кто проводит</dt>
          <dd>{interview.interviewer}</dd>
        </div>
      </div>
      {interview.message && <p className="whitespace-pre-line text-muted sm:col-span-2">{interview.message}</p>}
      {interview.decline_reason && <p className="text-muted sm:col-span-2">Причина: {interview.decline_reason}</p>}
      {interview.feedback && <p className="whitespace-pre-line sm:col-span-2">Отзыв: {interview.feedback}</p>}
    </dl>
  );
}
