"""Черновик профиля из внешнего источника: интерфейс показывает его кандидату, тот выбирает,
какие поля перенести, и сохраняет профиль обычным запросом. Сервер ничего не меняет сам."""

from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import Grade, WorkFormat
from app.schemas.candidate import Contacts
from app.schemas.common import SkillOut


class ProfileDraftOut(BaseModel):
    source: Literal["fsp", "resume"]
    full_name: str | None = None
    title: str | None = None
    about: str | None = None
    grade: Grade | None = None
    work_format: WorkFormat | None = None
    city: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    experience_years: int | None = None
    roles: list[str] = Field(default_factory=list, description="ключи справочника ролей")
    soft_skills: list[str] = Field(
        default_factory=list, description="ключи справочника софт-скиллов"
    )
    contacts: Contacts = Field(default_factory=Contacts)
    skills: list[SkillOut] = Field(default_factory=list)
    unknown_skills: list[str] = Field(default_factory=list, description="нет в справочнике")
    notes: list[str] = Field(default_factory=list, description="как получены значения")
