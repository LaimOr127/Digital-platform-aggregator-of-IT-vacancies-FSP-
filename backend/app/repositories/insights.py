"""Данные для радара зарплат и пути роста. Возвращают только значения для агрегатов;
вызываются внутри system_scope и никогда не отдаются наружу построчно."""

import uuid
from collections import Counter

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CandidateProfile, Offer, Skill, Vacancy, profile_skills, vacancy_skills
from app.models.enums import Grade, OfferStatus, SearchStatus, VacancyStatus

_MARKET = (VacancyStatus.ACTIVE, VacancyStatus.CLOSED)  # реальные вакансии, не черновики


def _vacancy_has_skill(skill_ids: list[uuid.UUID], vacancy_id_col=Vacancy.id):
    return exists().where(
        vacancy_skills.c.vacancy_id == vacancy_id_col, vacancy_skills.c.skill_id.in_(skill_ids)
    )


async def vacancy_salaries(
    session: AsyncSession, grade: Grade, skill_ids: list[uuid.UUID]
) -> list[tuple[uuid.UUID, int]]:
    """(компания, середина вилки) вакансий грейда с пересечением по навыкам."""
    stmt = select(Vacancy.company_id, (Vacancy.salary_min + Vacancy.salary_max) / 2).where(
        Vacancy.status.in_(_MARKET), Vacancy.grade == grade
    )
    if skill_ids:
        stmt = stmt.where(_vacancy_has_skill(skill_ids))
    return [(c, int(mid)) for c, mid in (await session.execute(stmt)).all()]


async def offer_salaries(
    session: AsyncSession, grade: Grade, skill_ids: list[uuid.UUID]
) -> list[tuple[uuid.UUID, int]]:
    """(компания, середина вилки) отправленных офферов — то, что компании реально предлагают."""
    stmt = select(Offer.company_id, (Offer.salary_min + Offer.salary_max) / 2).where(
        Offer.grade == grade, Offer.status != OfferStatus.WITHDRAWN
    )
    if skill_ids:
        stmt = stmt.where(_vacancy_has_skill(skill_ids, Offer.vacancy_id))
    return [(c, int(mid)) for c, mid in (await session.execute(stmt)).all()]


async def peer_expectations(
    session: AsyncSession, grade: Grade, skill_ids: list[uuid.UUID], exclude: uuid.UUID | None
) -> list[int]:
    """Ожидания других кандидатов того же грейда и стека (видимые в каталоге)."""
    stmt = select(CandidateProfile.salary_min).where(
        CandidateProfile.grade == grade,
        CandidateProfile.salary_min.is_not(None),
        CandidateProfile.is_hidden.is_(False),
        CandidateProfile.search_status != SearchStatus.CLOSED,
    )
    if exclude is not None:
        stmt = stmt.where(CandidateProfile.id != exclude)
    if skill_ids:
        stmt = stmt.where(
            exists().where(
                profile_skills.c.profile_id == CandidateProfile.id,
                profile_skills.c.skill_id.in_(skill_ids),
            )
        )
    return [int(v) for v in (await session.execute(stmt)).scalars()]


async def skill_demand(
    session: AsyncSession, grade: Grade, skill_ids: list[uuid.UUID]
) -> tuple[int, Counter[tuple[str, str]]]:
    """Сколько вакансий грейда (с пересечением по стеку) и какие навыки в них требуются."""
    vacancies = select(Vacancy.id).where(Vacancy.status.in_(_MARKET), Vacancy.grade == grade)
    if skill_ids:
        vacancies = vacancies.where(_vacancy_has_skill(skill_ids))
    ids = list((await session.execute(vacancies)).scalars())
    if not ids:
        return 0, Counter()
    rows = await session.execute(
        select(Skill.slug, Skill.name)
        .join(vacancy_skills, vacancy_skills.c.skill_id == Skill.id)
        .where(vacancy_skills.c.vacancy_id.in_(ids))
    )
    return len(ids), Counter((slug, name) for slug, name in rows.all())
