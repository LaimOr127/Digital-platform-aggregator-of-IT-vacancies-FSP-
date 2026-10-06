from sqlalchemy import JSON, Column, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin


class Category(IdMixin, Base):
    """Категория = дисциплина ФСП x уровень достижений. Создаётся правилами по мере появления."""

    __tablename__ = "categories"

    slug: Mapped[str] = mapped_column(String(64), unique=True)
    discipline: Mapped[str] = mapped_column(String(32), index=True)
    tier: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(255))


candidate_categories = Table(
    "candidate_categories",
    Base.metadata,
    Column("profile_id", ForeignKey("candidate_profiles.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "category_id", ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True, index=True
    ),
    Column("reasons", JSON, nullable=False, default=list),
)
