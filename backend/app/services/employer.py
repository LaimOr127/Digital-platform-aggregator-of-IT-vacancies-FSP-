"""Кабинет работодателя: своя компания и вакансии своей компании (тенант = company_id).

Чужая вакансия для репозитория не существует: ответ 404, а не 403, — id не подтверждается.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, ForbiddenError, NotFoundError
from app.models import EmployerCompany, Vacancy
from app.models.enums import VacancyStatus
from app.repositories.base import Page
from app.repositories.candidates import SkillRepository
from app.repositories.companies import CompanyRepository
from app.repositories.vacancies import VacancyRepository
from app.schemas.employer import VacancyCreateIn, VacancyUpdateIn
from app.services.access import Action, Principal, policy
from app.services.common import apply_fields, apply_salary, resolve_skills

VACANCY_TTL = timedelta(days=14)
_PLAIN_FIELDS = ("title", "description", "grade", "work_format", "city")


class InvalidStateError(AppError):
    status_code, code = 409, "invalid_state"


class EmployerService:
    def __init__(self, session: AsyncSession, principal: Principal) -> None:
        policy.ensure(principal, Action.COMPANY_READ_OWN)
        if principal.company_id is None:  # правило выше это исключает; явная проверка для типов
            raise ForbiddenError("no company")
        self.session = session
        self.principal = principal
        self.company_id: uuid.UUID = principal.company_id
        self.vacancies = VacancyRepository(session, company_id=self.company_id)
        self.skills = SkillRepository(session)

    async def company(self) -> EmployerCompany:
        return await CompanyRepository(self.session).get_or_404(self.company_id)

    async def list_vacancies(
        self, status: VacancyStatus | None, cursor: str | None, limit: int
    ) -> Page[Vacancy]:
        policy.ensure(self.principal, Action.VACANCY_READ)
        conditions = [Vacancy.status == status] if status else []
        return await self.vacancies.list_page(*conditions, cursor=cursor, limit=limit)

    async def get_vacancy(self, vacancy_id: uuid.UUID) -> Vacancy:
        vacancy = await self.vacancies.get_or_404(vacancy_id)
        policy.ensure(self.principal, Action.VACANCY_READ, vacancy)
        return vacancy

    async def create_vacancy(self, data: VacancyCreateIn) -> Vacancy:
        policy.ensure(self.principal, Action.VACANCY_WRITE)
        vacancy = Vacancy(
            company_id=self.company_id,
            created_by=self.principal.user_id,
            **data.model_dump(exclude={"skills"}),
        )
        vacancy.skills = await resolve_skills(self.skills, data.skills or [])
        await self.vacancies.add(vacancy)
        await self.session.commit()
        return vacancy

    async def update_vacancy(self, vacancy_id: uuid.UUID, data: VacancyUpdateIn) -> Vacancy:
        vacancy = await self._writable(vacancy_id)
        changes = data.model_dump(exclude_unset=True)
        apply_fields(vacancy, changes, _PLAIN_FIELDS)
        apply_salary(vacancy, changes)
        if data.skills is not None:
            vacancy.skills = await resolve_skills(self.skills, data.skills)
        await self.session.commit()
        return vacancy

    async def publish_vacancy(self, vacancy_id: uuid.UUID) -> Vacancy:
        """Публикация (и продление ещё на 14 дней) — только для одобренной компании."""
        vacancy = await self._writable(vacancy_id)
        policy.ensure(self.principal, Action.VACANCY_PUBLISH, vacancy)
        vacancy.status = VacancyStatus.ACTIVE
        vacancy.expires_at = datetime.now(UTC) + VACANCY_TTL
        await self.session.commit()
        return vacancy

    async def close_vacancy(self, vacancy_id: uuid.UUID) -> Vacancy:
        vacancy = await self._writable(vacancy_id)
        vacancy.status = VacancyStatus.CLOSED
        await self.session.commit()
        return vacancy

    async def delete_vacancy(self, vacancy_id: uuid.UUID) -> None:
        vacancy = await self._writable(vacancy_id)
        await self.vacancies.delete(vacancy)
        await self.session.commit()

    async def _writable(self, vacancy_id: uuid.UUID) -> Vacancy:
        vacancy = await self.vacancies.get(vacancy_id)
        if vacancy is None:
            raise NotFoundError("vacancy not found")
        policy.ensure(self.principal, Action.VACANCY_WRITE, vacancy)
        if vacancy.status == VacancyStatus.BLOCKED:
            raise InvalidStateError("вакансия заблокирована модератором")
        return vacancy
