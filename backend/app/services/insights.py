"""Радар зарплат и путь роста кандидата — по данным платформы, без внешних источников.

k-анонимность: распределение показывается только для групп не меньше K_ANON значений,
а данные компаний (вилки, офферы) — только если в группе не меньше MIN_COMPANIES компаний:
по медиане нельзя восстановить зарплату конкретного человека или вакансии одной компании.
"""

import statistics
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidStateError
from app.db.session import system_scope
from app.models import CandidateProfile, Skill
from app.models.enums import Grade, VerificationTier
from app.repositories import insights as data
from app.repositories.candidates import CandidateProfileRepository
from app.repositories.fsp import CategoryRepository
from app.schemas.insights import (
    GradeSalaryOut,
    GrowthOut,
    SalaryBandOut,
    SalaryRadarOut,
    SkillShareOut,
)
from app.services.access import Action, Principal, policy
from app.services.categorization import TIERS
from app.services.specializations import GRADE_ORDER

K_ANON = 5
MIN_COMPANIES = 3
_TOP_SKILLS = 6
_FSP_NEXT = {
    None: "Привяжите аккаунт ФСП: подтверждённые результаты поднимают вас в подборе работодателей",
    "base": "Продвинутый уровень ФСП: выйдите в финал всероссийского соревнования "
    "или займите призовое место на региональном",
    "advanced": "Высший уровень ФСП: займите призовое место на всероссийском "
    "или международном соревновании",
    "elite": "Вы на высшем уровне ФСП — подтверждайте результаты каждый сезон",
}


def band(values: list[int]) -> SalaryBandOut | None:
    if len(values) < K_ANON:
        return None
    p25, median, p75 = statistics.quantiles(values, n=4, method="inclusive")
    return SalaryBandOut(count=len(values), p25=_round(p25), median=_round(median), p75=_round(p75))


def market_band(rows: list[tuple[uuid.UUID, int]]) -> SalaryBandOut | None:
    """Данные компаний: ещё и порог по числу компаний."""
    if len({company for company, _ in rows}) < MIN_COMPANIES:
        return None
    return band([value for _, value in rows])


def _round(value: float) -> int:
    return int(round(value / 1000) * 1000)


def next_grade(grade: Grade | None) -> Grade | None:
    if grade is None:
        return None
    index = GRADE_ORDER.index(grade)
    return GRADE_ORDER[min(index + 1, len(GRADE_ORDER) - 1)]


class InsightsService:
    def __init__(self, session: AsyncSession, principal: Principal) -> None:
        self.session = session
        self.principal = principal

    # --- кандидат ---------------------------------------------------------------------
    async def candidate_radar(self) -> SalaryRadarOut:
        profile = await self._own_profile()
        names, skill_ids = self._skills(profile)
        radar = await self.radar(profile.grade, skill_ids, names, exclude=profile.id)
        radar.expectation = profile.salary_min
        reference = radar.vacancies or radar.offers
        if reference and profile.salary_min:
            radar.position = (
                "below"
                if profile.salary_min < reference.p25
                else "above"
                if profile.salary_min > reference.p75
                else "within"
            )
        return radar

    async def growth(self) -> GrowthOut:
        profile = await self._own_profile()
        if profile.grade is None:
            raise InvalidStateError("укажите грейд в профиле — путь роста строится от него")
        target = next_grade(profile.grade)
        _, skill_ids = self._skills(profile)
        have = {s.slug for s in profile.skills}
        async with system_scope(self.session):
            total, demand = await data.skill_demand(self.session, target, skill_ids)
            now = market_band(await data.vacancy_salaries(self.session, profile.grade, skill_ids))
            later = market_band(await data.vacancy_salaries(self.session, target, skill_ids))
        ranked = [
            SkillShareOut(slug=slug, name=name, share=round(count / total, 2))
            for (slug, name), count in demand.most_common()
        ]
        return GrowthOut(
            current_grade=profile.grade,
            target_grade=target if target != profile.grade else None,
            vacancies_considered=total,
            missing_skills=[s for s in ranked if s.slug not in have][:_TOP_SKILLS],
            strengths=[s for s in ranked if s.slug in have][:_TOP_SKILLS],
            salary_now=now.median if now else None,
            salary_target=later.median if later else None,
            fsp_next=_FSP_NEXT[await self._best_tier(profile)],
            min_group=K_ANON,
        )

    # --- рынок (работодатель и кандидат) ------------------------------------------------
    async def market(self, grade: Grade, skill_slugs: list[str]) -> SalaryRadarOut:
        policy.ensure(self.principal, Action.COMPANY_READ_OWN)
        rows = await self.session.execute(
            select(Skill.id, Skill.name).where(Skill.slug.in_(skill_slugs))
        )
        found = rows.all()
        return await self.radar(grade, [i for i, _ in found], [n for _, n in found], exclude=None)

    async def radar(
        self,
        grade: Grade | None,
        skill_ids: list[uuid.UUID],
        names: list[str],
        exclude: uuid.UUID | None,
    ) -> SalaryRadarOut:
        empty = SalaryRadarOut(
            grade=grade,
            skills=names,
            vacancies=None,
            offers=None,
            peers=None,
            ladder=[],
            min_group=K_ANON,
        )
        if grade is None:
            return empty
        async with system_scope(self.session):
            empty.vacancies = market_band(
                await data.vacancy_salaries(self.session, grade, skill_ids)
            )
            empty.offers = market_band(await data.offer_salaries(self.session, grade, skill_ids))
            empty.peers = band(
                await data.peer_expectations(self.session, grade, skill_ids, exclude)
            )
            empty.ladder = [
                GradeSalaryOut(
                    grade=g,
                    band=market_band(await data.vacancy_salaries(self.session, g, skill_ids)),
                )
                for g in GRADE_ORDER
            ]
        return empty

    async def _own_profile(self) -> CandidateProfile:
        policy.ensure(self.principal, Action.PROFILE_MANAGE_OWN)
        return await CandidateProfileRepository(self.session, self.principal.user_id).own_or_404()

    @staticmethod
    def _skills(profile: CandidateProfile) -> tuple[list[str], list[uuid.UUID]]:
        return [s.name for s in profile.skills], [s.id for s in profile.skills]

    async def _best_tier(self, profile: CandidateProfile) -> str | None:
        if profile.verification_tier != VerificationTier.VERIFIED_FSP:
            return None
        categories = await CategoryRepository(self.session).for_profile(profile.id)
        tiers = [c.tier for c, _ in categories]
        return max(tiers, key=TIERS.index) if tiers else "base"
