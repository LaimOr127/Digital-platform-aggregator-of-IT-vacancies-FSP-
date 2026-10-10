"""Автокатегоризация кандидатов по данным ФСП (детерминированно, без БД).

Категория = дисциплина ФСП x уровень: elite > advanced > base. Уровень считается по результатам,
а не по статусу соревнования (совет организаторов): одни соревнования не ставятся выше других,
учитываются число призовых мест и финалов, а простое участие уровень не поднимает — профиль нельзя
«набить» явками. Дисциплины между собой не ранжируются. Правила — стратегии CategoryRule: новое
правило — новый класс в RULES, остальной код не меняется.
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
    "elite": "призёры нескольких соревнований",
    "advanced": "призёры и неоднократные финалисты",
    "base": "участники соревнований",
}
_ELITE_PRIZES = 2  # два призовых места — устойчивый результат, а не удачный старт
_ADVANCED_FINALS = 2  # без призов — минимум два выхода в финал
LEVEL_TITLES = {
    "regional": "региональный",
    "national": "всероссийский",
    "international": "международный",
}
_RANK_TIERS = {"МСМК": "elite", "МС": "elite", "КМС": "advanced", "1": "advanced"}
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


def is_prize(e: Evidence) -> bool:
    return e.place is not None and e.place <= _PRIZE


def result_tier(e: Evidence) -> str:
    """Сила отдельного результата (для порядка достижений): приз > финал > участие, при любом
    уровне соревнования."""
    if is_prize(e):
        return "elite"
    return "advanced" if e.stage == "final" else "base"


def discipline_tier(items: list["Evidence"]) -> str:
    """Уровень в дисциплине: число призовых мест и финалов; участие без финала не считается."""
    prizes = sum(is_prize(e) for e in items)
    finals = sum(e.stage == "final" and not is_prize(e) for e in items)
    if prizes >= _ELITE_PRIZES:
        return "elite"
    if prizes or finals >= _ADVANCED_FINALS:
        return "advanced"
    return "base"


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
    """Уровень в дисциплине — по числу призов и финалов (discipline_tier); разряд повышает уровень
    там, где у спортсмена есть результаты (разряд без результатов категорию не даёт)."""

    def evaluate(self, evidence: list[Evidence], rank: str | None) -> list[CategoryMatch]:
        by_discipline: dict[str, list[Evidence]] = defaultdict(list)
        for item in evidence:
            by_discipline[item.discipline].append(item)
        matches = []
        for discipline, items in by_discipline.items():
            tier = discipline_tier(items)
            # обоснование — результаты, которые дали уровень (призы и финалы), или участие
            counted = [i for i in items if result_tier(i) != "base"] or items
            reasons = [describe(item) for item in counted]
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
