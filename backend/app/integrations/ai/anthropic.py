"""Anthropic Messages API: ответ через вызов инструмента со схемой — строго структурирован."""

from typing import Any

import httpx

from app.integrations.ai.base import AiClient

_API_VERSION = "2023-06-01"
_MAX_TOKENS = 1500
_TOOL = "respond"


class AnthropicClient(AiClient):
    async def _request(
        self, http: httpx.AsyncClient, system: str, user: str, schema: dict[str, Any]
    ) -> dict[str, Any]:
        body = {
            "model": self.model,
            "max_tokens": _MAX_TOKENS,
            "system": system,
            "tools": [{"name": _TOOL, "description": "Ответ по схеме", "input_schema": schema}],
            "tool_choice": {"type": "tool", "name": _TOOL},
            "messages": [{"role": "user", "content": user}],
        }
        headers = {"x-api-key": self.api_key, "anthropic-version": _API_VERSION}
        response = await http.post(f"{self.base_url}/v1/messages", json=body, headers=headers)
        response.raise_for_status()
        for block in response.json()["content"]:
            if block.get("type") == "tool_use" and block.get("name") == _TOOL:
                return block["input"]
        raise ValueError("нет вызова инструмента в ответе")
