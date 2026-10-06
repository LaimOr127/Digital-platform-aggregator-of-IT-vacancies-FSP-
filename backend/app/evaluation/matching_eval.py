"""Метрики подбора (ТЗ, критерий 1): доля релевантных кандидатов в топе выдачи на наборе
пар «вакансия — кандидат». Эталонная разметка — по скрытой истине кандидата:

- 2 «точно подходит»: та же специализация, настоящий грейд совпадает, есть нужная технология;
- 1 «близко»: грейд соседний при нужной технологии или точный грейд без неё;
- 0 — остальные.

Сравниваются три выдачи: IT Match (категория по тесту, результат теста, подтверждённые
навыки, ФСП — app/services/matching), «классическая» по самоописанию (заявленные грейд и
навыки, как на универсальных площадках) и случайный порядок.
"""

import math
import random
import statistics
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.evaluation.population import Opening, Person, openings, people
from app.evaluation.testing import confirmed_level
from app.models import CandidateProfile, Category, Skill, Vacancy
from app.models.enums import VerificationTier
from app.services.matching.factors import Candidate
from app.services.matching.scorer import match
from app.services.specializations import GRADE_ORDER

K = 10
Scorer = Callable[[Opening, Vacancy, Person, Candidate], float]


@dataclass(frozen=True)
class SystemScore:
    precision_at_5: float
    precision_at_10: float
    ndcg_at_10: float
    overrated_in_top: float  # доля кандидатов в топ-10 с настоящим грейдом ниже вакансии


@dataclass(frozen=True)
class MatchingReport:
    vacancies: int
    candidates: int
    relevant_per_vacancy: float
    systems: dict[str, SystemScore]


def run(seed: int = 2026, vacancies: int = 40, candidates: int = 1000) -> MatchingReport:
    rng = random.Random(seed)
    population = people(rng, candidates)
    profiles = [_candidate(person, rng) for person in population]
    jobs = [(opening, _vacancy(opening)) for opening in openings(rng, vacancies)]
    systems: dict[str, Scorer] = {
        "IT Match": lambda _o, vacancy, _p, candidate: match(vacancy, candidate).score,
        "По резюме (заявленное)": lambda opening, _v, person, _c: _resume_score(opening, person),
        "Случайный порядок": lambda *_: rng.random(),
    }
    scores = {
        name: _evaluate(scorer, jobs, population, profiles, rng) for name, scorer in systems.items()
    }
    relevant = statistics.fmean(
        sum(_relevance(o, p) == 2 for p in population) for o, _ in jobs
    )  # fmt: skip
    return MatchingReport(vacancies, candidates, relevant, scores)


def _relevance(opening: Opening, person: Person) -> int:
    if person.specialization != opening.specialization:
        return 0
    gap = abs(GRADE_ORDER.index(person.true_grade) - GRADE_ORDER.index(opening.grade))
    has_stack = bool(person.skills & set(opening.skills))
    if gap == 0 and has_stack:
        return 2
    return 1 if (gap == 1 and has_stack) or (gap == 0 and not has_stack) else 0


def _resume_score(opening: Opening, person: Person) -> float:
    """Классическая выдача: совпадение заявленных навыков и заявленного грейда."""
    if person.specialization != opening.specialization:
        return 0.0
    overlap = len(set(person.declared) & set(opening.skills)) / len(opening.skills)
    gap = abs(GRADE_ORDER.index(person.claimed_grade) - GRADE_ORDER.index(opening.grade))
    return 0.6 * overlap + 0.4 * (1.0 if gap == 0 else 0.5 if gap == 1 else 0.0)


def _evaluate(
    scorer: Scorer,
    jobs: list[tuple[Opening, Vacancy]],
    population: list[Person],
    profiles: list[Candidate],
    rng: random.Random,
) -> SystemScore:
    p5, p10, ndcg, overrated = [], [], [], []
    for opening, vacancy in jobs:
        # равные баллы — в случайном порядке, иначе порядок генерации влиял бы на метрику
        ranked = sorted(
            zip(population, profiles, strict=True),
            key=lambda pair: (scorer(opening, vacancy, *pair), rng.random()),
            reverse=True,
        )
        gains = [_relevance(opening, person) for person, _ in ranked]
        p5.append(sum(g == 2 for g in gains[:5]) / 5)
        p10.append(sum(g == 2 for g in gains[:K]) / K)
        ndcg.append(_ndcg(gains))
        target = GRADE_ORDER.index(opening.grade)
        overrated.append(
            sum(GRADE_ORDER.index(p.true_grade) < target for p, _ in ranked[:K]) / K
        )  # fmt: skip
    return SystemScore(
        statistics.fmean(p5), statistics.fmean(p10), statistics.fmean(ndcg),
        statistics.fmean(overrated),
    )  # fmt: skip


def _ndcg(gains: list[int]) -> float:
    def dcg(values: list[int]) -> float:
        return sum((2**g - 1) / math.log2(i + 2) for i, g in enumerate(values[:K]))

    ideal = dcg(sorted(gains, reverse=True))
    return dcg(gains) / ideal if ideal else 0.0


def _candidate(person: Person, rng: random.Random) -> Candidate:
    """Профиль, каким его видит система: заявленное, подтверждённое тестом и ФСП."""
    level, outcome = confirmed_level(person, rng)
    profile = CandidateProfile(
        specialization=person.specialization,
        grade=person.claimed_grade,
        confirmed_grade=GRADE_ORDER[level - 1] if level else None,
        assessment_score=outcome.score if outcome else None,
        confirmed_skills=list(outcome.skills) if outcome else [],
        verification_tier=VerificationTier.VERIFIED_FSP
        if person.fsp_tier
        else VerificationTier.SELF_DECLARED,
        city=person.city,
        work_formats=[person.work_format],
        salary_min=person.salary_min,
        last_activity_at=datetime.now(UTC) - timedelta(days=rng.randint(0, 150)),
    )
    profile.skills = [Skill(slug=s, name=s) for s in person.declared]
    tier = person.fsp_tier
    categories = (
        [Category(slug=f"fsp:{tier}", discipline="fsp", tier=tier, title=tier)] if tier else []
    )
    return Candidate(profile, categories)


def _vacancy(opening: Opening) -> Vacancy:
    vacancy = Vacancy(
        title="Вакансия",
        description="",
        specialization=opening.specialization,
        grade=opening.grade,
        work_format=opening.work_format,
        city=opening.city,
        salary_min=opening.salary_max // 2,
        salary_max=opening.salary_max,
    )
    vacancy.skills = [Skill(slug=s, name=s) for s in opening.skills]
    return vacancy
