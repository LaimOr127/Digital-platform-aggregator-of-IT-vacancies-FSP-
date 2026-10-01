"""Каталог кандидатов для работодателя: только видимые профили — не скрытые и не «не ищу».
Вторая линия — RLS: профили видит только одобренная компания."""

import uuid
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Select, func, select

from app.models import (
    CandidateProfile,
    Category,
    FspAchievement,
    Skill,
    candidate_categories,
    profile_skills,
)
from app.models.enums import Grade, SearchStatus, WorkFormat
from app.repositories.base import BaseRepository, Page


@dataclass(frozen=True)
class CatalogFilters:
    category: str | None = None
    grade: Grade | None = None
    work_format: WorkFormat | None = None
    skill: str | None = None
    search_status: SearchStatus | None = None


# кандидат скрыл профиль или не ищет работу — его нет в каталоге и ему нельзя отправить оффер
VISIBLE = (
    CandidateProfile.is_hidden.is_(False),
    CandidateProfile.search_status != SearchStatus.CLOSED,
)


class CatalogRepository(BaseRepository[CandidateProfile]):
    model = CandidateProfile

    def _scope(self, stmt: Select[Any]) -> Select[Any]:
        return stmt.where(*VISIBLE)

    async def by_ids(self, ids: list[uuid.UUID]) -> list[CandidateProfile]:
        if not ids:
            return []
        return list(
            (
                await self.session.execute(self._select().where(CandidateProfile.id.in_(ids)))
            ).scalars()
        )

    async def by_anon_id(self, anon_id: uuid.UUID) -> CandidateProfile | None:
        return await self.first(CandidateProfile.anon_id == anon_id)

    async def search(
        self, filters: CatalogFilters, cursor: str | None, limit: int
    ) -> Page[CandidateProfile]:
        conditions = []
        category, grade, work_format, skill = (
            filters.category,
            filters.grade,
            filters.work_format,
            filters.skill,
        )
        if filters.search_status:
            conditions.append(CandidateProfile.search_status == filters.search_status)
        if category:
            in_category = (
                select(candidate_categories.c.profile_id)
                .join(Category, Category.id == candidate_categories.c.category_id)
                .where(Category.slug == category)
            )
            conditions.append(CandidateProfile.id.in_(in_category))
        if grade:
            conditions.append(CandidateProfile.grade == grade)
        if work_format:
            conditions.append(CandidateProfile.work_format == work_format)
        if skill:
            with_skill = (
                select(profile_skills.c.profile_id)
                .join(Skill, Skill.id == profile_skills.c.skill_id)
                .where(Skill.slug == skill)
            )
            conditions.append(CandidateProfile.id.in_(with_skill))
        return await self.list_page(*conditions, cursor=cursor, limit=limit)

    async def category_counts(self) -> dict[str, int]:
        stmt = (
            select(Category.slug, func.count(candidate_categories.c.profile_id))
            .join(candidate_categories, candidate_categories.c.category_id == Category.id)
            .join(CandidateProfile, CandidateProfile.id == candidate_categories.c.profile_id)
            .where(*VISIBLE)
            .group_by(Category.slug)
        )
        return {slug: count for slug, count in (await self.session.execute(stmt)).all()}

    async def categories_for(self, profile_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[Category]]:
        stmt = (
            select(candidate_categories.c.profile_id, Category)
            .join(Category, Category.id == candidate_categories.c.category_id)
            .where(candidate_categories.c.profile_id.in_(profile_ids))
            .order_by(Category.slug)
        )
        result: dict[uuid.UUID, list[Category]] = defaultdict(list)
        for profile_id, category in (await self.session.execute(stmt)).all():
            result[profile_id].append(category)
        return result

    async def achievements_for(
        self, profile_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, list[FspAchievement]]:
        stmt = (
            select(FspAchievement)
            .where(FspAchievement.profile_id.in_(profile_ids))
            .order_by(FspAchievement.date.desc())
        )
        result: dict[uuid.UUID, list[FspAchievement]] = defaultdict(list)
        for achievement in (await self.session.execute(stmt)).scalars():
            result[achievement.profile_id].append(achievement)
        return result
