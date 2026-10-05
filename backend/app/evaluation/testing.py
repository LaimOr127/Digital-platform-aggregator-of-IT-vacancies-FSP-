"""Симуляция прохождения теста: синтетический кандидат отвечает на сгенерированные задания.

Вероятность верного ответа — та же модель IRT, что в оценке (engine.probability), от
настоящего уровня кандидата; задание по технологии, которой нет в настоящем стеке (вопрос
по iOS разработчику под Android), даётся кандидату на уровень хуже. Общие темы — алгоритмы,
системный дизайн, git — знакомы всем. Путь по грейдам повторяет правила продукта: не сдал —
тест ниже, сдал уверенно — тест выше.
"""

import random

from app.evaluation.population import ALL_SKILLS, Person
from app.services.assessment.engine import GeneratedItem, Outcome, assemble, evaluate, probability
from app.services.specializations import GRADE_ORDER

TECHNOLOGIES = frozenset(ALL_SKILLS)
Leak = dict[tuple, str]  # вариант задания -> известный ответ


def key(item: GeneratedItem) -> tuple:
    """Вариант задания как его видит кандидат: текст, код и порядок вариантов ответа."""
    return item.prompt, item.code, item.options


def right(item: GeneratedItem) -> str:
    return str(item.options.index(item.answer)) if item.kind == "choice" else item.answer


def wrong(item: GeneratedItem) -> str:
    if item.kind == "choice":
        return str((item.options.index(item.answer) + 1) % len(item.options))
    return str(int(item.answer) + 1)


def respond(item: GeneratedItem, person: Person, rng: random.Random, leak: Leak | None) -> str:
    if leak and key(item) in leak:
        return leak[key(item)]
    ability = person.ability
    technologies = set(item.skills) & TECHNOLOGIES
    if technologies and not technologies & person.skills:
        ability -= person.stack_gap
    return (
        right(item) if rng.random() < probability(ability, item.level, item.kind) else wrong(item)
    )


def take(
    person: Person,
    level: int,
    rng: random.Random,
    leak: Leak | None = None,
    items: list[GeneratedItem] | None = None,
) -> tuple[list[GeneratedItem], Outcome]:
    """Один тест на уровень level; items — готовый набор (для сравнения со статичным тестом)."""
    focus = frozenset(person.declared)
    items = items or assemble(person.specialization.value, level, rng, focus)
    responses = [respond(item, person, rng, leak) for item in items]
    return items, evaluate(items, responses, level)


def confirmed_level(person: Person, rng: random.Random) -> tuple[int | None, Outcome | None]:
    """Грейд, который система подтвердит кандидату, пройдя путь по правилам повторов."""
    level = GRADE_ORDER.index(person.claimed_grade) + 1
    _, outcome = take(person, level, rng)
    if not outcome.passed:
        while level > 1:
            level -= 1
            _, outcome = take(person, level, rng)
            if outcome.passed:
                return level, outcome
        return None, None
    best = level, outcome
    while outcome.confident and level < len(GRADE_ORDER):
        level += 1
        _, outcome = take(person, level, rng)
        if not outcome.passed:
            break
        best = level, outcome
    return best
