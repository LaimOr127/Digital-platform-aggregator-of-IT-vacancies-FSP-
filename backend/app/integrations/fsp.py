"""Интеграция с API ФСП. Сервисы зависят от протокола FspClient: мок и реальный API
подменяются реализацией, а тесты — фейком через DI."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.core.config import Settings
from app.core.errors import AppError, NotFoundError, RateLimitedError, ServiceUnavailableError


class FspVerificationError(AppError):
    code = "fsp_verification_failed"


@dataclass(frozen=True)
class FspAthlete:
    id: str
    full_name: str
    region: str | None
    rank: str | None


@dataclass(frozen=True)
class FspResult:
    external_id: str
    discipline: str
    competition_title: str
    level: str
    date: str
    place: int | None
    stage: str
    role: str
    team: str | None


@dataclass(frozen=True)
class FspVerificationStart:
    request_id: str
    email_masked: str
    expires_in: int
    demo_code: str | None = None


class FspClient(Protocol):
    async def get_athlete(self, athlete_id: str) -> FspAthlete: ...
    async def get_results(self, athlete_id: str) -> list[FspResult]: ...
    async def start_verification(self, athlete_id: str) -> FspVerificationStart: ...
    async def confirm_verification(self, request_id: str, code: str) -> str: ...


class HttpFspClient:
    """Клиент HTTP API ФСП (сейчас — мок fsp-mock с тем же контрактом)."""

    def __init__(
        self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self._http = httpx.AsyncClient(
            base_url=f"{settings.fsp_base_url.rstrip('/')}/api/v1",
            headers={"X-Api-Key": settings.secret("fsp_api_key")},
            timeout=settings.fsp_timeout_seconds,
            transport=transport,
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _request(self, method: str, path: str, json: dict | None = None) -> httpx.Response:
        try:
            response = await self._http.request(method, path, json=json)
        except httpx.HTTPError as exc:
            raise ServiceUnavailableError("ФСП временно недоступна") from exc
        if response.status_code == 404:
            raise NotFoundError("спортсмен ФСП не найден")
        if response.status_code == 429:
            raise RateLimitedError("слишком много попыток, запросите новый код")
        if response.status_code == 400:
            raise FspVerificationError("неверный или просроченный код")
        if response.status_code >= 300:
            raise ServiceUnavailableError("ФСП временно недоступна")
        return response

    async def get_athlete(self, athlete_id: str) -> FspAthlete:
        data = await self._json("GET", f"/athletes/{_safe_id(athlete_id)}")
        return _parse(
            lambda: FspAthlete(
                str(data["id"]), str(data["full_name"]), data.get("region"), data.get("rank")
            )
        )

    async def get_results(self, athlete_id: str) -> list[FspResult]:
        rows = await self._json("GET", f"/athletes/{_safe_id(athlete_id)}/results")
        return _parse(lambda: [_result(row) for row in rows])

    async def start_verification(self, athlete_id: str) -> FspVerificationStart:
        data = await self._json("POST", "/verification/start", {"athlete_id": athlete_id})
        return _parse(
            lambda: FspVerificationStart(
                str(data["request_id"]),
                str(data["email_masked"]),
                int(data["expires_in"]),
                data.get("demo_code"),
            )
        )

    async def confirm_verification(self, request_id: str, code: str) -> str:
        data = await self._json(
            "POST", "/verification/confirm", {"request_id": request_id, "code": code}
        )
        return _parse(lambda: str(data["athlete_id"]))

    async def _json(self, method: str, path: str, body: dict | None = None) -> Any:
        response = await self._request(method, path, body)
        return _parse(response.json)


def _parse[T](build: Callable[[], T]) -> T:
    """Неожиданный ответ ФСП (не JSON, другой контракт) — «ФСП недоступна», а не 500."""
    try:
        return build()
    except (ValueError, KeyError, TypeError) as exc:
        raise ServiceUnavailableError("ФСП вернула неожиданный ответ") from exc


def _safe_id(athlete_id: str) -> str:
    """ID ФСП в пути URL: только буквы, цифры и дефис (без обхода пути)."""
    if not athlete_id.replace("-", "").isalnum():
        raise NotFoundError("спортсмен ФСП не найден")
    return athlete_id


def _result(row: dict) -> FspResult:
    competition = row["competition"]
    return FspResult(
        external_id=row["id"],
        discipline=competition["discipline"],
        competition_title=competition["title"],
        level=competition["level"],
        date=competition["date"],
        place=row.get("place"),
        stage=row.get("stage", "final"),
        role=row.get("role", "member"),
        team=row.get("team"),
    )
