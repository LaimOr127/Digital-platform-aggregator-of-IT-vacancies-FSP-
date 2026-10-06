import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin, str_enum
from app.models.enums import UserRole


class User(IdMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(str_enum(UserRole, "user_role"), index=True)
    is_superadmin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    # согласие на обработку персональных данных и публикацию анонимного профиля (152-ФЗ)
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    # 2FA (TOTP) — обязательна для администраторов; секрет зашифрован (AES-GCM)
    totp_secret_enc: Mapped[str | None] = mapped_column(Text, default=None)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    totp_last_step: Mapped[int | None] = mapped_column(BigInteger, default=None)
    # одноразовый код подключения 2FA (выдаёт только CLI): без него пароль не позволяет
    # привязать свой аутентификатор; хранится хешем
    totp_enroll_hash: Mapped[str | None] = mapped_column(String(64), default=None)
    totp_enroll_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    # неверные коды подряд -> временная блокировка (в БД: переживает рестарт и сброс лимитера)
    totp_failures: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    totp_locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )


class RefreshToken(IdMixin, TimestampMixin, Base):
    """Refresh-токен с ротацией. family_id связывает цепочку: повторное использование
    отозванного токена отзывает всю семью (признак кражи)."""

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    family_id: Mapped[uuid.UUID] = mapped_column(index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
