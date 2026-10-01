// HTTP-клиент API: токен из памяти, единый формат ошибок, автоматический refresh при 401.
import { ApiError, toApiError } from "./errors";
import { session } from "./session";

const BASE = "/api/v1";
type Method = "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
type Query = Record<string, string | number | boolean | null | undefined>;
type Options = { body?: unknown; query?: Query };

function readCookie(name: string): string | null {
  const match = document.cookie.split("; ").find((part) => part.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.slice(name.length + 1)) : null;
}

function buildUrl(path: string, query?: Query): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null && value !== "") params.append(key, String(value));
  }
  const qs = params.toString();
  return `${BASE}${path}${qs ? `?${qs}` : ""}`;
}

function send(method: Method, url: string, body: unknown, token: string | null) {
  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;
  return fetch(url, {
    method,
    headers,
    credentials: "same-origin",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

/** ok — новый токен получен; invalid — сессии нет (401/403, нет cookie); transient — сбой сети/сервера. */
export type RefreshResult = "ok" | "invalid" | "transient";

let refreshing: Promise<RefreshResult> | null = null;

/** Новый access-токен по refresh-cookie. Параллельные вызовы в вкладке делят один запрос,
 * между вкладками — блокировка Web Locks: refresh-токен одноразовый, два одновременных
 * запроса с ним сервер считает кражей и отзывает всю сессию. */
export function refreshSession(): Promise<RefreshResult> {
  refreshing ??= withCrossTabLock(doRefresh).finally(() => {
    refreshing = null;
  });
  return refreshing;
}

function withCrossTabLock<T>(fn: () => Promise<T>): Promise<T> {
  const locks = typeof navigator !== "undefined" ? navigator.locks : undefined;
  return locks ? (locks.request("itmatch-auth-refresh", fn) as Promise<T>) : fn();
}

async function doRefresh(): Promise<RefreshResult> {
  const csrf = readCookie("csrf_token");
  if (!csrf) return "invalid";
  try {
    const res = await fetch(`${BASE}/auth/refresh`, {
      method: "POST",
      credentials: "same-origin",
      headers: { "X-CSRF-Token": csrf },
    });
    if (res.status === 401 || res.status === 403) return "invalid";
    if (!res.ok) return "transient";
    session.set((await res.json()).access_token);
    return "ok";
  } catch {
    return "transient";
  }
}

const transientError = () => new ApiError(503, "session_refresh_failed", "Нет связи с сервером, попробуйте ещё раз");

export async function api<T = unknown>(method: Method, path: string, options: Options = {}): Promise<T> {
  const url = buildUrl(path, options.query);
  const token = session.get();
  let res = await send(method, url, options.body, token);
  if (res.status === 401 && token) {
    // токен уже обновил параллельный запрос — повторяем с ним, без лишней ротации
    const current = session.get();
    const outcome = current && current !== token ? "ok" : await refreshSession();
    if (outcome === "transient") throw transientError();
    if (outcome === "invalid") {
      session.clear();
    } else {
      res = await send(method, url, options.body, session.get());
    }
  }
  if (!res.ok) throw await toApiError(res);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

/** Выход на сервере (отзыв refresh-cookie). Без csrf-cookie серверной сессии уже нет.
 * Ошибка пробрасывается: нельзя делать вид, что вышли, если cookie остался живым. */
export async function logoutRequest(): Promise<void> {
  const csrf = readCookie("csrf_token");
  if (!csrf) return;
  const res = await fetch(`${BASE}/auth/logout`, {
    method: "POST",
    credentials: "same-origin",
    headers: { "X-CSRF-Token": csrf },
  });
  if (!res.ok) throw await toApiError(res);
}

/** sub (id пользователя) из access-токена — только для сравнения, без проверки подписи. */
export function tokenSubject(token: string | null): string | null {
  try {
    const payload = token?.split(".")[1];
    if (!payload) return null;
    const json = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
    return (JSON.parse(json) as { sub?: string }).sub ?? null;
  } catch {
    return null;
  }
}

export { ApiError };
