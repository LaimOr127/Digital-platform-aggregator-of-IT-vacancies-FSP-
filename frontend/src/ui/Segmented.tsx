import { useRef, type KeyboardEvent } from "react";
import { cn } from "../lib/cn";

type Option<T extends string> = { value: T; label: string };

const STEP: Record<string, number> = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 };

/** Переключатель (ARIA radiogroup): одна остановка Tab, выбор стрелками, Home/End. */
export function Segmented<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: Option<T>[];
  onChange: (value: T) => void;
}) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const selected = options.findIndex((o) => o.value === value);
  // без выбранного значения ничего не отмечено, а Tab попадает на первый вариант
  const current = Math.max(0, selected);

  const select = (index: number) => {
    const next = (index + options.length) % options.length;
    onChange(options[next].value);
    refs.current[next]?.focus();
  };

  const onKeyDown = (e: KeyboardEvent) => {
    if (e.key in STEP) select(current + STEP[e.key]);
    else if (e.key === "Home") select(0);
    else if (e.key === "End") select(options.length - 1);
    else return;
    e.preventDefault();
  };

  return (
    <div
      role="radiogroup"
      aria-label={label}
      onKeyDown={onKeyDown}
      className="inline-flex flex-wrap gap-1 rounded-xl border border-line bg-surface p-1"
    >
      {options.map((o, i) => (
        <button
          key={o.value}
          ref={(el) => {
            refs.current[i] = el;
          }}
          type="button"
          role="radio"
          aria-checked={i === selected}
          tabIndex={i === current ? 0 : -1}
          onClick={() => onChange(o.value)}
          className={cn(
            "rounded-lg px-3 py-1.5 text-sm transition-colors",
            i === selected ? "bg-surface-2 text-fg shadow-sm" : "text-muted hover:text-fg",
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
