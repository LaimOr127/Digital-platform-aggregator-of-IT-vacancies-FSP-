import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin, str_enum
from app.models.enums import Grade, OfferStatus, WorkFormat


class Offer(IdMixin, TimestampMixin, Base):
    """Оффер работодателя кандидату. Вакансия и вилка — снимок на момент отправки:
    кандидат видит, что ему предложили, даже если вакансию потом закрыли."""

    __tablename__ = "offers"
    __table_args__ = (
        # повтор запроса с тем же Idempotency-Key не создаёт второй оффер
        UniqueConstraint("company_id", "idempotency_key", name="company_idempotency"),
        # не больше одного ожидающего ответа оффера на пару вакансия-кандидат
        Index(
            "uq_offers_pending_pair",
            "vacancy_id",
            "profile_id",
            unique=True,
            postgresql_where=text("status = 'sent'"),
            sqlite_where=text("status = 'sent'"),
        ),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("employer_companies.id", ondelete="CASCADE"), index=True
    )
    vacancy_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("vacancies.id", ondelete="SET NULL"), default=None
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    status: Mapped[OfferStatus] = mapped_column(
        str_enum(OfferStatus, "offer_status"), default=OfferStatus.SENT, index=True
    )
    company_name: Mapped[str] = mapped_column(String(200))
    vacancy_title: Mapped[str] = mapped_column(String(160))
    grade: Mapped[Grade] = mapped_column(str_enum(Grade, "grade"))
    work_format: Mapped[WorkFormat] = mapped_column(str_enum(WorkFormat, "work_format"))
    city: Mapped[str | None] = mapped_column(String(100), default=None)
    salary_min: Mapped[int] = mapped_column(Integer)
    salary_max: Mapped[int] = mapped_column(Integer)
    message: Mapped[str] = mapped_column(Text, default="")
    decline_reason: Mapped[str | None] = mapped_column(String(500), default=None)
    # снимок контактов, переданный кандидатом при принятии (AES-GCM, привязка к офферу):
    # работодатель читает только его, доступа к профилю кандидата для этого не нужно
    contact_name_enc: Mapped[str | None] = mapped_column(Text, default=None)
    contacts_enc: Mapped[str | None] = mapped_column(Text, default=None)
    idempotency_key: Mapped[str | None] = mapped_column(String(64), default=None)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class ContactReveal(IdMixin, Base):
    """Журнал раскрытия контактов: кто, когда и по какому офферу видел ПДн кандидата."""

    __tablename__ = "contact_reveals"

    offer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("offers.id", ondelete="CASCADE"), index=True
    )
    viewer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
