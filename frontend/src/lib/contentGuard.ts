// Защита текста теста и задач: копирование, контекстное меню и перетаскивание внутри блока
// запрещены, сочетания клавиш снимка экрана считаются нарушением.
//
// ponytail: браузер видит только сочетания клавиш (PrintScreen, Win+Shift+S, Cmd+Shift+3/4/5);
// снимок системной утилитой, телефоном или второй камерой страница не заметит. Это сдерживание,
// а не гарантия: устойчивость к утечке держится на банке параметрических заданий (docs/assessment.md).
import { useEffect, useRef } from "react";

/** Сочетание клавиш снимка экрана: Windows, macOS и утилита «Ножницы». */
export function isScreenshotKey(e: Pick<KeyboardEvent, "key" | "metaKey" | "shiftKey">): boolean {
  if (e.key === "PrintScreen") return true;
  // Cmd/Win + Shift + 3/4/5/S; с Shift цифры могут прийти символами раскладки (#, $, %)
  return e.metaKey && e.shiftKey && ["3", "4", "5", "s", "#", "$", "%"].includes(e.key.toLowerCase());
}

const BLOCKED_EVENTS = ["copy", "cut", "contextmenu", "dragstart"] as const;

/**
 * Возвращает ref защищаемого блока. onScreenshot вызывается один раз за время жизни блока
 * (keydown и keyup одного нажатия не дают двойного нарушения).
 */
export function useContentGuard<T extends HTMLElement>(onScreenshot: () => void, enabled = true) {
  const ref = useRef<T>(null);
  const handler = useRef(onScreenshot);
  handler.current = onScreenshot;

  useEffect(() => {
    if (!enabled) return;
    let reported = false;
    const block = (e: Event) => {
      if (ref.current && e.target instanceof Node && ref.current.contains(e.target)) e.preventDefault();
    };
    const onKey = (e: KeyboardEvent) => {
      if (reported || !isScreenshotKey(e)) return;
      reported = true;
      handler.current();
    };
    for (const name of BLOCKED_EVENTS) document.addEventListener(name, block);
    window.addEventListener("keydown", onKey);
    window.addEventListener("keyup", onKey);
    return () => {
      for (const name of BLOCKED_EVENTS) document.removeEventListener(name, block);
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("keyup", onKey);
    };
  }, [enabled]);

  return ref;
}
