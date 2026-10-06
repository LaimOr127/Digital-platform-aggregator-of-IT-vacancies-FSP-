"""Шаблоны заданий: каждое задание генерируется заново для каждой попытки.

Два вида шаблонов, оба устойчивы к утечке заданий между кандидатами:
- вычислительный: код или условие с параметрами (числа, данные, порядок операций выбираются
  случайно) — ответ другой попытки бесполезен, нужно понимать, как получить результат;
- пул утверждений: «какое утверждение верно / неверно» — 1 + 3 варианта из пулов верных и
  неверных утверждений, сотни сочетаний; выучить пул целиком — значит выучить тему.

Шаблон знает свой уровень сложности (1 — стажёр … 5 — lead), специализации и навыки:
по ним собирается тест для грейда и для конкретной вакансии.
"""

import random
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

from app.models.enums import Specialization

Kind = Literal["choice", "number"]
COMMON = "common"  # задание подходит всем специализациям


@dataclass(frozen=True)
class Item:
    """Сгенерированное задание. answer — только на сервере, кандидату не отдаётся."""

    prompt: str
    answer: str
    kind: Kind = "choice"
    options: tuple[str, ...] = ()
    code: str | None = None


@dataclass(frozen=True)
class Template:
    id: str
    level: int
    topic: str
    specializations: frozenset[str]
    skills: frozenset[str]
    build: Callable[[random.Random], Item] = field(compare=False)

    def generate(self, rng: random.Random) -> Item:
        return self.build(rng)


REGISTRY: dict[str, Template] = {}


def register(template: Template) -> Template:
    if template.id in REGISTRY:
        raise ValueError(f"duplicate template {template.id}")
    if not 1 <= template.level <= 5:
        raise ValueError(f"bad level in {template.id}")
    REGISTRY[template.id] = template
    return template


def _specs(specs: tuple[Specialization | str, ...]) -> frozenset[str]:
    return frozenset(s.value if isinstance(s, Specialization) else s for s in specs)


def computed(
    template_id: str,
    level: int,
    topic: str,
    specs: tuple[Specialization | str, ...],
    skills: tuple[str, ...] = (),
) -> Callable[[Callable[[random.Random], Item]], Callable[[random.Random], Item]]:
    """Декоратор вычислительного шаблона: функция получает генератор случайных чисел."""

    def wrap(build: Callable[[random.Random], Item]) -> Callable[[random.Random], Item]:
        register(Template(template_id, level, topic, _specs(specs), frozenset(skills), build))
        return build

    return wrap


def statements(
    template_id: str,
    level: int,
    topic: str,
    specs: tuple[Specialization | str, ...],
    skills: tuple[str, ...],
    true: tuple[str, ...],
    false: tuple[str, ...],
) -> None:
    """Шаблон-пул: «какое утверждение верно» (1 верное + 3 неверных) или наоборот."""
    if len(true) < 1 or len(false) < 3:
        raise ValueError(f"pool too small in {template_id}")

    def build(rng: random.Random) -> Item:
        inverse = len(true) >= 3 and rng.random() < 0.5
        if inverse:
            answer = rng.choice(false)
            options = [answer, *rng.sample(true, 3)]
            prompt = f"{topic}: какое утверждение НЕВЕРНО?"
        else:
            answer = rng.choice(true)
            options = [answer, *rng.sample(false, 3)]
            prompt = f"{topic}: какое утверждение верно?"
        rng.shuffle(options)
        return Item(prompt=prompt, answer=answer, options=tuple(options))

    register(Template(template_id, level, topic, _specs(specs), frozenset(skills), build))


def number(value: int) -> str:
    """Число с пробелами между разрядами: 1 000 000."""
    return f"{value:,}".replace(",", "\u00a0")


def numeric(prompt: str, answer: int, code: str | None = None) -> Item:
    return Item(prompt=prompt, answer=str(answer), kind="number", code=code)


def choice(
    rng: random.Random, prompt: str, answer: str, wrong: list[str], code: str | None = None
) -> Item:
    """Выбор из 4 вариантов: правильный и три неправильных без повторов, порядок случайный."""
    distractors = [w for w in dict.fromkeys(wrong) if w != answer][:3]
    if len(distractors) < 3:
        raise ValueError("нужно три разных неверных варианта")
    options = [answer, *distractors]
    rng.shuffle(options)
    return Item(prompt=prompt, answer=answer, options=tuple(options), code=code)
