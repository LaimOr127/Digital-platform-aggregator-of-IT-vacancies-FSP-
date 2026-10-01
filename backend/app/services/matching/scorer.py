"""Итоговый процент соответствия: взвешенная сумма факторов."""

from dataclasses import dataclass

from app.models import Vacancy
from app.services.matching.factors import FACTORS, Candidate, Factor, FactorScore


@dataclass(frozen=True)
class MatchResult:
    score: int  # 0..100
    factors: list[FactorScore]


def match(
    vacancy: Vacancy, candidate: Candidate, factors: tuple[Factor, ...] = FACTORS
) -> MatchResult:
    scores = [factor.score(vacancy, candidate) for factor in factors]
    total_weight = sum(s.weight for s in scores)
    value = sum(s.weight * s.share for s in scores) / total_weight
    return MatchResult(round(value * 100), scores)
