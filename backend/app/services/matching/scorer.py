"""Оценка кандидата: соответствие вакансии (лента кандидата), сила профиля и место в каталоге
работодателя под потребность."""

from dataclasses import dataclass

from app.models import Vacancy
from app.services.matching.factors import (
    FACTORS,
    NEED_FACTORS,
    STRENGTH_FACTORS,
    Candidate,
    FactorScore,
    VacancyContext,
)


@dataclass(frozen=True)
class MatchResult:
    score: int  # 0..100
    factors: list[FactorScore]
    summary: str = ""  # одна строка: почему кандидат на этом месте выдачи
    fit: float = 1.0  # под потребность: насколько категория кандидата подходит (группа выдачи)


def match(vacancy: Vacancy, candidate: Candidate) -> MatchResult:
    """Соответствие вакансии для ленты кандидата."""
    context = VacancyContext.of(vacancy)
    return _total([factor.score(context, candidate) for factor in FACTORS])


def strength(candidate: Candidate) -> MatchResult:
    """Сила профиля: место внутри категории (тест, ФСП, актуальность)."""
    return _total([factor.score(None, candidate) for factor in STRENGTH_FACTORS])


def for_need(
    vacancy: Vacancy, candidate: Candidate, context: VacancyContext | None = None
) -> MatchResult:
    """Каталог под потребность: группу задаёт категория (специализация и подтверждённый грейд
    против грейда вакансии), место внутри неё — тест и ФСП с теми же весами, что у силы профиля.
    Тест здесь — близость уровня к грейду вакансии: тест скорее занижает грейд, и «больше баллов —
    выше» поднимало в категории кандидатов уровнем выше (показала процедура оценки). Стек, формат,
    город, зарплата и описание поясняют выбор, но порядок не меняют; стек — фильтр каталога."""
    context = context or VacancyContext.of(vacancy)
    category, *info = [factor.score(context, candidate) for factor in NEED_FACTORS]
    ranked = _total([factor.score(context, candidate) for factor in STRENGTH_FACTORS])
    summary = "; ".join([category.detail, ranked.summary])
    return MatchResult(ranked.score, [category, *ranked.factors, *info], summary, category.share)


def rank_key(result: MatchResult) -> tuple[float, int]:
    """Порядок выдачи каталога: сначала категория, внутри неё — сила профиля."""
    return result.fit, result.score


def _total(scores: list[FactorScore]) -> MatchResult:
    total_weight = sum(s.weight for s in scores)
    value = sum(s.weight * s.share for s in scores) / total_weight
    # строка «почему»: решающие факторы (актуальность — только уточняет порядок)
    summary = "; ".join(s.detail for s in scores if s.key in {"assessment", "fsp"})
    return MatchResult(round(value * 100), scores, summary)


__all__ = ["MatchResult", "VacancyContext", "for_need", "match", "rank_key", "strength"]
