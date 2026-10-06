import uuid
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, StringConstraints, field_validator

from app.models.enums import (
    Education,
    Grade,
    SearchStatus,
    Specialization,
    VerificationTier,
    WorkFormat,
)
from app.schemas.common import SalaryRangeMixin, SkillOut
from app.services.cities import City
from app.services.specializations import ROLES, known_keys

SkillSlug = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9+#.\-]{0,63}$")]
# свой навык или качество, которого нет в справочнике: свободный текст
FreeText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]


class Contacts(BaseModel):
    phone: str | None = Field(default=None, max_length=32)
    telegram: str | None = Field(default=None, max_length=64)
    email: EmailStr | None = Field(default=None, max_length=254)


class ProfileUpdateIn(SalaryRangeMixin):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    contacts: Contacts | None = None
    title: str | None = Field(default=None, max_length=120)
    about: str | None = Field(default=None, max_length=4000)
    grade: Grade | None = None
    work_formats: list[WorkFormat] | None = Field(
        default=None, max_length=3, description="можно несколько: удалённо и гибрид"
    )
    city: City | None = None
    relocation: bool | None = Field(default=None, description="готов к переезду")
    education: Education | None = None
    is_hidden: bool | None = None
    search_status: SearchStatus | None = None
    show_fsp: bool | None = None
    show_salary: bool | None = None
    show_about: bool | None = None
    skills: list[SkillSlug] | None = Field(default=None, max_length=50, description="slug навыков")
    custom_skills: list[FreeText] | None = Field(
        default=None, max_length=20, description="навыки, которых нет в справочнике"
    )
    experience_years: int | None = Field(default=None, ge=0, le=50)
    roles: list[str] | None = Field(
        default=None, max_length=5, description="см. /public/dictionaries"
    )
    soft_skills: list[FreeText] | None = Field(
        default=None, max_length=10, description="ключи справочника или свой текст"
    )

    @field_validator("roles")
    @classmethod
    def _roles(cls, value: list[str] | None) -> list[str] | None:
        return None if value is None else known_keys(value, ROLES, "роль")

    @field_validator("work_formats", "custom_skills", "soft_skills")
    @classmethod
    def _unique(cls, value: list | None) -> list | None:
        return None if value is None else list(dict.fromkeys(value))


class ProfileOut(BaseModel):
    """Профиль глазами владельца: расшифрованные имя и контакты."""

    anon_id: uuid.UUID
    full_name: str | None
    contacts: Contacts
    title: str | None
    about: str | None
    grade: Grade | None
    work_formats: list[WorkFormat] = []
    city: str | None
    relocation: bool = False
    education: Education | None = None
    salary_min: int | None
    salary_max: int | None
    verification_tier: VerificationTier
    is_hidden: bool
    search_status: SearchStatus
    skills: list[SkillOut]
    custom_skills: list[str] = []
    # приватность: что видит работодатель в анонимной карточке
    show_fsp: bool = True
    show_salary: bool = True
    show_about: bool = True
    # из опроса и теста (меняются через /candidate/assessment)
    specialization: Specialization | None = None
    confirmed_grade: Grade | None = None
    assessment_score: int | None = None
    experience_years: int | None = None
    industries: list[str] = []
    roles: list[str] = []
    soft_skills: list[str] = []
