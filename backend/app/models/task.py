import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin, str_enum
from app.models.enums import Grade, Specialization


class EmployerTask(IdMixin, TimestampMixin, Base):
    """Короткая задача от компании для кандидатов специализации (грейд — по желанию).

    Система предлагает кандидату одну задачу за период; ответ — решение или подход к решению.
    """

    __tablename__ = "employer_tasks"

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("employer_companies.id", ondelete="CASCADE"), index=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(Text)
    specialization: Mapped[Specialization] = mapped_column(
        str_enum(Specialization, "specialization"), index=True
    )
    grade: Mapped[Grade | None] = mapped_column(str_enum(Grade, "grade"), default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class TaskAnswer(IdMixin, TimestampMixin, Base):
    """Ответ кандидата. company_id, название задачи и компании — снимок: так RLS обеих таблиц
    не ссылаются друг на друга, а кандидат видит историю и после закрытия задачи."""

    __tablename__ = "task_answers"
    __table_args__ = (
        UniqueConstraint("task_id", "profile_id"),  # один ответ на задачу
        CheckConstraint("rating IS NULL OR rating BETWEEN 1 AND 5", name="rating_range"),
    )

    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("employer_tasks.id", ondelete="CASCADE"), index=True
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("employer_companies.id", ondelete="CASCADE"), index=True
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True
    )
    task_title: Mapped[str] = mapped_column(String(160))
    # текст задачи: кандидат перечитывает своё задание и после её снятия
    task_body: Mapped[str] = mapped_column(Text, default="")
    company_name: Mapped[str] = mapped_column(String(200))
    answer: Mapped[str] = mapped_column(Text)
    rating: Mapped[int | None] = mapped_column(Integer, default=None)  # оценка компании 1..5
