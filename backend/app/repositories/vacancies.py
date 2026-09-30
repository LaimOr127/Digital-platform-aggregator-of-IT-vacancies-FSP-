import uuid
from typing import Any

from sqlalchemy import Select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Vacancy
from app.models.enums import VacancyStatus
from app.repositories.base import BaseRepository


class VacancyRepository(BaseRepository[Vacancy]):
    """Тенант = компания: работодатель видит и меняет только вакансии своей компании."""

    model = Vacancy

    def __init__(self, session: AsyncSession, company_id: uuid.UUID) -> None:
        super().__init__(session)
        self.company_id = company_id

    def _scope(self, stmt: Select[Any]) -> Select[Any]:
        return stmt.where(Vacancy.company_id == self.company_id)

    async def block_open(self) -> int:
        """Заблокировать черновики и активные вакансии компании (при блокировке компании)."""
        result = await self.session.execute(
            update(Vacancy)
            .where(
                Vacancy.company_id == self.company_id,
                Vacancy.status.in_([VacancyStatus.DRAFT, VacancyStatus.ACTIVE]),
            )
            .values(status=VacancyStatus.BLOCKED)
        )
        return result.rowcount  # type: ignore[attr-defined]
