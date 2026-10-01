"""Интерфейс языковой модели: запрос -> JSON по схеме. Реализации — по видам API."""

import json
import re
from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.integrations.ai.guard import UnsafeUrlError, ensure_public

TIMEOUT_SECONDS = 30.0


class AiUnavailableError(Exception):
    """Модель недоступна или ответила не по схеме — вызывающий использует запасной путь."""


class AiClient(ABC):
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.transport = transport  # тесты подменяют сеть
        self.allow_private = False  # частные сети — только явно (on-prem / локальная модель)

    async def complete_json(self, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
        try:
            await ensure_public(self.base_url, self.allow_private)
            async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS, transport=self.transport) as http:
                return await self._request(http, system, user, schema)
        except (
            UnsafeUrlError,
            httpx.HTTPError,
            ValueError,
            KeyError,
            TypeError,
            IndexError,
        ) as exc:
            raise AiUnavailableError(type(exc).__name__) from exc

    @abstractmethod
    async def _request(
        self, http: httpx.AsyncClient, system: str, user: str, schema: dict[str, Any]
    ) -> dict[str, Any]: ...


def extract_json(text: str) -> dict[str, Any]:
    """JSON из ответа модели: без обёрток ```json и пояснений вокруг."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end < start:
        raise ValueError("в ответе нет JSON")
    data = json.loads(text[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("ожидался объект JSON")
    return data
