"""Сборка теста и оценка уровня кандидата.

Тест на заявленный грейд g берёт задания трёх уровней сложности: g-1, g и g+1. Уровень
кандидата (theta, шкала 1–5, как у грейдов) оценивается по модели IRT с учётом угадывания
(3PL): P(верно) = c + (1 - c) / (1 + exp(-a (theta - b))), где b — уровень задания,
c — вероятность угадать (1/4 для выбора из четырёх вариантов). Оценка — апостериорное среднее
(EAP) с нейтральным априорным распределением: устойчиво и при всех верных/неверных ответах.

Грейд подтверждён, если theta >= g - 0.5; «уверенно» — если theta >= g + 0.5
(тогда кандидату сразу предлагается тест на грейд выше).
"""

import math
import random
from collections import defaultdict
from dataclasses import dataclass, field

from app.services.assessment import (  # noqa: F401 - модули регистрируют шаблоны
    bank_backend,
    bank_common,
    bank_data,
    bank_devops,
    bank_frontend,
    bank_general,
    bank_mobile,
    bank_qa,
    bank_security,
    bank_stack_dev,
    bank_stack_ops,
)
from app.services.assessment.items import COMMON, REGISTRY, Kind, Template
from app.services.specializations import SPECIALIZATIONS

ITEMS_TOTAL = 15
DISCRIMINATION = 1.7
GUESS: dict[Kind, float] = {"choice": 0.25, "number": 0.02}
PASS_MARGIN = 0.5
# минимум верных ответов для стажёра: ниже его уровня шкала не опускается, и одна оценка уровня
# пропускала случайные ответы примерно в половине попыток. 6 из 15 оставляют угадыванию ~1.3 %
# (5 из 15 — 6.3 %, выше допустимых 5 %); расчёт — docs/validation.md («Случайные ответы»)
MIN_CORRECT = {1: 6}
SCORE_SPAN = 2.0  # баллы 0..100 внутри категории покрывают уровни [g - 0.5, g + 1.5]
_GRID = [i / 50 for i in range(0, 301)]  # theta от 0 до 6
_PRIOR_MEAN, _PRIOR_SD = 3.0, 1.5
_SPECIFIC_WEIGHT, _SKILL_WEIGHT = 2.0, 2.0
# технологии стека (python, react, kafka…) в отличие от общих тем (алгоритмы, системный дизайн)
TECHNOLOGIES = frozenset(s for info in SPECIALIZATIONS.values() for s in info.skills)
# задание по технологии вне стека кандидата берётся, только если по стеку и общим темам не хватает:
# иначе знание чужого стека подменяет проверку уровня (так показала процедура оценки)
_OFF_STACK_WEIGHT = 0.1


