import type { ReactNode } from "react";

export function EmptyState({ icon, title, text, action }: { icon: ReactNode; title: string; text: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-line px-6 py-14 text-center">
      <span className="grid size-12 place-items-center rounded-full bg-surface-2 text-muted">{icon}</span>
      <h3 className="font-semibold">{title}</h3>
      <p className="max-w-sm text-sm text-muted">{text}</p>
      {action}
    </div>
  );
}
