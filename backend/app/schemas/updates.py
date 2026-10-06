from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CandidateUpdatesOut(BaseModel):
    """Когда в разделе кабинета кандидата последний раз что-то менялось (null — событий нет)."""

    vacancies: datetime | None = Field(description="публикация самой свежей вакансии")
    invitations: datetime | None
    responses: datetime | None
    interviews: datetime | None
    offers: datetime | None
    seen: dict[str, datetime] = Field(
        default={}, description="когда раздел открывали (на любом устройстве): раздел -> время"
    )


class EmployerUpdatesOut(BaseModel):
    """Время последнего события по разделам кабинета компании и вакансии, которые пора продлить."""

    renew_due: int = Field(description="опубликованных вакансий, которые истекают в ближайшие дни")
    applications: datetime | None
    tasks: datetime | None = Field(description="последний ответ кандидата на задачу компании")
    interviews: datetime | None
    offers: datetime | None
    seen: dict[str, datetime] = Field(
        default={}, description="когда раздел открывали (на любом устройстве): раздел -> время"
    )


CandidateSection = Literal["vacancies", "invitations", "responses", "interviews", "offers"]
EmployerSection = Literal["applications", "tasks", "interviews", "offers"]


class CandidateSeenIn(BaseModel):
    section: CandidateSection


class EmployerSeenIn(BaseModel):
    section: EmployerSection
