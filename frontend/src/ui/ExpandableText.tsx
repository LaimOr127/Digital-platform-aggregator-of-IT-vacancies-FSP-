// Длинный текст: первые строки и «Показать полностью» — чтобы описание можно было дочитать.
import { useState } from "react";
import { cn } from "../lib/cn";

/** Тексты короче этого показываются целиком, без кнопки. */
const CLAMP_FROM = 220;

type Props = { text: string; className?: string; label?: string };

export function ExpandableText({ text, className, label }: Props) {
  const [open, setOpen] = useState(false);
  const long = text.length > CLAMP_FROM;
  return (
    <div className={className}>
      <p className={cn("whitespace-pre-line", long && !open && "line-clamp-3")}>
        {label && <span className="text-muted">{label}: </span>}
        {text}
      </p>
      {long && (
        <button
          type="button"
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
          className="mt-1 text-sm font-medium underline underline-offset-2 hover:no-underline"
        >
          {open ? "Свернуть" : "Показать полностью"}
        </button>
      )}
    </div>
  );
}
