import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin, str_enum
from app.models.enums import ApplicationDirection, ApplicationStatus, Grade, WorkFormat

OPEN_STATUSES = "status IN ('sent', 'viewed')"


class Application(IdMixin, TimestampMixin, Base):
    """Выход на контакт: приглашение компании кандидату или отклик кандидата на вакансию.

    Приглашение содержит описание предложения, вилку, название компании и способ связи;
    вакансия не обязательна. Контакты кандидата (снимок, AES-GCM с привязкой к записи)
    компания получает, когда кандидат принял приглашение или откликнулся сам.
    """

    __tablename__ = "applications"
    __table_args__ = (
        CheckConstraint("salary_min > 0 AND salary_max >= salary_min", name="salary_range"),
        # одно открытое обращение на пару компания-кандидат: без засыпания приглашениями
        Index(
            "uq_applications_open_pair",
            "company_id",
            "profile_id",
            unique=True,
            postgresql_where=text(OPEN_STATUSES),
            sqlite_where=text(OPEN_STATUSES),
        ),
    )

    direction: Mapped[ApplicationDirection] = mapped_column(
        str_enum(ApplicationDirection, "application_direction"), index=True
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("employer_companies.id", ondelete="CASCADE"), index=True
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True
    )
    vacancy_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("vacancies.id", ondelete="SET NULL"), default=None, index=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        str_enum(ApplicationStatus, "application_status"),
        default=ApplicationStatus.SENT,
        index=True,
    )
    # предложение — снимок на момент отправки (вакансию могли изменить или закрыть)
    company_name: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    grade: Mapped[Grade] = mapped_column(str_enum(Grade, "grade"))
    work_format: Mapped[WorkFormat] = mapped_column(str_enum(WorkFormat, "work_format"))
    city: Mapped[str | None] = mapped_column(String(100), default=None)
    salary_min: Mapped[int] = mapped_column(Integer)
    salary_max: Mapped[int] = mapped_column(Integer)
    # как связаться с компанией: виден кандидату с самого начала (часть приглашения)
    contact_method: Mapped[str | None] = mapped_column(String(300), default=None)
    message: Mapped[str] = mapped_column(Text, default="")  # сопроводительное письмо отклика
    decline_reason: Mapped[str | None] = mapped_column(String(500), default=None)
    contact_name_enc: Mapped[str | None] = mapped_column(Text, default=None)
    contacts_enc: Mapped[str | None] = mapped_column(Text, default=None)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
