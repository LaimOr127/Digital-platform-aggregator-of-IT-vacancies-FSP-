"""Метрики механики тестирования (ТЗ, критерий 2): точность грейда, повторяемость,
дискриминативность заданий, устойчивость к распространению заданий."""

import random
import statistics
from collections import defaultdict
from dataclasses import dataclass, replace

from app.evaluation.population import Person, people
from app.evaluation.testing import Leak, confirmed_level, key, respond, right, take
from app.services.assessment.engine import GeneratedItem, assemble
from app.services.assessment.items import REGISTRY, Item
from app.services.specializations import GRADE_ORDER

MIDDLE = 3
LEAKED_TESTS = 20  # столько чужих тестов с ответами «утекло» к недобросовестному кандидату
VARIANT_DRAWS = 200


@dataclass(frozen=True)
class AssessmentReport:
    candidates: int
    grade_exact: float  # подтверждённый грейд совпал с настоящим
    grade_within_one: float
    grade_under: float  # подтверждён грейд ниже настоящего
    grade_over: float  # выше настоящего: работодатель переоценил бы кандидата
    no_category: float  # не подтвердил даже стажёра
    overclaim_caught: float  # завысил грейд — и система его не подтвердила
    confusion: dict[str, dict[str, int]]  # настоящий грейд -> подтверждённый -> число
    retest_decision: float  # одинаковое решение «сдал/не сдал» в двух попытках
    retest_theta_r: float  # корреляция оценок уровня в двух попытках
    retest_grade: float  # одинаковый итоговый грейд при повторном прохождении пути
    score_by_grade: dict[str, float]  # доля верных ответов в тесте Middle по настоящему грейду
    item_r_median: float  # медиана скорректированной точечно-бисериальной корреляции
    item_r_share: float  # доля шаблонов с r >= 0.2
    variants_median: int  # различных вариантов шаблона на VARIANT_DRAWS генераций
    overlap: float  # доля одинаковых заданий в двух тестах одной категории
    leak_pass_bank: float  # слабый кандидат с утёкшими ответами: доля сдавших (наш банк)
    honest_pass_bank: float  # тот же кандидат без утечки
    leak_pass_static: float  # то же для единого статичного теста
    honest_pass_static: float


def run(seed: int = 2026, candidates: int = 1000, stack_gap: float = 1.0) -> AssessmentReport:
    rng = random.Random(seed)
    population = people(rng, candidates, stack_gap)
    accuracy = _accuracy(population, rng)
    retest = _retest(population, rng)
    items = _items(population, rng)
    leaks = _leak_resistance(population, rng)
    return AssessmentReport(candidates=candidates, **accuracy, **retest, **items, **leaks)


def _accuracy(population: list[Person], rng: random.Random) -> dict:
    confusion: dict[str, dict[str, int]] = {g.value: defaultdict(int) for g in GRADE_ORDER}
    exact = near = under = over = missing = overclaimed = caught = 0
    for person in population:
        level, _ = confirmed_level(person, rng)
        truth = GRADE_ORDER.index(person.true_grade) + 1
        confusion[person.true_grade.value][GRADE_ORDER[level - 1].value if level else "none"] += 1
        exact += level == truth
        near += level is not None and abs(level - truth) <= 1
        under += level is None or level < truth
        over += level is not None and level > truth
        missing += level is None
        if GRADE_ORDER.index(person.claimed_grade) + 1 > truth:
            overclaimed += 1
            caught += level is None or level <= truth
    return {
        "grade_exact": exact / len(population),
        "grade_within_one": near / len(population),
        "grade_under": under / len(population),
        "grade_over": over / len(population),
        "no_category": missing / len(population),
        "overclaim_caught": caught / max(overclaimed, 1),
        "confusion": {g: dict(row) for g, row in confusion.items()},
    }


