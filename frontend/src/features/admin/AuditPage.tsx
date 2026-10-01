import { ScrollText } from "lucide-react";
import { useState } from "react";
import type { AuditEntry } from "../../api/types";
import { cn } from "../../lib/cn";
import { formatDateTime } from "../../lib/format";
import { PageHeader } from "../../ui/AppShell";
import { CursorListView } from "../../ui/CursorListView";
import { Segmented } from "../../ui/Segmented";
import { ALERT_ACTIONS, auditDetails, auditLabel } from "./auditLabels";
import { useAudit } from "./hooks";

type Filter = "all" | "admin." | "auth." | "offer." | "fsp.";

const FILTERS: { value: Filter; label: string }[] = [
  { value: "all", label: "Все" },
  { value: "admin.", label: "Модерация" },
  { value: "auth.", label: "Вход и 2FA" },
  { value: "offer.", label: "Офферы" },
  { value: "fsp.", label: "ФСП" },
];

export function AuditPage() {
  const [filter, setFilter] = useState<Filter>("all");
  const query = useAudit(filter === "all" ? undefined : filter);
  return (
    <>
      <PageHeader
        title="Журнал аудита"
        text="Неизменяемая история значимых действий: модерация, входы администраторов, офферы и раскрытие контактов."
      />
      <div className="mb-6 overflow-x-auto">
        <Segmented label="Тип событий" value={filter} options={FILTERS} onChange={setFilter} />
      </div>
      <CursorListView
        query={query}
        className="overflow-hidden rounded-2xl border border-line bg-surface"
        empty={{ icon: <ScrollText className="size-5" />, title: "Событий нет", text: "В этой категории пока ничего не произошло." }}
      >
        {(entry) => <AuditRow key={entry.id} entry={entry} />}
      </CursorListView>
    </>
  );
}

function AuditRow({ entry }: { entry: AuditEntry }) {
  const details = auditDetails(entry.meta);
  const alert = ALERT_ACTIONS.has(entry.action);
  return (
    <div className="grid gap-1 border-b border-line px-5 py-3 text-sm last:border-b-0 sm:grid-cols-[8.5rem_1fr]">
      <time dateTime={entry.created_at} className="tabular text-muted">
        {formatDateTime(entry.created_at)}
      </time>
      <div className="min-w-0">
        <p>
          <span className={cn("font-medium", alert && "text-danger")}>{auditLabel(entry.action)}</span>
          <span className="text-muted"> · {entry.actor_email ?? "система"}</span>
        </p>
        <p className="truncate text-xs text-muted">
          {entry.target_type && (
            <span className="font-mono">
              {entry.target_type}:{entry.target_id?.slice(0, 8)}
            </span>
          )}
          {details && <span> · {details}</span>}
        </p>
      </div>
    </div>
  );
}
