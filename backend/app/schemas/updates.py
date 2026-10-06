from datetime import datetime

from pydantic import BaseModel, Field


class CandidateUpdatesOut(BaseModel):
    """Когда в разделе кабинета кандидата последний раз что-то менялось (null — событий нет)."""

    vacancies: datetime | None = Field(description="публикация самой свежей вакансии")
    invitations: datetime | None
    responses: datetime | None
    interviews: datetime | None
    offers: datetime | None


class EmployerUpdatesOut(BaseModel):
    """Время последнего события по разделам кабинета компании и вакансии, которые пора продлить."""

    renew_due: int = Field(description="опубликованных вакансий, которые истекают в ближайшие дни")
    applications: datetime | None
    tasks: datetime | None = Field(description="последний ответ кандидата на задачу компании")
    interviews: datetime | None
    offers: datetime | None
