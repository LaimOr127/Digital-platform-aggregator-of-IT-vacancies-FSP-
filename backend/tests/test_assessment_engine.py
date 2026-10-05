"""Механика тестирования: банк параметрических заданий, оценка уровня, правила пересдачи."""

import random
from datetime import UTC, datetime, timedelta

import pytest

from app.models.enums import AssessmentResult, Grade, Specialization
from app.services.assessment.engine import (
    ITEMS_TOTAL,
    REGISTRY,
    TECHNOLOGIES,
    assemble,
    estimate,
    evaluate,
    is_correct,
    levels_for,
    pool,
)
from app.services.assessment.policy import AttemptRecord, decide
from app.services.specializations import SPECIALIZATIONS

NOW = datetime(2026, 10, 5, tzinfo=UTC)


@pytest.mark.parametrize("template_id", sorted(REGISTRY))
def test_every_template_generates_valid_varied_items(template_id):
    template, variants = REGISTRY[template_id], set()
    for seed in range(300):
        item = template.generate(random.Random(seed))
        if item.kind == "choice":
            assert len(set(item.options)) == 4 and item.answer in item.options
        else:
            int(item.answer)
        variants.add((item.prompt, item.code, item.options))
    # параметры меняются от попытки к попытке: выученный ответ чужой попытки не поможет
    assert len(variants) >= 10, template_id


def test_bank_covers_every_specialization_and_level():
    for specialization in Specialization:
        for level in range(1, 6):
            assert len(pool(specialization.value, level)) >= ITEMS_TOTAL // 3


def test_bank_covers_every_stack_technology():
    """Тест строится по стеку кандидата: каждая технология из стека специализации покрыта
    заданиями хотя бы на двух уровнях (иначе кандидат получает вопросы по чужому стеку —
    это занижало грейд в процедуре оценки, docs/validation.md)."""
    gaps = []
    for specialization, info in SPECIALIZATIONS.items():
        for skill in info.skills:
            levels = {t.level for t in pool_any_level(specialization.value) if skill in t.skills}
            if len(levels) < 2:
                gaps.append(f"{specialization.value}:{skill}:{sorted(levels)}")
    assert not gaps


def pool_any_level(specialization: str):
    return [t for level in range(1, 6) for t in pool(specialization, level)]


def test_test_brackets_claimed_grade():
    assert levels_for(3) == [2, 3, 4]
    assert levels_for(1) == [1, 2, 3] and levels_for(5) == [3, 4, 5]
    items = assemble("backend", 3, random.Random(1))
    assert len(items) == ITEMS_TOTAL and {i.level for i in items} == {2, 3, 4}
    assert len({i.template for i in items}) == ITEMS_TOTAL  # без повторов шаблона


def test_two_attempts_get_different_tasks():
    first = assemble("frontend", 2, random.Random("a"))
    second = assemble("frontend", 2, random.Random("b"))
    assert [(i.prompt, i.code, i.options) for i in first] != [
        (i.prompt, i.code, i.options) for i in second
    ]


def test_vacancy_skills_shift_the_selection():
    focused = [
        t
        for seed in range(40)
        for t in assemble("backend", 4, random.Random(seed), frozenset({"kafka"}))
    ]
    plain = [t for seed in range(40) for t in assemble("backend", 4, random.Random(seed))]
    share = lambda items: sum("kafka" in i.skills for i in items) / len(items)  # noqa: E731
    assert share(focused) >= share(plain)


def test_test_is_built_from_candidate_stack_and_general_topics():
    """Задания по технологиям вне стека — только если по стеку и общим темам не хватает."""
    stack = frozenset({"python", "postgresql"})
    off_stack = 0
    total = 0
    for seed in range(60):
        for item in assemble("backend", 3, random.Random(seed), stack):
            technologies = set(item.skills) & TECHNOLOGIES
            off_stack += bool(technologies) and not technologies & stack
            total += 1
    assert off_stack / total < 0.15


def test_answers_are_checked_on_the_server():
    choice = next(i for i in assemble("qa", 3, random.Random(7)) if i.kind == "choice")
    number = next(i for i in assemble("devops", 3, random.Random(7)) if i.kind == "number")
    right = str(choice.options.index(choice.answer))
    assert (
        is_correct(choice, right) and not is_correct(choice, "9") and not is_correct(choice, None)
    )
    assert is_correct(number, f" {number.answer} ") and not is_correct(number, "abc")


def test_ability_estimate_is_monotonic_and_bounded():
    def theta(correct: int) -> float:
        answers = [(3, "choice", i < correct) for i in range(15)]
        return estimate(answers)[0]

    values = [theta(n) for n in range(16)]
    assert values == sorted(values) and 0 < values[0] < values[-1] < 6


def test_evaluate_passes_fails_and_explains():
    items = assemble("backend", 3, random.Random(3))
    right = [str(i.options.index(i.answer)) if i.kind == "choice" else i.answer for i in items]
    strong = evaluate(items, right, 3)
    assert strong.passed and strong.confident and strong.score > 0 and strong.correct == 15
    assert sum(total for _, total in strong.topics.values()) == 15 and strong.skills
    weak = evaluate(items, [None] * 15, 3)
    assert not weak.passed and weak.score == 0 and weak.skills == ()


def _attempt(grade: Grade, result: AssessmentResult, days_ago: int, confident=False):
    return AttemptRecord(grade, result, confident, NOW - timedelta(days=days_ago))


def test_failed_grade_retry_waits_but_lower_grade_is_open():
    failed = [_attempt(Grade.SENIOR, AssessmentResult.FAILED, 1)]
    retry = decide(Grade.SENIOR, None, None, failed, NOW)
    assert not retry.allowed and retry.retry_at == NOW + timedelta(days=13)
    assert decide(Grade.MIDDLE, None, None, failed, NOW).allowed  # не понижаем, но даём шанс
    assert decide(Grade.SENIOR, None, None, failed, NOW + timedelta(days=14)).allowed


def test_confirmed_grade_changes_once_per_quarter():
    confirmed_at = NOW - timedelta(days=10)
    history = [_attempt(Grade.MIDDLE, AssessmentResult.PASSED, 10)]
    assert not decide(Grade.MIDDLE, Grade.MIDDLE, confirmed_at, history, NOW).allowed
    blocked = decide(Grade.SENIOR, Grade.MIDDLE, confirmed_at, history, NOW)
    assert not blocked.allowed and blocked.retry_at == confirmed_at + timedelta(days=90)
    assert decide(
        Grade.JUNIOR, Grade.MIDDLE, confirmed_at, history, NOW + timedelta(days=80)
    ).allowed


def test_confident_result_opens_next_grade_right_away():
    confirmed_at = NOW - timedelta(days=1)
    history = [_attempt(Grade.MIDDLE, AssessmentResult.PASSED, 1, confident=True)]
    assert decide(Grade.SENIOR, Grade.MIDDLE, confirmed_at, history, NOW).allowed
    assert not decide(Grade.LEAD, Grade.MIDDLE, confirmed_at, history, NOW).allowed
    late = NOW + timedelta(days=20)
    assert not decide(Grade.SENIOR, Grade.MIDDLE, confirmed_at, history, late).allowed
