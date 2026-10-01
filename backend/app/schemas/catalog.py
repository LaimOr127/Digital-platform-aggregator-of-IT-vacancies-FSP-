import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import Grade, OfferStatus, SearchStatus, VerificationTier, WorkFormat
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


class MatchFactorOut(BaseModel):
    key: str
    label: str
    weight: int
    share: float = Field(ge=0, le=1)
    detail: str


class MatchOut(BaseModel):
    """Соответствие вакансии: процент и вклад каждого фактора."""

    score: int = Field(ge=0, le=100)
    factors: list[MatchFactorOut]


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
    search_status: SearchStatus
    skills: list[str]
    categories: list[CandidateCategoryOut]
    achievements: list[str]
    about: str | None
    match: MatchOut | None = None


class OfferCreateIn(SalaryRangeMixin):
    """Оффер — по итогам успешного собеседования. Вилка обязательна (честный найм)."""

    interview_id: uuid.UUID
    salary_min: int = Field(gt=0, le=10_000_000)
    salary_max: int = Field(gt=0, le=10_000_000)
    message: str = Field(default="", max_length=2000)


class OfferDeclineIn(BaseModel):
    reason: str = Field(default="", max_length=500)


class OfferOut(BaseModel):
    id: uuid.UUID
    interview_id: uuid.UUID | None = None
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
