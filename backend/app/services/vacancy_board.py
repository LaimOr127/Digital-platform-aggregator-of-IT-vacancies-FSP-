"""Лента вакансий для кандидата: самостоятельный отклик — дополнение к основной механике,
когда приглашений пока нет. Вакансии упорядочены по соответствию профилю кандидата."""

import uuid
from dataclasses import asdict

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import TtlCache
from app.core.errors import NotFoundError
from app.core.timeutil import as_aware
from app.models import Application, CandidateProfile, EmployerCompany, Vacancy
from app.repositories.applications import CandidateApplicationRepository
from app.repositories.candidates import CandidateProfileRepository
from app.repositories.catalog import CatalogRepository
from app.repositories.vacancies import BoardFilters, PublishedVacancyRepository
from app.schemas.applications import BoardVacancyOut
from app.schemas.catalog import MatchFactorOut, MatchOut
from app.services.access import Action, Principal, policy
from app.services.applications.common import brief, companies, effective_status
from app.services.common import next_offset, parse_offset
from app.services.matching.factors import Candidate
from app.services.matching.scorer import MatchResult, match

MAX_VACANCIES = 500
BOARD_CACHE: TtlCache[list[tuple[uuid.UUID, MatchResult]]] = TtlCache(ttl=60, max_items=512)
_PREFIX = "v"


class VacancyBoardService:
    def __init__(self, session: AsyncSession, principal: Principal) -> None:
        policy.ensure(principal, Action.PROFILE_MANAGE_OWN)
        self.session = session
        self.profiles = CandidateProfileRepository(session, owner_id=principal.user_id)
        self.vacancies = PublishedVacancyRepository(session)

    async def list_vacancies(
        self, filters: BoardFilters, cursor: str | None, limit: int
    ) -> tuple[list[BoardVacancyOut], str | None]:
        profile = await self.profiles.own_or_404()
        # рейтинг считается один раз и листается из кэша; правка профиля или вакансий его сбрасывает
        key = (profile.id, profile.updated_at, filters, await self.vacancies.version())
        ranked = BOARD_CACHE.get(key)
        if ranked is None:
            ranked = await self._rank(profile, filters)
            BOARD_CACHE.put(key, ranked)
        offset = parse_offset(cursor, _PREFIX)
        page = ranked[offset : offset + limit]
        # снятые с публикации после расчёта рейтинга вакансии не показываются
        published = await self.vacancies.by_ids([vacancy_id for vacancy_id, _ in page])
        shown = [(published[vid], result) for vid, result in page if vid in published]
        applied = await CandidateApplicationRepository(self.session, profile.id).by_vacancies(
            [v.id for v, _ in shown]
        )
        found = await companies(self.session, {v.company_id for v, _ in shown})
        items = [_out(v, result, found.get(v.company_id), applied.get(v.id)) for v, result in shown]
        return items, next_offset(offset, limit, len(ranked), _PREFIX)

    async def _rank(
        self, profile: CandidateProfile, filters: BoardFilters
    ) -> list[tuple[uuid.UUID, MatchResult]]:
        categories = await CatalogRepository(self.session).categories_for([profile.id])
        candidate = Candidate(profile, categories.get(profile.id, []))
        scored = [
            (v.id, match(v, candidate)) for v in await self.vacancies.search(filters, MAX_VACANCIES)
        ]
        return sorted(scored, key=lambda pair: pair[1].score, reverse=True)

    async def vacancy(self, vacancy_id: uuid.UUID) -> BoardVacancyOut:
        profile = await self.profiles.own_or_404()
        vacancy = await self.vacancies.get(vacancy_id)
        if vacancy is None:
            raise NotFoundError("вакансия не найдена или снята с публикации")
        categories = await CatalogRepository(self.session).categories_for([profile.id])
        result = match(vacancy, Candidate(profile, categories.get(profile.id, [])))
        applied = await CandidateApplicationRepository(self.session, profile.id).by_vacancies(
            [vacancy.id]
        )
        found = await companies(self.session, {vacancy.company_id})
        return _out(vacancy, result, found.get(vacancy.company_id), applied.get(vacancy.id))


def _out(
    vacancy: Vacancy,
    result: MatchResult,
    company: EmployerCompany | None,
    application: Application | None,
) -> BoardVacancyOut:
    return BoardVacancyOut(
        id=vacancy.id,
        title=vacancy.title,
        description=vacancy.description,
        specialization=vacancy.specialization,
        grade=vacancy.grade,
        work_format=vacancy.work_format,
        city=vacancy.city,
        salary_min=vacancy.salary_min,
        salary_max=vacancy.salary_max,
        skills=sorted(s.name for s in vacancy.skills),
        expires_at=as_aware(vacancy.expires_at) if vacancy.expires_at else None,
        company=brief(company, ""),
        match=MatchOut(
            score=result.score, factors=[MatchFactorOut(**asdict(f)) for f in result.factors]
        ),
        application_status=effective_status(application) if application else None,
    )
