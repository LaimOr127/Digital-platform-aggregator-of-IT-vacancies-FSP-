"""Каталог кандидатов для работодателя: только видимые профили — не скрытые и не «не ищу».
Вторая линия — RLS: профили видит только одобренная компания."""

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import Select, String, cast, func, or_, select

from app.models import (
    CandidateProfile,
    Category,
    FspAchievement,
    Skill,
    candidate_categories,
    profile_skills,
)
from app.models.enums import Grade, SearchStatus, Specialization, VerificationTier, WorkFormat
from app.repositories.base import BaseRepository


@dataclass(frozen=True)
class CatalogFilters:
    category: tuple[Specialization, Grade] | None = None  # категория: специализация x грейд
    specialization: Specialization | None = None
    grade: Grade | None = None  # подтверждённый тестом (если теста нет — заявленный)
    work_format: WorkFormat | None = None  # среди форматов, подходящих кандидату
    city: str | None = None  # живёт в городе или готов к переезду
    skills: tuple[str, ...] = ()  # все выбранные навыки
    search_status: SearchStatus | None = None
    confirmed_only: bool = False  # только с категорией, подтверждённой тестом
    fsp_only: bool = False  # только с подтверждёнными достижениями ФСП
    fsp_category: str | None = None  # категория достижений ФСП (дисциплина x уровень)


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
        stmt = self._select().where(CandidateProfile.id.in_(ids))
        return list((await self.session.execute(stmt)).scalars())

    async def by_anon_id(self, anon_id: uuid.UUID) -> CandidateProfile | None:
        return await self.first(CandidateProfile.anon_id == anon_id)

    async def search_all(self, filters: CatalogFilters, limit: int) -> list[CandidateProfile]:
        """Кандидаты под фильтры для ранжирования: сначала подтверждённые тестом и сильные —
        они гарантированно попадут в рейтинг, даже если под фильтр подходит больше limit."""
        stmt = (
            self._select()
            .where(*_conditions(filters))
            .order_by(
                CandidateProfile.confirmed_grade.is_(None),
                CandidateProfile.assessment_score.desc().nulls_last(),
                CandidateProfile.created_at.desc(),
                CandidateProfile.id.desc(),
            )
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars())

    async def version(self) -> tuple[int, datetime | None]:
        """Признак изменения каталога: кэш рейтинга сбрасывается при любой правке профилей."""
        stmt = select(func.count(), func.max(CandidateProfile.updated_at)).where(*VISIBLE)
        count, updated = (await self.session.execute(stmt)).one()
        return count, updated

    async def category_counts(self) -> dict[tuple[Specialization, Grade], int]:
        stmt = (
            select(CandidateProfile.specialization, CandidateProfile.confirmed_grade, func.count())
            .where(
                *VISIBLE,
                CandidateProfile.specialization.is_not(None),
                CandidateProfile.confirmed_grade.is_not(None),
            )
            .group_by(CandidateProfile.specialization, CandidateProfile.confirmed_grade)
        )
        return {(s, g): n for s, g, n in (await self.session.execute(stmt)).all()}

    async def fsp_category_counts(self) -> dict[str, int]:
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

    async def skill_names(self, slugs: set[str]) -> dict[str, str]:
        if not slugs:
            return {}
        stmt = select(Skill.slug, Skill.name).where(Skill.slug.in_(slugs))
        return {slug: name for slug, name in (await self.session.execute(stmt)).all()}


def _conditions(filters: CatalogFilters) -> list[Any]:
    conditions: list[Any] = []
    profile = CandidateProfile
    category = filters.category
    if category:
        conditions += [
            profile.specialization == category[0],
            profile.confirmed_grade == category[1],
        ]
    if filters.specialization:
        conditions.append(profile.specialization == filters.specialization)
    if filters.grade:
        conditions.append(func.coalesce(profile.confirmed_grade, profile.grade) == filters.grade)
    if filters.confirmed_only:
        conditions.append(profile.confirmed_grade.is_not(None))
    if filters.fsp_only:
        conditions.append(profile.verification_tier == VerificationTier.VERIFIED_FSP)
    if filters.search_status:
        conditions.append(profile.search_status == filters.search_status)
    if filters.work_format:
        # список форматов хранится JSON-массивом: поиск по тексту одинаково работает в PostgreSQL
        # и SQLite; значения — из перечисления, поэтому совпадение в кавычках точное
        formats = cast(profile.work_formats, String)
        conditions.append(formats.like(f'%"{filters.work_format.value}"%'))
    if filters.city:
        conditions.append(or_(profile.city == filters.city, profile.relocation.is_(True)))
    if filters.fsp_category:
        in_category = (
            select(candidate_categories.c.profile_id)
            .join(Category, Category.id == candidate_categories.c.category_id)
            .where(Category.slug == filters.fsp_category)
        )
        conditions.append(profile.id.in_(in_category))
    for slug in filters.skills:
        with_skill = (
            select(profile_skills.c.profile_id)
            .join(Skill, Skill.id == profile_skills.c.skill_id)
            .where(Skill.slug == slug)
        )
        conditions.append(profile.id.in_(with_skill))
    return conditions
