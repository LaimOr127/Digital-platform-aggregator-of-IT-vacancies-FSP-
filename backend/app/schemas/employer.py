import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, HttpUrl

from app.models.enums import CompanyStatus, Grade, Specialization, VacancyStatus, WorkFormat
from app.schemas.candidate import SkillSlug
from app.schemas.common import ORMModel, SalaryRangeMixin, SkillOut
from app.services.cities import City


class CompanyOut(ORMModel):
    id: uuid.UUID
    name: str
    inn: str | None
    website: str | None
    status: CompanyStatus
    created_at: datetime
    description: str = ""
    industry: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    contact_telegram: str | None = None


class CompanyUpdateIn(BaseModel):
    """Профиль компании: описание, направление деятельности, контакты для кандидатов."""

    name: str | None = Field(default=None, min_length=2, max_length=200)
    website: HttpUrl | None = None
    description: str | None = Field(default=None, max_length=4000)
    industry: str | None = Field(default=None, max_length=120)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, max_length=32)
    contact_telegram: str | None = Field(default=None, max_length=64)


class VacancyUpdateIn(SalaryRangeMixin):
    title: str | None = Field(default=None, min_length=3, max_length=160)
    description: str | None = Field(default=None, max_length=10_000)
    grade: Grade | None = None
    specialization: Specialization | None = None
    work_format: WorkFormat | None = None
    city: City | None = None
    skills: list[SkillSlug] | None = Field(default=None, max_length=30)


class VacancyCreateIn(VacancyUpdateIn):
    """Создание: вилка обязательна (честный найм)."""

    title: str = Field(min_length=3, max_length=160)
    grade: Grade
    specialization: Specialization = Field(description="по ней и грейду строится подборка")
    work_format: WorkFormat
    salary_min: int = Field(gt=0, le=10_000_000)
    salary_max: int = Field(gt=0, le=10_000_000)


class VacancyOut(ORMModel):
    id: uuid.UUID
    company_id: uuid.UUID
    title: str
    description: str
    grade: Grade
    specialization: Specialization | None
    work_format: WorkFormat
    city: str | None
    salary_min: int
    salary_max: int
    status: VacancyStatus
    expires_at: datetime | None
    created_at: datetime
    skills: list[SkillOut]


class CompanyStatusIn(BaseModel):
    status: CompanyStatus
    reason: str = Field(default="", max_length=500)
