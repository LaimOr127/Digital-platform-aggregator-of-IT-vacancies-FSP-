"""Собеседование: приглашение со слотами -> кандидат выбирает время -> встреча с руководителем
-> компания отмечает результат -> после успешного собеседования — оффер.

Вакансия и компания — снимок на момент приглашения: кандидат видит, куда его звали,
даже если вакансию закрыли. До принятия оффера кандидат для компании анонимен.
"""

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin, str_enum
from app.models.enums import InterviewFormat, InterviewResult, InterviewStatus

ACTIVE_STATUSES = "status IN ('invited', 'scheduled')"


class Interview(IdMixin, TimestampMixin, Base):
    __tablename__ = "interviews"
    __table_args__ = (
        # одно активное приглашение на пару вакансия-кандидат
        Index(
            "uq_interviews_active_pair",
            "vacancy_id",
            "profile_id",
            unique=True,
            postgresql_where=text(ACTIVE_STATUSES),
            sqlite_where=text(ACTIVE_STATUSES),
        ),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("employer_companies.id", ondelete="CASCADE"), index=True
    )
    vacancy_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("vacancies.id", ondelete="SET NULL"), default=None
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    # собеседование назначается после состоявшегося контакта (принятое приглашение или отклик)
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("applications.id", ondelete="SET NULL"), default=None, index=True
    )
    status: Mapped[InterviewStatus] = mapped_column(
        str_enum(InterviewStatus, "interview_status"), default=InterviewStatus.INVITED, index=True
    )
    result: Mapped[InterviewResult | None] = mapped_column(
        str_enum(InterviewResult, "interview_result"), default=None
    )
    company_name: Mapped[str] = mapped_column(String(200))
    vacancy_title: Mapped[str] = mapped_column(String(160))
    # предложенные слоты (ISO 8601, UTC) и выбранное кандидатом время
    slots: Mapped[list[str]] = mapped_column(JSON, default=list)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    format: Mapped[InterviewFormat] = mapped_column(str_enum(InterviewFormat, "interview_format"))
    location: Mapped[str] = mapped_column(String(500))  # ссылка на встречу или адрес
    interviewer: Mapped[str] = mapped_column(String(120))  # кто проводит: руководитель
    message: Mapped[str] = mapped_column(Text, default="")
    decline_reason: Mapped[str | None] = mapped_column(String(500), default=None)
    feedback: Mapped[str | None] = mapped_column(Text, default=None)  # видит кандидат
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
