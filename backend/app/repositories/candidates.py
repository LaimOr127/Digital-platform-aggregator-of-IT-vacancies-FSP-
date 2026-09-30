import uuid
from typing import Any

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CandidateProfile, Skill
from app.repositories.base import BaseRepository


class CandidateProfileRepository(BaseRepository[CandidateProfile]):
    """Всегда ограничен одним владельцем: кандидат видит и меняет только свой профиль."""

    model = CandidateProfile

    def __init__(self, session: AsyncSession, owner_id: uuid.UUID) -> None:
        super().__init__(session)
        self.owner_id = owner_id

    def _scope(self, stmt: Select[Any]) -> Select[Any]:
        return stmt.where(CandidateProfile.user_id == self.owner_id)

    async def own(self) -> CandidateProfile | None:
        return await self.first()


class SkillRepository(BaseRepository[Skill]):
    model = Skill

    async def by_slugs(self, slugs: list[str]) -> list[Skill]:
        if not slugs:
            return []
        stmt = self._select().where(Skill.slug.in_(slugs))
        return list((await self.session.execute(stmt)).scalars())

    async def all(self) -> list[Skill]:
        stmt = self._select().order_by(Skill.name)
        return list((await self.session.execute(stmt)).scalars())
