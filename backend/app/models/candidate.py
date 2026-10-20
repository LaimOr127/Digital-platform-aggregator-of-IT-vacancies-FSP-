import datetime as dt
import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    false,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin, str_enum
from app.models.enums import Education, Grade, SearchStatus, Specialization, VerificationTier

profile_skills = Table(
    "profile_skills",
    Base.metadata,
    Column("profile_id", ForeignKey("candidate_profiles.id", ondelete="CASCADE"), primary_key=True),
    Column("skill_id", ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True, index=True),
)


class Skill(IdMixin, Base):
    __tablename__ = "skills"

    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(100))


class CandidateProfile(IdMixin, TimestampMixin, Base):
    """Профиль кандидата. Имя и контакты хранятся зашифрованными (AES-GCM);
    anon_id — публичный идентификатор для работодателя, не связанный с user_id."""

    __tablename__ = "candidate_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    anon_id: Mapped[uuid.UUID] = mapped_column(unique=True, default=uuid.uuid4)
    full_name_enc: Mapped[str | None] = mapped_column(Text, default=None)
    contacts_enc: Mapped[str | None] = mapped_column(Text, default=None)

    title: Mapped[str | None] = mapped_column(String(120), default=None)
    about: Mapped[str | None] = mapped_column(Text, default=None)
    grade: Mapped[Grade | None] = mapped_column(str_enum(Grade, "grade"), default=None, index=True)
    # форматы работы (WorkFormat): можно несколько — например, удалённо и гибрид
    work_formats: Mapped[list[str]] = mapped_column(JSON, default=list)
    city: Mapped[str | None] = mapped_column(String(100), default=None)
    relocation: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    education: Mapped[Education | None] = mapped_column(
        str_enum(Education, "education"), default=None
    )
    salary_min: Mapped[int | None] = mapped_column(Integer, default=None)
    salary_max: Mapped[int | None] = mapped_column(Integer, default=None)
    verification_tier: Mapped[VerificationTier] = mapped_column(
        str_enum(VerificationTier, "verification_tier"), default=VerificationTier.SELF_DECLARED
    )
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    # приватность: что из профиля видит работодатель в анонимной карточке
    show_fsp: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    show_salary: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    show_about: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    # статус поиска: «не ищу» — профиль не в каталоге, офферы не приходят
    search_status: Mapped[SearchStatus] = mapped_column(
        str_enum(SearchStatus, "search_status"),
        default=SearchStatus.OPEN,
        server_default=SearchStatus.OPEN.value,
    )

    # опрос при регистрации: специализация, отрасли, роли, стаж — основа категории
    specialization: Mapped[Specialization | None] = mapped_column(
        str_enum(Specialization, "specialization"), default=None, index=True
    )
    experience_years: Mapped[float | None] = mapped_column(Float, default=None)  # лет, 3.4
    industries: Mapped[list[str]] = mapped_column(JSON, default=list)
    roles: Mapped[list[str]] = mapped_column(JSON, default=list)
    soft_skills: Mapped[list[str]] = mapped_column(JSON, default=list)  # ключи справочника и свои
    custom_skills: Mapped[list[str]] = mapped_column(JSON, default=list)  # навыки вне справочника
    survey_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    # категория = специализация x грейд, подтверждённый тестом (grade — заявленный кандидатом)
    confirmed_grade: Mapped[Grade | None] = mapped_column(
        str_enum(Grade, "confirmed_grade"), default=None, index=True
    )
    grade_confirmed_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    assessment_score: Mapped[int | None] = mapped_column(Integer, default=None)
    confirmed_skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    # последнее действие, подтверждающее актуальность профиля (тест, решение задачи)
    last_activity_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )

    skills: Mapped[list[Skill]] = relationship(secondary=profile_skills, lazy="selectin")
