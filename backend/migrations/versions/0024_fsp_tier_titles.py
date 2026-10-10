"""Названия уровней ФСП: уровень считается по числу призов и финалов, а не по статусу соревнования

Revision ID: 0024
Revises: 0023
Create Date: 2026-10-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.services.categorization import all_categories

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    for category in all_categories():
        bind.execute(
            sa.text("UPDATE categories SET title = :title WHERE slug = :slug"),
            {"title": category.title, "slug": category.slug},
        )


def downgrade() -> None:
    """Старые названия не восстанавливаются: правило уровня изменилось."""
