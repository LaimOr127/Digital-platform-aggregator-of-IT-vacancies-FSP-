"""Каталог кандидатов для работодателя: категории со счётчиками и анонимные карточки.

Карточка не раскрывает личность: нет имени, контактов, ID ФСП, названий соревнований
(достижения обобщены так же, как в анонимном паспорте). Только одобренные компании.
"""

import uuid
from dataclasses import asdict

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import TtlCache
from app.core.errors import ForbiddenError, InvalidStateError, NotFoundError
from app.models import CandidateProfile, Vacancy
from app.repositories.base import Page
from app.repositories.catalog import CatalogFilters, CatalogRepository
from app.repositories.fsp import CategoryRepository
from app.repositories.vacancies import VacancyRepository
from app.schemas.catalog import (
    CandidateCardOut,
    CandidateCategoryOut,
    CatalogCategoryOut,
    MatchFactorOut,
    MatchOut,
)
from app.services.access import Action, Principal, policy
from app.services.categorization import TIERS, describe_anonymous
from app.services.fsp_sync import to_evidence
from app.services.matching.factors import Candidate
from app.services.matching.scorer import MatchResult, VacancyContext, match

# сортировка по соответствию оценивает до стольких кандидатов (новые — первыми)
MAX_SCORED = 1000
MATCH_CACHE: TtlCache[list[tuple[uuid.UUID, MatchResult]]] = TtlCache(ttl=60, max_items=256)


class CatalogService:
    def __init__(self, session: AsyncSession, principal: Principal) -> None:
        policy.ensure(principal, Action.CATALOG_READ)
        self.session = session
        self.principal = principal
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
        filters: CatalogFilters,
        cursor: str | None,
        limit: int,
        vacancy_id: uuid.UUID | None = None,
    ) -> tuple[list[CandidateCardOut], str | None]:
        if vacancy_id is not None:
            return await self._by_match(filters, vacancy_id, cursor, limit)
        page: Page[CandidateProfile] = await self.catalog.search(filters, cursor, limit)
        return await build_cards(self.catalog, page.items), page.next_cursor

    async def _by_match(
        self, filters: CatalogFilters, vacancy_id: uuid.UUID, cursor: str | None, limit: int
    ) -> tuple[list[CandidateCardOut], str | None]:
        """Самые подходящие кандидаты — сверху; при равенстве — новые профили.

        Рейтинг кэшируется на минуту: страницы листаются без пересчёта и в стабильном
        порядке; правка вакансии (updated_at) сразу даёт новый рейтинг.
        """
        vacancy = await VacancyRepository(self.session, self._company_id()).get_or_404(vacancy_id)
        key = (vacancy.id, vacancy.updated_at, filters)
        ranking = MATCH_CACHE.get(key)
        if ranking is None:
            ranking = await self._rank(vacancy, filters)
            MATCH_CACHE.put(key, ranking)
        offset = _offset(cursor)
        page = ranking[offset : offset + limit]
        # видимость проверяется заново: кандидат мог скрыться после расчёта рейтинга
        visible = {p.id: p for p in await self.catalog.by_ids([pid for pid, _ in page])}
        shown = [(visible[pid], result) for pid, result in page if pid in visible]
        cards = await build_cards(self.catalog, [p for p, _ in shown])
        for card, (_, result) in zip(cards, shown, strict=True):
            card.match = MatchOut(
                score=result.score,
                factors=[MatchFactorOut(**asdict(f)) for f in result.factors],
            )
        has_more = offset + limit < len(ranking)
        return cards, f"{_OFFSET_PREFIX}{offset + limit}" if has_more else None

    async def _rank(
        self, vacancy: Vacancy, filters: CatalogFilters
    ) -> list[tuple[uuid.UUID, MatchResult]]:
        profiles = await self.catalog.search_all(filters, MAX_SCORED)
        categories = await self.catalog.categories_for([p.id for p in profiles])
        context = VacancyContext.of(vacancy)
        ranking = [
            (p.id, match(vacancy, Candidate(p, categories.get(p.id, [])), context=context))
            for p in profiles
        ]
        ranking.sort(key=lambda pair: pair[1].score, reverse=True)  # устойчиво: новые выше
        return ranking

    def _company_id(self) -> uuid.UUID:
        if self.principal.company_id is None:
            raise ForbiddenError("подбор по вакансии доступен работодателю")
        return self.principal.company_id

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
            search_status=p.search_status,
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


_OFFSET_PREFIX = "m"


def _offset(cursor: str | None) -> int:
    """Курсор сортировки по соответствию — позиция в отсортированном списке."""
    if not cursor:
        return 0
    if not cursor.startswith(_OFFSET_PREFIX) or not cursor[1:].isdigit():
        raise InvalidStateError("некорректный курсор")
    return int(cursor[1:])
