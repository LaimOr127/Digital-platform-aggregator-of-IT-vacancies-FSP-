"""Синтетические кандидаты и вакансии со скрытой истиной (детерминированно по seed)."""

import random
from dataclasses import dataclass

from app.models.enums import Grade, Specialization, WorkFormat
from app.services.specializations import GRADE_ORDER, SPECIALIZATIONS, grade_at

ALL_SKILLS = sorted({s for info in SPECIALIZATIONS.values() for s in info.skills})
CITIES = ("Москва", "Казань", "Новосибирск")
# ориентир вилки по грейдам, ₽ в месяц: стажёр .. lead
BASE_SALARY = {1: 60_000, 2: 120_000, 3: 220_000, 4: 330_000, 5: 420_000}


@dataclass(frozen=True)
class Person:
    """Кандидат: истина (ability, true_grade, skills) и то, что он сообщает о себе."""

    specialization: Specialization
    ability: float  # настоящий уровень по шкале грейдов 1..5
    true_grade: Grade
    claimed_grade: Grade
    skills: frozenset[str]  # настоящий стек
    declared: tuple[str, ...]  # заявленный в профиле (бывает «накрученным»)
    fsp_tier: str | None  # base / advanced / elite или нет истории ФСП
    city: str
    work_format: WorkFormat
    salary_min: int
    stack_gap: float = 1.0  # насколько хуже решает задания по незнакомой технологии (в уровнях)


@dataclass(frozen=True)
class Opening:
    specialization: Specialization
    grade: Grade
    skills: tuple[str, ...]
    city: str
    work_format: WorkFormat
    salary_max: int


def people(rng: random.Random, count: int, stack_gap: float = 1.0) -> list[Person]:
    return [_person(rng, stack_gap) for _ in range(count)]


def _person(rng: random.Random, stack_gap: float) -> Person:
    specialization = rng.choice(list(Specialization))
    ability = min(5.4, max(0.6, rng.gauss(3.0, 1.1)))
    level = min(5, max(1, round(ability)))
    # самооценка: часть кандидатов завышает грейд, меньшая часть — занижает
    drift = rng.choices((1, 0, -1), weights=(25, 65, 10))[0]
    stack = SPECIALIZATIONS[specialization].skills
    skills = frozenset(rng.sample(stack, k=min(len(stack), rng.randint(2, 4))))
    declared = sorted(skills)
    if rng.random() < 0.35:  # «накрутка» резюме: популярные навыки, которых нет
        declared += rng.sample([s for s in ALL_SKILLS if s not in skills], k=4)
    return Person(
        specialization=specialization,
        ability=ability,
        true_grade=grade_at(level),
        claimed_grade=grade_at(level + drift),
        skills=skills,
        declared=tuple(declared),
        fsp_tier=_fsp_tier(rng, ability),
        city=rng.choice(CITIES),
        work_format=rng.choice(list(WorkFormat)),
        salary_min=int(round(BASE_SALARY[level] * rng.uniform(0.85, 1.2), -4)),
        stack_gap=stack_gap,
    )


def _fsp_tier(rng: random.Random, ability: float) -> str | None:
    """Участники соревнований ФСП — меньшинство, чаще среди сильных."""
    if rng.random() > 0.1 + 0.08 * ability:
        return None
    return "elite" if ability > 4.3 else "advanced" if ability > 3.3 else "base"


def openings(rng: random.Random, count: int) -> list[Opening]:
    result = []
    for _ in range(count):
        specialization = rng.choice(list(Specialization))
        level = rng.choice((2, 3, 3, 4, 4, 5))
        stack = SPECIALIZATIONS[specialization].skills
        result.append(
            Opening(
                specialization=specialization,
                grade=GRADE_ORDER[level - 1],
                skills=tuple(rng.sample(stack, k=min(3, len(stack)))),
                city=rng.choice(CITIES),
                work_format=rng.choice(list(WorkFormat)),
                salary_max=int(round(BASE_SALARY[level] * 1.25, -4)),
            )
        )
    return result
