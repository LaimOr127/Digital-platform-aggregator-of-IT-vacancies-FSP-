"""Итоговый процент соответствия: взвешенная сумма факторов."""

from dataclasses import dataclass

from app.models import Vacancy
from app.services.matching.factors import (
    FACTORS,
    STRENGTH_FACTORS,
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
    return _total([factor.score(context, candidate) for factor in factors])


def strength(candidate: Candidate) -> MatchResult:
    """Сила профиля без вакансии: ранжирование внутри категории (тест, ФСП, актуальность)."""
    return _total([factor.score(None, candidate) for factor in STRENGTH_FACTORS])


def _total(scores: list[FactorScore]) -> MatchResult:
    total_weight = sum(s.weight for s in scores)
    value = sum(s.weight * s.share for s in scores) / total_weight
    return MatchResult(round(value * 100), scores)


__all__ = ["MatchResult", "VacancyContext", "match", "strength"]
