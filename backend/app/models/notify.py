"""Уведомления: очередь исходящих писем (outbox) и одноразовые токены из писем.

Письмо ставится в очередь в той же транзакции, что и действие (регистрация, оффер), и
отправляется воркером: ответ API не зависит от почтового сервера и не выдаёт по времени,
зарегистрирован ли адрес. Параметры письма (ссылки с токенами, названия) зашифрованы
и стираются после отправки. Адресат определяется при отправке: письмо не уйдёт
заблокированному пользователю, а email не хранится в очереди.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin, str_enum, utcnow
from app.models.enums import EmailTokenPurpose, OutboxStatus, RecipientType


class OutboxMessage(IdMixin, TimestampMixin, Base):
    __tablename__ = "outbox_messages"

    kind: Mapped[str] = mapped_column(String(48))  # шаблон письма
    recipient_type: Mapped[RecipientType] = mapped_column(str_enum(RecipientType, "recipient_type"))
    recipient_id: Mapped[uuid.UUID]
    payload_enc: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[OutboxStatus] = mapped_column(
        str_enum(OutboxStatus, "outbox_status"), default=OutboxStatus.PENDING, index=True
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class EmailToken(IdMixin, TimestampMixin, Base):
    """Токен из письма (подтверждение почты, сброс пароля): хранится хешем, одноразовый."""

    __tablename__ = "email_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    purpose: Mapped[EmailTokenPurpose] = mapped_column(
        str_enum(EmailTokenPurpose, "email_token_purpose")
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
