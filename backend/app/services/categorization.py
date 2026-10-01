"""Автокатегоризация кандидатов по данным ФСП (детерминированно, без БД).

Категория = дисциплина ФСП x уровень: elite > advanced > base. Правила — стратегии
CategoryRule: новое правило — новый класс в RULES, остальной код не меняется.
"""

from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass

DISCIPLINES = {
    "product": "Продуктовое программирование",
    "algorithmic": "Алгоритмическое программирование",
    "security": "Программирование систем информационной безопасности",
    "drones": "Программирование беспилотных авиационных систем",
    "robotics": "Программирование робототехники",
}
TIERS = ("base", "advanced", "elite")  # по возрастанию
TIER_TITLES = {
    "elite": "призёры всероссийского и международного уровня",
    "advanced": "финалисты и призёры регионального уровня",
    "base": "участники соревнований",
}
LEVEL_TITLES = {
    "regional": "региональный",
    "national": "всероссийский",
    "international": "международный",
}
_RANK_TIERS = {"МСМК": "elite", "МС": "elite", "КМС": "advanced", "1": "advanced"}
_TOP_LEVELS = ("national", "international")
_PRIZE = 3


@dataclass(frozen=True)
class Evidence:
    discipline: str
    level: str
    place: int | None
    stage: str
    title: str
    date: str


@dataclass(frozen=True)
class CategoryMatch:
    slug: str
    discipline: str
    tier: str
    title: str
    reasons: tuple[str, ...]


def result_tier(e: Evidence) -> str:
    prize = e.place is not None and e.place <= _PRIZE
    if prize and e.level in _TOP_LEVELS:
        return "elite"
    if (e.level in _TOP_LEVELS and e.stage == "final") or (prize and e.level == "regional"):
        return "advanced"
    return "base"


def _stronger(a: str, b: str) -> str:
    return a if TIERS.index(a) >= TIERS.index(b) else b


def describe(e: Evidence) -> str:
    outcome = f"{e.place} место" if e.place else ("финал" if e.stage == "final" else "участие")
    return f"{outcome} — {e.title} ({e.date[:4]}, {LEVEL_TITLES.get(e.level, e.level)} уровень)"


def describe_anonymous(e: Evidence) -> str:
    """Без названия соревнования: по публичным протоколам нельзя однозначно найти человека."""
    outcome = (
        "призёр"
        if e.place and e.place <= _PRIZE
        else ("финалист" if e.stage == "final" else "участник")
    )
    return f"{outcome} — {LEVEL_TITLES.get(e.level, e.level)} уровень, {e.date[:4]}"


def build_match(discipline: str, tier: str, reasons: list[str]) -> CategoryMatch:
    title = f"{DISCIPLINES.get(discipline, discipline)}: {TIER_TITLES[tier]}"
    return CategoryMatch(f"{discipline}-{tier}", discipline, tier, title, tuple(sorted(reasons)))


class CategoryRule(ABC):
    @abstractmethod
    def evaluate(self, evidence: list[Evidence], rank: str | None) -> list[CategoryMatch]: ...


class DisciplineTierRule(CategoryRule):
    """Лучший результат в дисциплине задаёт уровень; разряд повышает уровень там,
    где у спортсмена есть результаты (разряд без результатов категорию не даёт)."""

    def evaluate(self, evidence: list[Evidence], rank: str | None) -> list[CategoryMatch]:
        by_discipline: dict[str, list[Evidence]] = defaultdict(list)
        for item in evidence:
            by_discipline[item.discipline].append(item)
        matches = []
        for discipline, items in by_discipline.items():
            tier = "base"
            for item in items:
                tier = _stronger(tier, result_tier(item))
            reasons = [describe(item) for item in items if result_tier(item) == tier]
            rank_tier = _RANK_TIERS.get(rank or "", "base")
            if TIERS.index(rank_tier) > TIERS.index(tier):
                tier, reasons = rank_tier, [f"Спортивный разряд: {rank}"]
            matches.append(build_match(discipline, tier, reasons))
        return matches


RULES: tuple[CategoryRule, ...] = (DisciplineTierRule(),)


def all_categories() -> list[CategoryMatch]:
    """Полный справочник категорий (дисциплина x уровень): засевается заранее, чтобы
    категоризация только ссылалась на него и не создавала строки конкурентно."""
    return [build_match(d, t, []) for d in DISCIPLINES for t in reversed(TIERS)]


def categorize(
    evidence: list[Evidence], rank: str | None, rules: tuple[CategoryRule, ...] = RULES
) -> list[CategoryMatch]:
    matches = [m for rule in rules for m in rule.evaluate(evidence, rank)]
    return sorted(matches, key=lambda m: m.slug)
