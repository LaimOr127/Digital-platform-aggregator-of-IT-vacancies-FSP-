import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin, str_enum
from app.models.enums import CompanyStatus, MemberRole


class EmployerCompany(IdMixin, TimestampMixin, Base):
    __tablename__ = "employer_companies"

    name: Mapped[str] = mapped_column(String(200))
    inn: Mapped[str | None] = mapped_column(String(12), default=None)
    website: Mapped[str | None] = mapped_column(String(255), default=None)
    # профиль компании: его видит кандидат в приглашении и вакансии
    description: Mapped[str] = mapped_column(Text, default="")
    industry: Mapped[str | None] = mapped_column(String(120), default=None)
    contact_email: Mapped[str | None] = mapped_column(String(254), default=None)
    contact_phone: Mapped[str | None] = mapped_column(String(32), default=None)
    contact_telegram: Mapped[str | None] = mapped_column(String(64), default=None)
    status: Mapped[CompanyStatus] = mapped_column(
        str_enum(CompanyStatus, "company_status"), default=CompanyStatus.PENDING, index=True
    )


class CompanyMember(IdMixin, TimestampMixin, Base):
    __tablename__ = "company_members"
    __table_args__ = (UniqueConstraint("company_id", "user_id", name="company_user"),)

    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("employer_companies.id", ondelete="CASCADE"), index=True
    )
    # MVP: пользователь состоит ровно в одной компании
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    role: Mapped[MemberRole] = mapped_column(str_enum(MemberRole, "member_role"))
