import { CalendarClock, ClipboardList, MapPin, Pencil, Send, Trash2, XCircle } from "lucide-react";
import { motion } from "motion/react";
import type { Vacancy } from "../../api/types";
import { daysLeft, labels } from "../../lib/format";
import { vacancyTone } from "../../lib/tones";
import { Badge } from "../../ui/Badge";
import { Button } from "../../ui/Button";
import { useAction } from "../../ui/useAction";
import { RENEW_SOON_DAYS, useCloseVacancy, usePublishVacancy } from "./hooks";
import { Salary } from "../../ui/Salary";

type Props = {
  vacancy: Vacancy;
  canPublish: boolean;
  onEdit: (v: Vacancy) => void;
  onDelete: (v: Vacancy) => void;
  onPreview: (v: Vacancy) => void;
};

/** Опубликованная вакансия, которую пора продлить (или уже истёкшая). */
export const needsRenewal = (v: Vacancy): boolean => {
  const left = v.status === "active" ? daysLeft(v.expires_at) : null;
  return left !== null && left <= RENEW_SOON_DAYS;
};

/** Порядок в списке компании: сначала к продлению, затем живые, внизу закрытые и снятые. */
export const vacancyRank = (v: Vacancy): number =>
  needsRenewal(v) ? 0 : v.status === "closed" || v.status === "blocked" ? 2 : 1;

export function VacancyCard({ vacancy: v, canPublish, onEdit, onDelete, onPreview }: Props) {
  const run = useAction();
  const publish = usePublishVacancy();
  const close = useCloseVacancy();
  const editable = v.status !== "blocked";
  const left = v.status === "active" ? daysLeft(v.expires_at) : null;
  const renew = needsRenewal(v);

  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-line bg-surface p-5 transition-colors hover:border-muted/40"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="flex items-center gap-2 text-lg font-semibold">
            {renew && (
              <span
                className="inline-flex size-6 shrink-0 items-center justify-center rounded-full bg-accent text-sm font-bold text-on-accent"
                title="Пора продлить"
              >
                !<span className="sr-only">Пора продлить:</span>
              </span>
            )}
            <span className="truncate">{v.title}</span>
          </h3>
          <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted">
            {v.specialization && <span>{labels.specialization[v.specialization]}</span>}
            <span>{labels.grade[v.grade]}</span>
            <span>{labels.workFormat[v.work_format]}</span>
            {v.city && (
              <span className="inline-flex items-center gap-1">
                <MapPin className="size-3.5" aria-hidden />
                {v.city}
              </span>
            )}
          </p>
        </div>
        <Badge tone={vacancyTone[v.status]}>{labels.vacancyStatus[v.status]}</Badge>
      </div>

      <p className="mt-4 text-xl font-semibold tabular"><Salary min={v.salary_min} max={v.salary_max} /></p>

      {v.skills.length > 0 && (
        <ul className="mt-4 flex flex-wrap gap-2" aria-label="Навыки">
          {v.skills.map((s) => (
            <li key={s.slug} className="rounded-full border border-line px-2.5 py-0.5 text-xs text-muted">
              {s.name}
            </li>
          ))}
        </ul>
      )}

      <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-line pt-4">
        {left !== null && (
          <span
            className={`mr-auto inline-flex items-center gap-1.5 text-sm ${
              renew ? "rounded-full bg-warn/15 px-2.5 py-1 font-semibold text-warn" : "text-muted"
            }`}
          >
            <CalendarClock className="size-4" aria-hidden />
            {left > 0 ? `Осталось дней: ${left}` : "Срок истёк — продлите или закройте"}
          </span>
        )}
        {v.status === "blocked" && <span className="mr-auto text-sm text-danger">Заблокирована модератором</span>}
        <div className="ml-auto flex flex-wrap gap-2">
          {v.specialization && (
            <Button variant="ghost" size="sm" onClick={() => onPreview(v)}>
              <ClipboardList className="size-3.5" aria-hidden />
              Пример теста
            </Button>
          )}
          {editable && (
            <Button variant="secondary" size="sm" onClick={() => onEdit(v)}>
              <Pencil className="size-3.5" aria-hidden />
              Изменить
            </Button>
          )}
          {editable && v.status !== "closed" && (
            <Button
              size="sm"
              onClick={() => run(publish, v.id, v.status === "active" ? "Продлено на 14 дней" : "Вакансия опубликована")}
              loading={publish.isPending}
              disabled={!canPublish}
              title={canPublish ? undefined : "Публикация доступна после одобрения компании"}
            >
              <Send className="size-3.5" aria-hidden />
              {v.status === "active" ? "Продлить" : "Опубликовать"}
            </Button>
          )}
          {v.status === "active" && (
            <Button variant="ghost" size="sm" onClick={() => run(close, v.id, "Вакансия закрыта")} loading={close.isPending}>
              <XCircle className="size-3.5" aria-hidden />
              Закрыть
            </Button>
          )}
          {editable && (
            <Button variant="ghost" size="sm" onClick={() => onDelete(v)} aria-label={`Удалить «${v.title}»`}>
              <Trash2 className="size-3.5" aria-hidden />
            </Button>
          )}
        </div>
      </div>
    </motion.article>
  );
}
