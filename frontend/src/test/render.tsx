// Общая обвязка компонентных тестов: запросы, уведомления, роутер; fetch — подменённый.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router";
import { vi } from "vitest";
import { ToastProvider } from "../ui/Toast";

export const json = (body: unknown, status = 200) =>
  new Response(status === 204 ? null : JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

/** fetch по таблице «окончание пути -> ответ»; возвращает мок для проверки запросов. */
export function serveRoutes(routes: Record<string, (init?: RequestInit) => Response>) {
  const mock = vi.fn(async (url: string, init?: RequestInit) => {
    const path = Object.keys(routes).find((p) => String(url).split("?")[0].endsWith(p));
    return path ? routes[path](init) : json({ error: { code: "not_found", message: "нет" } }, 404);
  });
  vi.stubGlobal("fetch", mock);
  return mock;
}

/** Тело последнего запроса с телом по этому пути (GET того же адреса пропускается). */
export function bodyOf(mock: ReturnType<typeof vi.fn>, path: string) {
  const calls = mock.mock.calls.filter(([url, init]) => String(url).split("?")[0].endsWith(path) && init?.body);
  return JSON.parse(String(calls.at(-1)?.[1]?.body ?? "null"));
}

export function renderWithApp(element: ReactElement, path = "/") {
  // без повторов: ошибочный ответ сразу виден в интерфейсе, тест не ждёт паузы между попытками
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <MemoryRouter initialEntries={[path]}>{element}</MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  );
}
