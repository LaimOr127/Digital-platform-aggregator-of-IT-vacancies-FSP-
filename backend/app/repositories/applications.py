"""Приглашения и отклики: тенант-компания и тенант-кандидат (чужие записи не существуют)."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, Select, and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Application
from app.models.enums import ApplicationDirection, ApplicationStatus
from app.repositories.base import BaseRepository

OPEN = (ApplicationStatus.SENT, ApplicationStatus.VIEWED)


class _ScopedRepository(BaseRepository[Application]):
    """Тенант задаёт колонка-владелец: компания или профиль кандидата."""

    model = Application
    column: Any  # атрибут модели: читается через класс, иначе сработает как дескриптор ORM

    def __init__(self, session: AsyncSession, owner_id: uuid.UUID) -> None:
        super().__init__(session)
        self.owner_id = owner_id

    def _scope(self, stmt: Select[Any]) -> Select[Any]:
        return stmt.where(type(self).column == self.owner_id)

    async def mark_viewed(
        self, direction: ApplicationDirection, ids: list[uuid.UUID], now: datetime
    ) -> None:
        """Адресат открыл список: отправленные ему записи становятся «просмотрено»."""
        if not ids:
            return
        await self.session.execute(
            update(Application)
            .where(
                type(self).column == self.owner_id,
                Application.id.in_(ids),
                Application.direction == direction,
                Application.status == ApplicationStatus.SENT,
                Application.expires_at > now,
            )
            .values(status=ApplicationStatus.VIEWED, viewed_at=now)
            # без синхронизации в памяти: записи перечитываются после commit
            .execution_options(synchronize_session=False)
        )


class CompanyApplicationRepository(_ScopedRepository):
    column = Application.company_id

    async def declined_invitation_since(
        self, profile_id: uuid.UUID, since: datetime
    ) -> Application | None:
        """Последний отказ кандидата от приглашения этой компании (пауза перед новым)."""
        stmt = (
            self._select()
            .where(
                Application.profile_id == profile_id,
                Application.direction == ApplicationDirection.INVITATION,
                Application.status == ApplicationStatus.DECLINED,
                Application.responded_at >= since,
            )
            .order_by(Application.responded_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()


class CandidateApplicationRepository(_ScopedRepository):
    column = Application.profile_id

    async def by_vacancies(self, vacancy_ids: list[uuid.UUID]) -> dict[uuid.UUID, Application]:
        """Последний отклик или приглашение по каждой вакансии (для отметки в списке вакансий)."""
        if not vacancy_ids:
            return {}
        stmt = (
            self._select()
            .where(Application.vacancy_id.in_(vacancy_ids))
            .order_by(Application.created_at)
        )
        return {
            a.vacancy_id: a for a in (await self.session.execute(stmt)).scalars() if a.vacancy_id
        }


async def expire_pair(
    session: AsyncSession, company_id: uuid.UUID, profile_id: uuid.UUID, now: datetime
) -> None:
    """Просроченное открытое обращение пары освобождает место для нового, не дожидаясь worker."""
    await session.execute(
        update(Application)
        .where(
            Application.company_id == company_id,
            Application.profile_id == profile_id,
            Application.status.in_(OPEN),
            Application.expires_at <= now,
        )
        .values(status=ApplicationStatus.EXPIRED)
        .execution_options(synchronize_session=False)
    )


async def expire_overdue(session: AsyncSession, now: datetime) -> int:
    """Без ответа дольше срока -> «истёк» (worker, контекст system)."""
    result = await session.execute(
        update(Application)
        .where(Application.status.in_(OPEN), Application.expires_at < now)
        .values(status=ApplicationStatus.EXPIRED)
    )
    return result.rowcount  # type: ignore[attr-defined]


def status_condition(status: ApplicationStatus, now: datetime) -> ColumnElement[bool]:
    """Статус так, как его видит пользователь: просроченное открытое — уже «истёк»."""
    is_open = Application.status.in_(OPEN)
    if status in OPEN:
        return and_(Application.status == status, Application.expires_at > now)
    if status == ApplicationStatus.EXPIRED:
        return or_(
            Application.status == ApplicationStatus.EXPIRED,
            and_(is_open, Application.expires_at <= now),
        )
    return Application.status == status
