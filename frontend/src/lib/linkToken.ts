// Токен из ссылки в письме: передаётся во фрагменте (#token=...), который браузер не отправляет
// на сервер, — он не попадает в логи прокси и заголовок Referer.

/** Токен из адреса страницы (без изменения адреса — безопасно для повторных рендеров). */
export function readLinkToken(hash: string = window.location.hash): string | null {
  const token = new URLSearchParams(hash.replace(/^#/, "")).get("token");
  return token && /^[\w-]{20,128}$/.test(token) ? token : null;
}

/** Убрать токен из адреса и истории браузера, когда он прочитан. */
export function forgetLinkToken(): void {
  if (window.location.hash) window.history.replaceState(null, "", window.location.pathname);
}
