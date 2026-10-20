import { ArrowRight, Lock } from "lucide-react";
import { useState } from "react";
import type { Profile, ProfileDraft } from "../../../api/types";
import { useDictionaries } from "../../../api/queries";
import { formatDate, labels } from "../../../lib/format";
import { Button } from "../../../ui/Button";
import { Dialog } from "../../../ui/Dialog";
import type { ProfileFormInput } from "../schemas";
import { CLAIMED_FIELDS, fieldChanges, newLists, type DraftLists, type FieldChange } from "./draft";

type Props = {
  draft: ProfileDraft;
  form: ProfileFormInput;
  profile: Profile;
  skillNames: Map<string, string>;
  onApply: (changes: FieldChange[], lists: DraftLists) => void;
  onClose: () => void;
};

type ListKey = "skills" | "roles" | "soft_skills";

const SOURCE = { fsp: "Данные из анкеты ФСП", resume: "Данные из резюме" } as const;

/** Проверка черновика: какие поля перенести в форму. По умолчанию отмечено всё; сохраняет кандидат.
 * Категорию и подтверждённый грейд перенос не меняет: грейд и специализация — заявленные значения. */
export function DraftDialog({ draft, form, profile, skillNames, onApply, onClose }: Props) {
  const all = fieldChanges(draft, form);
  const confirmed = profile.confirmed_grade !== null && profile.confirmed_grade !== undefined;
  // категория подтверждена тестом — грейд и специализация из черновика её не меняют
  const locked = confirmed ? all.filter((c) => CLAIMED_FIELDS.includes(c.field)) : [];
  const changes = all.filter((c) => !locked.includes(c));
  const lists = newLists(draft, form);
  const dictionaries = useDictionaries().data;
  const names = new Map([...(dictionaries?.roles ?? []), ...(dictionaries?.soft_skills ?? [])].map((o) => [o.value, o.label]));
  const listRows: { key: ListKey; label: string; items: string[] }[] = [
    {
      key: "skills",
      label: "Стек",
      items: [...lists.skills.map((s) => skillNames.get(s) ?? s), ...lists.custom_skills],
    },
    { key: "roles", label: "Роли", items: lists.roles.map((r) => names.get(r) ?? r) },
    { key: "soft_skills", label: "Софт-скиллы", items: lists.soft_skills.map((s) => names.get(s) ?? s) },
  ];
  const [selected, setSelected] = useState(() => new Set<string>([...changes.map((c) => c.field), ...listRows.map((r) => r.key)]));
  const toggle = (key: string) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  const shownLists = listRows.filter((r) => r.items.length > 0);
  const nothing = changes.length === 0 && shownLists.length === 0;
  const categoryTitle =
    confirmed && profile.specialization && profile.confirmed_grade
      ? `${labels.specialization[profile.specialization]}, ${labels.grade[profile.confirmed_grade]}`
      : "";

  return (
    <Dialog open title={SOURCE[draft.source]} onClose={onClose} wide>
      <p className="mb-3 rounded-lg bg-surface-2 px-3 py-2 text-sm">
        Категорию и грейд определяет тест. Данные из {draft.source === "fsp" ? "анкеты" : "резюме"} их не меняют.
      </p>
      {draft.notes.length > 0 && (
        <ul className="mb-4 flex flex-col gap-1 text-xs text-muted">
          {draft.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      )}
      {nothing && locked.length === 0 && <p className="text-sm text-muted">Новых данных нет — профиль уже содержит всё найденное.</p>}
      <ul className="flex flex-col divide-y divide-line">
        {changes.map((change) => (
          <li key={change.field}>
            <label className="flex cursor-pointer items-start gap-3 py-3 text-sm">
              <input
                type="checkbox"
                className="mt-1 accent-accent"
                checked={selected.has(change.field)}
                onChange={() => toggle(change.field)}
              />
              <span className="min-w-0 flex-1">
                <span className="font-medium">{change.label}</span>
                {CLAIMED_FIELDS.includes(change.field) && (
                  <span className="block text-xs text-muted">Заявленное значение. Подтверждает его только тест</span>
                )}
                <Values change={change} />
              </span>
            </label>
          </li>
        ))}
        {locked.map((change) => (
          <li key={change.field} className="flex items-start gap-3 py-3 text-sm">
            <Lock className="mt-0.5 size-4 shrink-0 text-muted" aria-hidden />
            <span className="min-w-0 flex-1">
              <span className="font-medium">{change.label}</span>
              <span className="mt-1 block text-muted">
                Категория «{categoryTitle}» подтверждена тестом и из {draft.source === "fsp" ? "анкеты" : "резюме"} не
                меняется.
                {profile.category_change_at && ` Сменить можно через опрос с ${formatDate(profile.category_change_at)}.`}
              </span>
            </span>
          </li>
        ))}
        {shownLists.map((row) => (
          <li key={row.key}>
            <label className="flex cursor-pointer items-start gap-3 py-3 text-sm">
              <input type="checkbox" className="mt-1 accent-accent" checked={selected.has(row.key)} onChange={() => toggle(row.key)} />
              <span>
                <span className="font-medium">{row.label}</span>
                <span className="mt-1 block text-fg">{row.items.join(", ")}</span>
              </span>
            </label>
          </li>
        ))}
      </ul>
      {lists.custom_skills.length > 0 && (
        <p className="mt-3 text-xs text-muted">Нет в справочнике — добавятся как свои навыки: {lists.custom_skills.join(", ")}</p>
      )}
      <div className="mt-6 flex justify-end gap-3">
        <Button variant="ghost" onClick={onClose}>
          Отмена
        </Button>
        <Button
          disabled={nothing}
          onClick={() =>
            onApply(changes.filter((c) => selected.has(c.field)), {
              skills: selected.has("skills") ? lists.skills : [],
              custom_skills: selected.has("skills") ? lists.custom_skills : [],
              roles: selected.has("roles") ? lists.roles : [],
              soft_skills: selected.has("soft_skills") ? lists.soft_skills : [],
            })
          }
        >
          Перенести в профиль
        </Button>
      </div>
    </Dialog>
  );
}

function Values({ change }: { change: FieldChange }) {
  return (
    <span className="mt-1 flex flex-wrap items-center gap-2 text-muted">
      {change.current && <span className="line-through">{preview(change.current)}</span>}
      {change.current && <ArrowRight className="size-3.5" aria-hidden />}
      <span className="whitespace-pre-line break-words text-fg">{preview(change.suggested)}</span>
    </span>
  );
}

function preview(text: string): string {
  return text.length > 240 ? `${text.slice(0, 240)}…` : text;
}
