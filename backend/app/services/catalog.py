"""Каталог кандидатов для работодателя: категории со счётчиками и анонимные карточки.

Карточка не раскрывает личность: нет имени, контактов, ID ФСП, названий соревнований
(достижения обобщены так же, как в анонимном паспорте). Только одобренные компании.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models import CandidateProfile
from app.models.enums import Grade, WorkFormat
from app.repositories.base import Page
from app.repositories.catalog import CatalogRepository
from app.repositories.fsp import CategoryRepository
from app.schemas.catalog import CandidateCardOut, CandidateCategoryOut, CatalogCategoryOut
from app.services.access import Action, Principal, policy
from app.services.categorization import TIERS, describe_anonymous
from app.services.fsp_sync import to_evidence


class CatalogService:
    def __init__(self, session: AsyncSession, principal: Principal) -> None:
        policy.ensure(principal, Action.CATALOG_READ)
        self.session = session
        self.catalog = CatalogRepository(session)

    async def categories(self) -> list[CatalogCategoryOut]:
        counts = await self.catalog.category_counts()
        categories = await CategoryRepository(self.session).all_ordered()
        ordered = sorted(categories, key=lambda c: (c.discipline, -TIERS.index(c.tier)))
        return [
            CatalogCategoryOut(
                slug=c.slug,
                discipline=c.discipline,
                tier=c.tier,
                title=c.title,
                candidates=counts.get(c.slug, 0),
            )
            for c in ordered
        ]

    async def candidates(
        self,
        category: str | None,
        grade: Grade | None,
        work_format: WorkFormat | None,
        skill: str | None,
        cursor: str | None,
        limit: int,
    ) -> tuple[list[CandidateCardOut], str | None]:
        page: Page[CandidateProfile] = await self.catalog.search(
            category, grade, work_format, skill, cursor, limit
        )
        return await build_cards(self.catalog, page.items), page.next_cursor

    async def candidate(self, anon_id: uuid.UUID) -> CandidateCardOut:
        profile = await self.catalog.by_anon_id(anon_id)
        if profile is None:
            raise NotFoundError("кандидат не найден или скрыл профиль")
        (card,) = await build_cards(self.catalog, [profile])
        return card


async def build_cards(
    catalog: CatalogRepository, profiles: list[CandidateProfile]
) -> list[CandidateCardOut]:
    """Карточки пачкой: категории и достижения — двумя запросами на всю страницу."""
    ids = [p.id for p in profiles]
    categories = await catalog.categories_for(ids)
    achievements = await catalog.achievements_for(ids)
    return [
        CandidateCardOut(
            anon_id=p.anon_id,
            title=p.title,
            grade=p.grade,
            work_format=p.work_format,
            city=p.city,
            salary_min=p.salary_min,
            salary_max=p.salary_max,
            verification_tier=p.verification_tier,
            skills=sorted(s.name for s in p.skills),
            categories=[
                CandidateCategoryOut(slug=c.slug, tier=c.tier, title=c.title)
                for c in categories.get(p.id, [])
            ],
            achievements=[describe_anonymous(to_evidence(a)) for a in achievements.get(p.id, [])],
            about=p.about,
        )
        for p in profiles
    ]
