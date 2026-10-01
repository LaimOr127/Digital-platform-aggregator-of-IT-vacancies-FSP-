"""Ограничение частоты запросов. Интерфейс один, хранилище — на выбор (RATE_LIMIT_BACKEND):

- memory — скользящее окно в памяти процесса (тесты, один процесс);
- postgres — общее для всех процессов и реплик api (ratelimit_pg.py): лимиты, в том числе
  на коды 2FA и подбор пароля, не размножаются при масштабировании.
"""

import ipaddress
import time
from collections import defaultdict, deque
from collections.abc import Callable
from typing import Protocol

from fastapi import Request

from app.core.errors import RateLimitedError

_PERIODS = {"second": 1, "minute": 60, "hour": 3600, "day": 86_400}
_MAX_KEYS = 10_000


def parse_rate(rate: str) -> tuple[int, int]:
    """'10/minute' -> (10, 60)."""
    count, period = rate.split("/")
    return int(count), _PERIODS[period]


class Limiter(Protocol):
    async def hit(self, key: str, limit: int, window: int) -> bool:
        """True — запрос разрешён; False — лимит исчерпан."""
        ...


class RateLimiter:
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        # окно каждого ключа: очистка не сбрасывает часовые счётчики по минутному окну
        self._windows: dict[str, int] = {}
        self._clock = clock

    async def hit(self, key: str, limit: int, window: int) -> bool:
        """True — запрос разрешён; False — лимит исчерпан."""
        now = self._clock()
        if key not in self._hits and len(self._hits) >= _MAX_KEYS:
            self._evict(now)
        self._windows[key] = window
        hits = self._hits[key]
        while hits and hits[0] <= now - window:
            hits.popleft()
        if len(hits) >= limit:
            return False
        hits.append(now)
        return True

    def _evict(self, now: float) -> None:
        """Память ограничена: сначала удаляем ключи, чьё собственное окно истекло, затем —
        самые старые (половину), чтобы перебор IP не делал очистку на каждом запросе."""
        stale = [k for k, h in self._hits.items() if not h or h[-1] <= now - self._windows[k]]
        for key in stale:
            self._drop(key)
        if len(self._hits) >= _MAX_KEYS:
            by_age = sorted(self._hits, key=lambda k: self._hits[k][-1])
            for key in by_age[: len(by_age) // 2]:
                self._drop(key)

    def _drop(self, key: str) -> None:
        del self._hits[key]
        del self._windows[key]


def build_limits(rates: dict[str, str]) -> dict[str, tuple[int, int]]:
    """Разбор лимитов при старте: неверная настройка роняет запуск, а не каждый запрос."""
    return {scope: parse_rate(rate) for scope, rate in rates.items()}


def client_ip(request: Request) -> str:
    """IP клиента после --proxy-headers uvicorn (за Caddy). IPv6 — по сети /64:
    у одного клиента обычно вся подсеть, и смена адреса в ней не обходит лимит."""
    host = request.client.host if request.client else "unknown"
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return host
    if address.version == 6:
        return str(ipaddress.ip_network(f"{host}/64", strict=False))
    return host


async def check_rate_limit(request: Request, scope: str, key: str | None = None) -> None:
    """Лимит области scope для ключа (по умолчанию — IP клиента)."""
    limit, window = request.app.state.rate_limits[scope]
    limiter: Limiter = request.app.state.rate_limiter
    if not await limiter.hit(f"{scope}:{key or client_ip(request)}", limit, window):
        raise RateLimitedError("too many requests")
