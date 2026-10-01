import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import Grade, OfferStatus, VerificationTier, WorkFormat
from app.schemas.common import SalaryRangeMixin


class CatalogCategoryOut(BaseModel):
    slug: str
    discipline: str
    tier: str
    title: str
    candidates: int


class CandidateCategoryOut(BaseModel):
    slug: str
    tier: str
    title: str


class CandidateCardOut(BaseModel):
    """Анонимная карточка кандидата: без имени, контактов, ID ФСП и названий соревнований."""

    anon_id: uuid.UUID
    title: str | None
    grade: Grade | None
    work_format: WorkFormat | None
    city: str | None
    salary_min: int | None
    salary_max: int | None
    verification_tier: VerificationTier
    skills: list[str]
    categories: list[CandidateCategoryOut]
    achievements: list[str]
    about: str | None


class OfferCreateIn(SalaryRangeMixin):
    """Вилка обязательна и проверяется общим правилом (честный найм)."""

    anon_id: uuid.UUID
    vacancy_id: uuid.UUID
    salary_min: int = Field(gt=0, le=10_000_000)
    salary_max: int = Field(gt=0, le=10_000_000)
    message: str = Field(default="", max_length=2000)


class OfferDeclineIn(BaseModel):
    reason: str = Field(default="", max_length=500)


class OfferOut(BaseModel):
    id: uuid.UUID
    status: OfferStatus
    company_name: str
    vacancy_title: str
    grade: Grade
    work_format: WorkFormat
    city: str | None
    salary_min: int
    salary_max: int
    message: str
    decline_reason: str | None
    expires_at: datetime
    responded_at: datetime | None
    created_at: datetime


class EmployerOfferOut(OfferOut):
    candidate: CandidateCardOut | None = Field(
        default=None, description="карточка, если кандидат ещё виден в каталоге"
    )


class OfferContactsOut(BaseModel):
    full_name: str | None
    phone: str | None
    telegram: str | None
    email: str | None
