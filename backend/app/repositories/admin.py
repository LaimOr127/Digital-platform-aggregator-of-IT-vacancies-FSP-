"""Репозитории модерации: без фильтра владельца — доступ даёт AccessPolicy (роль admin),
вторая линия — RLS (роль admin привилегирована в политиках)."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, EmployerCompany, User, Vacancy
from app.repositories.base import BaseRepository


class AllVacanciesRepository(BaseRepository[Vacancy]):
    model = Vacancy


class AllUsersRepository(BaseRepository[User]):
    model = User

    async def emails(self, ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
        if not ids:
            return {}
        rows = await self.session.execute(select(User.id, User.email).where(User.id.in_(ids)))
        return dict(rows.all())  # type: ignore[arg-type]


class AuditLogRepository(BaseRepository[AuditLog]):
    model = AuditLog


async def company_names(session: AsyncSession, ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    if not ids:
        return {}
    rows = await session.execute(
        select(EmployerCompany.id, EmployerCompany.name).where(EmployerCompany.id.in_(ids))
    )
    return dict(rows.all())


def like_pattern(query: str) -> str:
    """Подстрока для ILIKE: спецсимволы шаблона экранируются (поиск, а не шаблон)."""
    escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"