def _retest(population: list[Person], rng: random.Random) -> dict:
    """Два независимых теста одному человеку: задания разные, уровень тот же."""
    same_decision, thetas, same_grade = 0, ([], []), 0
    for person in population:
        level = GRADE_ORDER.index(person.claimed_grade) + 1
        _, first = take(person, level, rng)
        _, second = take(person, level, rng)
        same_decision += first.passed == second.passed
        thetas[0].append(first.theta)
        thetas[1].append(second.theta)
        same_grade += confirmed_level(person, rng)[0] == confirmed_level(person, rng)[0]
    return {
        "retest_decision": same_decision / len(population),
        "retest_theta_r": statistics.correlation(*thetas),
        "retest_grade": same_grade / len(population),
    }


def _items(population: list[Person], rng: random.Random) -> dict:
    """Дискриминативность: связь верности ответа на задание с суммой остальных ответов теста."""
    marks: dict[str, list[tuple[int, int]]] = defaultdict(list)
    by_grade: dict[str, list[float]] = defaultdict(list)
    for person in population:
        items = assemble(person.specialization.value, MIDDLE, rng, frozenset(person.declared))
        responses = _marks(items, person, rng)
        total = sum(responses)
        by_grade[person.true_grade.value].append(total / len(items))
        for item, mark in zip(items, responses, strict=True):
            marks[item.template].append((mark, total - mark))
    correlations = [_r(pairs) for pairs in marks.values() if len(pairs) >= 20]
    correlations = [r for r in correlations if r is not None]
    return {
        "score_by_grade": {g: statistics.fmean(v) for g, v in by_grade.items()},
        "item_r_median": statistics.median(correlations),
        "item_r_share": sum(r >= 0.2 for r in correlations) / len(correlations),
        "variants_median": _variants_median(),
    }


def _marks(items: list[GeneratedItem], person: Person, rng: random.Random) -> list[int]:
    return [int(respond(item, person, rng, None) == right(item)) for item in items]


def _r(pairs: list[tuple[int, int]]) -> float | None:
    marks, rest = zip(*pairs, strict=True)
    if len(set(marks)) < 2 or len(set(rest)) < 2:
        return None
    return statistics.correlation(marks, rest)


def _variants_median() -> int:
    counts = []
    for template in REGISTRY.values():
        rng = random.Random(template.id)
        counts.append(len({_variant(template.generate(rng)) for _ in range(VARIANT_DRAWS)}))
    return int(statistics.median(counts))


def _variant(item: Item) -> tuple:
    return item.prompt, item.code, item.options


def _leak_resistance(population: list[Person], rng: random.Random) -> dict:
    """Утечка: слабый кандидат (уровень на грейд ниже Middle) знает ответы на чужие тесты."""
    weak = [replace(p, ability=MIDDLE - 1 + rng.uniform(-0.3, 0.3)) for p in population[:300]]
    overlaps, leak_bank, honest_bank, leak_static, honest_static = [], 0, 0, 0, 0
    static_tests: dict[str, list] = {}
    for person in weak:
        spec = person.specialization.value
        leak: Leak = {}
        for _ in range(LEAKED_TESTS):
            for item in assemble(spec, MIDDLE, rng, frozenset(person.declared)):
                leak[key(item)] = right(item)
        mine, outcome = take(person, MIDDLE, rng, leak)
        leak_bank += outcome.passed
        honest_bank += take(person, MIDDLE, rng)[1].passed
        other = assemble(spec, MIDDLE, rng, frozenset(person.declared))
        overlaps.append(len({key(i) for i in mine} & {key(i) for i in other}) / len(mine))
        # базовый вариант: единый тест для всех — одной утечки достаточно
        static = static_tests.setdefault(spec, assemble(spec, MIDDLE, random.Random(spec)))
        static_leak = {key(i): right(i) for i in static}
        leak_static += take(person, MIDDLE, rng, static_leak, items=static)[1].passed
        honest_static += take(person, MIDDLE, rng, items=static)[1].passed
    total = len(weak)
    return {
        "overlap": statistics.fmean(overlaps),
        "leak_pass_bank": leak_bank / total,
        "honest_pass_bank": honest_bank / total,
        "leak_pass_static": leak_static / total,
        "honest_pass_static": honest_static / total,
    }
