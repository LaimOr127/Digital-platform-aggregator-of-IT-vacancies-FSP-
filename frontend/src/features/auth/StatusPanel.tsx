import { CircleAlert, CircleCheck } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router";
import { cn } from "../../lib/cn";
import { buttonClasses } from "../../ui/Button";

type Props = { ok: boolean; title: string; children: ReactNode; action?: { to: string; label: string } };

/** Итог операции по ссылке из письма: успех или понятная причина отказа и следующий шаг. */
export function StatusPanel({ ok, title, children, action }: Props) {
  const Icon = ok ? CircleCheck : CircleAlert;
  return (
    <div className="flex flex-col gap-5">
      <div
        role={ok ? "status" : "alert"}
        className={cn(
          "flex items-start gap-3 rounded-xl border p-4 text-sm",
          ok ? "border-accent/30 bg-accent/5" : "border-danger/30 bg-danger/5",
        )}
      >
        <Icon className={cn("mt-0.5 size-5 shrink-0", ok ? "text-accent" : "text-danger")} aria-hidden />
        <div>
          <p className="font-medium">{title}</p>
          <div className="mt-1 text-muted">{children}</div>
        </div>
      </div>
      {action && (
        <Link to={action.to} className={buttonClasses("primary", "lg")}>
          {action.label}
        </Link>
      )}
    </div>
  );
}
