"""Хелперы, общие для сервисов профиля и вакансий."""

from typing import Protocol

from app.core.errors import AppError
from app.models import Base, Skill
from app.repositories.candidates import SkillRepository
from app.schemas.common import check_salary_range


class UnknownSkillsError(AppError):
    status_code, code = 422, "unknown_skills"


class NullNotAllowedError(AppError):
    status_code, code = 422, "null_not_allowed"


class HasSalary(Protocol):
    salary_min: int | None
    salary_max: int | None


def apply_fields(target: Base, changes: dict, fields: tuple[str, ...]) -> None:
    """Частичное обновление (PATCH): явный null очищает только nullable-колонки,
    для NOT NULL — ошибка 422 вместо IntegrityError/500."""
    columns = target.__table__.c  # type: ignore[attr-defined]
    for field in fields:
        if field not in changes:
            continue
        if changes[field] is None and not columns[field].nullable:
            raise NullNotAllowedError(f"поле {field} не может быть пустым")
        setattr(target, field, changes[field])


def apply_salary(target: HasSalary, changes: dict) -> None:
    """Частичное обновление вилки: проверяем итоговую пару, а не только пришедшие поля."""
    salary_min = changes.get("salary_min", target.salary_min)
    salary_max = changes.get("salary_max", target.salary_max)
    try:
        check_salary_range(salary_min, salary_max)
    except ValueError as exc:
        raise AppError(str(exc)) from exc
    apply_fields(target, changes, ("salary_min", "salary_max"))  # type: ignore[arg-type]


async def resolve_skills(skills: SkillRepository, slugs: list[str]) -> list[Skill]:
    """Слаги -> объекты навыков; неизвестные слаги — ошибка (словарь ведёт админ)."""
    found = await skills.by_slugs(list(dict.fromkeys(slugs)))
    missing = set(slugs) - {s.slug for s in found}
    if missing:
        raise UnknownSkillsError("неизвестные навыки: " + ", ".join(sorted(missing)))
    return found
