import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import (
    Education,
    Grade,
    OfferStatus,
    SearchStatus,
    Specialization,
    VerificationTier,
    WorkFormat,
)
from app.schemas.common import SalaryRangeMixin


class CatalogCategoryOut(BaseModel):
    """Категория кандидатов: специализация x подтверждённый тестом грейд."""

    slug: str
    title: str
    specialization: Specialization
    grade: Grade
    candidates: int


class FspCategoryOut(BaseModel):
    """Категория достижений ФСП: дисциплина x уровень результатов."""

    slug: str
    discipline: str
    tier: str
    title: str
    candidates: int


class CandidateCategoryOut(BaseModel):
    slug: str
    tier: str
    title: str


class CategoryBriefOut(BaseModel):
    slug: str
    title: str


class MatchFactorOut(BaseModel):
    key: str
    label: str
    weight: int
    share: float = Field(ge=0, le=1)
    detail: str


class MatchOut(BaseModel):
    """Оценка с объяснением: соответствие вакансии или сила профиля внутри категории."""

    score: int = Field(ge=0, le=100)
    factors: list[MatchFactorOut]


class CandidateCardOut(BaseModel):
    """Анонимная карточка кандидата: без имени, контактов, ID ФСП и названий соревнований."""

    anon_id: uuid.UUID
    title: str | None
    specialization: Specialization | None
    category: CategoryBriefOut | None = Field(description="категория по итогам теста")
    grade: Grade | None = Field(description="заявленный кандидатом")
    confirmed_grade: Grade | None = Field(description="подтверждённый тестом")
    assessment_score: int | None
    experience_years: int | None
    work_formats: list[WorkFormat]
    city: str | None
    relocation: bool = False
    education: Education | None = None
    salary_min: int | None
    salary_max: int | None
    verification_tier: VerificationTier
    search_status: SearchStatus
    skills: list[str]
    confirmed_skills: list[str] = Field(description="навыки, подтверждённые ответами теста")
    fsp_categories: list[CandidateCategoryOut]
    achievements: list[str]
    about: str | None
    last_activity_at: datetime | None
    match: MatchOut | None = Field(default=None, description="соответствие вакансии")
    strength: MatchOut | None = Field(default=None, description="сила профиля в категории")


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
