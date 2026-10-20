"""Демо-данные для раздела модерации: жалобы кандидатов на часть опубликованных вакансий.
Статусы компаний и вакансий и заблокированных кандидатов задаёт demo.py при создании."""

import random

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CandidateProfile, User, Vacancy, VacancyComplaint
from app.models.enums import ComplaintReason, VacancyStatus

_COMPLAINTS = {
    ComplaintReason.SALARY: "На собеседовании назвали сумму вдвое ниже вилки.",
    ComplaintReason.FAKE: "Компания не отвечает, сайт не открывается.",
    ComplaintReason.SPAM: "Просят оплатить «обучение» перед выходом на работу.",
    ComplaintReason.DISCRIMINATION: "В описании ограничение по возрасту.",
    ComplaintReason.OTHER: "Вакансия давно закрыта, но висит в ленте.",
}


async def seed_complaints(session: AsyncSession, rng: random.Random, vacancies: int) -> int:
    """1–3 жалобы от демо-кандидатов на несколько опубликованных вакансий без жалоб
    (повторная заливка не нарушает уникальность «кандидат — вакансия»)."""
    targets = list(
        (
            await session.execute(
                select(Vacancy.id)
                .where(
                    Vacancy.status == VacancyStatus.ACTIVE,
                    Vacancy.id.not_in(select(VacancyComplaint.vacancy_id)),
                )
                .limit(200)
            )
        ).scalars()
    )
    profiles = list(
        (
            await session.execute(
                select(CandidateProfile.id)
                .join(User, User.id == CandidateProfile.user_id)
                .where(User.email.like("demo-%@demo.itmatch.local"), User.is_active.is_(True))
                .limit(200)
            )
        ).scalars()
    )
    if not profiles or not targets:
        return 0
    rows = []
    for vacancy_id in rng.sample(targets, k=min(len(targets), vacancies)):
        for profile_id in rng.sample(profiles, k=min(len(profiles), rng.randint(1, 3))):
            reason = rng.choice(list(_COMPLAINTS))
            rows.append(
                {
                    "vacancy_id": vacancy_id,
                    "profile_id": profile_id,
                    "reason": reason.value,
                    "comment": _COMPLAINTS[reason],
                }
            )
    await session.execute(insert(VacancyComplaint), rows)
    return len(rows)
