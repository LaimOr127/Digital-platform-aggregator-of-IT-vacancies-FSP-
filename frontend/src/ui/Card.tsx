import type { HTMLAttributes } from "react";
import { cn } from "../lib/cn";

export function Card({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("rounded-2xl border border-line bg-surface p-6", className)} {...rest} />;
}

/** Заголовок раздела — плашка со скруглением, как на слайдах шаблона ФСП. */
export function CardTitle({ className, ...rest }: HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h2
      className={cn(
        "inline-flex w-fit items-center gap-2 rounded-full bg-pill px-3.5 py-1 text-sm font-semibold tracking-tight text-on-pill",
        className,
      )}
      {...rest}
    />
  );
}
