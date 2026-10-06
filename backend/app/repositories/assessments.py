"""Попытки теста: тенант — профиль кандидата (чужие попытки для репозитория не существуют)."""

import uuid
from typing import Any

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Assessment
from app.models.enums import AssessmentStatus, Specialization
from app.repositories.base import BaseRepository


class AssessmentRepository(BaseRepository[Assessment]):
    model = Assessment

    def __init__(self, session: AsyncSession, profile_id: uuid.UUID) -> None:
        super().__init__(session)
        self.profile_id = profile_id

    def _scope(self, stmt: Select[Any]) -> Select[Any]:
        return stmt.where(Assessment.profile_id == self.profile_id)

    async def in_progress(self) -> list[Assessment]:
        stmt = self._select().where(Assessment.status == AssessmentStatus.IN_PROGRESS)
        return list((await self.session.execute(stmt)).scalars())

    async def history(self, limit: int = 20) -> list[Assessment]:
        stmt = (
            self._select()
            .where(Assessment.status != AssessmentStatus.IN_PROGRESS)
            .order_by(Assessment.created_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars())

    async def finished_for(self, specialization: Specialization) -> list[Assessment]:
        stmt = (
            self._select()
            .where(
                Assessment.specialization == specialization,
                Assessment.status == AssessmentStatus.COMPLETED,
            )
            .order_by(Assessment.finished_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars())
