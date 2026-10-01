"""Ограничение частоты запросов (скользящее окно в памяти процесса).

Хранилище живёт в app.state: у каждого экземпляра приложения (и теста) своё.
Для нескольких реплик api заменяется реализацией на PostgreSQL с тем же интерфейсом.
"""

import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import Request

from app.core.errors import RateLimitedError

_PERIODS = {"second": 1, "minute": 60, "hour": 3600, "day": 86_400}
_MAX_KEYS = 10_000


def parse_rate(rate: str) -> tuple[int, int]:
    """'10/minute' -> (10, 60)."""
    count, period = rate.split("/")
    return int(count), _PERIODS[period]


class RateLimiter:
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._clock = clock

    def hit(self, key: str, limit: int, window: int) -> bool:
        """True — запрос разрешён; False — лимит исчерпан."""
        now = self._clock()
        if key not in self._hits and len(self._hits) >= _MAX_KEYS:
            self._evict(now, window)
        hits = self._hits[key]
        while hits and hits[0] <= now - window:
            hits.popleft()
        if len(hits) >= limit:
            return False
        hits.append(now)
        return True

    def _evict(self, now: float, window: int) -> None:
        """Память ограничена: сначала удаляем ключи без свежих запросов, затем — самые старые
        (половину), чтобы перебор IP не делал очистку на каждом запросе."""
        stale = [k for k, h in self._hits.items() if not h or h[-1] <= now - window]
        for key in stale:
            del self._hits[key]
        if len(self._hits) >= _MAX_KEYS:
            by_age = sorted(self._hits, key=lambda k: self._hits[k][-1])
            for key in by_age[: len(by_age) // 2]:
                del self._hits[key]


def build_limits(rates: dict[str, str]) -> dict[str, tuple[int, int]]:
    """Разбор лимитов при старте: неверная настройка роняет запуск, а не каждый запрос."""
    return {scope: parse_rate(rate) for scope, rate in rates.items()}


def client_ip(request: Request) -> str:
    """IP клиента после --proxy-headers uvicorn (за Caddy)."""
    return request.client.host if request.client else "unknown"


def check_rate_limit(request: Request, scope: str, key: str | None = None) -> None:
    """Лимит области scope для ключа (по умолчанию — IP клиента)."""
    limit, window = request.app.state.rate_limits[scope]
    limiter: RateLimiter = request.app.state.rate_limiter
    if not limiter.hit(f"{scope}:{key or client_ip(request)}", limit, window):
        raise RateLimitedError("too many requests")
