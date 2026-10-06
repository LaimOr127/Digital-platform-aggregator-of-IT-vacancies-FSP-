// Уведомления: aria-live, автозакрытие. Показ — через useToast().
import { AnimatePresence, motion } from "motion/react";
import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { cn } from "../lib/cn";

type Toast = { id: number; text: string; tone: "success" | "error" };
type Notify = (text: string, tone?: Toast["tone"]) => void;

const ToastContext = createContext<Notify>(() => undefined);
const LIFETIME_MS = 4000;
let nextId = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const notify = useCallback<Notify>((text, tone = "success") => {
    const id = ++nextId;
    setToasts((list) => [...list, { id, text, tone }]);
    setTimeout(() => setToasts((list) => list.filter((t) => t.id !== id)), LIFETIME_MS);
  }, []);

  return (
    <ToastContext.Provider value={notify}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 bottom-4 z-50 flex flex-col items-center gap-2 px-4">
        {/* живые регионы существуют заранее: ошибки озвучиваются сразу, успехи — вежливо */}
        <ToastRegion toasts={toasts.filter((t) => t.tone === "error")} live="assertive" />
        <ToastRegion toasts={toasts.filter((t) => t.tone === "success")} live="polite" />
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => useContext(ToastContext);

function ToastRegion({ toasts, live }: { toasts: Toast[]; live: "assertive" | "polite" }) {
  return (
    <div aria-live={live} className="flex flex-col items-center gap-2">
      <AnimatePresence>
        {toasts.map((t) => (
          <motion.div
            key={t.id}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 12 }}
            className={cn(
              "rounded-xl border px-4 py-2.5 text-sm shadow-lg backdrop-blur",
              t.tone === "success" ? "border-accent/30 bg-surface-2/95 text-fg" : "border-danger/40 bg-surface-2/95 text-danger",
            )}
          >
            {t.text}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
