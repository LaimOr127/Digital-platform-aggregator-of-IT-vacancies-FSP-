"""OpenAI-совместимый Chat Completions API: OpenAI, YandexGPT/GigaChat через совместимый шлюз,
локальные Ollama, vLLM, LM Studio. Ответ — JSON-объект; схема передаётся в инструкции."""

import json
from typing import Any

import httpx

from app.integrations.ai.base import AiClient, extract_json


class OpenAiCompatibleClient(AiClient):
    async def _request(
        self, http: httpx.AsyncClient, system: str, user: str, schema: dict[str, Any]
    ) -> dict[str, Any]:
        instruction = (
            f"{system}\n\nОтветь одним JSON-объектом строго по этой JSON-схеме, без пояснений:\n"
            f"{json.dumps(schema, ensure_ascii=False)}"
        )
        body: dict[str, Any] = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": instruction},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        url = f"{self.base_url}/chat/completions"
        response = await http.post(url, json=body, headers=headers)
        if response.status_code == httpx.codes.BAD_REQUEST:
            # не все совместимые серверы знают response_format — повтор без него
            body.pop("response_format")
            response = await http.post(url, json=body, headers=headers)
        response.raise_for_status()
        return extract_json(response.json()["choices"][0]["message"]["content"])
