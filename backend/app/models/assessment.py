import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin, str_enum
from app.models.enums import AssessmentResult, AssessmentStatus, Grade, Specialization


class Assessment(IdMixin, TimestampMixin, Base):
    """Попытка теста на грейд. items — сгенерированные для этой попытки задания вместе
    с правильными ответами: хранятся только на сервере, кандидату ответы не отдаются."""

    __tablename__ = "assessments"

    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True
    )
    specialization: Mapped[Specialization] = mapped_column(
        str_enum(Specialization, "specialization")
    )
    grade: Mapped[Grade] = mapped_column(str_enum(Grade, "grade"))
    status: Mapped[AssessmentStatus] = mapped_column(
        str_enum(AssessmentStatus, "assessment_status"), default=AssessmentStatus.IN_PROGRESS
    )
    seed: Mapped[str] = mapped_column(String(32))
    items: Mapped[list[dict]] = mapped_column(JSON)
    responses: Mapped[list[str | None] | None] = mapped_column(JSON, default=None)
    survey: Mapped[dict] = mapped_column(JSON, default=dict)  # снимок опроса на момент теста
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    result: Mapped[AssessmentResult | None] = mapped_column(
        str_enum(AssessmentResult, "assessment_result"), default=None
    )
    theta: Mapped[float | None] = mapped_column(Float, default=None)
    theta_error: Mapped[float | None] = mapped_column(Float, default=None)
    correct: Mapped[int | None] = mapped_column(Integer, default=None)
    score: Mapped[int | None] = mapped_column(Integer, default=None)
    confident: Mapped[bool] = mapped_column(Boolean, default=False)
    topics: Mapped[dict | None] = mapped_column(JSON, default=None)
