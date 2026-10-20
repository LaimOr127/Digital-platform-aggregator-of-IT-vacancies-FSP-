// Сдерживание утечки заданий теста и задач: копирование, контекстное меню и перетаскивание внутри
// блока запрещены, PrintScreen считается нарушением, задания скрываются, когда окно неактивно, а
// поверх них — водяной знак с идентификатором кандидата (утечку можно отследить).
//
// Это сдерживание, а не блокировка: системные снимки macOS (Cmd+Shift+3/4/5), сторонние программы
// и фото экрана телефоном страница заметить не может. Основная защита — у каждого кандидата свой
// вариант заданий (docs/assessment.md).
import { useEffect, useRef, useState } from "react";

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

/**
 * Окно потеряло фокус или вкладка скрыта: задания нужно спрятать. Уходы считаются и уходят в
 * результат как сигнал — без автоматического провала (случайное переключение не наказывается).
 */
export function useFocusGuard(enabled = true) {
  const [hidden, setHidden] = useState(false);
  const [leaves, setLeaves] = useState(0);
  useEffect(() => {
    if (!enabled) return;
    let away = false;
    const leave = () => {
      if (away) return; // blur и visibilitychange одного ухода — один раз
      away = true;
      setHidden(true);
      setLeaves((n) => n + 1);
    };
    const back = () => {
      if (document.visibilityState !== "visible") return;
      away = false;
      setHidden(false);
    };
    const onVisibility = () => (document.visibilityState === "hidden" ? leave() : back());
    window.addEventListener("blur", leave);
    window.addEventListener("focus", back);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      window.removeEventListener("blur", leave);
      window.removeEventListener("focus", back);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [enabled]);
  return { hidden, leaves };
}
