import { AlertCircle, Info } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "../lib/cn";

export function Alert({ tone = "danger", children }: { tone?: "danger" | "warn" | "info"; children: ReactNode }) {
  const Icon = tone === "info" ? Info : AlertCircle;
  return (
    <div
      role={tone === "danger" ? "alert" : "status"}
      className={cn(
        "flex gap-3 rounded-xl border px-4 py-3 text-sm",
        tone === "danger" && "border-danger/40 bg-danger/10 text-danger",
        tone === "warn" && "border-warn/40 bg-warn/10 text-warn",
        tone === "info" && "border-info/40 bg-info/10 text-info",
      )}
    >
      <Icon className="mt-0.5 size-4 shrink-0" aria-hidden />
      <div>{children}</div>
    </div>
  );
}