@dataclass(frozen=True)
class GeneratedItem:
    template: str
    level: int
    topic: str
    skills: tuple[str, ...]
    kind: Kind
    prompt: str
    answer: str
    options: tuple[str, ...] = ()
    code: str | None = None

    def as_dict(self) -> dict:
        return {
            "template": self.template,
            "level": self.level,
            "topic": self.topic,
            "skills": list(self.skills),
            "kind": self.kind,
            "prompt": self.prompt,
            "answer": self.answer,
            "options": list(self.options),
            "code": self.code,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GeneratedItem":
        return cls(
            template=data["template"],
            level=data["level"],
            topic=data["topic"],
            skills=tuple(data["skills"]),
            kind=data["kind"],
            prompt=data["prompt"],
            answer=data["answer"],
            options=tuple(data["options"]),
            code=data.get("code"),
        )


def levels_for(target: int) -> list[int]:
    """Три соседних уровня вокруг заявленного; у крайних грейдов окно сдвигается внутрь шкалы."""
    start = min(max(target - 1, 1), 3)
    return [start, start + 1, start + 2]


def level_counts(target: int) -> list[tuple[int, int]]:
    """Сколько заданий каждого уровня. У стажёра уровня ниже нет, и в окне 1-2-3 треть заданий —
    уровня Middle: на них стажёр отвечает почти наугад. Поэтому у него больше заданий своего уровня
    (все 6 шаблонов банка) и меньше Middle: 6/6/3 вместо 5/5/5 (docs/validation.md)."""
    if target == 1:
        return [(1, 6), (2, 6), (3, 3)]
    levels = levels_for(target)
    return list(zip(levels, _split(ITEMS_TOTAL, len(levels)), strict=True))


def pool(specialization: str, level: int) -> list[Template]:
    return [
        t
        for t in REGISTRY.values()
        if t.level == level and (specialization in t.specializations or COMMON in t.specializations)
    ]


def assemble(
    specialization: str, target: int, rng: random.Random, focus: frozenset[str] = frozenset()
) -> list[GeneratedItem]:
    """Задания уровней target-1..target+1: выбор шаблонов случайный, с весом за специализацию
    и за навыки из focus (стек кандидата или навыки вакансии); каждое задание — новый вариант."""
    items: list[GeneratedItem] = []
    for level, count in level_counts(target):
        chosen = _weighted_sample(pool(specialization, level), count, rng, specialization, focus)
        items.extend(_instance(t, rng) for t in chosen)
    return items


def _split(total: int, parts: int) -> list[int]:
    base, extra = divmod(total, parts)
    return [base + (1 if i >= parts - extra else 0) for i in range(parts)]


def _weighted_sample(
    templates: list[Template],
    count: int,
    rng: random.Random,
    specialization: str,
    focus: frozenset[str],
) -> list[Template]:
    candidates = list(templates)
    chosen: list[Template] = []
    while candidates and len(chosen) < count:
        weights = [_weight(t, specialization, focus) for t in candidates]
        picked = rng.choices(candidates, weights=weights, k=1)[0]
        candidates.remove(picked)
        chosen.append(picked)
    return chosen


def _weight(template: Template, specialization: str, focus: frozenset[str]) -> float:
    weight = (
        1.0
        + (_SPECIFIC_WEIGHT if specialization in template.specializations else 0.0)
        + _SKILL_WEIGHT * len(template.skills & focus)
    )
    technologies = template.skills & TECHNOLOGIES
    if focus & TECHNOLOGIES and technologies and not technologies & focus:
        weight *= _OFF_STACK_WEIGHT
    return weight


def _instance(template: Template, rng: random.Random) -> GeneratedItem:
    item = template.generate(rng)
    return GeneratedItem(
        template=template.id,
        level=template.level,
        topic=template.topic,
        skills=tuple(sorted(template.skills)),
        kind=item.kind,
        prompt=item.prompt,
        answer=item.answer,
        options=item.options,
        code=item.code,
    )


def is_correct(item: GeneratedItem, response: str | None) -> bool:
    """Выбор — индекс варианта; число — целое (пробелы между разрядами допускаются)."""
    if response is None:
        return False
    value = response.strip().replace(" ", "").replace(" ", "")
    if item.kind == "choice":
        return (
            value.isdigit()
            and int(value) < len(item.options)
            and (item.options[int(value)] == item.answer)
        )
    try:
        return int(value) == int(item.answer)
    except ValueError:
        return False


def probability(theta: float, level: int, kind: Kind) -> float:
    guess = GUESS[kind]
    return guess + (1 - guess) / (1 + math.exp(-DISCRIMINATION * (theta - level)))


def estimate(responses: list[tuple[int, Kind, bool]]) -> tuple[float, float]:
    """EAP-оценка уровня и её стандартная ошибка по ответам (уровень, вид, верно ли)."""
    posterior = []
    for theta in _GRID:
        log_p = -((theta - _PRIOR_MEAN) ** 2) / (2 * _PRIOR_SD**2)
        for level, kind, correct in responses:
            p = probability(theta, level, kind)
            log_p += math.log(p if correct else 1 - p)
        posterior.append(log_p)
    peak = max(posterior)
    weights = [math.exp(v - peak) for v in posterior]
    total = sum(weights)
    mean = sum(t * w for t, w in zip(_GRID, weights, strict=True)) / total
    variance = sum((t - mean) ** 2 * w for t, w in zip(_GRID, weights, strict=True)) / total
    return mean, math.sqrt(variance)


@dataclass(frozen=True)
class Outcome:
    theta: float
    error: float
    correct: int
    total: int
    passed: bool
    confident: bool
    score: int  # 0..100: положение внутри категории (для ранжирования)
    topics: dict[str, list[int]] = field(default_factory=dict)  # тема -> [верно, всего]
    skills: tuple[str, ...] = ()  # навыки, подтверждённые ответами


def level_from_score(level: int, score: int) -> float:
    """Уровень кандидата по подтверждённому грейду и баллам — обратная к расчёту score."""
    return level - PASS_MARGIN + SCORE_SPAN * score / 100


def evaluate(items: list[GeneratedItem], responses: list[str | None], target: int) -> Outcome:
    marks = [is_correct(item, r) for item, r in zip(items, responses, strict=True)]
    theta, error = estimate([(i.level, i.kind, m) for i, m in zip(items, marks, strict=True)])
    topics: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    per_skill: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for item, mark in zip(items, marks, strict=True):
        topics[item.topic][0] += int(mark)
        topics[item.topic][1] += 1
        for skill in item.skills:
            per_skill[skill][0] += int(mark)
            per_skill[skill][1] += 1
    passed = theta >= target - PASS_MARGIN and sum(marks) >= MIN_CORRECT.get(target, 0)
    confident = target < 5 and theta >= target + PASS_MARGIN
    score = round(100 * min(1.0, max(0.0, (theta - (target - PASS_MARGIN)) / SCORE_SPAN)))
    skills = tuple(sorted(s for s, (ok, n) in per_skill.items() if ok and ok * 2 >= n))
    return Outcome(
        theta=round(theta, 2),
        error=round(error, 2),
        correct=sum(marks),
        total=len(items),
        passed=passed,
        confident=confident,
        score=score if passed else 0,
        topics=dict(topics),
        skills=skills,
    )
