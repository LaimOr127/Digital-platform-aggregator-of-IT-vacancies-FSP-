import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin, str_enum
from app.models.candidate import Skill
from app.models.enums import Grade, Specialization, VacancyStatus, WorkFormat

vacancy_skills = Table(
    "vacancy_skills",
    Base.metadata,
    Column("vacancy_id", ForeignKey("vacancies.id", ondelete="CASCADE"), primary_key=True),
    Column("skill_id", ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True, index=True),
)


class Vacancy(IdMixin, TimestampMixin, Base):
    """Вакансия. Вилка обязательна (принцип «честного найма»), срок жизни — 14 дней."""

    __tablename__ = "vacancies"
    __table_args__ = (
        CheckConstraint("salary_min > 0 AND salary_max >= salary_min", name="salary_range"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("employer_companies.id", ondelete="CASCADE"), index=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    grade: Mapped[Grade] = mapped_column(str_enum(Grade, "grade"), index=True)
    # специализация + грейд вакансии = категория кандидатов, из которой строится подборка
    specialization: Mapped[Specialization | None] = mapped_column(
        str_enum(Specialization, "specialization"), default=None, index=True
    )
    work_format: Mapped[WorkFormat] = mapped_column(str_enum(WorkFormat, "work_format"))
    city: Mapped[str | None] = mapped_column(String(100), default=None)
    salary_min: Mapped[int] = mapped_column(Integer)
    salary_max: Mapped[int] = mapped_column(Integer)
    status: Mapped[VacancyStatus] = mapped_column(
        str_enum(VacancyStatus, "vacancy_status"), default=VacancyStatus.DRAFT, index=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    skills: Mapped[list[Skill]] = relationship(secondary=vacancy_skills, lazy="selectin")
