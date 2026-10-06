"""Статус поиска работы кандидата: активно ищу / рассматриваю / не ищу

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "candidate_profiles",
        sa.Column(
            "search_status",
            sa.Enum(
                "active",
                "open",
                "closed",
                name="search_status",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            server_default="open",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("candidate_profiles", "search_status")
