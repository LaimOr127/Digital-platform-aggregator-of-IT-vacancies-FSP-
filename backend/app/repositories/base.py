"""BaseRepository[T]: CRUD, курсорная пагинация и фильтр владельца/тенанта — один раз.

Наследник задаёт model и при необходимости _scope(): любой запрос репозитория проходит через
_scope, поэтому чтение/изменение чужих строк невозможно даже при известном id (защита от IDOR).
"""

import base64
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import Select, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, NotFoundError
from app.models.base import Base

MAX_PAGE = 100


class InvalidCursorError(AppError):
    code = "invalid_cursor"


@dataclass(frozen=True)
class Page[T]:
    items: list[T]
    next_cursor: str | None


def encode_cursor(created_at: datetime, row_id: uuid.UUID) -> str:
    raw = f"{created_at.isoformat()}|{row_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        created, row_id = base64.urlsafe_b64decode(cursor.encode()).decode().split("|")
        return datetime.fromisoformat(created), uuid.UUID(row_id)
    except (ValueError, UnicodeDecodeError) as exc:
        raise InvalidCursorError("invalid cursor") from exc


class BaseRepository[ModelT: Base]:
    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _scope(self, stmt: Select[Any]) -> Select[Any]:
        """Фильтр владельца/тенанта. По умолчанию — без ограничений (справочники)."""
        return stmt

    def _select(self) -> Select[Any]:
        return self._scope(select(self.model))

    async def get(self, row_id: uuid.UUID) -> ModelT | None:
        stmt = self._select().where(self.model.id == row_id)  # type: ignore[attr-defined]
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def lock_or_404(self, row_id: uuid.UUID) -> ModelT:
        """Строка с блокировкой до конца транзакции (SELECT ... FOR UPDATE): параллельные
        изменения одной записи выполняются по очереди, а не «последний перезаписал»."""
        stmt = self._select().where(self.model.id == row_id).with_for_update()  # type: ignore[attr-defined]
        obj = (await self.session.execute(stmt)).scalar_one_or_none()
        if obj is None:
            raise NotFoundError(f"{self.model.__tablename__} not found")
        return obj

    async def get_or_404(self, row_id: uuid.UUID) -> ModelT:
        obj = await self.get(row_id)
        if obj is None:
            raise NotFoundError(f"{self.model.__tablename__} not found")
        return obj

    async def first(self, *conditions: Any) -> ModelT | None:
        stmt = self._select().where(*conditions).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_page(
        self, *conditions: Any, cursor: str | None = None, limit: int = 20
    ) -> Page[ModelT]:
        """Новые сверху; курсор = (created_at, id) последнего элемента страницы."""
        created, row_id = self.model.created_at, self.model.id  # type: ignore[attr-defined]
        stmt = self._select().where(*conditions)
        if cursor:
            c_created, c_id = decode_cursor(cursor)
            stmt = stmt.where(or_(created < c_created, and_(created == c_created, row_id < c_id)))
        limit = max(1, min(limit, MAX_PAGE))
        stmt = stmt.order_by(created.desc(), row_id.desc()).limit(limit + 1)
        rows = list((await self.session.execute(stmt)).scalars())
        has_more = len(rows) > limit
        rows = rows[:limit]
        next_cursor = (
            encode_cursor(rows[-1].created_at, rows[-1].id) if has_more and rows else None  # type: ignore[attr-defined]
        )
        return Page(items=rows, next_cursor=next_cursor)

    async def add(self, obj: ModelT) -> ModelT:
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def delete(self, obj: ModelT) -> None:
        await self.session.delete(obj)
        await self.session.flush()
