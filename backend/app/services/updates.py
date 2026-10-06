"""Индикаторы нового в кабинетах: когда в разделе последний раз что-то происходило.

Сервер отдаёт только время последнего события раздела; что пользователь уже видел, помнит
браузер (точка гаснет, когда раздел открыт). ponytail: отметка «просмотрено» — на устройство,
а не на аккаунт; если понадобится синхронизация между устройствами, хранить её в БД.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ForbiddenError
from app.core.timeutil import as_aware
from app.models import Application, Interview, Offer, TaskAnswer, Vacancy
from app.models.enums import ApplicationDirection, VacancyStatus
from app.repositories.candidates import CandidateProfileRepository
from app.schemas.updates import CandidateUpdatesOut, EmployerUpdatesOut
from app.services.access import Action, Principal, policy
from app.services.employer import VACANCY_TTL

RENEW_SOON = timedelta(days=3)  # вакансию пора продлить, если до снятия осталось меньше


def _latest(column: Any, *conditions: Any) -> Any:
    return select(func.max(column)).where(*conditions).scalar_subquery()


def _aware(value: datetime | None) -> datetime | None:
    return as_aware(value) if value else None


class CandidateUpdatesService:
    def __init__(self, session: AsyncSession, principal: Principal) -> None:
        policy.ensure(principal, Action.PROFILE_MANAGE_OWN)
        self.session = session
        self.profiles = CandidateProfileRepository(session, principal.user_id)

    async def get(self) -> CandidateUpdatesOut:
        profile_id = (await self.profiles.own_or_404()).id
        own = Application.profile_id == profile_id
        row = (
            await self.session.execute(
                select(
                    # публикация и продление сдвигают срок жизни: срок минус TTL — момент публикации
                    _latest(Vacancy.expires_at, Vacancy.status == VacancyStatus.ACTIVE),
                    _latest(
                        Application.updated_at,
                        own,
                        Application.direction == ApplicationDirection.INVITATION,
                    ),
                    _latest(
                        Application.updated_at,
                        own,
                        Application.direction == ApplicationDirection.RESPONSE,
                    ),
                    _latest(Interview.updated_at, Interview.profile_id == profile_id),
                    _latest(Offer.updated_at, Offer.profile_id == profile_id),
                )
            )
        ).one()
        published = _aware(row[0])
        return CandidateUpdatesOut(
            vacancies=published - VACANCY_TTL if published else None,
            invitations=_aware(row[1]),
            responses=_aware(row[2]),
            interviews=_aware(row[3]),
            offers=_aware(row[4]),
        )


class EmployerUpdatesService:
    def __init__(self, session: AsyncSession, principal: Principal) -> None:
        policy.ensure(principal, Action.COMPANY_READ_OWN)
        if principal.company_id is None:  # исключено правилом выше; явная проверка для типов
            raise ForbiddenError("no company")
        self.session = session
        self.company_id = principal.company_id

    async def get(self) -> EmployerUpdatesOut:
        company = self.company_id
        soon = datetime.now(UTC) + RENEW_SOON
        row = (
            await self.session.execute(
                select(
                    select(func.count())
                    .select_from(Vacancy)
                    .where(
                        Vacancy.company_id == company,
                        Vacancy.status == VacancyStatus.ACTIVE,
                        Vacancy.expires_at <= soon,
                    )
                    .scalar_subquery(),
                    _latest(Application.updated_at, Application.company_id == company),
                    _latest(
                        TaskAnswer.created_at,
                        TaskAnswer.company_id == company,
                        TaskAnswer.blocked.is_(False),
                    ),
                    _latest(Interview.updated_at, Interview.company_id == company),
                    _latest(Offer.updated_at, Offer.company_id == company),
                )
            )
        ).one()
        return EmployerUpdatesOut(
            renew_due=row[0],
            applications=_aware(row[1]),
            tasks=_aware(row[2]),
            interviews=_aware(row[3]),
            offers=_aware(row[4]),
        )
