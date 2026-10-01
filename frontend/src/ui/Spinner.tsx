import { cn } from "../lib/cn";

export function Spinner({ className }: { className?: string }) {
  return (
    <span
      role="status"
      aria-label="Загрузка"
      className={cn("inline-block size-4 animate-spin rounded-full border-2 border-current border-r-transparent", className)}
    />
  );
}

export function FullScreenSpinner() {
  return (
    <div className="grid min-h-dvh place-items-center text-muted">
      <Spinner className="size-6" />
    </div>
  );
}

export function LoadingBlock() {
  return (
    <div className="flex justify-center py-16 text-muted">
      <Spinner className="size-6" />
    </div>
  );
}
