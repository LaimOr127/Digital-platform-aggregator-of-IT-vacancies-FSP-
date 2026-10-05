import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EmployerCompany, Skill, Vacancy, vacancy_skills
from app.models.enums import CompanyStatus, Grade, Specialization, VacancyStatus, WorkFormat
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


@dataclass(frozen=True)
class BoardFilters:
    specialization: Specialization | None = None
    grade: Grade | None = None
    work_format: WorkFormat | None = None
    skill: str | None = None
    query: str | None = None  # поиск по названию


class PublishedVacancyRepository(BaseRepository[Vacancy]):
    """Опубликованные вакансии для кандидатов: активные, не истёкшие, компания одобрена.
    В PostgreSQL то же ограничение дублирует RLS (политика vacancy_read)."""

    model = Vacancy

    def _scope(self, stmt: Select[Any]) -> Select[Any]:
        approved = select(EmployerCompany.id).where(
            EmployerCompany.status == CompanyStatus.APPROVED
        )
        return stmt.where(
            Vacancy.status == VacancyStatus.ACTIVE,
            or_(Vacancy.expires_at.is_(None), Vacancy.expires_at > datetime.now(UTC)),
            Vacancy.company_id.in_(approved),
        )

    async def search(self, filters: BoardFilters, limit: int) -> list[Vacancy]:
        stmt = self._select().where(*_board_conditions(filters))
        stmt = stmt.order_by(Vacancy.created_at.desc(), Vacancy.id.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars())


def _board_conditions(filters: BoardFilters) -> list[Any]:
    conditions: list[Any] = []
    if filters.specialization:
        conditions.append(Vacancy.specialization == filters.specialization)
    if filters.grade:
        conditions.append(Vacancy.grade == filters.grade)
    if filters.work_format:
        conditions.append(Vacancy.work_format == filters.work_format)
    if filters.query:
        conditions.append(func.lower(Vacancy.title).contains(filters.query.lower()))
    if filters.skill:
        with_skill = (
            select(vacancy_skills.c.vacancy_id)
            .join(Skill, Skill.id == vacancy_skills.c.skill_id)
            .where(Skill.slug == filters.skill)
        )
        conditions.append(Vacancy.id.in_(with_skill))
    return conditions
