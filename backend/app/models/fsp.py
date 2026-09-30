import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin


class FspVerification(IdMixin, TimestampMixin, Base):
    """Незавершённая привязка: запрос кода в ФСП. Одна на профиль (новый запрос заменяет)."""

    __tablename__ = "fsp_verifications"

    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), unique=True
    )
    athlete_id: Mapped[str] = mapped_column(String(32))
    request_id: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class FspLink(IdMixin, TimestampMixin, Base):
    """Подтверждённая привязка. Аккаунт ФСП принадлежит ровно одному профилю."""

    __tablename__ = "fsp_links"

    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), unique=True
    )
    athlete_id: Mapped[str] = mapped_column(String(32), unique=True)
    rank: Mapped[str | None] = mapped_column(String(16), default=None)
    region: Mapped[str | None] = mapped_column(String(120), default=None)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class FspAchievement(IdMixin, TimestampMixin, Base):
    """Результат соревнования из ФСП (копия для категоризации и паспорта)."""

    __tablename__ = "fsp_achievements"
    __table_args__ = (UniqueConstraint("profile_id", "external_id", name="profile_result"),)

    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True
    )
    external_id: Mapped[str] = mapped_column(String(64))
    discipline: Mapped[str] = mapped_column(String(32), index=True)
    competition_title: Mapped[str] = mapped_column(String(255))
    level: Mapped[str] = mapped_column(String(32))
    date: Mapped[str] = mapped_column(String(10))
    place: Mapped[int | None] = mapped_column(Integer, default=None)
    stage: Mapped[str] = mapped_column(String(32))
    role: Mapped[str] = mapped_column(String(32))
    team: Mapped[str | None] = mapped_column(String(120), default=None)
