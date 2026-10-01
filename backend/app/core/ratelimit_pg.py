"""Лимитер в PostgreSQL: общий для всех процессов и реплик api.

Счётчики — в нежурналируемой таблице rate_limit_buckets (быстро; при сбое БД обнуляются, что
для лимитов допустимо). Окно — скользящее по приближению «два ведра»: текущее окно плюс
доля предыдущего, пропорциональная непрошедшей части. Одна атомарная команда на проверку.
Старые вёдра удаляет worker.
"""

import hashlib
import time

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

_HIT = text(
    """
    WITH cur AS (
        INSERT INTO rate_limit_buckets (key, bucket, hits, expires_at)
        VALUES (:key, :bucket, 1, to_timestamp(:expires))
        ON CONFLICT (key, bucket) DO UPDATE SET hits = rate_limit_buckets.hits + 1
        RETURNING hits
    )
    SELECT (SELECT hits FROM cur),
           COALESCE((SELECT hits FROM rate_limit_buckets WHERE key = :key AND bucket = :prev), 0)
    """
)
_PURGE = text("DELETE FROM rate_limit_buckets WHERE expires_at < now()")


class PostgresRateLimiter:
    def __init__(self, engine: AsyncEngine, clock=time.time) -> None:
        self._engine = engine
        self._clock = clock

    async def hit(self, key: str, limit: int, window: int) -> bool:
        now = self._clock()
        bucket = int(now // window)
        elapsed = (now - bucket * window) / window  # доля текущего окна, 0..1
        params = {
            # в БД — хеш ключа: email и IP не хранятся открытым текстом
            "key": hashlib.sha256(key.encode()).hexdigest(),
            "bucket": bucket,
            "prev": bucket - 1,
            "expires": (bucket + 2) * window,
        }
        async with self._engine.begin() as conn:
            current, previous = (await conn.execute(_HIT, params)).one()
        return current + previous * (1 - elapsed) <= limit


async def purge_expired(engine: AsyncEngine) -> int:
    async with engine.begin() as conn:
        result = await conn.execute(_PURGE)
    return result.rowcount  # type: ignore[attr-defined]
