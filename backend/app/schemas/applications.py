import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import (
    ApplicationDirection,
    ApplicationStatus,
    Grade,
    Specialization,
    WorkFormat,
)
from app.schemas.catalog import CandidateCardOut, MatchOut
from app.schemas.common import SalaryRangeMixin
from app.services.cities import City


class InvitationIn(SalaryRangeMixin):
    """Приглашение кандидату: описание предложения, вилка, способ связи. Вакансия — по желанию."""

    anon_id: uuid.UUID
    vacancy_id: uuid.UUID | None = None
    title: str = Field(min_length=3, max_length=160, description="должность")
    description: str = Field(min_length=10, max_length=4000, description="описание предложения")
    grade: Grade
    work_format: WorkFormat
    city: City | None = None
    salary_min: int = Field(gt=0, le=10_000_000)
    salary_max: int = Field(gt=0, le=10_000_000)
    contact_method: str = Field(
        min_length=3, max_length=300, description="как связаться: Telegram, почта, телефон"
    )


class ResponseIn(BaseModel):
    message: str = Field(default="", max_length=2000, description="сопроводительное письмо")


class AcceptResponseIn(BaseModel):
    contact_method: str = Field(min_length=3, max_length=300, description="как связаться")


class DeclineIn(BaseModel):
    reason: str = Field(default="", max_length=500)


class CompanyBriefOut(BaseModel):
    """Профиль компании глазами кандидата."""

    name: str
    industry: str | None
    website: str | None
    description: str


class ApplicationBase(BaseModel):
    id: uuid.UUID
    direction: ApplicationDirection
    status: ApplicationStatus
    vacancy_id: uuid.UUID | None
    title: str
    description: str
    grade: Grade
    work_format: WorkFormat
    city: str | None
    salary_min: int
    salary_max: int
    message: str
    decline_reason: str | None
    expires_at: datetime
    viewed_at: datetime | None
    responded_at: datetime | None
    created_at: datetime


class ApplicationOut(ApplicationBase):
    """Для кандидата: компания и способ связи с ней (по отклику — после ответа компании)."""

    company: CompanyBriefOut
    contact_method: str | None


class EmployerApplicationOut(ApplicationBase):
    """Для компании: анонимная карточка кандидата; контакты — отдельным запросом."""

    contact_method: str | None
    contacts_available: bool
    candidate: CandidateCardOut | None = Field(
        default=None, description="карточка, если кандидат виден в каталоге"
    )


class BoardVacancyOut(BaseModel):
    """Вакансия в ленте кандидата: соответствие его профилю и статус его отклика."""

    id: uuid.UUID
    title: str
    description: str
    specialization: Specialization | None
    grade: Grade
    work_format: WorkFormat
    city: str | None
    salary_min: int
    salary_max: int
    skills: list[str]
    expires_at: datetime | None
    company: CompanyBriefOut
    match: MatchOut
    application_status: ApplicationStatus | None = Field(
        description="статус отклика или приглашения по этой вакансии"
    )
