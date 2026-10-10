"""Черновик профиля из внешнего источника: интерфейс показывает его кандидату, тот выбирает,
какие поля перенести, и сохраняет профиль обычным запросом. Сервер ничего не меняет сам."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import Education, Grade, Specialization, WorkFormat
from app.schemas.candidate import Contacts
from app.schemas.common import SkillOut
from app.services.cities import canonical_city


class ProfileDraftOut(BaseModel):
    # город проверяется и при дополнении черновика ответом ИИ (присваивание поля)
    model_config = ConfigDict(validate_assignment=True)

    source: Literal["fsp", "resume"]
    full_name: str | None = None
    title: str | None = None
    about: str | None = None
    grade: Grade | None = Field(default=None, description="заявленный — подсказка для опроса")
    specialization: Specialization | None = Field(
        default=None, description="по стеку — подсказка для опроса; категорию определяет тест"
    )
    work_formats: list[WorkFormat] = Field(default_factory=list)
    relocation: bool | None = None
    education: Education | None = None
    city: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    experience_years: float | None = Field(default=None, description="лет, с одной десятой")
    roles: list[str] = Field(default_factory=list, description="ключи справочника ролей")
    soft_skills: list[str] = Field(
        default_factory=list, description="ключи справочника софт-скиллов или свой текст"
    )
    contacts: Contacts = Field(default_factory=Contacts)
    skills: list[SkillOut] = Field(default_factory=list)
    unknown_skills: list[str] = Field(default_factory=list, description="нет в справочнике")
    notes: list[str] = Field(default_factory=list, description="как получены значения")

    @field_validator("city")
    @classmethod
    def _city(cls, value: str | None) -> str | None:
        return canonical_city(value)  # профиль принимает только города из справочника
