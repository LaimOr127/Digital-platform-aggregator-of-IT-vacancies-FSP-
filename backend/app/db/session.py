"""Один движок и фабрика сессий на процесс. Репозитории получают сессию через DI.

RLS: в session.info["rls"] кладётся (user_id, role); в начале КАЖДОЙ транзакции
значения передаются в PostgreSQL через set_config(..., is_local=true) и видны политикам RLS.
"""

import uuid
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import Connection, event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings

RLS_KEY = "rls"
SYSTEM_ROLE = "system"


def _engine_kwargs(url: str) -> dict:
    if url.startswith("sqlite"):
        # тесты: одна in-memory БД на движок
        return {"poolclass": StaticPool, "connect_args": {"check_same_thread": False}}
    return {"pool_pre_ping": True, "pool_size": 5}


_SET_RLS_SQL = text(
    "SELECT set_config('app.user_id', :uid, true), set_config('app.role', :role, true)"
)


def _rls_params(ctx: tuple[uuid.UUID | None, str]) -> dict[str, str]:
    user_id, role = ctx
    return {"uid": str(user_id or ""), "role": role}


def _is_postgres(session: Session) -> bool:
    return session.bind is not None and session.bind.dialect.name == "postgresql"


@event.listens_for(Session, "after_begin")
def _apply_rls_context(session: Session, _transaction: object, connection: Connection) -> None:
    ctx = session.info.get(RLS_KEY)
    if ctx is not None and _is_postgres(session):
        connection.execute(_SET_RLS_SQL, _rls_params(ctx))


async def set_rls_context(session: AsyncSession, user_id: uuid.UUID | None, role: str) -> None:
    """Задать контекст RLS: сразу для текущей транзакции и для всех следующих транзакций сессии."""
    session.sync_session.info[RLS_KEY] = (user_id, role)
    if _is_postgres(session.sync_session):
        await session.execute(_SET_RLS_SQL, _rls_params((user_id, role)))


class Database:
    def __init__(self, url: str) -> None:
        # hide_parameters: значения (email, шифртексты) не попадают в тексты ошибок и логи
        self.engine: AsyncEngine = create_async_engine(
            url, hide_parameters=True, **_engine_kwargs(url)
        )
        self.sessionmaker = async_sessionmaker(self.engine, expire_on_commit=False)

    async def ping(self) -> bool:
        try:
            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    async def dispose(self) -> None:
        await self.engine.dispose()


_db: Database | None = None


def get_database() -> Database:
    global _db
    if _db is None:
        _db = Database(get_settings().database_url)
    return _db


async def get_session(
    db: Annotated[Database, Depends(get_database)],
) -> AsyncIterator[AsyncSession]:
    async with db.sessionmaker() as session:
        yield session
