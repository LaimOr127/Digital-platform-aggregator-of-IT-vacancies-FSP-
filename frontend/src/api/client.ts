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

let refreshing: Promise<boolean> | null = null;

/** Новый access-токен по refresh-cookie. Параллельные вызовы делят один запрос. */
export function refreshSession(): Promise<boolean> {
  refreshing ??= doRefresh().finally(() => {
    refreshing = null;
  });
  return refreshing;
}

async function doRefresh(): Promise<boolean> {
  const csrf = readCookie("csrf_token");
  if (!csrf) return false;
  try {
    const res = await fetch(`${BASE}/auth/refresh`, {
      method: "POST",
      credentials: "same-origin",
      headers: { "X-CSRF-Token": csrf },
    });
    if (!res.ok) return false;
    session.set((await res.json()).access_token);
    return true;
  } catch {
    return false;
  }
}

export async function api<T = unknown>(method: Method, path: string, options: Options = {}): Promise<T> {
  const url = buildUrl(path, options.query);
  const token = session.get();
  let res = await send(method, url, options.body, token);
  if (res.status === 401 && token) {
    if (await refreshSession()) {
      res = await send(method, url, options.body, session.get());
    } else {
      session.clear();
    }
  }
  if (!res.ok) throw await toApiError(res);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

/** Выход: CSRF-заголовок обязателен, cookie очищает сервер. */
export async function logoutRequest(): Promise<void> {
  const csrf = readCookie("csrf_token") ?? "";
  await fetch(`${BASE}/auth/logout`, {
    method: "POST",
    credentials: "same-origin",
    headers: { "X-CSRF-Token": csrf },
  }).catch(() => undefined);
  session.clear();
}

export { ApiError };
