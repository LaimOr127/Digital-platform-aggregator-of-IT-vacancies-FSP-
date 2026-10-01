"""Итоговый процент соответствия: взвешенная сумма факторов."""

from dataclasses import dataclass

from app.models import Vacancy
from app.services.matching.factors import (
    FACTORS,
    Candidate,
    Factor,
    FactorScore,
    VacancyContext,
)


@dataclass(frozen=True)
class MatchResult:
    score: int  # 0..100
    factors: list[FactorScore]


def match(
    vacancy: Vacancy,
    candidate: Candidate,
    factors: tuple[Factor, ...] = FACTORS,
    context: VacancyContext | None = None,
) -> MatchResult:
    """context — подготовленная вакансия: передаётся при оценке многих кандидатов подряд."""
    context = context or VacancyContext.of(vacancy)
    scores = [factor.score(context, candidate) for factor in factors]
    total_weight = sum(s.weight for s in scores)
    value = sum(s.weight * s.share for s in scores) / total_weight
    return MatchResult(round(value * 100), scores)


__all__ = ["MatchResult", "VacancyContext", "match"]
