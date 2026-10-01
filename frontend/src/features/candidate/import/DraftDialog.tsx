import { ArrowRight } from "lucide-react";
import { useState } from "react";
import type { ProfileDraft } from "../../../api/types";
import { Button } from "../../../ui/Button";
import { Dialog } from "../../../ui/Dialog";
import type { ProfileFormInput } from "../schemas";
import { fieldChanges, newSkills, type FieldChange } from "./draft";

type Props = {
  draft: ProfileDraft;
  form: ProfileFormInput;
  skillNames: Map<string, string>;
  onApply: (changes: FieldChange[], skills: string[]) => void;
  onClose: () => void;
};

const SOURCE = { fsp: "Данные из анкеты ФСП", resume: "Данные из резюме" } as const;

/** Проверка черновика: какие поля перенести в форму. Сохраняет профиль сам кандидат. */
export function DraftDialog({ draft, form, skillNames, onApply, onClose }: Props) {
  const changes = fieldChanges(draft, form);
  const skills = newSkills(draft, form);
  const [selected, setSelected] = useState(() => new Set(changes.filter((c) => c.preselected).map((c) => c.field)));
  const [withSkills, setWithSkills] = useState(true);
  const toggle = (field: FieldChange["field"]) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(field)) next.delete(field);
      else next.add(field);
      return next;
    });
  const nothing = changes.length === 0 && skills.length === 0;

  return (
    <Dialog open title={SOURCE[draft.source]} onClose={onClose} wide>
      {draft.notes.length > 0 && (
        <ul className="mb-4 flex flex-col gap-1 text-xs text-muted">
          {draft.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      )}
      {nothing && <p className="text-sm text-muted">Новых данных нет — профиль уже содержит всё найденное.</p>}
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
                <span className="mt-1 flex flex-wrap items-center gap-2 text-muted">
                  {change.current && <span className="line-through">{preview(change.current)}</span>}
                  {change.current && <ArrowRight className="size-3.5" aria-hidden />}
                  <span className="whitespace-pre-line break-words text-fg">{preview(change.suggested)}</span>
                </span>
              </span>
            </label>
          </li>
        ))}
        {skills.length > 0 && (
          <li>
            <label className="flex cursor-pointer items-start gap-3 py-3 text-sm">
              <input type="checkbox" className="mt-1 accent-accent" checked={withSkills} onChange={(e) => setWithSkills(e.target.checked)} />
              <span>
                <span className="font-medium">Добавить навыки</span>
                <span className="mt-1 block text-fg">{skills.map((s) => skillNames.get(s) ?? s).join(", ")}</span>
              </span>
            </label>
          </li>
        )}
      </ul>
      {draft.unknown_skills.length > 0 && (
        <p className="mt-3 text-xs text-muted">
          Нет в справочнике (не добавлены): {draft.unknown_skills.join(", ")}
        </p>
      )}
      <div className="mt-6 flex justify-end gap-3">
        <Button variant="ghost" onClick={onClose}>
          Отмена
        </Button>
        <Button
          disabled={nothing}
          onClick={() => onApply(changes.filter((c) => selected.has(c.field)), withSkills ? skills : [])}
        >
          Перенести в профиль
        </Button>
      </div>
    </Dialog>
  );
}

function preview(text: string): string {
  return text.length > 240 ? `${text.slice(0, 240)}…` : text;
}
