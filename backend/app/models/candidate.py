import uuid

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin, TimestampMixin, str_enum
from app.models.enums import Grade, SearchStatus, VerificationTier, WorkFormat

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
    work_format: Mapped[WorkFormat | None] = mapped_column(
        str_enum(WorkFormat, "work_format"), default=None
    )
    city: Mapped[str | None] = mapped_column(String(100), default=None)
    salary_min: Mapped[int | None] = mapped_column(Integer, default=None)
    salary_max: Mapped[int | None] = mapped_column(Integer, default=None)
    verification_tier: Mapped[VerificationTier] = mapped_column(
        str_enum(VerificationTier, "verification_tier"), default=VerificationTier.SELF_DECLARED
    )
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    # статус поиска: «не ищу» — профиль не в каталоге, офферы не приходят
    search_status: Mapped[SearchStatus] = mapped_column(
        str_enum(SearchStatus, "search_status"),
        default=SearchStatus.OPEN,
        server_default=SearchStatus.OPEN.value,
    )

    skills: Mapped[list[Skill]] = relationship(secondary=profile_skills, lazy="selectin")
