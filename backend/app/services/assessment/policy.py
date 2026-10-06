"""Когда кандидату можно пройти тест на грейд.

- Грейд не понижается принудительно: не прошедший тест сразу может пройти тест на грейд ниже.
- Проваленный тест закрывает на 14 дней этот грейд и все грейды выше (иначе тест можно
  «перебирать» или перескочить через проваленный уровень); путь вниз открыт сразу.
- Подтверждённый грейд меняется (вверх или вниз) не чаще раза в 90 дней.
- Исключение: после уверенного результата 14 дней доступен тест на грейд выше — так сильный
  кандидат сразу калибруется, а не ждёт три месяца.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.models.enums import AssessmentResult, Grade
from app.services.specializations import level

CHANGE_COOLDOWN = timedelta(days=90)
RETRY_COOLDOWN = timedelta(days=14)
UPGRADE_WINDOW = timedelta(days=14)


@dataclass(frozen=True)
class AttemptRecord:
    grade: Grade
    result: AssessmentResult | None
    confident: bool
    finished_at: datetime | None


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str
    retry_at: datetime | None = None


def decide(
    target: Grade,
    confirmed: Grade | None,
    confirmed_at: datetime | None,
    attempts: list[AttemptRecord],
    now: datetime,
) -> Decision:
    """attempts — завершённые попытки текущей специализации, новые первыми."""
    if confirmed == target:
        return Decision(False, "грейд уже подтверждён")
    failed = next(
        (
            a
            for a in attempts
            if a.result == AssessmentResult.FAILED and level(a.grade) <= level(target)
        ),
        None,
    )
    if failed and failed.finished_at and now < failed.finished_at + RETRY_COOLDOWN:
        retry_at = failed.finished_at + RETRY_COOLDOWN
        reason = (
            "повторить тест на этот грейд можно позже"
            if failed.grade == target
            else "после неудачи грейды выше проваленного откроются позже"
        )
        return Decision(False, reason, retry_at)
    if confirmed is None or confirmed_at is None:
        return Decision(True, "")
    if _upgrade_offered(target, confirmed, attempts, now):
        return Decision(True, "уверенный результат: можно сразу подтвердить грейд выше")
    if now < confirmed_at + CHANGE_COOLDOWN:
        return Decision(
            False, "менять грейд можно раз в три месяца", confirmed_at + CHANGE_COOLDOWN
        )
    return Decision(True, "")


def _upgrade_offered(
    target: Grade, confirmed: Grade, attempts: list[AttemptRecord], now: datetime
) -> bool:
    if level(target) != level(confirmed) + 1:
        return False
    last = attempts[0] if attempts else None
    return bool(
        last
        and last.grade == confirmed
        and last.result == AssessmentResult.PASSED
        and last.confident
        and last.finished_at
        and now < last.finished_at + UPGRADE_WINDOW
    )
