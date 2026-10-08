// Шаблоны подключения: заполняют вид API, адрес и пример модели (название модели — уточните
// у провайдера). Любой сервис с OpenAI-совместимым API подключается как «Другой».
import type { AiProviderKind } from "../../../api/types";

export type Preset = { id: string; label: string; kind: AiProviderKind; base_url: string; model: string; hint?: string };

export const PRESETS: Preset[] = [
  // российская модель первой: организаторы ждут её из-за передачи персональных данных
  {
    id: "yandex",
    label: "YandexGPT — рекомендуется (данные остаются в России)",
    kind: "openai",
    base_url: "https://llm.api.cloud.yandex.net/v1",
    model: "gpt://<folder_id>/yandexgpt/latest",
    hint: "В модели замените <folder_id> на ID каталога Yandex Cloud (b1g…); ключ — API-ключ сервисного аккаунта с ролью ai.languageModels.user",
  },
  { id: "openai", label: "OpenAI", kind: "openai", base_url: "https://api.openai.com/v1", model: "gpt-4o-mini" },
  { id: "anthropic", label: "Anthropic Claude", kind: "anthropic", base_url: "https://api.anthropic.com", model: "claude-sonnet-5-5" },
  { id: "deepseek", label: "DeepSeek", kind: "openai", base_url: "https://api.deepseek.com/v1", model: "deepseek-chat" },
  { id: "openrouter", label: "OpenRouter", kind: "openai", base_url: "https://openrouter.ai/api/v1", model: "openai/gpt-4o-mini" },
  {
    id: "ollama",
    label: "Ollama (локально)",
    kind: "openai",
    base_url: "http://host.docker.internal:11434/v1",
    model: "llama3.1",
    hint: "Данные не покидают ваш сервер; ключ не нужен",
  },
  { id: "custom", label: "Другой (OpenAI-совместимый API)", kind: "openai", base_url: "https://", model: "" },
];
