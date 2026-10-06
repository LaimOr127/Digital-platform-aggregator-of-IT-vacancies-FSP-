"""Подключённая языковая модель (настраивает суперадмин в интерфейсе).

Ключ API хранится зашифрованным (AES-GCM, привязка к записи) и никогда не отдаётся
наружу — интерфейс видит только последние символы. Активна не больше одной модели.
"""

from sqlalchemy import Boolean, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin, str_enum
from app.models.enums import AiProviderKind


class AiProvider(IdMixin, TimestampMixin, Base):
    __tablename__ = "ai_providers"
    __table_args__ = (
        Index(
            "uq_ai_providers_active",
            "is_active",
            unique=True,
            postgresql_where=text("is_active"),
            sqlite_where=text("is_active"),
        ),
    )

    name: Mapped[str] = mapped_column(String(80))
    kind: Mapped[AiProviderKind] = mapped_column(str_enum(AiProviderKind, "ai_provider_kind"))
    base_url: Mapped[str] = mapped_column(String(300))
    model: Mapped[str] = mapped_column(String(120))
    api_key_enc: Mapped[str | None] = mapped_column(Text, default=None)
    key_hint: Mapped[str | None] = mapped_column(String(8), default=None)  # последние символы
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
