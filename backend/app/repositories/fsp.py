"""Данные ФСП и категории. Всё, что принадлежит кандидату, фильтруется по profile_id."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Select, delete, insert, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category, FspAchievement, FspLink, FspVerification, candidate_categories
from app.repositories.base import BaseRepository


class _ProfileScoped[ModelT](BaseRepository[ModelT]):  # type: ignore[type-var]
    def __init__(self, session: AsyncSession, profile_id: uuid.UUID) -> None:
        super().__init__(session)
        self.profile_id = profile_id

    def _scope(self, stmt: Select[Any]) -> Select[Any]:
        return stmt.where(self.model.profile_id == self.profile_id)  # type: ignore[attr-defined]

    async def own(self) -> ModelT | None:
        return await self.first()

    async def delete_own(self) -> None:
        await self.session.execute(
            delete(self.model).where(self.model.profile_id == self.profile_id)  # type: ignore[attr-defined]
        )


class FspVerificationRepository(_ProfileScoped[FspVerification]):
    model = FspVerification


class FspLinkRepository(_ProfileScoped[FspLink]):
    model = FspLink


class FspAchievementRepository(_ProfileScoped[FspAchievement]):
    model = FspAchievement

    async def all(self) -> list[FspAchievement]:
        stmt = self._select().order_by(FspAchievement.date.desc(), FspAchievement.external_id)
        return list((await self.session.execute(stmt)).scalars())


async def links_due(session: AsyncSession, before: datetime, limit: int) -> list[FspLink]:
    """Привязки, которые пора синхронизировать (worker, контекст system)."""
    stmt = (
        select(FspLink)
        .where(or_(FspLink.last_synced_at.is_(None), FspLink.last_synced_at < before))
        .order_by(FspLink.last_synced_at.nulls_first())
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars())


class CategoryRepository(BaseRepository[Category]):
    model = Category

    async def ensure(self, slug: str, discipline: str, tier: str, title: str) -> Category:
        existing = await self.first(Category.slug == slug)
        if existing is not None:
            return existing
        return await self.add(Category(slug=slug, discipline=discipline, tier=tier, title=title))

    async def replace_for_profile(
        self, profile_id: uuid.UUID, assigned: list[tuple[Category, list[str]]]
    ) -> None:
        await self.session.execute(
            delete(candidate_categories).where(candidate_categories.c.profile_id == profile_id)
        )
        if assigned:
            await self.session.execute(
                insert(candidate_categories),
                [
                    {"profile_id": profile_id, "category_id": c.id, "reasons": reasons}
                    for c, reasons in assigned
                ],
            )

    async def for_profile(self, profile_id: uuid.UUID) -> list[tuple[Category, list[str]]]:
        stmt = (
            select(Category, candidate_categories.c.reasons)
            .join(candidate_categories, candidate_categories.c.category_id == Category.id)
            .where(candidate_categories.c.profile_id == profile_id)
            .order_by(Category.slug)
        )
        return [(row[0], list(row[1] or [])) for row in (await self.session.execute(stmt)).all()]
