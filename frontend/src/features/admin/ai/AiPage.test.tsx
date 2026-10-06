import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { AiProvider } from "../../../api/types";
import { bodyOf, json, renderWithApp, serveRoutes } from "../../../test/render";
import { AiPage } from "./AiPage";

const provider: AiProvider = {
  id: "p1",
  name: "YandexGPT",
  kind: "openai",
  base_url: "https://llm.api.cloud.yandex.net/v1",
  model: "yandexgpt",
  has_key: true,
  key_hint: "…abcd",
  is_active: false,
  created_at: "2026-10-01T00:00:00Z",
};

afterEach(() => vi.unstubAllGlobals());

describe("AI settings", () => {
  it("lists models, checks connection and activates one", async () => {
    const mock = serveRoutes({
      "/admin/ai-providers": () => json([provider]),
      "/admin/ai-providers/p1/test": () => json({ ok: false, latency_ms: 12, message: "Ошибка 401: неверный ключ" }),
      "/admin/ai-providers/p1/activate": () => json([{ ...provider, is_active: true }]),
    });
    renderWithApp(<AiPage />);
    expect(await screen.findByText("Ключ …abcd")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Проверить" }));
    expect(await screen.findByText("Ошибка 401: неверный ключ")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Сделать активной" }));
    expect(mock.mock.calls.some(([url]) => String(url).endsWith("/p1/activate"))).toBe(true);
  });

  it("connects a model from a preset", async () => {
    const mock = serveRoutes({
      "/admin/ai-providers": (init) => (init?.method === "POST" ? json(provider, 201) : json([])),
    });
    renderWithApp(<AiPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Подключить модель" }));
    await userEvent.selectOptions(screen.getByLabelText("Шаблон"), "ollama");
    expect(screen.getByText(/Данные не покидают ваш сервер/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Подключить" }));
    expect(bodyOf(mock, "/admin/ai-providers")).toEqual({
      name: "Ollama (локально)",
      kind: "openai",
      base_url: "http://host.docker.internal:11434/v1",
      model: "llama3.1",
      api_key: null,
    });
  });
});
