import { Check } from "lucide-react";
import { cn } from "../lib/cn";

type Option = { value: string; label: string };

/** Набор чипов: несколько значений (флажки) или одно (single). Каждый чип — кнопка
 * с aria-pressed: состояние читают скринридеры, переключение — пробелом или Enter. */
export function ChipGroup({
  options,
  value,
  onChange,
  single = false,
  max,
}: {
  options: Option[];
  value: string[];
  onChange: (value: string[]) => void;
  single?: boolean;
  max?: number;
}) {
  const toggle = (option: string) => {
    if (single) return onChange([option]);
    if (value.includes(option)) return onChange(value.filter((v) => v !== option));
    if (max && value.length >= max) return;
    onChange([...value, option]);
  };
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((o) => {
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
  );
}
