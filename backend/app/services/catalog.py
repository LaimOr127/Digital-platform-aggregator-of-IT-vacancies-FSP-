"""Каталог кандидатов для работодателя: категории со счётчиками и анонимные карточки.

Выдача строится от категорий (специализация x грейд, подтверждённый тестом) и результатов
теста, а не от самоописания. Без вакансии кандидаты упорядочены по силе подтверждённого
профиля; с вакансией (описанием потребности) — по соответствию ей. У каждой позиции —
объяснение по факторам. Фильтры уточняют выдачу, не меняя порядка внутри неё.

Карточка не раскрывает личность: нет имени, контактов, ID ФСП, названий соревнований.
"""

import uuid
from dataclasses import asdict

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import TtlCache
from app.core.errors import ForbiddenError, NotFoundError
from app.core.timeutil import as_aware
from app.models import CandidateProfile, Category, Vacancy
from app.repositories.catalog import CatalogFilters, CatalogRepository
from app.repositories.fsp import CategoryRepository
from app.repositories.vacancies import VacancyRepository
from app.schemas.catalog import (
    CandidateCardOut,
    CandidateCategoryOut,
    CatalogCategoryOut,
    CategoryBriefOut,
    FspCategoryOut,
    MatchFactorOut,
    MatchOut,
)
from app.services.access import Action, Principal, policy
from app.services.categorization import TIERS, describe_anonymous
from app.services.common import next_offset, parse_offset
from app.services.fsp_sync import to_evidence
from app.services.matching.factors import Candidate
from app.services.matching.scorer import MatchResult, VacancyContext, match, strength
from app.services.specializations import (
    GRADE_ORDER,
    SPECIALIZATIONS,
    category_slug,
    category_title,
)

# ранжируются до стольких кандидатов (сначала подтверждённые тестом и сильные)
MAX_SCORED = 3000
Ranking = list[tuple[uuid.UUID, MatchResult]]
RANKING_CACHE: TtlCache[Ranking] = TtlCache(ttl=60, max_items=256)


