"""Собеседования: тенант-компания и тенант-кандидат; просрочка без ответа — как у офферов."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, Select, and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Interview
from app.models.enums import InterviewStatus
from app.repositories.base import BaseRepository

_INVITED = InterviewStatus.INVITED


class CompanyInterviewRepository(BaseRepository[Interview]):
    model = Interview

    def __init__(self, session: AsyncSession, company_id: uuid.UUID) -> None:
        super().__init__(session)
        self.company_id = company_id

    def _scope(self, stmt: Select[Any]) -> Select[Any]:
        return stmt.where(Interview.company_id == self.company_id)

    async def declined_since(self, profile_id: uuid.UUID, since: datetime) -> Interview | None:
        """Последний отказ кандидата после since: пауза перед новым приглашением."""
        stmt = (
            self._select()
            .where(
                Interview.profile_id == profile_id,
                Interview.status == InterviewStatus.DECLINED,
                Interview.responded_at >= since,
            )
            .order_by(Interview.responded_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()


class CandidateInterviewRepository(BaseRepository[Interview]):
    model = Interview

    def __init__(self, session: AsyncSession, profile_id: uuid.UUID) -> None:
        super().__init__(session)
        self.profile_id = profile_id

    def _scope(self, stmt: Select[Any]) -> Select[Any]:
        return stmt.where(Interview.profile_id == self.profile_id)


def status_condition(status: InterviewStatus, now: datetime) -> ColumnElement[bool]:
    """Статус глазами пользователя: просроченное приглашение — уже «истекло»."""
    overdue = and_(Interview.status == _INVITED, Interview.expires_at <= now)
    if status == _INVITED:
        return and_(Interview.status == _INVITED, Interview.expires_at > now)
    if status == InterviewStatus.EXPIRED:
        return or_(Interview.status == InterviewStatus.EXPIRED, overdue)
    return Interview.status == status


async def expire_overdue(session: AsyncSession, now: datetime) -> int:
    """Приглашения без ответа после срока -> expired (worker, контекст system)."""
    result = await session.execute(
        update(Interview)
        .where(Interview.status == _INVITED, Interview.expires_at < now)
        .values(status=InterviewStatus.EXPIRED)
    )
    return result.rowcount  # type: ignore[attr-defined]


async def expire_pair(
    session: AsyncSession, vacancy_id: uuid.UUID, profile_id: uuid.UUID, now: datetime
) -> None:
    """Просроченное приглашение этой пары освобождает место для нового, не дожидаясь worker."""
    await session.execute(
        update(Interview)
        .where(
            Interview.vacancy_id == vacancy_id,
            Interview.profile_id == profile_id,
            Interview.status == _INVITED,
            Interview.expires_at <= now,
        )
        .values(status=InterviewStatus.EXPIRED)
    )
