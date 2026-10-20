// Плашка о cookie на главной: выбор хранится в браузере и больше не спрашивается.
// Cookie у сайта только обязательные (сессия и защита от подделки запросов) и ставятся при
// входе, поэтому выбор пока ничего не отключает. Появится аналитика — грузить её при "all".
import { motion } from "motion/react";
import { useState } from "react";
import star from "../../assets/fsp-star.svg";
import { Button } from "../../ui/Button";

type Choice = "all" | "necessary" | "declined";

const KEY = "itmatch.cookie-consent";

// хранилище бывает недоступно (приватный режим, запрет в настройках) — тогда спросим снова
function saved(): string | null {
  try {
    return localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function CookieBanner() {
  const [open, setOpen] = useState(() => saved() === null);
  if (!open) return null;

  const choose = (choice: Choice) => {
    try {
      localStorage.setItem(KEY, choice);
    } catch {
      // не сохранилось — плашка просто скроется до следующего визита
    }
    setOpen(false);
  };

  return (
    <motion.section
      aria-label="Cookie"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className="fixed inset-x-3 bottom-3 z-50 rounded-2xl border border-line bg-surface p-5 shadow-2xl shadow-black/50 sm:inset-x-auto sm:bottom-6 sm:left-6 sm:max-w-lg"
    >
      <div className="flex items-start gap-3">
        <img src={star} alt="" aria-hidden className="size-8 shrink-0" />
        <div>
          <h2 className="font-semibold">Cookie на сайте</h2>
          <p className="mt-1.5 text-sm leading-relaxed text-muted">
            Обязательные cookie ставятся только при входе в аккаунт: они хранят сессию и защищают от подделки
            запросов. Аналитических и рекламных cookie у нас нет.
          </p>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <Button size="sm" onClick={() => choose("all")}>
          Принять все
        </Button>
        <Button size="sm" variant="secondary" onClick={() => choose("necessary")}>
          Только обязательные
        </Button>
        <Button size="sm" variant="ghost" onClick={() => choose("declined")}>
          Отказаться
        </Button>
      </div>
    </motion.section>
  );
}