class CatalogService:
    def __init__(self, session: AsyncSession, principal: Principal) -> None:
        policy.ensure(principal, Action.CATALOG_READ)
        self.session = session
        self.principal = principal
        self.catalog = CatalogRepository(session)

    async def categories(self) -> list[CatalogCategoryOut]:
        counts = await self.catalog.category_counts()
        return [
            CatalogCategoryOut(
                slug=category_slug(spec, grade),
                title=category_title(spec, grade),
                specialization=spec,
                grade=grade,
                candidates=counts.get((spec, grade), 0),
            )
            for spec in SPECIALIZATIONS
            for grade in GRADE_ORDER
        ]

    async def fsp_categories(self) -> list[FspCategoryOut]:
        counts = await self.catalog.fsp_category_counts()
        categories = await CategoryRepository(self.session).all_ordered()
        ordered = sorted(categories, key=lambda c: (c.discipline, -TIERS.index(c.tier)))
        return [
            FspCategoryOut(
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
        """Рейтинг кэшируется на минуту: страницы листаются без пересчёта и в стабильном порядке;
        правка вакансии или любого профиля сразу даёт новый рейтинг."""
        vacancy = await self._vacancy(vacancy_id) if vacancy_id else None
        version = await self.catalog.version()
        key = (vacancy.id, vacancy.updated_at) if vacancy else "strength"
        ranking = RANKING_CACHE.get((key, version, filters))
        if ranking is None:
            ranking = await self._rank(vacancy, filters)
            RANKING_CACHE.put((key, version, filters), ranking)
        offset = parse_offset(cursor, _OFFSET_PREFIX)
        page = ranking[offset : offset + limit]
        # видимость проверяется заново: кандидат мог скрыться после расчёта рейтинга
        visible = {p.id: p for p in await self.catalog.by_ids([pid for pid, _ in page])}
        shown = [(visible[pid], result) for pid, result in page if pid in visible]
        cards = await build_cards(self.catalog, [p for p, _ in shown])
        for card, (_, result) in zip(cards, shown, strict=True):
            explained = MatchOut(
                score=result.score, factors=[MatchFactorOut(**asdict(f)) for f in result.factors]
            )
            if vacancy:
                card.match = explained
            else:
                card.strength = explained
        return cards, next_offset(offset, limit, len(ranking), _OFFSET_PREFIX)

    async def _vacancy(self, vacancy_id: uuid.UUID) -> Vacancy:
        if self.principal.company_id is None:
            raise ForbiddenError("подбор по вакансии доступен работодателю")
        return await VacancyRepository(self.session, self.principal.company_id).get_or_404(
            vacancy_id
        )

    async def _rank(self, vacancy: Vacancy | None, filters: CatalogFilters) -> Ranking:
        profiles = await self.catalog.search_all(filters, MAX_SCORED)
        categories = await self.catalog.categories_for([p.id for p in profiles])
        context = VacancyContext.of(vacancy) if vacancy else None
        ranking = []
        for p in profiles:
            candidate = Candidate(p, categories.get(p.id, []))
            result = match(vacancy, candidate, context=context) if vacancy else strength(candidate)
            ranking.append((p.id, result))
        ranking.sort(key=lambda pair: pair[1].score, reverse=True)  # устойчиво: порядок SQL
        return ranking

    async def candidate(self, anon_id: uuid.UUID) -> CandidateCardOut:
        profile = await self.catalog.by_anon_id(anon_id)
        if profile is None:
            raise NotFoundError("кандидат не найден или скрыл профиль")
        (card,) = await build_cards(self.catalog, [profile])
        categories = await self.catalog.categories_for([profile.id])
        result = strength(Candidate(profile, categories.get(profile.id, [])))
        card.strength = MatchOut(
            score=result.score, factors=[MatchFactorOut(**asdict(f)) for f in result.factors]
        )
        return card


async def build_cards(
    catalog: CatalogRepository, profiles: list[CandidateProfile]
) -> list[CandidateCardOut]:
    """Карточки пачкой: категории, достижения и названия навыков — по запросу на страницу."""
    ids = [p.id for p in profiles]
    fsp = await catalog.categories_for(ids)
    achievements = await catalog.achievements_for(ids)
    names = await catalog.skill_names({s for p in profiles for s in p.confirmed_skills or []})
    # приватность: скрытые кандидатом разделы не попадают в карточку
    return [
        _card(
            p,
            fsp.get(p.id, []) if p.show_fsp else [],
            achievements.get(p.id, []) if p.show_fsp else [],
            names,
        )
        for p in profiles
    ]


def _card(
    p: CandidateProfile, fsp: list[Category], achievements: list, names: dict[str, str]
) -> CandidateCardOut:
    category = (
        CategoryBriefOut(
            slug=category_slug(p.specialization, p.confirmed_grade),
            title=category_title(p.specialization, p.confirmed_grade),
        )
        if p.specialization and p.confirmed_grade
        else None
    )
    return CandidateCardOut(
        anon_id=p.anon_id,
        title=p.title,
        specialization=p.specialization,
        category=category,
        grade=p.grade,
        confirmed_grade=p.confirmed_grade,
        assessment_score=p.assessment_score,
        experience_years=p.experience_years,
        work_format=p.work_format,
        city=p.city,
        salary_min=p.salary_min if p.show_salary else None,
        salary_max=p.salary_max if p.show_salary else None,
        verification_tier=p.verification_tier,
        search_status=p.search_status,
        skills=sorted(s.name for s in p.skills),
        confirmed_skills=sorted(names.get(s, s) for s in p.confirmed_skills or []),
        fsp_categories=[CandidateCategoryOut(slug=c.slug, tier=c.tier, title=c.title) for c in fsp],
        achievements=[describe_anonymous(to_evidence(a)) for a in achievements],
        about=p.about if p.show_about else None,
        last_activity_at=as_aware(p.last_activity_at) if p.last_activity_at else None,
    )


_OFFSET_PREFIX = "m"
