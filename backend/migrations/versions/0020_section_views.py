"""Отметки «раздел просмотрен» на сервере: индикаторы нового синхронны на всех устройствах

Revision ID: 0020
Revises: 0019
Create Date: 2026-10-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from migrations.rls import PRIVILEGED, UID, disable, enable, policy

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = ("section_views",)
# отметки видит и меняет только их владелец (и система)
_POLICIES = [
    policy("section_views_own", "section_views", "ALL", f"(user_id::text = {UID} OR {PRIVILEGED})")
]


def upgrade() -> None:
    op.create_table(
        "section_views",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("section", sa.String(length=32), nullable=False),
        sa.Column("seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_section_views_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "section", name=op.f("pk_section_views")),
    )
    enable(_TABLES, _POLICIES)


def downgrade() -> None:
    disable(_TABLES, _POLICIES)
    op.drop_table("section_views")
