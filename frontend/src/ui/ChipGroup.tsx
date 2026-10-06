import { Check, Plus } from "lucide-react";
import { useId, useState } from "react";
import { cn } from "../lib/cn";

type Option = { value: string; label: string };

/** Набор чипов: несколько значений (флажки) или одно (single). Каждый чип — кнопка
 * с aria-pressed: состояние читают скринридеры, переключение — пробелом или Enter.
 * allowCustom: можно дописать своё значение, которого нет в списке. */
export function ChipGroup({
  options,
  value,
  onChange,
  single = false,
  max,
  allowCustom = false,
}: {
  options: Option[];
  value: string[];
  onChange: (value: string[]) => void;
  single?: boolean;
  max?: number;
  allowCustom?: boolean;
}) {
  const toggle = (option: string) => {
    if (single) return onChange([option]);
    if (value.includes(option)) return onChange(value.filter((v) => v !== option));
    if (max && value.length >= max) return;
    onChange([...value, option]);
  };
  // свои значения показываются чипами рядом со справочными
  const known = new Set(options.map((o) => o.value));
  const all = [...options, ...value.filter((v) => !known.has(v)).map((v) => ({ value: v, label: v }))];
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap gap-2">
        {all.map((o) => {
          const active = value.includes(o.value);
          return (
            <button
              key={o.value}
              type="button"
              aria-pressed={active}
              onClick={() => toggle(o.value)}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm transition-colors",
                active ? "border-accent bg-accent/15 text-fg" : "border-line text-muted hover:text-fg",
              )}
            >
              {active && <Check className="size-3.5 text-accent" aria-hidden />}
              {o.label}
            </button>
          );
        })}
      </div>
      {allowCustom && !single && (
        <CustomInput disabled={Boolean(max && value.length >= max)} onAdd={(text) => !value.includes(text) && toggle(text)} />
      )}
    </div>
  );
}

const CUSTOM_MAX = 40;

function CustomInput({ disabled, onAdd }: { disabled: boolean; onAdd: (text: string) => void }) {
  const [text, setText] = useState("");
  const id = useId();
  const add = () => {
    const value = text.trim();
    if (!value) return;
    onAdd(value);
    setText("");
  };
  return (
    <div className="flex gap-2">
      <label htmlFor={id} className="sr-only">
        Своё значение
      </label>
      <input
        id={id}
        value={text}
        maxLength={CUSTOM_MAX}
        disabled={disabled}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          // Enter добавляет значение и не отправляет форму
          if (e.key !== "Enter") return;
          e.preventDefault();
          add();
        }}
        placeholder="Своё — введите и нажмите Enter"
        className="h-9 min-w-0 flex-1 rounded-lg border border-line bg-surface-2 px-3 text-sm placeholder:text-muted/70 focus:border-accent focus:outline-none disabled:opacity-50"
      />
      <button
        type="button"
        onClick={add}
        disabled={disabled || !text.trim()}
        className="inline-flex items-center gap-1 rounded-lg border border-line px-3 text-sm text-muted hover:text-fg disabled:opacity-40"
      >
        <Plus className="size-3.5" aria-hidden />
        Добавить
      </button>
    </div>
  );
}
