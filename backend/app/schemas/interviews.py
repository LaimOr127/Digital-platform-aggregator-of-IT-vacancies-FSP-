import uuid
from datetime import datetime
from typing import Self

from pydantic import AwareDatetime, BaseModel, Field, model_validator

from app.models.enums import InterviewFormat, InterviewResult, InterviewStatus
from app.schemas.catalog import CandidateCardOut


class InterviewInviteIn(BaseModel):
    """Приглашение: 1-3 варианта времени, формат, кто проводит (руководитель)."""

    anon_id: uuid.UUID
    vacancy_id: uuid.UUID
    slots: list[AwareDatetime] = Field(min_length=1, max_length=3)
    duration_minutes: int = Field(default=60, ge=15, le=240)
    format: InterviewFormat
    location: str = Field(min_length=3, max_length=500, description="ссылка на встречу или адрес")
    interviewer: str = Field(min_length=2, max_length=120)
    message: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def _online_link(self) -> Self:
        if self.format == InterviewFormat.ONLINE and not self.location.startswith("https://"):
            raise ValueError("для онлайн-встречи нужна ссылка https://")
        return self


class InterviewAcceptIn(BaseModel):
    slot: AwareDatetime


class InterviewReasonIn(BaseModel):
    reason: str = Field(default="", max_length=500)


class InterviewCompleteIn(BaseModel):
    result: InterviewResult
    feedback: str = Field(default="", max_length=2000, description="видит кандидат")


class InterviewOut(BaseModel):
    id: uuid.UUID
    status: InterviewStatus
    result: InterviewResult | None
    company_name: str
    vacancy_title: str
    vacancy_id: uuid.UUID | None
    slots: list[datetime]
    duration_minutes: int
    scheduled_at: datetime | None
    format: InterviewFormat
    location: str
    interviewer: str
    message: str
    decline_reason: str | None
    feedback: str | None
    expires_at: datetime
    responded_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    offer_id: uuid.UUID | None = Field(default=None, description="оффер по итогам, если отправлен")


class EmployerInterviewOut(InterviewOut):
    candidate: CandidateCardOut | None = None
