import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin


class Passport(IdMixin, TimestampMixin, Base):
    """Паспорт навыков: снимок профиля, подписанный Ed25519. id — публичная ссылка."""

    __tablename__ = "passports"
    # не больше одного действующего паспорта на профиль (защита от параллельного выпуска)
    __table_args__ = (
        Index(
            "uq_passports_active_profile",
            "profile_id",
            unique=True,
            postgresql_where=text("revoked_at IS NULL"),
            sqlite_where=text("revoked_at IS NULL"),
        ),
    )

    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True
    )
    payload: Mapped[dict] = mapped_column(JSON)
    signature: Mapped[str] = mapped_column(Text)
    key_id: Mapped[str] = mapped_column(String(32))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
