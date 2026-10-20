import type { HTMLAttributes } from "react";
import { cn } from "../lib/cn";

export function Card({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("rounded-2xl border border-line bg-surface p-6", className)} {...rest} />;
}

/** Заголовок раздела — как в брендбуке ФСП: JetBrains Mono, прописными, с разрядкой. */
export function CardTitle({ className, ...rest }: HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h2
      className={cn("flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.08em] text-fg", className)}
      {...rest}
    />
  );
}
